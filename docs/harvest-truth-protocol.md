# Harvest-truth protocol — 明日の現地採証 (Sprint-X1, task-18)

**Where:** 富保 farm, the soybean parcel · **When (GO window):**
**明日 09:00–13:00** (combine and weighbridge both operate; afternoon wind
risk rises on the coast) · **Bring:** phone (charged), the weigh ticket,
a pocket notebook. **Total time: 25–40 minutes inside the window.**

> **TL;DR for the founder (lead: read this verbatim)**
> Bring back FIVE things: ① the scale TICKET (photo of it + its number
> and kg), ② a MOISTURE number (borrowed meter, or grab a litre sample
> bag for the lab), ③ the GRADE slip if the elevator grades, ④ THREE
> photos (combine dashboard counter, the scale printout, one field-edge
> shot standing IN a corner), ⑤ three CORNER pins — stand in NW/NE/SW
> corners with the phone's map app and note lat/lon **plus the accuracy
> figure the screen shows**. Then read the numbers to the agent over the
> phone (he types them), or fill the one-page JSON in this file. Every
> item you bring is scored against what the engine PREDICTED — this is
> how the machine learns its own error bars. None of it is wasted even
> if the combine breaks: the pins alone start the farm's first real map.

---

## 1. The checklist — what, why, how it scores

### a) Weigh ticket (裁定基准)

