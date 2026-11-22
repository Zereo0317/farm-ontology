# Agronomy decision engine v0 — spec of record (WS3)

Owner: `agronomy` (board task `task-3`). Branch: `ws/agronomy/engine-v0`.
Written 2026-11-18. This document is the rule book the code encodes; the
code's docstrings carry the same rule text, so neither can drift alone
without the reviewers noticing.

Inherits §1 of `decision-infra-roadmap.md` verbatim:

1. refuse when an input is missing; a gap is published, never guessed;
2. native support travels with every value; joins never rewrite support;
3. `permits_financial_use` flips only on a written grant (v0: always FALSE);
4. `factsAt`/`associatedAt` point-in-time semantics everywhere.

The engine **proposes**; humans (or, at Phase 4, safety-cased controllers)
**dispose**. Every output carries `use_class: field-ops`,
`config_version`, and a support stamp.

---

## 1. Module map

| Module | Deliverable | Public surface |
| --- | --- | --- |
| `farm_ontology/agronomy/common.py` | shared vocabulary | `AgronomyGap`, `AgronomyRefusal`, `Gap`, `SupportDeclaration`, `canonical_json`, `deterministic_id`, `CONFIG_VERSION`, `DRAFTED_BY`, `PERMITS_FINANCIAL_USE_V0`, `USE_CLASS_FIELD_OPS` |
| `farm_ontology/agronomy/phenology.py` | WS3.1 | `phenology_reading(rows, sowing=…, emergence=…, at=…)`, `daily_gdd_contribution`, `GDD_THRESHOLDS`, `PhenologyReading` |
| `farm_ontology/agronomy/irrigation.py` | WS3.2 | `irrigation_advisory(rows, reading=…, sensor_rows=…, parcel=…, at=…, cfg=…, soil=…)`, `has_calibrated_coverage`, `SoilProfile`, `IrrigationCfg`, `CoverageLevel` |
| `farm_ontology/agronomy/spray_windows.py` | WS3.3 | `scan_spray_windows(hourly_rows, at=…)` → `(windows, summary)`, `SPRAY_CONFIG`, `SprayWindow`, `Verdict` |
| `farm_ontology/agronomy/fertility.py` | WS3.4 | `soil_fertility_note(rows, at=…)`, `REQUIRED_SOIL_ANALYTES`, `SoilReading` |
| `farm_ontology/agronomy/recommendation.py` | WS3.5 | `draft_recommendation(...)`, `RecommendationRecord`, `InputRef`, `RationaleStep`, `KINDS`, `REFUSED_KINDS` |

Dependencies: standard library + `farm_ontology.{model,build,timeutil}`
only. No network, no wall-clock reads, no new dependencies.

## 2. Phenology (WS3.1)

Accumulator: `GDD_day = clamp(t_mean − 10, 0, 20)` °C·d.

| Constant | Value | Source note |
| --- | --- | --- |
| `GDD_BASE_C` | 10.0 | VERIFY [SOY-GDD-BASE]: base 10 °C is standard Japanese soybean-guideline practice (Unirosse / tenki.jp growing guides). Recalibrate per cultivar before reliance. |
| `GDD_CAP_CONTRIBUTION_C` | 20.0 | Modelling choice, DECLARED: a daily MEAN above 30 °C contributes no more than a 30 °C mean (heat above 30 °C buys little development). Not a measured physiological limit. |
| `CULTIVAR_GDD_PROFILES['hokkaido-short']` (DEFAULT) | VE 90 · V1 160 · V2 230 · V3 300 · V4 355 · V5 385 · R1 395 · R3 505 · R5 715 · R6 825 · **R7 950** · **R8 1050** | CALIBRATED for Hokkaido Yukihomare/Ryuuhou-class cultivars. Published anchors: MAFF varietal sheet (ユキホマレ, earliest-maturing white-eye, combine from late September); J-CS.proc.223 abstract (道央 maturity 9月下旬–10月上旬 even after June sowing); HRO 豆類地帯別栽培指針 平成4–5 (zones delimited BY accumulated temperature). Fitted on the RECORDED 2026 site climates of the fieldtest matrix (see below); per-threshold provenance lives in the profile's `per_stage_sources`. Trial parameters of the NARO development-model lineage (日作紀 2015 84:408-3 柳ホウ系 1.4–2.8 d error; 2025 94:263 extending to ユキホマレ) are TODO-VERIFY — the numbers are locked in PDFs and NOT yet ingested. NO photoperiod term (declared limitation; warm-climate seasons compress). |
| `CULTIVAR_GDD_PROFILES['generic-extension']` (RETAINED) | VE 90 · V1 190 · V2 290 · V3 390 · V4 510 · V5 640 · V6 780 · R1 830 · R3 1060 · R5 1260 · R6 1560 · R7 1850 · R8 2100 | VERIFY [SOY-GDD-TABLE]: the v0 continental public-guide table, RETAINED verbatim for non-Hokkaido comparability and backward compatibility; proven by the 2026 campaign to over-demand 40–56 % on Hokkaido climates. |
| `METHOD_NOISE_GDD` | 45.0 | Any stage announcement is at least this uncertain (the table is coarse). |

