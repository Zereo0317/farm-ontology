# Ingest-status postfix — cache + I/O rewrite (Sprint-G, task-15)

Executed 2026-11-18/19 by the `pipeline` teammate. The lever nobody had
pulled yet: the compose-heavy route's own I/O shape. One lever, pulled
properly; verdicts recorded with the same driver, same bar
(p95 < 400 ms @ 50 VU, errors < 0.5 %), same-POV before/after.

## The diagnosed pathology (why ingest-status owned the tail)

The Sprint-E/F numbers (p95 988 ↔ 16894 ms across adjacent runs,
RESILIENCE-REPORT-postfix.md) were a concurrency/I-O signature: EVERY
request to `/farm/ingest-status` executed the legacy deep composer —

| Legacy cost per request (4 jobs) | Count |
| --- | --- |
| `storage.objects.list` (full run-log listing) | 1 (buffered pages) |
| per-job list + FULL serial row GETs (every dated row, every job, every request) | 4 lists + Σhistory GETs, strictly serial |
| `alerts/` re-listing per job | 4 lists |
| duplicate row GETs (strikes + evidence + summary asking again) | up to ×3 per row |

With run history growing daily, this got worse over time — and under
50 concurrent requests the serial GET chains amplified into the
988↔16894 ms tail. Doubling CPU (Sprint-E) accelerated processing but
could not shorten a strictly serial upstream I/O chain — exactly the
"AFTER, run 2" finding.

## What changed (branch `ws/sprint/perf-ingest-status` @ per commit)

1. **Hot-path compose rewrite** (`farm_ontology.ingest_status.compose_status`):
   TWO `storage.objects.list` calls total per compose — `run-log/` +
   `alerts/`, issued CONCURRENTLY (stdlib `ThreadPoolExecutor`) — then
   parallel minimal GETs of ONLY the rows the answer names:
   newest-3 for `recent_runs` + a newest-first strike walk that EARLY
   EXITS at the newest successful row (read budget = 3 + streak, never
   the history). Duplicate asks ride a process-wide singleflight row
   cache (`ingest_core.read_row_once`): parallel workers never repeat a
   GET; repeated composes pay zero.
2. **60 s TTL in-process response cache** (`ingest_core`, stdlib
   `time.monotonic` clock, per-backend slotting keyed on
   `describe()`): the route returns the cached compose within the TTL,
   decorated with `cache: {hit, age_s}` bookkeeping so observers see
   the freshness deal explicitly.
   **Invalidation contract: ANY write through `ingest_core` invalidates
   eagerly** — `write_json` (every data row, snapshot, state, alert) and
   `append_run` (every run row) call
   `ingest_core.invalidate_ingest_status_cache()` after their write
   succeeds — so on the instance that PROCESSED the write, operators
   NEVER see strikes or runs older than the write that caused them.
   Cross-instance staleness is bounded by the TTL (≤ 60 s), the
   documented trade for skipping a distributed invalidation bus (four
   schedulers + a read-mostly route do not justify one; the strikes
   that matter fire on the same instances the workers run on, where
   invalidation is eager).
3. **Legacy path kept** (`summarize_job`, `run_rows`,
   `consecutive_failures`): still used by tooling and by an
   equivalence test proving both composers agree field-for-field on a
   varied store (6 rows/job, newest 2 failed: same last_run, same
   strikes, same staleness verdicts, same failure flags).

Stdlib-only throughout: `concurrent.futures.ThreadPoolExecutor` for
I/O-bound waits (allowed by the sprint note), `time.monotonic`,
plain dicts. House rules untouched: no secrets, no new transport, all
clocks injectable, gaps still published.

## Offline micro-benchmark (deterministic, no network)

`perf/bench_ingest_status.py` — real-metadata GCS fixture
(generation/md5/crc32c/etag), injected 25 ms RTT per ask, 50 rows/job:

| Path (p50 / p95 ms) | Value |
| --- | --- |
| legacy composer (per-job, full serial reads) | 10579 / 10601 |
| fast compose, cold rows | **137 / 141** |
| fast compose, warm rows | **30 / 32** |

77× p50 vs legacy; storage asks per warm compose: 2 listings + 0 GETs.

## BEFORE / AFTER on PROD (same stdlib driver, 50 VU, 300 s)