| | |
| --- | --- |
| **DO** | Photograph the ticket whole; copy the TICKET NUMBER and GROSS WEIGHT (kg) exactly as printed; note the weigh time and whose scale it was. |
| **WHY** | The mass is the hard floor under every yield claim the record will ever make. Forecast/biomass talk is cheap; a weighbridge ticket is the one number no one argues with. |
| **HOW THE LEDGER SCORES THE ENGINE** | The engine predicted R8 (full maturity) at **2026-09-27** for this season (calibrated `hokkaido-short` profile). The delta to YOUR weigh date is recorded two ways: calendar days, and **GDD-days** (the season's thermal time between modelled maturity and the real combine stop — the dry-down head-room the model gave you or stole from you). Within ±7 days → **HIT**; outside → **MISS** (both honest; a miss with the numbers attached is exactly how the model gets tuned for 2027). Weighing BEFORE the predicted R8 is flagged explicitly — either wet grain went in early or the model is late; your moisture% arbitrates. |

### b) Moisture %

| | |
| --- | --- |
| **DO** | If a meter is borrowable (JA office/ neighbour): one reading, note the meter model. Else: a sealed litre bag from the tank mid-stream, labelled with the time — lab later. |
| **WHY** | Validates the R8/harvest-timing advice end-to-end: 12–15 % is combination-grade soy (VERIFY [MOISTURE-NORMS]: product label and the buyer's spec govern, not the engine). Wet-but-weighed grain means the model was right to say "not yet" — you overrode it; dry grain after a long wait means the model's R8 ran conservative. |
| **HOW THE LEDGER SCORES** | Transported verbatim on the bundle with its instrument (or `sample-bag-for-lab`); cross-checked against the R8-delta note when the weigh preceded R8. No engine threshold pretends to grade your moisture — the lab and the buyer do. |

### c) Grade / class certificate (等級証明)

| | |
| --- | --- |
| **DO** | If the elevator/co-op grades: photograph the certificate, note class (1等/2等…) and who graded. |
| **WHY** | Future quality claims (the 加工適性 pedigree of Yukihomare-class beans) must trace to an INSPECTOR, never to the engine's optimism. |
| **HOW THE LEDGER SCORES** | This sprint: stored witness fact (`grade-certificate`, class string, photo name). Quality-vs-season scoring arrives with a graded-history backlog — declared TODO in the protocol. |

### d) Photos: combine counter, scale printout, field edge

| | |
| --- | --- |
| **DO** | ① combine display showing the AREA counter (ha) if visible; ② the truck scale printout next to the ticket; ③ one shot from a field corner along the edge. |
| **WHY** | ①+ticket → implied kg/ha once the polygon exists (no area counter, no per-ha math — the record refuses to divide by a guessed hectare); ③ anchors the polygon attempt to a visible landmark. |
| **HOW THE LEDGER SCORES** | Filenames ride the bundle as `photos`; the per-ha implication is computed LATER, only when BOTH the area counter value and a surveyed polygon exist — never before (house rule: no divisions by folklore). |

### e) Three corner GPS pins — the parcel's first map

| | |
| --- | --- |
| **DO** | Stand IN each of NW / NE / SW corners (SE optional). Map app → drop/hold pin → read LAT, LON and the ACCURACY figure on screen (e.g. "±3.5 m"). Say them slowly if dictating. Order matters: corners in sequence. |
| **WHY** | Ends the point-pin era: three corners → the first real BoundaryVersion → every future satellite/soil/weather join gains a polygon to land on. Accuracy from the screen is recorded; UNKNOWN accuracy stays unknown — never averaged into fairy-tale metres. |
| **HOW THE LEDGER SCORES** | On intake the pins attempt a boundary version via the Store (tenure `unknown` until a source exists; worst stated accuracy governs; any missing accuracy ⇒ `accuracy_unknown=true`). This is not scored vs the engine — it CREATES the thing later scores will need. |

## 2. Entering it — the ONE command

After the visit the agent (or you) saves the filled template and runs:

```
python -m farm_ontology.harvest_truth founder-filled.json --at 2026-10-XXTHH:MM:SS+09:00 --out harvest-truth-result.json
```

* `--at` = the intake moment (any time after the visit; aware ISO stamp).
* Add optional context keys INSIDE the JSON for self-scoring:
  `_sowing` ("2026-05-20T09:00:00+09:00"), `_cultivar_profile`
  ("hokkaido-short"), `_season_rows` (paste the season's daily rows from
  the record when the agent has them — without them the truth is still
  stored and the validation row honestly abstains).
* Output: observation committed via the Store (or its refusal, verbatim),
  boundary attempt, the ValidationRow, and the teaser line, e.g.:

```
prediction vs actual [observation/boundary/...]: model R8 2026-09-27 →
weigh 2026-09-30 = +3 d (+21.5 GDD-d) — HIT (±7 d tolerance, engine
agronomy-engine-v0-config-2)
```

## 3. The EXACT template (fill the nulls; nulls are honest)

```json
{
  "template": "harvest-truth-v1",
  "parcel_iri": null,
  "collection_date": null,
  "dictated_over_phone": null,
  "weigh_ticket": { "ticket_number": null, "gross_weight_kg": null,
                    "weighed_at": null, "scale_description": null },
  "moisture": { "percent": null, "measured_with": null, "sample_bag_photo": null },
  "grade_certificate": { "present": null, "class": null, "inspector": null,
                         "certificate_photo": null },
  "photos": { "combine_display": null, "truck_scale_printout": null,
              "field_edge": null },
  "gps_pins": [],
  "operator_notes": null
}
```

* `parcel_iri` and `collection_date` (YYYY-MM-DD) are required; the
  parcel line is PRE-PRINTED by the agent before the visit.
* `gps_pins`: `[{"corner":"NW","lat":42.70185,"lon":142.40712,
  "accuracy_m":3.5}, …]` — coordinates as STRINGS preserve the exact
  typed precision ("42.701850" keeps its zero).
* `dictated_over_phone`: `true` makes the record state FARMER-RECALL
  (whose mouth the truth came from) — that is an honesty FEATURE, not a
  confession.
* At least ONE witnessed item or the intake refuses (`empty-truth`).

Blank printable copy: `fixtures/harvest/founder-template-blank.json`;
worked examples (synthetic numbers): `founder-filled-hit.json`,
`founder-filled-miss.json`.

## 4. Standing rules this protocol obeys

Screening-class ingest (promotion is another gate); no financial-use
implications; personal_data false by construction (no names in the
template); the Store decides — refusals are surfaced verbatim, never
worked around; timestamps injected (no wall clock); unknown stays
unknown; stdlib-only, offline, deterministic ids (re-filing the same
bundle to a fresh store reproduces the same observation IRI).

**Known modelling nuance, declared:** the R8 crossing used for scoring
comes from the phenology rows' publisher daily-mean temperature. Derived
(max+min)/2 bases cross ~8 days EARLIER on the same fixture — scoring
always uses the publisher mean; the discrepancy is documented, not hidden.

## 5. Reproduction & tests

`tests/test_harvest_truth.py` (27 tests): parse refusals, store law
(unit/screening/recall/IRI-replay), pins→polygon, hit/miss/premature
scoring, tolerance inclusivity, no-extrapolation, teaser shape, and the
no-season-context honest abstention. Run:

```
python -m unittest discover -s tests -t .
```