**Campaign acceptance check (2026-11-18 postfix run).** With
`hokkaido-short` on the recorded fixtures: R7 = 950 GDD crossed
Sep 4 (Biratori), Sep 4 (Obihiro), Sep 14 (Nakafurano); Nemuro banks
813.7 by Oct 15 = **−14.3 %** miss at the coldest maritime site (inside
the 15 % budget); GDD-vs-R7 sums otherwise bank +6.7 % to +16.8 %
SURPLUS (warm-site fail-safe direction). R8 = 1050 crossed Sep 17–19
(Biratori/Obihiro) and Oct 12 (Nakafurano), aligning combine-readiness
with the published late-Sep–early-Oct window; Nemuro attains R6 (825)
on Oct 10 before the frost/kill window. The literal "R7 ON a late-Sep
date" reading is NOT satisfied by design: the whole R7→R8→harvest arc
completes inside the published window instead — recorded-climate
geometry beats calendar literalism, and the tension is published here
rather than smoothed away.

Stage = highest threshold reached (`Vn` compressed to buckets; gaps
between V3→V4 numbering are deliberate compression, not omission).
Uncertainty = `max(METHOD_NOISE_GDD, |cumulative − threshold_midpoint|)`
GDD, where the midpoint of the SURROUNDING thresholds is the stage's
empirical centre; a days-equivalent divides that band by the mean realised
daily contribution and is `None` (a gap, never a fake date) when the mean
rate is below `MIN_MEAN_RATE_FOR_DAYS_BAND` (1.0 °C·d/day).

Anchors: accumulation starts at SOWING. With only an EMERGENCE
observation, accumulation starts at emergence day with `EMERGENCE_CREDIT_GDD`
(= the VE threshold, 90) credited — the `anchor` field says which. When
both exist, sowing is used and the credit implied by the emergence date is
cross-checked; |implied − 90| > 45 ⇒ `anchor_conflict=True` (flagged,
never silently corrected).

Unknown `cultivar_profile` ids raise KeyError with the known-profile menu
(loud, registry-backed; Suzuki-cha / Toyoharuka etc. stay TODO-flagged,
never interpolated).

Missing anchor ⇒ `AgronomyGap("missing-sowing-anchor", missing=[sowing,
emergence])`. Duplicate dates, regressive dates, malformed rows (index +
field named), missing/mixed `native_resolution_km` ⇒ named gaps.

## 3. Irrigation adviser (WS3.2)

FAO-56 dual-Kc daily balance, `ETc ≈ (Kcb + Ke) × ET₀`, over rows
`{date, eto_mm, rain_mm, native_resolution_km, t_mean_c?}`. The reading
(§2) supplies the cultivar profile; soil profile is DECLARED
(`SoilProfile`: θfc 0.30, θwp 0.15, rooting 0.7 m ⇒ TAW 105 mm, p 0.50 ⇒
RAW 52.5 mm — VERIFY [FAO-56] Table 22 soybean p≈0.50; parameters
generic loam, not measured Hokkaido soil).

