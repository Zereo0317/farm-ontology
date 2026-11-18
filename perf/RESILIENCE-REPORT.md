# Resilience proofs — Sprint-E (task-12): load test X7 + ColdStartKill chaos drill X5

Executed 2026-11-18 (JST evening) by the `markets` teammate wearing the
resilience hat. Everything here is repeatable with ONE command per proof;
raw console outputs and RESULT JSONs ship beside this runbook.

Services (all verified live during the run):

| Item | Value |
| --- | --- |
| Prod (load-test target) | `farm-seges-ai` — https://farm-seges-ai-451400509859.asia-east1.run.app |
| Staging (chaos-drill target) | `farm-seges-ai-staging` — https://farm-seges-ai-staging-kadpjlgt4q-de.a.run.app |
| Record bucket | `gs://farm-seges-ai-records` (versioned, GCS-backed record store) |
| Drill job (sanctioned writer) | Cloud Run job `farm-observation-drill` |
| gcloud identity | `segescloud@gmail.com` @ `seges-ai` (checked by both scripts' preflight) |

---

## X7 — k6 load test, 50 VU ramp / 5 min, prod READ routes

One command: `perf\run-load-test.ps1` (auto-detects k6; falls back to
`perf\load_test.py`, a stdlib-threads driver emitting the same summary).
This run used **k6 v2.4.0** (GitHub release zip; winget has no k6 package
on this box — the fallback driver exists exactly for that case and is
offline-tested).

Routes walked per iteration with weights 6:3:1 (`/livez` :
`/farm/ingest-status` : `/farm/weather`) — the third-party-calling route
stays the rarest on purpose. Ramp: 1 m to 25 VU, 3.5 m at 50 VU, 30 s drain.

### THE HONEST BAR — recorded verbatim: **BREACHED**

(Two full runs, same verdict; the FINAL run's numbers are canonical
below — `perf/verdict-k6.json` + `perf/k6-metrics-full.json`; run-1's
dump kept as `k6-metrics-full-run1.json`.)

p50 = **665 ms** · p95 = **1832 ms** (bar: <400 ms — MISSED ×4.6) ·
p99 = n/a (percentile not retained in summary export) ·
error rate = **0.000%** (bar <0.5% — MET) · 9,759 requests, 0 failed
checks. k6 exit 99 (thresholds crossed) = the honest-breach signal, by design.

| Route | p50 | p95 | p99 |
| --- | --- | --- | --- |
| /livez | 181 ms | 1013 ms | — |
| /farm/ingest-status | 925 ms | 3783 ms | — |
| /farm/weather | 596 ms | 1504 ms | — |

Console excerpt (verbatim, final run):

```
HONEST BAR SUMMARY (parsed by perf/run-load-test.ps1)
  base_url: https://farm-seges-ai-451400509859.asia-east1.run.app
  p50/p95/p99 (ms): 665 / 1832 / null
  requests: 9759  checks: 9759 passed / 0 failed
  error rate: 0%
  bar p95<400ms: false  bar errors<0.5%: true
  VERDICT: BREACHED (recorded verbatim below)
  livez: p50=181 p95=1013 p99=null
  ingest-status: p50=925 p95=3783 p99=null
  farm-weather: p50=596 p95=1504 p99=null
```

Run-1 corroborates the shape (p50 1064 / p95 2512, same 0% errors over
6,912 requests) — the breach is stable, not a fluke: p50 sits NEAR the
bar while p95 explodes 3-6× over p50, and even `/livez` (no downstream
calls) triples its p95 under load.

**Interpretation (hypotheses, marked as such — follow-up work, not fact):**
the record's own stdlib ThreadingHTTPServer is single-process Python;
under a Cloud Run default single-instance/CPU-throttled posture, request
concurrency queues. The 3-VU smoke already tripled livez's p95, so the
prime suspects are (1) request-based CPU allocation idling between
requests, (2) conservative maxScale on prod, (3) the weather/status
routes' per-request upstream calls inflating tails (consistent with
ingest-status being the slowest route — it composes the run-log).
Fixes belong to a sprint that OWNS the deployment (infra): cpu-boost /
min-instances-maxScale tuning / caching compose-heavy routes. Not
dispatched from here; recorded as the follow-up.

---

## X5 — ColdStartKill chaos drill (STAGING ONLY, prod untouched)

One command: `perf\chaos-drill.ps1`. Two runs are preserved:
`perf/chaos-20261118T120442Z` (run 1 — instructive partial failure) and
`perf/chaos-20261118T120905Z` (run 2 — fully green after a script fix;
the FIX was to the drill script itself, never to the shipped packages).

### Run-2 verdict (verbatim from RESULTS.json)

```json
{"drill_ok":true,"min_instances_zero":true,"observation_written":true,
 "observation_readable":true,"ledger_uploaded":true,"ledger_ack_appended":true,
 "ledger_restored_chain_ok":true,
 "restored_snapshot":{"739eb4e818921e21134494811cb86853":"acknowledged"},
 "cold_start_measured":[3218.0,432.0,1356.0,2284.0],
 "cold_start_note":"hit1 = cold boot of the fresh minScale-0 revision; hits 2-4 warm",
 "revision_recycled":"farm-seges-ai-staging-00112-7j6"}
```

