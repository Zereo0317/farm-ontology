# Field-test multi-site REPORT — WS3 agronomy engine vs five real 2026 climates

Campaign: `field-multisite` · Agent: `fieldhw` (QA hat) · Run date:
**2026-11-18** (fixtures captured 2026-11-18 ~04:11–04:12 UTC, see
`fixtures/fieldtest/site-*/year2026.json`, all `captured_live: true`).
Branch: `ws/test/field-multisite`. Raw machine result:
`reports/fieldtest-matrix-raw.json`.

**Mission framing (founder directive): 実地試験 across multiple sites
until the engine breaks.** This report is a FINDER's ledger — nothing in
the engine was altered, no assertion weakened, no config overridden. The
harness (`farm_ontology/fieldtest/`) collects; the engine owners dispose.

---

## 1. Executive verdicts

| Site | Verdict | Final stage | GDD (sow→drive-end) | GDD by Oct 15 | Irrigation net / advise | Blocker | Rough | Cosmetic |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| biratori-hidaka | **CONTRADICTS SANITY** | R3 (stalled) | 1116.8 | 1109.7 | 0.0 mm / no | 0 | 4 | 0 |
| obihiro-tokachi | **CONTRADICTS SANITY** | R3 (stalled) | 1101.9 | 1094.0 | 60.4 mm / yes | 0 | 4 | 0 |
| nakafurano-kamikawa | **CONTRADICTS SANITY** | R1 (stalled) | 1015.3 | 1013.6 | 0.0 mm / no | 0 | 4 | 0 |
| nemuro-hanasaki | **CONTRADICTS SANITY + wind squint** | R1 (stalled) | 838.5 | 813.7 | 139.5 mm / yes | 0 | 5 | 0 |
| tsuruoka-shonai (control) | arithmetically clean, **carries the Kcb design flaw** | R7 | 1893.4 | 1823.2 | 0.0 mm / no | 0 | 1 | 0 |
| **TOTAL** | | | | | | **0** | **18** | **0** |

Headline: **0 blockers** — the engine never crashed, never emitted an
unnamed failure, and its honesty plumbing held everywhere (§5) — but the
**phenology model contradicts Hokkaido agronomic reality at 4/4 Hokkaido
sites** (§3, Q1): with REAL 2026 archive weather, every Hokkaido field
stalls at R1–R3 instead of reaching R7/R8. That is a defect ledger an
operator cannot dismiss, regardless of the zero-blocker cleanliness.

## 2. Consolidated defect ledger (18 rough, grouped by rule)

| Rule (verbatim id) | Stage | Count | Sites | One-line gist |
| --- | --- | --- | --- | --- |
| `gdd-band-breach` | sanity | 4 | all Hokkaido | season GDD below even the LENIENT lower sanity band |
| `r7-not-reached-by-oct15` | sanity | 4 | all Hokkaido | 813–1110 GDD banked vs 1850 needed for R7 |
| `stage-below-r6-at-drive-end` | sanity | 4 | all Hokkaido | season never reached full seed (R1/R3 finals) |
| `kcb-static-across-season` | irrigation | 5 | **all five** | Kcb frozen at the final-stage value for the whole trace |
| `nemuro-wind-suspicious` | sanity | 1 | Nemuro | 11.88 m/s peak winds yet 6 GO windows across 6 scans |
| transport/fixture defects | fixture | 0 | — | all five captures succeeded first-try; the transport→defect path is proven in the offline suite instead |

Severity rubric used: `blocker` = crash / unnamed failure / honesty-rule
violation / gate leak; `rough` = designed engine failure surfacing where
it should not, or engine-vs-region disagreement; `cosmetic` = metadata
noise. No test or engine change rode on these verdicts.

## 3. The sharp questions, answered with receipts

### Q1 — Does phenology hit R7/R8 late-Sep–Oct for Hokkaido?

