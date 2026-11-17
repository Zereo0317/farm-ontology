# WS4.4 positioning upgrade — from `gps_accuracy: unknown` to a metre-level parcel polygon

Owner: `fieldhw` (`task-4`) · Companion docs:
[`sensor-kit-bom.md`](sensor-kit-bom.md) (field day shares the RSSI walk),
`docs/decision-infra-roadmap.md` §WS4.4-4.5, `docs/field-sop.md`.

## 0. State of play and the retirement condition

Today every boundary the store accepts can carry either `accuracy_m` (a
metre value) or `accuracy_unknown: true` — but never neither and never
both (`R-accuracy`, rules.py:353-359). The Biratori parcel currently rides
on a phone point-fix: the honest `unknown` era
(fieldkit.py:49: `accuracy = "unknown" if metres is None else
"stated-metres"`).

**Retirement condition (adopted):** the `unknown` era is formally
retirable the day a `BoundaryVersion` exists whose

1. `digitising_method` names the RTK field walk executed under this plan
   (`walk-rtk-ntrip` or `walk-rtk-base`),
2. `crs` = `EPSG:4326` with `coordinate_decimals ≥ 6`,
3. `accuracy_m` holds the *worst-vertex* horizontal accuracy from §4.5,
   `accuracy_unknown = false`,
4. `area_ha` is computed by the declared `area_method`,
5. the boundary is appended as a *successor* via `predecessors` to the
   point-era boundary so the store preserves the revision chain
   (BoundaryVersion.predecessors, model.py:116).

From that commit onward, new field observations record metres (the
field-SOP clause "type metres only when the device showed metres" starts
yielding values), and the phrase *"GPS accuracy unknown"* disappears from
new records without anyone editing history — because nothing is deleted
in an append-only store. Unknown tenure, unknown licences: untouched —
only the *positioning* unknown dies.

## 1. Options considered (cost/accuracy/effort, 2026-11-17 yen)