**Running Kcb (D-ENGINE-2 fix, 2026-11-18).** The v0 balance drove Kcb
from the SEASON-FINAL phenology reading for every day of the trace — the
campaign's `kcb-static-across-season` artefact (Hokkaido sites billed
their vegetative weeks at pod-fill rates; the control ran at
senescence rates). The fixed balance interpolates Kcb per day from the
day's RUNNING cumulative GDD through the anchor table
`KCB_ANCHOR_PROFILES[profile]` — e.g. `hokkaido-short`: (0, 0.15) →
(90, 0.20) → (395, 1.00) → (505, 1.15) → (715, 1.15) → (825, 1.05) →
(950, 0.60) → (1050, 0.35). Anchor VALUES are the FAO-56 Table 17
soybean basal coefficients (ini 0.15 / mid 1.15 / end 0.50; VERIFY
[FAO-56-T17]) placed on the profile's own stage thresholds; the daily
GDD input is `t_mean_c` when the row carries it, else the
`(t_max+t_min)/2` textbook mean from the SAME row (the basis used is
declared per trace row); days with no temperature at all now refuse with a named gap; they never
contribute an assumed zero GDD.

Remaining declared simplifications (all in `IRRIGATION_CONFIG_SOURCE_NOTE`):
flat 20 % runoff haircut (conservative: never hides water need), no
climate adjustment of Kc_max, `fc ≈ Kcb/Kc_max`, surface layer TEW 12 /
REW 5 mm.

Output: net irrigation requirement (mm) = `max(0, Dr_end − RAW)` at the
horizon end, `recommend` bool, `why` sentence, full daily trace, and the
**support declaration**:

| Rung | Requirement | Claim text |
| --- | --- | --- |
| 1. grid | always | `grid-support (native NxN km)` — N read from the rows themselves; mixed N ⇒ `grid-resolution-mixed` gap (a blend would rewrite support) |
| 2. probe | a live calibrated sensor row covers the parcel | `probe-support (instrument-point, probe footprint radius R m, sensor …)` — a point probe's claim is its FOOTPRINT; no radius given ⇒ "extent unspecified"; the word "ha" never appears from the engine's pen |
| 3. parcel | the SENSOR ITSELF declares `coverage_area_ha` | `parcel-support (sensor-reported 0.4 ha coverage, sensor …)` — the area is ECHOED, never computed |

`has_calibrated_coverage(sensor_rows, parcel, at)` is the honest gate. It
reuses the sensors-ingest eligibility concept exactly: a live
`calibration_activity` plus an unexpired `recalibration_due` plus adviser
freshness (72 h). Store `Observation`s were already cert-gated by
`farm_ontology.sensors.ingest` at commit time, so only freshness is
re-checked for them; raw projection rows (typically deserialised from
JSON, as in `fixtures/agronomy/sensor-coverage-rows.json`) must
self-certify completely, with parcel links stated EXPLICITLY — the ingest
adapter never asserts a join, and neither does the engine. Every excluded
row is published with its reason (`no-parcel-link`,
`no-calibration-activity`, `calibration-expired`,
`no-phenomenon-end`, `stale-beyond-freshness-window`).

A fresh calibrated probe never REWRITES the grid number in v0: its
reading yields a divergence note (grid-model depletion vs
probe-implied depletion) for the human signatory. That is the whole
point of the ladder — support climbs with evidence, numbers do not.

## 4. Spray windows (WS3.3)

Scans strictly-hourly rows `{time, wind_ms, precip_mm, temp_c,
native_resolution_km}` covering the scan context (`at` inside the
series; series may begin at most `CONTEXT_BACK_HOURS`=24 before it).
Candidate = maximal contiguous run (≥ `MIN_RUN_HOURS`=2) where the loose
bounds hold: wind ≤ 3, precip = 0, temp within [5, 30].

| Rule | GO | CAUTION | NO-GO |
| --- | --- | --- | --- |
| wind (VERIFY [SPRAY-WINDOW]: JP low-drift ground-sprayer norm) | every hour ≤ 3 m/s; ≤ 2 m/s additionally tags `GO (conservative)` | — | any hour > 3 m/s (run splits) |
| temperature (glyphosate-type systemic uptake guideline) | every hour in [10, 25] °C | hours in [5,10) ∪ (25,30] flagged `temp-in-go-band` | outside [5, 30] |
| precip | run dry AND rainfast tail (6 h after run) verifiably dry | tail unverifiable (data ends) ⇒ `rainfast-window-unverifiable` | any rain in run or verified tail ⇒ `rainfast-tail-wet` |