**NO, uniformly — this is the campaign's central finding.** Banked GDD by
2026-10-15: Biratori 1109.7, Obihiro 1094.0, Nakafurano 1013.6, Nemuro
813.7 — against the engine's R7 threshold of **1850**. Shortfalls of
40–56 %. The control (Tsuruoka) reached R7 exactly as warm-climate norms
predict (1823.2 by Oct 15, 1893.4 final), which isolates the problem to
the engine's stage table × Hokkaido's climate, not to GDD arithmetic in
general.

Mechanism hypothesis (both stated, neither lab-grown):
1. **`GDD_THRESHOLDS` over-demands for Hokkaido varieties.** The engine
   ships the table as CONFIG with `VERIFY [SOY-GDD-TABLE]` ("rounded
   public-guide approximation … recalibrate against local variety
   trials"). The values (R7 1850 / R8 2100, base 10 °C) resemble
   continental North-American extension curves; Hokkaido-bred
   short-season varieties (Yukihomare, Ryuho class) are engineered
   precisely to mature inside Hokkaido's ~1000–1400 GDD (base 10) budget.
   Robustness check performed: advancing sowing to the window's earliest
   legal day (May 10) adds only ~80 GDD — nowhere near closing a
   ~750-GDD gap — so the contradiction is NOT an artefact of the sow
   default.
2. Base-10 accumulation on maritime cool-night regimes may itself
   undercount Hokkaido development (alternative: a lower/variety-specific
   base). Either way the FIX is the engine's own prescribed one —
   recalibrate the CONFIG table against local trial data — and the matrix
   quantifies how far off the v0 numbers are.

Consequence for the product: irrigation's Kcb curve and any stage-gated
advisory inherit the same table; until recalibrated, phenology-stamped
outputs for Hokkaido carry a KNOWN, QUANTIFIED regional bias.

### Q2 — Does irrigation EVER imply parcel support without sensor coverage?

**No — verified both negatively and positively at every site.** Without
sensor rows, coverage level stayed `none` at 5/5 sites, support extras
carried no `probe-support`/`parcel-support` text, and the
`support-ladder-climb` / `parcel-claim-without-sensor` /
`probe-claim-without-sensor` probes all stayed silent. Positively: the
four sensor-gate edges behaved per contract at every site — uncertified
row refused, expired-cert row refused, live-cert point probe adopted as
`probe-footprint`, sensor-declared-area row adopted as `parcel-support`
(hectares echoed from the sensor, never computed). Feeding a certified
parcel-linked row through the adviser surfaced the claim in extras while
the mm number stayed bit-identical (the `sensor-altered-balance` defect
never fired) — v0's promise "sensors annotate, never mutate the balance"
held.

### Q3 — Are spray windows sane for Nemuro winds?

Mostly yes, with one flagged squint. Across six midday-JST 48 h scans
(Jun 15 → Oct 05): Nemuro slice winds peaked at 6.27 / **11.88** /
5.97 / 4.95 / 10.42 / 9.96 m/s. NO-GO+CAUTION dominate (July 15: all
hours unviable, zero windows; the 11.88 m/s storm day produced no GO).
Six GO windows survived the season — concentrated in the Aug 15 / Sep–Oct
scans where hulls of calm sat between gusts. The harness flagged
`nemuro-wind-suspicious` (≥8 m/s peaks AND ≥6 GOs pattern) for human
review: coastal Nemuro DOES gift short sprayable lulls, so the pattern is
plausible — but the lulls are precious and the report recommends the
adviser eventually add gust-sensitivity caveats (hourly 10 m wind is not
a boom-height gust). No rule misfire occurred: every verdict carried its
rule evidence.

### Q4 — Do the edges fire NAMED gaps (missing ETo etc.)?

**Yes — 9/9 edge probes fired with their own names at every site** (45/45
across the matrix, zero `edge-name-mismatch` / `edge-exception` /
`edge-missed` defects): `missing-sowing-anchor`, `grid-resolution-mixed`,
`regressive-dates`, `malformed-row` (the missing-ETo probe, naming
`row[0].eto_mm`), `hour-sequence-hole`, `stale-hours`,
`refusal:refused-use` (hedge-kind proposal), `no-inputs`,
`refusal:born-expired`. During development the harness itself was caught
by this discipline once — my first slice-builder overfed context hours
and the engine answered `stale-hours` with perfect manners (fixed in the
harness, NOT the engine; the incident is retained in git history as
evidence the failure surface tells the truth).

## 4. Nastiest three defects, verbatim

1. **The design artefact that visits every site (both directions):**

   > `[rough/irrigation] kcb-static-across-season: Kcb held constant at
   > 1.133 across 165 daily rows while the season-spanning curve should
   > have traversed several anchors (final stage R3); vegetative weeks
   > tariffed at reproductive water use — v0 artefact, biases ETc and the
   > deficit upward`

   — Biratori. The v0 balance drives Kcb from the SEASON-FINAL
   phenology reading for every day of the trace. Hokkaido sites
   (final stage R3) billed the whole vegetative season at pod-fill water
   use (Kcb ≈ 1.10–1.14), inflating ETc; the CONTROL (final stage R7)
   ran the entire warm season at 0.5479 — senescence-rate water use —
   which flatters its 0.0 mm verdict. One artefact, opposite biases, and
   it touches every irrigation recommendation the engine has ever
   drafted for a multi-month season.

2. **The sanity contradiction that spans all of Hokkaido:**

   > `[rough/sanity] r7-not-reached-by-oct15: cumulative GDD by 2026-10-15
   > is 813.7 (R7 threshold 1850); Hokkaido short-season norms expect R7
   > within late-Sep–Oct (VERIFY [SOY-GDD-TABLE])`

   — Nemuro, the mildest case. Even the engine's own VERIFY tag feared
   this; the campaign upgraded the fear to a measured, per-site number.

3. **The storm-lull pattern on the coast:**

   > `[rough/sanity] nemuro-wind-suspicious: Nemuro slice winds peaked at
   > 11.88 m/s yet 6 GO windows appeared across 6 scans — plausible only
   > if the gusts sat outside the scanned runs; verify against the site's
   > maritime climatology`

   — not wrong, but the kind of "GO in gale season" that deserves a human
   eye before it ever reaches a spray decision.

## 5. Where the engine HELD (the non-findings that matter)

- Honesty plumbing end-to-end: gaps are NAMED, published, and typed;
  refusals refuse; no exception ever escaped the engine's designed
  failure envelope in 5 full seasons + 45 edge probes (0 blockers).
- `RecommendationRecord` integrity on every site: deterministic ids,
  `permits_financial_use` false, `requires_human_signoff` true,
  finite expiry (the `rec-financial-use-flipped` / `rec-signoff-missing`
  blockers never fired).
- The support ladder (grid → probe → parcel) resisted both
  under-claiming and over-claiming under the sensor-gate matrix (Q2).
- The `stale-hours` containment rule defending "next 48 h" semantics —
  it literally refused the harness's first, too-greedy slices (§3 Q4).
- Input archaeology: publisher NULLs pass through and become engine
  gaps, never adapter inventions (archive 2026 data arrived complete for
  these five points; the NULL path is proven by offline tests).

## 6. Sites contradicting agronomic sanity — the distrust auditor's list

1. ALL FOUR Hokkaido sites finish the season BELOW R6 (R1–R3 finals).
   Real Hokkaido soybean reaches R7/R8 by late Sep–mid Oct. **Confirmed
   contradiction, quantified (Q1).**
2. Nemuro — Japan's cool maritime shoulder — asked for **139.5 mm of
   supplemental irrigation** while fog-fed coastal fields rarely demand
   anywhere near that; the sum of the Kcb artefact (constant 1.10) and
   2026's dry stretch. Partial artefact, partially real weather; the
  分解 belongs to the engine owners.
3. Tsuruoka's 0.0 mm verdict is TOO comfortable: the artefact halved its
   water use; on true per-day Kcb the control would likely post a small
   but nonzero requirement. (Flagged by reasoning here; a per-day-Kcb rerun
   is the engine owners' experiment to run.)
4. My own sanity BANDS are VERIFY-tagged constructions, not gospel —
   but the contradiction survives every generosity probe performed on
   them (§3 Q1).

## 7. Method, provenance, and limits

- Fixtures: ONE live request per site (sanctioned under
  `FARM_ONLINE_TESTS=1`) to the Open-Meteo **archive** API, 2026-05-01 →
  2026-10-31, GMT, daily (t max/min/mean, precip sum, FAO-56 ET0, wind
  max) + hourly (t, precip, wind 10 m). Raw responses preserved verbatim
  (`captured_live: true`, `fetched_at`, endpoint, query). Sizes:
  184 daily rows, 4416 hourly rows, ~168 KB each.
- Adaptation is FAITHFUL: values pass through untouched (NULLs stay
  NULLs → engine gaps); grid support declared uniformly 11 km
  (`VERIFY [ARCHIVE-GRID]`: archive mixes ERA5 ~25 km / ERA5-Land
  ~9–11 km; declaring one value exercises the no-blending rule on honest
  inputs).
- Clocks: engine anchors injected from the registry (sow defaults per
  site, JST 09:00); scan instants fixed dates at 03:00 UTC. No wall
  clock in the matrix path. Drive window = sow + 165 days clipped to
  fixture end.
- Limits: archive reanalysis ≠ JMA MSM operational forecasts (a WS2-era
  concern); sanity bands and JMA block anchors are VERIFY-tagged
  registry claims (Nakafurano's block deliberately LEFT NONE — gap, not
  guess); soil profile is generic loam; no field probes existed yet
  (sensor story exercised via the gate matrix instead). Suite status at
  report time: **1446 tests OK (skipped=4, the pre-existing online
  gating)**, including 26 new fieldtest tests (registry contract + 
  harness behaviour, all offline on synthetic fixtures).

## 8. For the engine owners (NOT implemented here — finder's counsel)

1. **Recalibrate `GDD_THRESHOLDS` to Hokkaido variety-trial data** — the
   engine ships it as CONFIG exactly for this; the matrix supplies the
   measurable target (reach R7 by ~1300–1500 GDD for Yukihomare/Ryuho
   class; VERIFY against JA/Hokkaren trials). Bump CONFIG_VERSION.
2. **Per-day running Kcb** — feed each day's running cumulative GDD into
   the basal curve instead of the final reading's; removes the
   both-directions artefact; expect Hokkaido deficits to DROP and the
   control's zero to budge; rerun this matrix after.
3. **Gust-awareness note in spray output** (even v0 text) for coastal
   sites where hourly 10 m means conceal short violent lulls.

## 9. Artifacts & reproduction

- `farm_ontology/fieldtest/sites.py` (+ tests
  `tests/test_fieldtest_sites.py`): registry, bands, VERIFY tags.
- `farm_ontology/fieldtest/harness.py` (+ tests
  `tests/test_fieldtest_harness.py`): finder, capture gate, adapter,
  edge probes, matrix runner.
- `fixtures/fieldtest/site-*/year2026.json`: the five raw captures.
- `reports/fieldtest-matrix-raw.json`: full machine result.
- Reproduce: `python -m unittest discover -s tests -t .` then
  `python -m farm_ontology.fieldtest.harness` (offline, uses committed
  fixtures). Recapture with `FARM_ONLINE_TESTS=1 python -m
  farm_ontology.fieldtest.harness --fetch`.

— end of report. The engine broke exactly where it feared it would, told
the truth about it everywhere, and needs a CONFIG edit (not a philosophy
edit) to speak Hokkaido.
