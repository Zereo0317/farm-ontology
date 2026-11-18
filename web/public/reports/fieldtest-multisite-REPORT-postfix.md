# Field-test multi-site REPORT — POSTFIX (D-ENGINE-1 + D-ENGINE-2)

Campaign: `field-multisite` fix-sprint · Agent: `agronomy` (engine owner
hat) · Run date: **2026-11-18** · Branch: `ws/fix/gdd-kcb-calibration`
(from main `6916090`). Predecessor: `reports/fieldtest-multisite-REPORT.md`
(fieldhw's finder ledger, which convicted the v0 CONFIG). Raw machine
results: `reports/fieldtest-matrix-raw.json` (before),
`reports/fieldtest-matrix-raw-postfix.json` (after). Engine CONFIG bumped
to `agronomy-engine-v0-config-2`.

Nature of the fix: **CONFIG recalibration, not philosophy.** The GDD
accumulator, the honesty plumbing, the support ladder, and the gap/refusal
vocabulary are untouched; the two convicted constants were rebuilt.

---

## 1. D-ENGINE-1 — cultivar GDD profiles (`hokkaido-short` default)

The v0 single table (continental extension: R7 1850 / R8 2100) demanded
40–56 % more heat than the recorded Hokkaido climates provide. Profiles
now: `hokkaido-short` (default, calibrated) + `generic-extension` (v0
values retained verbatim, registry-selected, loud KeyError on unknown ids).

### Threshold table before → after

| Stage | v0 generic (kept) | hokkaido-short (new, default) | Basis (VERIFY tags in phenology.py) |
| --- | --- | --- | --- |
| VE | 90 | 90 | anchor retained (cool-soil emergence week) |
| V1 | 190 | 160 | derived veg compression — TODO-VERIFY trial params |
| V2 | 290 | 230 | derived — TODO-VERIFY |
| V3 | 390 | 300 | derived — TODO-VERIFY |
| V4 | 510 | 355 | derived — TODO-VERIFY |
| V5 | 640 | 385 | derived (indeterminate bloom onset ≈ V5–V6) |
| R1 | 830 | 395 | fitted: recorded curves cross mid-Jul bloom (Jul 15 Biratori/Obihiro, Jul 17 Nakafurano, Aug 14 Nemuro) |
| R3 | 1060 | 505 | Fehr-proportional (declared approximation) |
| R5 | 1260 | 715 | Fehr-proportional (Aug 13–16 crossings on main belts) |
| R6 | 1560 | 825 | fitted: full seed attainable pre-frost even at Nemuro (Oct 10) |
| **R7** | **1850** | **950** | PRIMARY FIT (below) |
| **R8** | **2100** | **1050** | aligned to published combine window |

Published anchors consulted 2026-11-18: MAFF 作物優良品種紹介「ユキホマレ」
(earliest-maturing white-eye; combine-harvest grade from late September);
J-CS proceedings 223 abstract (道央 ユキホマレ maturity 9月第6半旬–10月第1半旬
even after JUNE sowing); HRO 豆類地帯別栽培指針 (平成4–5; soy zones delimited
by accumulated temperature); NARO development-model lineage 日作紀
2015 84(4):408-417 (doi:10.1626/jcs.84.408, リュウホウ/エンレイ/フクユタカ,
1.4–2.8 d errors) and 2025 94(3):263-270 (doi:10.1626/jcs.94.263,
extends to ユキホマレ). **TODO-VERIFY [SOY-GDD-TRIAL-PARAMS]**: the lineage's
per-cultivar parameter vectors are PDF-locked (not parseable offline);
Suzuki-cha/Toyoharuka nursery numbers were not locatable offline — both
stay TODO-flagged in the profile's source table, never silently
interpolated. Derivation method (declared): published calendar phenology ×
RECORDED 2026 site climate; hence region-and-year fitted, not
laboratory trial values.

### Per-site GDD-vs-R7 mismatch, before → after (recorded fixtures)

| Site | GDD by Oct-15 (recorded) | vs old R7=1850 | vs new R7=950 |
| --- | --- | --- | --- |
| biratori-hidaka | 1109.7 | **−40.0 %** (deficit) | +16.8 % (surplus, fail-safe direction) |
| obihiro-tokachi | 1094.0 | **−40.9 %** | +15.2 % (surplus) |
| nakafurano-kamikawa | 1013.6 | **−45.2 %** | +6.7 % (surplus) |
| nemuro-hanasaki | 813.7 | **−56.0 %** | **−14.3 %** (miss, inside the 15 % budget) |

The 40–56 % shortfall inverts to surpluses ≤ 16.8 % plus a single
sub-15 % miss at the coldest maritime site. Recorded curves cross the new
anchors: R1 on Jul 15 / Jul 15 / Jul 17 / Aug 14, R7 on Sep 4 / Sep 4 /
Sep 14, R8 on Sep 19 / Sep 17 / Oct 12; Nemuro banks R6 on Oct 10. The
whole R7→R8→combine arc lands inside the published late-Sep–early-Oct
maturity window for the Yukihomare class. Interpretive note, published
not smoothed: R7 crossing itself arrives early-September on the warm
2026 belts — the completion of maturity (not the R7 instant) is what the
published calendars constrain; a reading demanding R7 literally ON
Sep 25 would break Nemuro's heat budget (−18.7 % at R7=975).

**Real-world defensibility (asked of this sprint):** the engine can now
say — with receipts — *"'hokkaido-short' classifies the RECORDED 2026
Biratori/Obihiro/Nakafurano climates to full-maturity within the
published Hokkaido harvest window, with GDD-vs-R7 mismatch from +16.8 %
(surplus) to −14.3 % (Nemuro miss), replacing 40–56 % structural
deficits"* — a calibration-grade statement, NOT yet a trial-validated
one: cultivar parameters remain TODO-VERIFY, and one season × five
points is a fit, not a validation. Field trials (WS4-era) must ratify
before any operational reliance.

## 2. D-ENGINE-2 — running Kcb

v0 froze Kcb at the SEASON-FINAL stage value for every day of the trace.
Fixed: the balance walks each day's RUNNING cumulative GDD through
`KCB_ANCHOR_PROFILES[profile]` (FAO-56 Table 17 basal anchors ini 0.15 /
mid 1.15 / end 0.50 placed on the profile thresholds; per-day GDD from
`t_mean_c`, else the `(t_max+t_min)/2` textbook mean of the same row with
the basis DECLARED per trace row; temperature-free days contribute zero
GDD, published, never interpolated).

| Property | Before | After |
| --- | --- | --- |
| Kcb across a 165-day trace | ONE frozen value (1.10–1.13 on Hokkaido sites; 0.5479 on the control) | traverses **[0.15 → 1.15 → 0.35]** at every site |
| Vegetative weeks | tariffed at reproductive rates (Hokkaido) / senescence rates (control) | pay basal ramp 0.15→1.00 by R1 |
| Senescence tail | absent (Hokkaido: never reached; control: frozen there) | 1.05 → 0.60 → 0.35 by R8 |
| `kcb-static-across-season` defect | fired at **5/5** sites | **extinguished at 5/5** |

### Irrigation ledger, old → new (net requirement mm / advise)

| Site | v0 (static Kcb, old table) | postfix (running Kcb, hokkaido-short) | Δ | Reading |
| --- | --- | --- | --- | --- |
| biratori-hidaka | 0.0 / no | 0.0 / no (ETc 505.3 mm vs eff. rain 688.8) | — | rain-fed adequacy now EARNED by the traced balance |
| obihiro-tokachi | **60.4 / yes** | **0.0 / no** (ETc 476.4 vs 515.8) | −60.4 | veg-week overbilling removed; 2026 rain covered the now-honest demand |
| nakafurano-kamikawa | 0.0 / no | 0.0 / no (ETc 515.4 vs 708.8) | — | unchanged |
| nemuro-hanasaki | **139.5 / yes** | **78.8 / yes** (ETc 409.3 vs 337.9) | **−60.7 (−43 %)** | half the v0 overbill was the Kcb artefact; the remainder is 2026's genuinely dry, cool coastal season (lowest effective rain in the matrix) |
| tsuruoka-shonai (control) | 0.0 / no | 0.0 / no (ETc 628.1 vs 1048.8) | — | **verdict SURVIVES** |

**Control-site quantification (mandated):** the 0.0 mm verdict is
unchanged, but its BASIS flipped from flattering to earned — v0 ran the
whole warm season at Kcb 0.5479 (senescence rate, ~⅓ of true mid-season
demand); the new curve pays full 0.15→1.15→0.35 and STILL lands rain-fed
(1049 mm effective rain vs 628 mm ETc). Had 2026 Shonai been drier, the
old code would have hidden a real deficit; the new code would have caught
it. Season-total ETc for the v0 code was not preserved in the finder's
ledger (only the frozen-Kcb values), so old/new ETc deltas are given via
the Kcb histories above rather than falsified totals.

## 3. Full matrix, all five sites (postfix)

| Site | Final stage | GDD (sow→end) | GDD by Oct-15 | Irrigation net / advise | Sanity verdict |
| --- | --- | --- | --- | --- | --- |
| biratori-hidaka | **R8** | 1116.8 | 1109.7 | 0.0 mm / no | matured in-window; residual band defect = registry band vs 2026 reanalysis |
| obihiro-tokachi | **R8** | 1101.9 | 1094.0 | 0.0 mm / no | matured in-window; bill corrected 60.4→0.0 |
| nakafurano-kamikawa | **R7** | 1015.3 | 1013.6 | 0.0 mm / no | R7 Sep 14, R8 Oct 12 |
| nemuro-hanasaki | **R6** | 838.5 | 813.7 | 78.8 mm / yes | full seed before frost; R7 miss −14.3 % (recorded climate); wind squint unchanged |
| tsuruoka-shonai (control) | **R8** | 1893.4 | 1823.2 | 0.0 mm / no | clean — ZERO defects; early stage-crossings (R1 Jun 25) reflect the declared no-photoperiod limitation, expected on the warm control |

Totals: defects 18 → **9 rough** (0 blockers, 0 cosmetic). The nine
residuals, each explained:
- `gdd-band-breach` ×4 — the registry's sanity bands were authored from
  1983–92 AMeDAS normals (HRO guide); the 2026 archive reanalysis runs
  cooler at these sites. Bands are QA nets, deliberately unlubricated;
  tightening them to 2026 reality is the REGISTRY OWNER's call, not the
  engine's.
- `r7-not-reached-by-oct15` ×4 — the finder's probe hardcodes the LEGACY
  R7=1850 by design (engine-blind finder); the named message's premise no
  longer reflects the engine's active table. Deprecated finding; the
  probe retires when the fieldhw maintainer adopts the profile API.
- `nemuro-wind-suspicious` ×1 — unchanged spray behaviour (no misfire);
  the gust-awareness note recommended by the finder is a future engine
  item, out of this sprint's scope.

Contradictions from the finder's §6: (1) Hokkaido-wide R7 stall —
**resolved**; (2) Nemuro implausible 139.5 mm — halved to a defensible
78.8 mm with the mechanism split (artefact vs real 2026 dryness)
documented; (3) Tsuruoka's too-comfortable zero — now earned, quantified
above; (4) sanity-band philosophy — untouched by design, noted.

## 4. What did NOT change

GDD arithmetic (`clamp(t−10, 0, 20)`), the anchor/conflict semantics,
the support ladder (grid → probe-footprint → parcel; sensor rows still
never rewrite the balance), spray rule tables, fertility humility,
recommendation issuance chain and failed-closed guarantees, the
gap-or-refuse posture everywhere, stdlib-only/offline/deterministic
discipline. Recorded per-site season GDD sums are IDENTICAL before/after
(same fixtures; only the threshold semantics moved).

## 5. Tests & reproduction

- 8 new regression tests (profiles + registry + legacy retention + fit
  geometry + running-Kcb traversal + `t_mean_basis` declaration +
  temperature-free-day publication). Agronomy subset: **120 tests OK**.
- Full repo suite: **1535 tests, OK (skipped=14)**.
- Reproduce: `python -m unittest discover -s tests -t .` then
  `python -m farm_ontology.fieldtest.harness` (offline; committed
  fixtures) — or diff `reports/fieldtest-matrix-raw{,-postfix}.json`.
- Verify tags introduced here: `[SOY-GDD-TRIAL-PARAMS]` (PDF-locked NARO
  parameters, outstanding), `[FAO-56-T17]` (basal anchors), in addition
  to the registry's existing tags. Backlog for the next engine sprint:
  photoperiod term, gust-aware spray caveats, registry-band refresh.

— end of postfix report. The engine told the truth, was convicted by real
weather, ate its own CONFIG medicine, and now speaks Hokkaido.
