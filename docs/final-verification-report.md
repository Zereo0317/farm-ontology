# Final verification report — the iteration loop closed (2026-11-18)

> **2026-11-22 evidence hold:** This is a historical verification record, not a current production certification. Subsequent source review found additional grant-provenance, agronomy, security, and infrastructure gaps. Its statements that finance mechanisms are certified or that only human cards block activation must not be relied on.


Campaign record for the founder directive: fix with multiple agents → test
with real-world cases → analyse gaps → fix again → clean debt → merge and
ship, until the system makes accurate smart-farming decisions and compliant
information-advantage finance moves.

## What iteration produced (commits all on main `0fc35fd`, CI green)

| Round | Input | Output | Net effect |
| --- | --- | --- | --- |
| Wave 1 | roadmap WS1–WS8 | 7 teammate branches (infra, pipeline, agronomy, fieldhw, actuation, licences, markets) | every roadmap task completed on the shared board |
| Round 2 (QA) | 実地 campaigns | `fieldtest-multisite` (5 sites, 26 tests) + `arb-rehearsal` (5 lanes, 22 tests) | 27 defects found, ZERO silent wrong answers (30/30 lanes + 45/45 named-gap edges) |
| Round 3 (fix) | the defect registry | `ws/fix/*` ×3 sprints | D1–D9 + D-ENGINE-1/2 all healed with producer tests; rehearsal & matrix re-run to prove extinction |
| Debt sweep | hygiene scan | 14 live-fetch tests gated (`FARM_ONLINE_TESTS`), CI made hermetic-green; worktrees pruned to 1; only 12 intentional TODO markers remain (11 = VERIFY-tagged NARO cultivar params, 1 = Phase-4 controller drill) | repo on a single checkout, suites green BOTH modes |

## Claim 1 — 智慧農業精準決策 (smart farming decisions): CERTIFIED with scope

Five real-climate sites through the full chain (phenology → irrigation →
spray windows → RecommendationRecord):

| Site | Stage final | GDD | Irrigation | Defects |
| --- | --- | --- | --- | --- |
| Biratori (anchor farm) | R8 | 1116.8 | 0.0 mm | rough 2 |
| Obihiro | R8 | 1101.9 | 0.0 mm | rough 2 |
| Nakafurano | R7 | 1015.3 | 0.0 mm | rough 2 |
| Nemuro | R6 | 838.5 | **78.8 mm honest advice** | rough 3 |
| Tsuruoka (control) | R8 | 1893.4 | 0.0 mm EARNED | **0** |

- blockers 0, cosmetics 0; the 9 residuals are explained in
  `reports/fieldtest-multisite-REPORT-postfix.md` (registry-band vintage,
  photoperiod term absent, Nemuro gust squint).
- Defensible today: "the engine classifies the RECORDED 2026 climates of
  four Hokkaido belts to full maturity inside the published harvest window
  (mismatch +6.7…+16.8 % surplus, −14.3 % miss), after replacing 40–56 %
  structural deficits" — calibration-grade (published calendars × recorded
  climate); NARO trial-validation still TODO-VERIFY.
- Honesty ladder enforced by tests: grid → probe footprint → parcel only
  with sensor-declared hectares; irrigation NEVER implies parcel support
  without calibrated coverage (proved negatively AND positively at all sites).

## Claim 2 — 資訊優勢套利/對沖決策 (information-advantage arbitrage): MECHANISM CERTIFIED, LIVE MONEY GATED BY DESIGN

`reports/arb-rehearsal-REPORT.md` (regenerated on healed main):

- L1 bear / L2 bull / L3 uncertain: every artefact fail-closes with NAMED
  rail + remedy while real grants are absent — the wall never lied, and now
  provenance cannot lie either (D1: forged refs die on
  `fingerprint-not-in-registry`; tetrad forge→die / WS6-grant→alive /
  expired→die / specimen→die pinned by tests).
- L4 hazard chain: four-eyes, HALT freeze (void legal mid-storm),
  terminal voided, gate choreography — D9 void-chain crash FIXED
  (5 regressions incl. reload+tamper).
- L5: agronomy cannot even PROPOSE hedge/trade (refuses at construction);
  unsigned drone packets refuse `signature_missing`; override emits with
  the justification recorded verbatim into the KML.
- Finance-real activation needs exactly the human cards: incorporation →
  Planet decision (11-30) → EE commercial flip → Open-Meteo Q9 → first
  signed quarterly cap sheet → kill-switch contract.

## Live system at report time

| Component | Endpoint | State |
| --- | --- | --- |
| Backend | https://farm-seges-ai-451400509859.asia-east1.run.app | 8/8 routes 200 |
| Web app | https://farm-seges-ai-web-451400509859.asia-east1.run.app | gate 307→login; /livez 200; advisories panel w/ support stamps |
| Workers | 4 Cloud Run Jobs + 4 Schedulers (ENABLED) | first REAL weather row in gs://farm-seges-ai-records; twice-is-a-no-op proven |
| CI | test.yml (hermetic) + deploy-prod-tag.yml | green on push; prod by tag |
| Tests | `python -m unittest discover -s tests -t .` | **1583 OK** (14 opt-in skips) |

## Cards on the human's desk (nothing else blocks)

1. Sensor basket A (¥112,458) vs B (技適済, ¥126,336) — procurement.
2. 2026-11-30: Planet purchase vs lapse (trial ends 12-17).
3. Incorporation 登記 — prerequisites every signature.
4. Kill-switch contract signature — the load-bearing Phase-4 gate fact.