Every window carries `evidence`: which rule fired, at which bound, worst
observed hour. Hours belonging to no candidate are listed in
`summary["unusable_spans"]` with their disqualifying rule — the report
explains its silences. RAINFAST 6 h is a conservative stand-in for the
product label, which governs in reality (VERIFY-tagged).

## 5. Fertility skeleton (WS3.4)

Requires ALL of `ph, ec, n_available, p_available, k_available,
om_percent` (sampling ≤ 3 years old, homogeneous declared support).
Missing/partial ⇒ `AgronomyGap("needs-soil-chemistry", missing=[…])`
enumerating exactly what the lab must supply. Unknown analytes,
duplicates, stale rows, mixed supports, missing support ⇒ named gaps.

Complete chemistry ⇒ a **REVIEW-REQUIRED** note set: pH comfort band
[6.0, 7.0] (soybean; acidic Andosol-typical values flagged for
DISCUSSION, no lime dose computed), EC watch at 2 dS/m (coarse screen),
N-P-K/OM echoed verbatim with method/lab/depth and NO thresholds —
Hokkaido prefecture fertiliser standards govern locally and are not yet
ingested. The notes state, and the tests enforce, that **an agronomist
signs every dose**; v0 computes none. This is house humility as a
contract, not a mood.

## 6. Recommendation record (WS3.5)

`RecommendationRecord` fields: `recommendation_id` (deterministic),
`kind` (`irrigation | spray | fertility | phenology-query`),
`inputs` (list of `InputRef`: observation IRI + native support + licence
instrument/permissions/expiry), `rationale` (rule trace `RationaleStep`s),
`uncertainty` (band dict or None), `use_class` (`field-ops`),
`permits_financial_use` (**structurally FALSE in v0** — it is not even a
constructor parameter), `drafted_by='agronomy-engine'`,
`requires_human_signoff=True`, `drafted_at`, `expires_at` (aware,
strictly after drafted_at else `AgronomyRefusal("born-expired")`),
`payload`, `config_version`.

Replayability: the id is `rec:<sha256[0:32]>` over canonical JSON of
config-version + kind + inputs + rationale + payload. Timestamps are
EXCLUDED from identity (they are stamps, not identity): rebuilding from
the same inputs on another day yields the same id. Input ARRAY order
participates in identity (canonical JSON sorts keys, not arrays) — WS2's
deterministic ingest ordering is what makes replays byte-stable.

Refused uses stay refused: kinds `hedge/trade/sell/buy/short/long/
settlement/trigger/nature-unit` raise `AgronomyRefusal("refused-use")`
at construction — a recommendation object for a refused use never exists
to be waved around later. This is the WS3-side complement to the store's
closed class-C policy and to `docs/alpha-fairness-doctrine.md` §6: the
command ledger proposes farm actions only AFTER a human approves; this
record is what the human is approving, and it can never smuggle in a
market use.

## 7. Fixtures (`fixtures/agronomy/`)

All synthetic, `captured_live: false`, no real coordinates; provenance in
that directory's README. `daily-eto-rain-season.json` (134 d,
JMA-MSM-like 5 km), `hourly-weather-48h.json` (rule-regime crafted),
`soil-chemistry.json` + `-short.json` (plausible Hokkaido Andosol lab
sheet: pH 5.6, EC 0.35 dS/m, N 18 / P 12 / K 21 mg/100g, OM 9.8 %),
`sensor-coverage-rows.json` (five coverage scenarios incl. expired cert,
uncertified, foreign parcel, sensor-declared 0.4 ha array).

Developing against these keeps WS3 independent of WS2; the swap to live
ingest (below) must not require an engine change.

## 8. Contract shape — how WS2 (task-2) feeds this engine

The engine consumes PLAIN ROW MAPPINGS with exactly these keys:

