# fixtures/agronomy — synthetic decision-engine fixtures

**All files in this directory are synthetic.** `captured_live` is `false`
everywhere, the values are shaped to be plausible for a Hokkaido
soybean season, no coordinates point at any real farm, and lab names /
device ids are demonstrations.

| File | Shape | Used by |
| --- | --- | --- |
| `daily-eto-rain-season.json` | `{parcel_iri, sowing_hint, rows: [{date, t_mean_c, eto_mm, rain_mm, native_resolution_km}]}` — 134 daily rows, 2026-05-20 → 2026-09-30, JMA-MSM-like 5 km grid | `phenology.py`, `irrigation.py` |
| `hourly-weather-48h.json` | `{parcel_iri, hours: [{time, wind_ms, precip_mm, temp_c, native_resolution_km}]}` — 48 hourly rows starting 2026-08-10T00Z, regime crafted to exercise every spray rule branch | `spray_windows.py` |
| `soil-chemistry.json` | `{rows: [{analyte, value, unit, depth_cm, sampled_at, method, native_support}]}` — complete 6-analyte Andosol-like sheet | `fertility.py` |
| `soil-chemistry-short.json` | same shape, two analytes removed | `fertility.py` (gap enumeration) |
| `sensor-coverage-rows.json` | projection rows mirroring `fixtures/sensors/device-proto-soil.json` with EXPLICIT parcel links added (the sensors-ingest adapter never asserts joins), covering: live-certified probe, expired cert, uncertified, sensor-declared `coverage_area_ha`, foreign parcel | `irrigation.has_calibrated_coverage` |

Provenance discipline mirrors the rest of the repo: contract fixtures are
marked `captured_live: false`, and this README is the provenance note.
WS2 (task-2) will replace these rows with ingested observations through
the Store; the engine reads row mappings precisely so that swap is a
pipeline change, not an engine change.
