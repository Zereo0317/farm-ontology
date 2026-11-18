# Trust and risk — the evidence behind the promises

> Content pack for the pitch pages (consumer: the page builder, task-20).
> Language will be localized; the facts below are the checklist the pages
> must keep. Every number was taken from a repository artefact that anyone
> can open — sources are cited inline as file paths. Verified 2026-11-18
> against `main` @ `9fba9a8`.

The one-sentence version: **every claim ships with its evidence, and every
"no" ships with its name.** Reliability here is not a slogan; it is an
architecture of tests, ledgers, manifests and drills whose outputs are
files an auditor can read. Equally important: we publish our own unfixed
flaws with named owners. What follows is that case, then that honesty.

---

## 1. Why reliable — six proofs

### Proof 1 · The suite that greets every change

1,686 automated checks pass before anything merges (run verified on
`main` @ `9fba9a8`: `Ran 1686 tests … OK`). 14 additional checks exercise
the real upstream data portals and run only behind an explicit opt-in flag,
so the default CI loop is fully offline and never flaky-for-network-
reasons. Discipline on top of volume: every defect repaired this cycle
landed with a *producer test* — code that regenerates the bug and dies if
the fix regresses. The suite grew through three supervised rounds (QA
campaign → fixes → re-rehearsal) rather than accreting casually.
Source: `docs/final-verification-report.md`, `tests/`.

### Proof 2 · Fault injection we actually ran

On 2026-11-18 we deliberately knocked the legs out from under the staging
service and photographed the fall: minimum instances set to zero (guaranteeing
the next request boots a *cold, empty* container), a fresh observation
written through the public path, the command ledger shipped to durable
storage, and the container then recycled underneath all of it. Result of the
drill, from its own log (`perf/chaos-20261118T120905Z/drill.log`):

- first request after recycling (the cold hit): **3,218 ms** to first byte —
  slow, survivable, and now a *measured* number instead of a guess;
- subsequent warm hits: 432 / 1,356 / 2,284 ms;
- the observation written mid-drill was readable afterwards;
- the hash-chained command ledger survived storage round-trip: after
  restore, the chain **re-verified end-to-end** and the command showed its
  correct final state (`acknowledged`);
- drill verdict: `drill_ok: true`.

Honesty rider: the first attempt that morning *failed* its verdict
(`perf/chaos-20261118T120442Z`, cold start 5,743 ms, incomplete recycle) —
we kept the failing log. Systems that only photograph successful dress
rehearsals are theatre.

### Proof 3 · Durability with receipts, not vibes

Farm records ship nightly to versioned cloud-object storage. The export
job does not declare success on "attempted": it **reads the snapshot back
and compares the SHA-256 hash and the member list** before calling it done,
then appends one manifest row per snapshot (deduplicated, so re-runs are
safe). The first real run's manifest row carries the actual hash —
snapshot `record-snapshot-20261118T115029Z.tar.gz`, sha256
`d48604beba00…f44bfadda5e5be83`, 9 members, independently downloaded and
re-verified afterwards. Source: `deploy/nightly-export.md`.

### Proof 4 · Surveillance on three continents

The live service is probed continuously by uptime checks from **three
global checker regions** (asia-pacific, usa-iowa, europe) against the
health and weather endpoints, wired to email + webhook alerting. Alert
.lines also stand guard over hazard-feed watchers, hourly weather
freshness (target: never more than 20 minutes stale during waking hours),
and a three-strikes rule on scheduled ingest workers. Source:
`deploy/GCP_SETUP.md`, `docs/decision-infra-roadmap.md` §4.

### Proof 5 · The licence wall that fails closed

Money-moving features stay switched off until a *written, machine-readable
grant* exists — expiry demotes them automatically, with no human needing to
remember, and a forged grant reference dies on a registry fingerprint check.
This cycle's adversarial rehearsal proved the tetrad: forged → dies, valid
grant → alive, expired → dies, specimen (sample text) → dies. Policy
decisions themselves are recorded openly — the decision log's bottom line
literally reads: class C stays closed, financial use stays false, no
invented GPS metres. Source: `docs/decision-log.md`,
`reports/arb-rehearsal-REPORT.md`.

### Proof 6 · Point-in-time replay (the auditor's favourite)

Every recorded value carries the instant it was *true as of* (`factsAt` /
`associatedAt`), so any past analysis can be reconstructed exactly as it
looked *then* — not corrected backwards with hindsight. Demonstration from
the point-in-time test rig: querying the dataset before a USDA report
release returns 1 price subject; after the release, 5. Tomorrow's number
can never leak into yesterday's decision. Source:
`farm_ontology/markets/pit_dataset.py`, QA campaign report.

### The proof inside the criticism

Our load-test report's headline verdict against our own backend is
**"BREACHED"** — and we shipped it that way. It measured the real latency
distribution under burst load, named exactly which route owns the slow
tail, which previous fix improved what (median response time fell 43 %
after the CPU bump), and which decision now awaits its owner. We consider
that report our single most persuasive reliability artefact: the same
machinery that certifies the wins is incapable of flattering us. Source:
`perf/RESILIENCE-REPORT-postfix.md`.

Across the adversarial QA campaign this cycle: **30 of 30** attack lanes
and **45 of 45** gap-handling edges behaved as designed, **zero silent
wrong answers** were found — every one of the 27 defects surfaced either
crashed loudly, refused with a named gap, or was already caught by tests.
All were subsequently fixed with producer tests and the rehearsal re-run to
prove extinction. Source: `docs/final-verification-report.md`.