Timestamped step trail (full log: `chaos-20261118T120905Z/drill.log`):

| UTC time | step | result |
| --- | --- | --- |
| 12:09:05 | artifact dir | `perf/chaos-20261118T120905Z` |
| 12:09:08 | preflight | account/project OK |
| 12:09:11 | snapshot | staging on rev `00109-lhs`, 100% traffic, maxScale 3 |
| 12:09:24 | min-instances=0 | `gcloud run services update … --min-instances 0` OK |
| 12:09:25 | ledger built | `CommandLedger`: propose(service)→approve(human≠proposer)→dispatch(job receipt) — command_id `739eb4e8…`, 3 records |
| 12:09:34 | ledger → GCS | `gs://farm-seges-ai-records/chaos-drills/ledger-20261118T120905Z.jsonl` |
| 12:09:54 | observation drill job | exit 0 — one dry-run observation written through the GCS backend |
| 12:09:57 | ledger acknowledged | 4th record appended, state `acknowledged` |
| 12:10:11 | final ledger → GCS | overwrite-updated object (versioned bucket) |
| 12:10:23 | **recycle** | additive env-bump → NEW revision `farm-seges-ai-staging-00112-7j6`, ready in 5 s |
| 12:10:36 | cold hit | **3218 ms** TTFB on /livez (the empty revision's first boot) |
| 12:10:38–46 | warm hits | 432 / 1356 / 2284 ms |
| 12:10:49 | readability (a) | staging `/farm/ingest-status` HTTP 200 post-recycle; latest obs object `gs://…/field-notes/obs-20261118T120948Z.json` reads back **with its stamps** (`permits_financial_use` present) |
| 12:11:05 | ledger survival (b) | pulled `chaos-drills/ledger-….jsonl` from the GCS layout into `%TEMP%\farm-restore-…` → `CommandLedger.from_path` → `verify_chain()` **ok, 4 records, problems []**, snapshot `acknowledged` |

Console excerpt (run 2, verbatim — the money line is the cold/warm pair):

```
[2026-11-18T12:10:23.990Z][recycle] env-bump ok=True new-revision=farm-seges-ai-staging-00112-7j6
[2026-11-18T12:10:36.462Z][cold-hit] hit=1 ttfb_ms=3218 status=200
[2026-11-18T12:10:38.913Z][cold-hit] hit=2 ttfb_ms=432 status=200
[2026-11-18T12:10:42.280Z][cold-hit] hit=3 ttfb_ms=1356 status=200
[2026-11-18T12:10:46.573Z][cold-hit] hit=4 ttfb_ms=2284 status=200
[2026-11-18T12:11:05.809Z][ledger-verify] ok=True :: {"verify_ok": true, "records": 4, "problems": [], "snapshot": {"739eb4e818921e21134494811cb86853": "acknowledged"}}
```

### Run-1 lessons (kept because the failure IS evidence)

Run 1 (`chaos-20261118T120442Z`) executed every infra step correctly but
died at the ledger-ack step: the drill generated an inline python `-c`
program with a WINDOWS BACKSLASH PATH interpolated into a non-raw string
— `unicodeescape` SyntaxError. Honest consequences recorded there:
the ledger reached GCS in `dispatched` state (never falsely claimed
`acknowledged`), and run 2 completed the lifecycle after switching the
path to `sys.argv`. Verify-hash note: the two runs minted the SAME
command_id (`739eb4e8…`) because ids are CONTENT-derived (timestamps
excluded) — cross-ledger this is by-design replay identity, and the drill
now documents it.

### THE ONE WEAKNESS (the deliverable's named takeaway)

**The HTTP service has no observations/read route: after killing the
pod, "the record is still readable" could only be PROVEN at the storage
layer (`gcloud storage cat` of the obs object) and via the drill job's
own round-trip — never through the service itself.** Durability exists
(GCS-backed, versioned, chain-verifiable) but is currently
route-invisible; until an authenticated `/farm/observations` read path
exists, the service cannot demonstrate its own durability, and neither
can any operator.

Secondary observations recorded in the report above: the p95 honest-bar
breach under concurrency (with hypotheses), the staging env-var editing
pitfall (reconfirmed run 1→2: unquoted `--update-env-vars` compositions
must stay additive, per the 00085 note in `deploy/staging-cutover.md`),
and cold-start penalty ≈ 2.8–5.7 s first-byte on a minScale-0 revision.

---

## Repeatability (one command each)

```powershell
# X7 load test (k6 auto / stdlib fallback), honest-bar verdict printed:
.\perf\run-load-test.ps1                 # prod, 50 VU / 5 min
.\perf\run-load-test.ps1 -Quick          # 60 s sanity pass

# X5 chaos drill (staging ONLY; prod never mutated):
.\perf\chaos-drill.ps1
```

Artifacts: `perf/load-test.js`, `perf/load_test.py` (+ its offline tests),
`perf/run-load-test.ps1`, `perf/chaos-drill.ps1`, `perf/verdict-k6.json`
(final-run verdict), `perf/k6-metrics-full.json` (same run's native
dump), `perf/k6-metrics-full-run1.json` + `perf/k6-metrics-smoke.json`
(corroboration), `perf/chaos-20261118T120442Z/`,
`perf/chaos-20261118T120905Z/`, console logs.