```jsonc
// phenology + irrigation, per day:
{"date": "2026-08-10", "t_mean_c": 24.1, "eto_mm": 4.8, "rain_mm": 0.0,
 "native_resolution_km": 5}

// spray windows, per hour:
{"time": "2026-08-10T04:00:00+00:00", "wind_ms": 1.8, "precip_mm": 0.0,
 "temp_c": 21.5, "native_resolution_km": 5}

// optional calibrated soil row (irrigation), per reading — EVERY key is
// doing honest-claim work; omit none carelessly:
{"sensor_iri": "sensor/proto-01",
 "parcel_iri": "observation/boundary/…",      // explicit link, never inferred
 "value": 24.8, "depth_cm": 10,
 "probe_radius_m": 2.0,                        // OPTIONAL footprint
 "coverage_area_ha": null,                     // ONLY when the sensor declares area
 "phenomenon_end": "2026-08-10T03:30:00+00:00",
 "calibration_activity": "activity/…",
 "recalibration_due": "2027-04-21"}

// fertility, per analyte:
{"analyte": "ph", "value": 5.6, "unit": "pH",
 "sampled_at": "2026-10-20T02:00:00+00:00",
 "native_support": "soil-sample-grid-composite", "depth_cm": 15,
 "lab": "…", "method": "1:2.5 water suspension"}
```

Pipeline obligations implied by this contract, in priority order:

1. **Daily grid ingest worker (WS2.1 extended)** — commit one row per day
   per variable (`t_mean_c`, `eto_mm`, `rain_mm`) with the JMA MSM native
   resolution preserved and `availability_time` set. THIS is the single
   feed the engine wants first: phenology + irrigation both starve
   without it, and spray windows can start from the same hourly stream.
2. Hourly continuity for spray scans (holes ⇒ the engine refuses; WS2
   must dedupe by phenomenon+issue time exactly as WS2.1 already plans).
3. Device JSON → store via the existing `sensors.ingest` path, PLUS the
   explicit parcel-link projection table (a join through `Store.add_join`,
   or a pipeline-maintained projection that names `parcel_iri` per row).
4. Lab results land as fertility rows whenever WS4's kit produces them —
   the engine is ready and refuses cleanly until then.

Failure posture: if WS2 emits a row violating the contract, the engine
raises a NAMED gap citing the offending index/field — the pipeline gets a
machine-readable complaint, not a silent degradation.


### Irrigation state and point-in-time migration

Operational irrigation calls require `IrrigationInitialState` with the
end-of-day date immediately before the first trace row, cumulative GDD,
root and surface depletion, and an evidence reference. Each row must
declare `source_kind` as `observation` or `forecast` and an aware
`availability_time` no later than the query instant. Observations must be
completed before the query date. Missing temperature, non-contiguous
dates, and missing or future availability refuse with named gaps. The
returned `ending_state` can seed a contiguous next trace without losing
the development or water balance.

Legacy archive fixtures lack state and point-in-time availability evidence;
the fieldtest harness now reports `gap:missing-initial-state` instead of
turning those rows into an operational recommendation. Test-only synthetic
fixtures may declare synthetic evidence; this does not validate a field
state, a forecast source, or an agronomic model. A caller-provided evidence
string is not independent verification, and phenology reading provenance
still requires a trusted verification boundary before operational use.


### Phenology and spray time guards

Phenology refuses nonfinite temperatures, nonpositive/nonfinite native
resolution, missing anchor days, and gaps in the daily sequence. An aware
as-of instant is required; each row must declare itself an observation
with an aware availability time no later than that instant, and its calendar
date must precede the instant's UTC date. Forecasts, current/future dates,
missing metadata and unavailable data refuse. The resulting reading carries
the as-of instant and latest declared source availability; irrigation
refuses readings whose timestamps cannot support its own decision instant.
These are caller-supplied assertions, not authenticated provenance or a
verification of the source's local-day cutoff. A trusted source registry and
local-calendar semantics remain required before operational reliance.
Legacy archive fixtures lacking this metadata refuse; synthetic test-only
metadata is never assigned to real archive captures.

Spray scans use earlier hours only as context: candidate windows include
only complete hourly slots whose starts are at or after the scan instant.
This does not establish product-label suitability, source availability,
or forecast accuracy.