## 2. Performance posture — measured, both directions

Bar: p95 under 400 ms at steady state. Verdict at last measurement:
**not yet met globally**, and here is the full anatomy, from
`perf/RESILIENCE-REPORT-postfix.md`:

| Measurement | Before (1 vCPU) | After (2 vCPU) |
| --- | --- | --- |
| Requests | 12,280 | 8,374 (healthy-upstream window) |
| Error rate | 0.000 % | 0.179 % |
| Median (p50) | 499 ms | **286 ms** |
| p95 (all routes) | 2,496 ms | 6,925 ms * |
| Health endpoint p95 | 1,134 ms | **320 ms** |
| Ingest-status p95 (worst route) | 6,805 ms | 988 ms (best) ↔ 16,894 ms (heavy-tail variance) |

\* The global p95 is dominated by two named causes: run-to-run variance in
the compose-heavy ingest-status route (per-request storage listing — an
I/O and concurrency signature, not a CPU one), and occasional degradation
of the upstream weather provider itself, during which every request parks
at the outbound timeout (~20.4 s) while the system responds with honest
`gap` bodies rather than stale data dressed as fresh. The raw driver JSON
for both runs is committed (`perf/baseline-before-cpu2.json`,
`perf/after-cpu2.json`) so any successor can re-run the same bar.

## 3. Risk register — owned, not hidden

Severities are ours and current as of 2026-11-18; the register is reviewed
quarterly (governance doctrine §8). "Owner" is the accountable lane.

| # | Risk | Severity | Evidence it is real | Mitigation in place | Next lever | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | Tail latency breaches the 400 ms bar under load (p95) | **Medium-high** — customer-visible sluggishness at burst | Public "BREACHED" verdict in `perf/RESILIENCE-REPORT-postfix.md`; ingest-status swings 988 ↔ 16,894 ms between adjacent runs | CPU doubled (p50 −43 %); per-route visibility; upstream flaps degrade to honest `gap` responses, never fake data | Cache the compose-heavy route or adopt min-instances — cost/perf trade-off **deliberately reserved for the founder** | Founder + infra |
| R2 | Cultivar development parameters unverified against the Japanese national trial literature (NARO) | Medium — stage-date precision, grant-review optics | 11 `TODO-VERIFY` tags in `farm_ontology/agronomy/` (params locked in PDFs, `日作紀 2015/2025` lineage, 1.4–2.8-day error class) | Current profile calibrated on *published* variety anchors + recorded 2026 site climates; certification explicitly scoped as calibration-grade | Acquire/ingest the trial PDFs, re-fit, re-certify | Agronomy |
| R3 | No photoperiod term in the phenology model | Low — declared limitation, already quantified on the control site | Warm-climate season compression documented in model docstrings; Tsuruoka control site shows the effect and still graded 0 defects | Declared in code, spec, and every output that relies on it; cold-region farms (our beachhead) barely feel it | Add the term if warm-latitudes become a market | Agronomy |
| R4 | Calibration rests on a single season's recorded climate | Medium — multi-year drift unquantified | Fieldtest matrix is 2026 climates across 5 sites | Per-stage provenance lives with every threshold; registry bands expose vintage; mismatch bands published (+6.7…+16.8 % surplus, −14.3 % miss) | Re-fit each new season; diverge-and-alert when bands drift | Agronomy + field |
| R5 | The licence wall delays revenue-bearing finance features | Medium — schedule, not correctness | Every financial class fails closed until human signatures land (incorporation → Planet decision → Earth Engine registration → paid weather tier → quarterly cap sheet → kill-switch contract) | The wall is the product; gates cannot be talked past — they can only be *satisfied* | Execute the human cards, in order, each conferring its unlock | Founder + licences |
| R6 | Production serves from a single region | Medium — regional outage = outage | Cloud Run prod in `asia-east1` only; durability layer is region-redundant, serving layer is not | Nightly verified snapshots + manifests + restore path already proven by drill; uptime watched from 3 regions | Second serving region with warm records, documented RTO | Infra |
| R7 | Team bus factor: one founder, judgment concentrated | **Structural, high** if unaddressed | Solo-founder constraint recorded in the roadmap's own risk register | Nearly everything proceduralised: doctrine, decision log, shared task board, per-sprint audit trails; agents execute, humans dispose | Second human committer; documented handoff drills | Founder |
| R8 | Upstream weather-source flaps and discontinuities | Medium — observed live this cycle | During one measurement window every upstream call hit its ~20 s cap (`perf/RESILIENCE-REPORT-postfix.md` chronology) | Multi-source adapters (national + private + satellite-derived), staleness bounds, gap-bodies over invented values, recorded-header feeds that degrade gracefully | Widen source diversity; cache-last-good with explicit staleness stamps | Pipeline |

## 4. Claims a buyer can audit

For the pitch pages: every customer-facing reliability claim should be
paired with its evidence pointer, exactly as above. Two house principles
worth surfacing verbatim on any page:

1. **"Missing is stated."** When the system does not know — sensor absent,
   source degraded, parameter unverified — the response says so, names the
   gap, and proposes the remedy. It never guesses and never blurs a
   claim's strength to please.
2. **"Authority is human."** Recommendations are proposed by software, but
   every step that moves product, money, or machines carries a named human
   signature on a tamper-evident, replay-verifiable ledger — and the
   emergency stop is a signed human record too.
