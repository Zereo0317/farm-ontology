# WS4 calibration protocol — factory cal to field-usable, and what a calibrated row means

Owner: `fieldhw` (`task-4`) · Applies to the kit in
[`sensor-kit-bom.md`](sensor-kit-bom.md) · Governing rules this protocol is
written against: `farm_ontology/rules.py` (`R-sensor`, `R-error`),
`farm_ontology/model.py::ErrorStatement`, and the store's refusal ledger.

---

## 0. Why this document exists (the record-level meaning)

The roadmap's honesty rules forbid a value from pretending to be more
supported than its instrument. Today that means:

- `hectare_weather_claim = True` requires `sensor_iri` **and**
  `calibration_activity` (`R-sensor`, rules.py:260-274);
- a class B reading requires an `ErrorStatement` whose metric is not
  `uncalibrated` (`class_b_blockers`);
- sensor values are never written onto boundaries that have no sensor.

Those gates only bite if *something* stamps rows as calibrated. This
protocol is that something. **Definition adopted by ingest
(`farm_ontology/sensors/ingest.py`):**

> A *calibrated sensor row* is an observation that entered the Store with
> (a) a `sensor_iri`, (b) a `calibration_activity` naming a live
> certificate executed under this protocol, (c) a `recalibration_due` in
> the future at the row's phenomenon time, and (d) an `ErrorStatement`
> whose metric is `rmse` or `bias` with a numeric value measured by this
> protocol. Rows failing (a)–(d) are refused at ingest
> (`R-sensor`), never stored.