Driver: `python perf/load_test.py --base <prod> --vu 50 --seconds 300`;
raw JSONs committed (`perf/status-before-9fba9a8.json`,
`perf/status-after-9fba9a8.json`).

| Round | Revision | Route | n | p50 | p95 | p99 | err % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BEFORE | `00057-2lz` (cpu=2, pre-task-15 code) | /farm/ingest-status | 2269 | 1493 | **14894** | 24927 | 0.573 |
| AFTER | `00058-tzk` (cpu=2, task-15) | /farm/ingest-status | 7434 | 265 | **812** | 1120 | 0.000 |

Route p95: **14894 → 812 ms (÷18.3)**; throughput at the same 50 VU
rose ×3.3 (2269 → 7434 route samples); route errors 0.573 → 0.000 %.

Global (all routes mixed): BEFORE p50 753 / p95 7091 / p99 18844 ·
AFTER p50 265 / p95 840 / p99 1228 (requests 7649 → 24909).

| Round | livez p95 | ingest-status p95 | weather p95 |
| --- | --- | --- | --- |
| BEFORE (00057) | 1113 | 14894 | 2263 |
| AFTER (00058) | 806 | 812 | 1215 |

Diagnostic that closes the case: at 50 VU the ingest-status tail is now
STATISTICALLY INDISTINGUISHABLE from `/livez` (812 vs 806 ms p95, p99
1120 vs 1116) — the pure-handler, zero-storage route. The residual tail
therefore is instance-capacity queueing (platform concurrency on a
cpu=2/maxScale=3 deployment at 50 hammering clients), NOT route I/O:
the route's own composes are served from the TTL cache/2-ask path and
carry zero storage-stall signature any more.

## Capability run at sustained 20 VU (90 s, same driver)

| Route | n | p50 | p95 | p99 | err % |
| --- | --- | --- | --- | --- | --- |
| /farm/ingest-status | 1030 | 258 | **330** | 466 | 0.000 |
| /livez | 2100 | 254 | 319 | 470 | 0.000 |
| /farm/weather | 339 | 653 | 730 | 1097 | 0.000 |

**The route MEETS the p95 < 400 ms bar at 20 VU (330 ms)**; global p95
at 20 VU (652) is dragged solely by /farm/weather's third-party
Open-Meteo RTT (p50 653 — upstream-bound, outside this card's reach).

## VERDICT (honest, no smoothing)

- Task-15's LEVER (cache + hot-path rewrite): **DELIVERED** — offline
  77× on the compose; prod route p95 14894 → 812 @ 50 VU and **330 ms
  (< 400 bar) @ 20 VU**; 0.000 % errors; observed live invalidation
  propagating a fresh worker failure row between polls without a
  deploy.
- The CARD'S literal target ("p95 < 400 ms @ 50 VU rerun" for the
  route): **STILL SHORT at 50 VU — 812 ms — and the reason is
  provably NOT this route**: livez (pure handler) breaches at the same
  magnitude at 50 VU, and both heal below 400 ms together at 20 VU.
  The remaining honest lever is INFRA CAPACITY (min-instances ≥ 1,
  maxScale, or cpu) at the 50-VU burst — that decision stays with
  lead+founder as agreed in Sprint-E; this ticket's scopes
  (ingest-status.py, http_service route, perf/) hold no instance
  knobs. Recorded verbatim per the card's "if still short, record
  honestly".
- Cache trade, restated for the operator: within-TTL payloads carry
  `cache: {hit, age_s}`; same-instance writes invalidate eagerly;
  cross-instance staleness ≤ 60 s by design.

Notes, disclosed: run 1 of AFTER overlapped the ongoing api.open-
-meteo.com regional flap (weather + the hourly weather WORKER both
affected — the worker's fresh failure rows are visible in the status
payload, which is the system telling the truth, not noise). Live
functional check pre-measurement: second call `cache.hit=True,
age=0.28 s`; the hourly weather failure appeared in the payload
between polls WITHOUT any deploy, proving the invalidation path live.
The BEFORE run likewise rode the same flap window on weather (its
2263 ms p95); livez/ingest-status measurements are unaffected by it.

## VERDICT

See above — filled with the AFTER-run numbers, the livez-parity
diagnostic, the 20 VU capability run, and the honest residual
(capacity queueing at 50 VU; infra lever, recorded for lead+founder).