| Option | Hardware cost | Running cost | Expected horizontal accuracy | Setup effort | Operation risk in Biratori |
| --- | --- | --- | --- | --- | --- |
| **A. Smartphone + NTRIP trial** | ¥0 hardware (existing phone) | **¥0 during free trials**: public caster demo windows and RTK-app trial periods (checked 2026-11-17); paid fallback regional RTK service ¥1.5–6k/yr — quote at signup | 0.3–1.0 m typical where a cast covers the Saru river corridor; degrade to 2–5 m where only carrier-style differential remains | Low: install app, subscribe cast, walk | Cast availability is the deciding risk: public casters assume ~20 km baseline norms, and Biratori's inland valley may carry no nearby cast — **the one-weekend trial answers it** |
| **B. Secondhand GNSS RTK module + base rental** | u-blox ZED-F9P secondhand board: ¥45–60k ([AliExpress marketplace envelope](https://www.aliexpress.com/w/wholesale-u-blox-ZED-F9P.html), verify at cart); dual-band GNSS antenna ¥8–15k | Rental base (commercial Japanese survey-gear rental house): ¥8–15k/week — quote on request; or a neighbouring farm's base over a free NTRIP caster | 1–3 cm base-rover; 2–5 cm absolute to benchmark tripod | Medium-high: mount base over a known point (GSI 三角点 near Biratori), configure RTCM3 rover | Cold-boot convergence 5–15 min; cold hands; needs 2 people |
| **C. Smartphone + QZSS correction** (Michibiki MADOCA-PPP capable apps) | ¥0 | ¥0 (public service) | 0.5–1.5 m, improving as MADOCA matures | Low | National coverage but wide accuracy variance; good as a CONTROL arm, not primary |

**Trial ladder chosen: A first (one weekend, ¥0, decidable), B only if A's
residual > 2 m at ≥ 30 % of vertices.** The DIY permanent-base road
(ZED-F9P base at farmhouse publishing NTRIP to the laptop) is parked as
Year-2 infrastructure in `docs/later-routes.md` spirit — priced now
(≈¥75k) so the human card knows what deferral costs.

Receipt-price discipline: every ¥ figure above is a *2026-11-17 market
envelope from public listing pages*, verified live where a direct product
page answered (Seeed/AliExpress-style storefronts render server-side;
GeoNET/EPX quoting flows need a login — those lines are marked
*quote-at-signup*). Purchases post ONLY to
`reports/fieldhw-cost-log.md` after the human card, per WS4 ground rule.

## 2. What the trial buys, concretely

One weekend, two operators (operator + navigator roles), phone on a
1.4 m monopod for multipath hygiene, PDF field sheet printed from this
doc. Deliverables: a walked polygon + per-vertex accuracy, byte-equal to
the JSON shape in §4.6, plus the RSSI walk share of
[sensor-kit-bom.md §4](sensor-kit-bom.md).

## 3. Pre-walk checklist

1. Phone: GPS-test app (e.g. GPSTest/Folia) logging NMEA-GGA at 1 Hz,
   `${phone}` model + OS build in the sheet header (device provenance for
   the record).
2. Cast credentials tested IN the parking lot (fix state RTK-FLOAT seen
   before departure); fallback carrier 4G hotspot paired.
3. Walk canvas: ortho print + previous parcel sketch (point-era
   boundary) loaded to annotate vertex renumbering.
4. Weather gate: no walk in driving rain (phone IP insufficient) or
   > 15 m/s gusts (canopy sway multipath).
5. Benchmark anchors: confirm GSI triangulation point visible from ≥ 2
   vertices, note its 3-sec coords (https://maps.gsi.go.jp) for the
   polygon closure check (§4.4).

## 4. Field-walk procedure (polygon + per-vertex accuracy in metres)

### 4.1 Vertex plan

Parcel corners walked **clockwise, outside 0.5 m from fence line**; a
vertex at every direction change ≥ 15°, hedge-gap entrances, and the two
drain outlets. Vertex numbers V01…Vn annotated live on the ortho print.

### 4.2 Occupancy rule per vertex

| NTRIP fix state | Dwelling | Recorded | Flag |
| --- | --- | --- | --- |
| RTK-FIX | ≥ 30 s dwell | centroid of fixes ± stddev | `w-fixed` |
| RTK-FLOAT | ≥ 60 s dwell | centroid ± bigger stddev, accepted **only if stddev ≤ 2.0 m** | `w-float` |
| DGPS/3D-only | ≥ 120 s dwell | centroid ± stddev; **rejected** if stddev > 5 m | `w-carry` |
| no fix / stddev breach | — | no vertex; walk continues; revisit at end | `w-open` |

Stddev comes from the app's live scatter read at the
mono-pod stationary pose, 3 samples averaged; it is the **only** accuracy
figure admitted to the polygon record. DSD = discipline: no sitting fix
while smoking, no pocket warmth, antenna verticality eyeballed twice.

### 4.3 Polygon hygiene

1. Interior diagonals: after closing, walk two interior diagonals and one
   figure-closure loop returning to V01; residual gap at re-arrival ≤
   1.5 m (with `w-fixed`) or ≤ 3 m (`w-float`) else re-walk the weakest
   quartile of vertices.
2. Hedge-shaded sides (N and W at Biratori get tree skew): re-occupied
   twice; disagreements > 2 m get median-of-occupancies, flagged
   `w-shadow`.
3. Multipath sermons: away from truck/trailer metal ≥ 5 m; antenna above
   head height.

### 4.4 Closure computation

Shoelace area with the equirectangular metre approximation ALREADY in
the repo (`farm_ontology/identity.py:equirectangular_overlap_ha`
documents the honest name of that geometry class) —
`area_method = "shoelace-equirectangular-walk"`; nothing new gets
invented silently. Result cross-checked against the ortho-reported area
within 4 % else re-walk suspicion flag `w-area`.

### 4.5 Per-vertex accuracy → the `accuracy_m` of the BoundaryVersion

```
vertex_accuracy_m[i] = stddev_i × inflation[z]
z = 1 fixed, 2 float, 3 carry-carrying
polygon_accuracy_m = max(vertex_accuracy_m)   ← worst-vertex honesty
```

`stddev_i` at 1σ over ≤ 30 fixes each; the ×2/×3 inflations convert a
dwell statistic into a conservative positional envelope. The exported
record stores BOTH the per-vertex list (for WS5's sprayer boom
trust, later) and the scalar worst (for the BoundaryVersion field).

### 4.6 Export JSON (walk artifact, then stored)

```json
{
  "walk_id": "walk-rtk-ntrip-2026-12-xx",
  "device": "Pixel-8a/Android15-GPSTest3.9",
  "caster": "ntrip.example.jp:2101/mountpoint",
  "vertices": [
    {"v": "V01", "lat": 42.xxxxxx, "lon": 142.xxxxxx,
     "stddev_m": 0.4, "state": "w-fixed", "accuracy_m": 0.4},
    {"v": "V02", "lat": ..., "lon": ..., "stddev_m": 1.6,
     "state": "w-float", "accuracy_m": 3.2}
  ],
  "closure_residual_m": 0.9,
  "diagonal_checks_m": [1.1, 1.4],
  "polygon_accuracy_m": 3.2,
  "area_ha": 0.41,
  "area_method": "shoelace-equirectangular-walk",
  "crs": "EPSG:4326",
  "coordinate_decimals": 6,
  "benchmark_refs": ["GSI 三角点 美園 (3-sec coords recorded)"]
}
```

### 4.7 Into the record (the Store governs; nothing is special-cased)

```python
from farm_ontology.model import BoundaryVersion
from farm_ontology.store import Store
from farm_ontology.build import mint

boundary = BoundaryVersion(
    iri=mint("boundary", "biratori-parcel-walk1"),
    geometry_iri=mint("geometry", "biratori-parcel-walk1"),
    wkt=polygon_wkt_walk,               # §4.6 vertices, CW, 6 decimals
    crs="EPSG:4326",
    digitising_method="walk-rtk-ntrip",
    boundary_date=walk_day,             # tz-aware
    accuracy_unknown=False,
    accuracy_m=artifact["polygon_accuracy_m"],
    area_method="shoelace-equirectangular-walk",
    surveyor=mint("agent", "fieldwalk-operator"),   # role only, no PII
    tenure="unknown",                   # untouched by positioning
    personal_data=False,
    coordinate_decimals=6,
    area_ha=artifact["area_ha"],
    predecessors=(point_era_boundary_iri,),          # revision chain
    accuracy_note="worst-vertex envelope per hardware/rtk-positioning-plan.md",
)
store.add_boundary(boundary, at=walk_day)
```

`R-accuracy` accepts because exactly one of accuracy_m/accuracy_unknown is
set; `R-tenure` untouched; spatial-join refusal rules keep protecting
grid/pixel observations from masquerading as boundary readings.

## 5. Same-day RSSI walk (shared with the sensor kit)

While covering the perimeter: pocket-loRa node (SN50v3 configured
transmit-only bench mode or a 2nd phone with the dragino BLE app) logs
RSSI at each vertex for the planned gateway location(s). Rule:
**RSSI ≥ −115 dBm at every planned soil-probe site** ⇒ LoRaWAN confirmed
single-gateway; any weaker vertex documents a duty-cycle-free excuse for
either raising the antenna (BOM line 7) or invoking the LTE-M fallback
(BOM optional line 11). The sheet note goes in
`hardware/` as an annex at deployment time, not now — plan is final when
the walk JSON is final.

## 6. Decision tree (this plan, formalised)

```
Weekend trial (option A) executed?
├─ ≥70 % vertices w-fixed OR w-float(σ≤2.0 m)  → ACCEPT: polygon lands,
│    accuracy_m = worst-vertex, `unknown` era retired per §0.
├─ 30–70 % good vertices                       → RETRY A once (different
│    cast/window) + pre-book option B rental.
└─ <30 % good vertices                         → ESCALATE to option B
     (rented base wk ¥8–15k + 2nd-hand F9P rover quoted): decision card
     goes to the human BEFORE money moves; walk repeats under option B.
```

## 7. What this plan deliberately does NOT do

- No drone photogrammetry alternative (drone licensing + pilot certs are
  a WS6/legal-adjacent affair; the runway cost dwarfs a walk).
- No cadastral claim. Tenure stays `unknown` until its own evidence —
  accurate geometry ≠ ownership.
- No permanent base-station build (parked, priced in §1).
- No API calls: the walk artifact is a JSON file in `field-notes/`
  land, exactly like every other field record. Offline-first, always.

— end of positioning plan.
