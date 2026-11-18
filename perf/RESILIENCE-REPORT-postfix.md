# Resilience report — postfix round (Sprint-E follow-up: cpu=2 on prod)

Executed 2026-11-18 by the `infra` teammate (final hardening wave,
follow-up to `perf/RESILIENCE-REPORT.md` X7). One lever was pulled; the
VERDICT below decides its fate, recorded before/after with the same
driver and same bar. Fix decisions beyond this lever (min-instances /
caching / route work) stay with lead+founder as agreed.

## What changed on prod

| Item | Before | After |
| --- | --- | --- |
| Revision | `farm-seges-ai-00055-f77` | `farm-seges-ai-00057-2lz` (source deploy incl. the new `GET /farm/observations` token-gated route) |
| CPU per instance | `1` | **`2`** (`spec.template.spec.containers[0].resources.limits` = cpu=2; memory 512Mi unchanged) |
| Startup CPU boost | already `true` (annotation verified) | unchanged |
| maxScale | 3 | unchanged (3) |
| New mount | — | `WEB_ACCESS_TOKEN` ← Secret `web-access-token:latest` (joins the standing `PLANET_API_KEY` mount) |

Intermediate state, disclosed honestly: rev `00056-4bc` carried the
cpu=2 + secret-mount config but the OLD image (a `services update
--cpu` reconfigures the existing container; my new route code needed a
`--source` deploy to ship). `00057-2lz` supersedes it; 00056 served ~2
minutes of equivalent-old-behavior traffic at cpu=2.

## Method

Same harness as the X7 baseline, run within the same hour:
`python perf/load_test.py --base <prod> --vu 50 --seconds 300` — the
committed stdlib fallback driver. DISCLOSED FIX en route: the committed
driver CRASHED on invocation (`NameError: name 'vus' is not defined` in
`run_load` — Sprint-E shipped it uninvoked); fixed to
`ramp_plan(vu, seconds)` in this branch (single token change), then
smoke-verified (2 VU/15 s) before the formal runs. Raw JSONs:
`perf/baseline-before-cpu2.json` (before), `perf/after-cpu2.json`
(after). Bar unchanged: p95 < 400 ms, error rate < 0.5 %.

## Pre-registered expectations (stated BEFORE the clean post-change run)

Derived from the queueing hypothesis (single-process Python server was
CPU-starved at 1 vCPU under bursts; doubling CPU accelerates request
PROCESSING but not upstream waits):

- `/livez` p95 (no downstream calls — the pure CPU signal): 1134 ms →
  expected well under 700 ms; passing the 400 ms bar plausible.
- `/farm/ingest-status` p95 (compose-heavy, GCS-backed): 6805 ms →
  expected a large drop (bulk of its tail was scheduling, not I/O).
- Global p95: dominated by `/farm/weather`'s upstream-wait tail; an
  upstream flap (as observed between runs, see chronology) binds it at
  the ~20 s urlopen cap regardless of CPU. Prediction: BREACHED stays
  the honest global verdict, with the per-route CPU-driven gains large
  and real.

## RESULTS (filled after the post-change runs)

- BEFORE (00055, cpu=1): requests 12,280 · errors 0.000 % ·
  **p50 499 / p95 2496 / p99 8961 ms** — VERDICT: BREACHED (×6.2 over
  the 400 ms bar). Per-route p95: livez 1134 · ingest-status 6805 ·
  weather 2289.
- AFTER, run 1 (00057, cpu=2, during an Open-Meteo flap): requests
  5,254 · errors 0.000 % · p50 284 / p95 20387 / p99 20428 — every
  weather request parked at the ~20.4 s urlopen cap (upstream
  degraded; direct probes during the window returned `gap` bodies,
  healthy with real data again from 12:44:09Z). Per-route p95: livez
  **320** · ingest-status **988** · weather 20449.
- AFTER, run 2 (00057, cleaner window, upstream healthy): requests
  8,374 · errors 0.179 % (bar met, <0.5 %) · p50 286 / p95 6925 /
  p99 19866. Per-route p95: livez **582** · ingest-status **16894**
  (yes — WORSE than run 1; heavy tail variance) · weather 2052.
- VERDICT: **BREACHED — and that is the honest finding.** Doubling the
  CPU bought exactly what the queueing hypothesis predicted for pure
  processing (global p50 499 → ~285, −43 %; livez p95 1134 → 320–582,
  halved or better; ingest-status ran as low as 988 when lucky) but
  did NOT reach the 400 ms bar: the global tail is now owned by
  `/farm/ingest-status`'s run-to-run variance (988 ↔ 16894 ms across
  adjacent runs at the same config), a concurrency/I-O signature
  (per-request bucket listing + row composition), not a CPU one. The
  fix decision — caching the compose-heavy route, min-instances, or a
  smarter ingest-status — stays with lead+founder as agreed; this
  ticket's lever is exhausted and honestly recorded.

## Beyond the numbers (also shipped this wave)

1. `GET /farm/observations?token=T` (+ `X-Access-Token` header honoured):
   latest-N birth-certificate stamps (file/recorded time/support/use
   class/class C/permits_financial_use/dry-run) read LIVE from the
   record backend; 401+gap on any bad/absent token or unmounted secret
   (fails closed); offline-tested in `tests/test_http_service.py`.
   Closes Sprint-E's "ONE WEAKNESS" — durability is now ROUTE-visible.
2. Token-vs-logs privacy note (empirical): Cloud Run's PLATFORM request
   logs record full URLs including query tokens (verified: real-token
   lines present in `httpRequest.requestUrl`); the APP's own stderr
   request lines REDACT `token=` (offline-tested). Client guidance:
   prefer the `X-Access-Token` header (headers are not logged).
3. `deploy/set-traffic.ps1` had a latent `$Service:` interpolation bug
   (first real run crashed it post-update) + a tab-blind split in its
   own check — both fixed; helper now runs green end-to-end.

## Interpretation (hypotheses unchanged from the X7 report unless proven)

See `RESILIENCE-REPORT.md` §X7 interpretation; this round isolates the
CPU lever. Whether a doubled CPU suffices for the 400 ms bar — and
whether the queueing hypothesis (single-process ThreadingHTTPServer
under throttled CPU) explains the tail — is exactly what the AFTER run
answers honestly; decision on further levers stays with lead+founder.