These are the only rows eligible to carry the *'calibrated on-farm
sensor'* badge demanded by the WS3.2 irrigation gate and the memo/publish
layer ("Hectare weather is present only where a calibrated sensor was
present"). The `feature_kind=pixel` ambition of WS2's NDVI baseline and
this kit share the same principle: **the error metric is earned by a
method, not asserted by a vendor page.** Uncalibrated rows may still exist
in `field-notes/` as engineering logs, but `ingest_device_json` will not
admit them into the governed store — refusal, not silence.

Certificate lifetimes by instrument are set in §9.

## 1. Scope

| Instrument | Calibration authority here | Section |
| --- | --- | --- |
| 2× capacitive soil VWC probe (S2104 / SE02) | Gravimetric cross-check (this doc §4) | hardest |
| Tipping-bucket rain gauge (WH-SP-RG) | Known-volume pour + siting rule (§5) | medium |
| Leaf-wetness grid | Wet/dry endpoint only — no quantitative claim (§5.4) | light |
| Air T/RH (SHT31 under shield) | Shelter + aspiration discipline + annual bench check (§6) | light |

Everything is done with: one kitchen scale (0.1 g), two 500 ml graduated
cylinders, auger/hand trowel, oven or drying cabinet, tins with lids, field
sheets, gloves. No lab service is presupposed for the pilot; a soil lab
(Oikos or Rakuno Gakuen annex) is engaged once per season for reference
chemistry in WS3.4.

## 2. Site map and sampling depths

Demo plot (parcel polygon from WS4.4's RTK walk): three vertical profiles
P1/P2/P3 at ridge-head / mid / ridge-tail of the soy block.

Depths: **10 cm, 30 cm, 50 cm** — the A-horizon moisture the crop feels
first, the B-horizon reserve, and the deep-buffer the drought question
turns on. One probe body per profile; the kit's two movable probes migrate
between profiles on a rota (Week A: P1@10+P2@30, Week B: P3@50+P1@30 …),
logged in the rota sheet. Never interpolate across profiles.

## 3. Terminology

- **factory calibration** — vendor polynomial (air ↔ 0 %, water ↔ 100 %).
- **field calibration** — equation/pairwise offsets derived from
  coincident gravimetric samples in *this* field's Aso-derived volcanic
  ash soil, executed by this protocol.
- **calibration event** — one dated execution of a section below,
  producing one `calibration_activity` IRI,
  e.g. `activity/grav-3pt-2027-04-21-biratori`, recorded in the field
  notebook and mirrored into the fixture-ledger (JSON in
  `field-notes/calibrations/`).
- **certificate** — the (activity IRI, expiry) pair a device wears. The
  adapter reads it per payload (`calibration_activity`,
  `recalibration_due`); an expired certificate earns **zero** rows
  (`R-sensor` refusal), matching the licence-ledger's fail-closed habits.

## 4. Soil probe gravimetric cross-check (3-point)

Volumetric water content θᵥ (m³/m³) is what the probe claims;
gravimetric θ_g (g/g) times bulk density ρ_b (g/cm³) is what the weighing
proves: **θᵥ = θ_g × ρ_b**.

### 4.1 Setup

1. 24–48 h without heavy rain or irrigation (a "representative drying
   slope", not saturation shock — the factory polynomial is worst exactly
   at the wet extreme in volcanic soils).
2. Probes seated vertically, full contact, undisturbed for ≥ 24 h (fresh
   insertion voids shift dielectric readings ~0.02).

### 4.2 Points (3, one per depth-tier, replicated)

| Point | Depth | Sampling protocol |
| --- | --- | --- |
| S1 | 10 cm | ring-core the *annulus* 5 cm from the probe rod, same horizon |
| S2 | 30 cm | side-wall core flush against rod midpoint |
| S3 | 50 cm | auger nose directly below rod tip |

**Replicates: 3 cores per point** (adjacent 10 cm positions), hence
**9 weighings per probe per event**.

### 4.3 Execution (each core)

1. Log probe's raw % reading *immediately before* coring (15-min logger
   row nearest the moment is acceptable; note deviation >7.5 min).
2. Extract core, seal tin, field-mass within 15 min (evaporation bias).
3. Oven-dry 105 °C ± 5 °C for 24 h (48 h if the core smells damp), cool in
   desiccator, reweigh.
4. ρ_b from the ring volume (100 cm³ rings).

### 4.4 Fitting the field calibration

- Reject any core whose θ_g duplicate spread exceeds 0.02 g/g; re-core.
- Fit per probe: θᵥ_field = a·θᵥ_factory + b (least squares over 9 pairs;
  expect a∈[0.9,1.1], b∈[−0.03,+0.03]). Publish (a, b, n, RMSE) — nothing
  else is a calibration.
- The kit may report factory units while the (a, b) live in the event
  record; the adapter maps `calibration_error.value_fraction` to **RMSE of
  the fitted residuals in m³/m³**.

### 4.5 Acceptance tolerance

**RMSE ≤ 0.03 m³/m³ (absolute) and |bias| ≤ 0.02 m³/m³.**

- PASS → certificate minted, 12-month life (§9).
- Marginal (RMSE ≤ 0.035): certificate with flag `cf-borderline`, 6-month
  life,probe scheduled for recalibration before the next drought-window.
- FAIL → no certificate; probe demoted to engineering-log only until
  re-seated and re-checked. **A failed probe never earns rows.**

Volcanic ash (Andosol) subsoils hold bound water that biases dielectric
methods wet at low θ; if RMSE fails only below 15 % factory-θ, restrict
the certificate to θ ≥ 15 % (documented in the event record) — honest
domains, not convenience refits.

### 4.6 Inter-probe consistency gate

The two probes must agree within 0.03 m³/m³ side-by-side for 48 h at one
site after calibration, else both certificates are withheld (the kit
cannot attribute which drifted). Same rule after any firmware update.

## 5. Rain gauge: siting (WMO-ish) + volume check

### 5.1 Siting rule (adapted from WMO No. 8 guidance to a hedged farm plot)

1. Funnel rim **level** (spirit bubble checked monthly) and **1.2–1.5 m
   above effective ground**; ≥ 30 cm above tallest crop at maturity
   (soybean ~0.8–1.0 m → 1.2 m pole minimum).
2. **Distance from obstruction ≥ 2× obstacle height** above rim level
   (hedgerows, sheds, treeline); if only 1–2× is achievable, accept and
   record the obstruction azimuth as `cf-sited-shadowed` — never hide it.
3. ≥ 4 m from the mast steelwork; gauge gets its own pole.
4. Snow season: rim raised to 1.5 m in November; **November-drain rule**
   (§5.3) unless heated.
5. Same position every season: coordinates go into the calibration
   event; moving the gauge forces a fresh siting note.

### 5.2 Volume-pour verification (event `pour-YYYY-MM-DD`)

1. Slow-pour exactly 500.0 ml distilled water through the funnel over
   10 min (syphon bottle; splashes lie).
2. Expected: 500 ml = 500 cm³ over mouth-area A cm² / 10 = mm of water…
   for the WH-SP-RG 200 cm² class mouth ≈ 25.0 mm ≈ **89.5 tips at
   0.2794 mm** — accept count 86–93 (±4 %).
3. Repeat twice (3 pours/event). Bias (count-measured) recorded as the
   device's `metric=bias` fraction; RMSE not meaningful for a binary
   bucket — bias IS the certificate's error statement.
4. Accept: |bias| ≤ 4 % with monotone tip mechanics (no double-trips).
   Else clean mesh, re-level, retest; persistent failure = instrument
   retirement.

### 5.3 Hokkaido winter posture

Between first sustained frost and snowmelt: the bucket drains, dries, and
inverts; a frozen catch chamber cracks and 0.2794 mm stops being true.
February–March rows from the gauge are structurally absent →
`gap_reason: sensor-down` (a governed GAP_REASON, already
namespace-blessed), **never a zero**. April re-prime re-verifies with one
pour (§5.2, single event).

### 5.4 Leaf-wetness grid

Endpoint ritual at dusk each field day: breath- or spray-fog the grid to
register wet (1), dry 10 min at room air to register dry (0). Insertion
resistance out of range (grid corroded) → `sf-h04` flag, row suppressed.
The row's honest claim is **surface wetness presence**, index 0/1 only —
no %-film inference, no ppm poetry.

## 6. Air T/RH shelter

1. Multi-plate louvre shield (BOM line 8), white PETG, open below.
2. Bottom plate ≥ 1.5 m above ground and expected to stay above the
   settled snow-pack (Biratori plan ~1.0 m + margin); strap to dedicated
   pole, never the mast.
3. ≥ 5 m from shed walls,heat exhausts, livestock pens; morning-shade
   azimuth (E-SE shading matters more in December).
4. Quarterly blow-out of dust from SHT31 membrane (gentle bulb air).
5. Annual bench check against the psychrometer standard: RH deviating
   > 3 % or T > 0.3 °C → note `cf-drift` + recalibration service window.
   Until re-passed, certificate survives but rows wear `cf-drift`.

## 7. Firmware logging / uplink interval

| Node | Uplink | Content |
| --- | --- | --- |
| S2104 soil ×2 | **15 min** | VWC %, soil T °C, battery mV |
| LSN50v2-S31 | **15 min** | T °C, RH %, battery |
| SN50v3 (MOD12) | **15 min**, tips carried as since-last-count | tip count, wetness bit, battery |

Why 15 min: evaporation/spray-window dynamics (WS3.3 needs a 3-hourly
resolution minimum — 15 min oversamples without hurting the
8500 mAh energy budget: 4×/h × ~55 mA.tx burst ≪ self-discharge floor).
Rain tips are edge-integrated by the node, so the 15-min bucket is loss-
free for intensities ≤ 5.6 mm/h per bucket-slot.

Clock discipline: every payload carries its own phenomenon/availability/
generated times (UTC). Drift > 90 s (checked against gateway RX time) →
`sf-h05`, rows suppressed until re-sync. The adapter rejects payload rows
whose intrinsic clocks mis-order (tested in
`tests/test_sensor_ingest.py`).

## 8. Data QC flags (attached per record by the ingest path)

| Flag | Meaning | Effect on store eligibility |
| --- | --- | --- |
| `sf-h01` | battery < 3.0 V (Li-SOCl2 knee approaching) | rows pass,但 flagged in the event ledger; battery line maintained |
| `sf-h02` | RSSI/SNR marginal (< −120 dBm / < −7 dB at SF7-9) | rows pass; link-budget review booked |
| `sf-h03` | GPS/fix-stamp mismatch on relocated node | rows pass; relocation note mandatory in calibration ledger |
| `sf-h04` | wetness grid resistance out of band | row suppressed (no value) |
| `sf-h05` | clock drift > 90 s | rows suppressed until resync |
| `cf-borderline` | calibration RMSE marginal | certificate halved-life (§4.5) |
| `cf-drift` | annual check deviation noted | rows flagged, recalibration scheduled |
| `cf-sited-shadowed` | gauge sited at 1–2× obstruction | permanent siting annotation |

Flags travel in the device JSON (`qc: {...}`); the governed store carries
what the rules bless; the calibration ledger in `field-notes/calibrations/`
carries everything, refusal-included, mirroring the repo's
"refusals are stored" doctrine.

## 9. Certificate lifetime table

| Instrument | Event | Full life | Marginal | After firmware flash |
| --- | --- | --- | --- | --- |
| Soil VWC probe | §4 3-pt gravimetric | 12 mo | 6 mo (`cf-borderline`) | both probes re-consistency-gated (§4.6) |
| Rain gauge | §5.2 pour ×3 | 12 mo (+Nov/prime event) | n/a | count-chain integrity re-checked |
| Wetness grid | §5.4 endpoints | per-season install | — | re-endpoint at install |
| Air T/RH | §6 bench | 12 mo | flagged `cf-drift` | re-bench |

Expiration is mechanical: `recalibration_due` in each payload; the adapter
refuses rows whose phenomenon time crossed the due date (`R-sensor:
expired certificate`). Renewal = fresh event, fresh IRI, fresh payloads;
history is never edited.

## 10. Who signs

Human operator performs events (one Saturday afternoon per quarter);
`fieldhw` maintains this protocol, the adapter, and the ledger plumbing.
Certificates enter payloads as two strings and one error object — the
minimal, auditable surface the store already governs.
