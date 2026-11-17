# WS4 field sensor kit — procurement BOM (Biratori soybean pilot)

Agent: `fieldhw` · Task: `task-4` · Prices checked **2026-11-17** (see each
line's source URL; conversions at 1 USD = 159.58 JPY, 1 EUR = 1.1006 USD —
[exchange-rate-api snapshot](https://open.er-api.com/v6/latest/USD), updated
2026-11-17 00:02 UTC). Machine-readable twin: [`bom.csv`](bom.csv).

## 0. Connectivity decision: LoRaWAN, not LTE-M — justified for rural Biratori

The mandate offered LoRaWAN (gateway + nodes) **or** LTE-M trackers. Both
were priced. **LoRaWAN wins for this pilot**:

| Criterion | LoRaWAN (chosen) | LTE-M trackers |
| --- | --- | --- |
| Rural coverage at Biratori (42.70 N, 142.41 E) | Self-provided: one gateway on the farmhouse covers the whole parcel. AS923 (Japan's LoRaWAN band) has no dependence on carrier rollout in valley terrain | LTE-M (Band 1/8/18/19) exists along route 237 and around Biratori-chō but valley dead spots are plausible near ridge plots; a dead spot silently kills rows |
| Recurring cost | ¥0/mo (backhaul = existing farm broadband; optional MVNO dongle as fallback) | ¥400–1,000/mo per device per SIM forever |
| 5-year hardware cost at 4 devices | ~¥96k once (incl. gateway) | ¥24k upfront + ¥24k–60k cumulative subscriptions |
| Winter survivability | Li-SOCl2 nodes unaffected by base-station behaviour | Tracker batteries drain faster in cold reporting cycles |
| Failure surface | One gateway, ours, diagnosable on-site | Carrier QoS opaque, SIM contracts churn |
| Risk | Gateway is a single point — mitigated by inexpensive spare policy later | Locked to a vendor's cloud + eSIM plan |

The LTE-M path remains the sanctioned **fallback** for the far ridge if the
first week's link-budget walk (§4) shows marginal RSSI; the BOM therefore
carries a dongle+SIM *optional* line, not an order.

## 1. Radio-legality note (honest sourcing)

Lines sourced from ELSPINA (Dear IoT) are **技適取得済み** (Japan radio-equipment certified).
The Seeed S2104 (basket A) ships multi-band 863–928 MHz and requires the
operator to set the **AS923** channel plan via its Bluetooth app; operating
it in Japan is legal only under its certification status — Seeed's S210X
line carries TELEC/Japan certifications per their CE/FCC documentation set
(product page, Documents & Certification table, fetched 2026-11-17), which
we record in the cost log at purchase (invoice + cert PDF filed under
`hardware/`). If procurement prefers zero paperwork, choose **basket B**
(100 % ELSPINA-certified hardware) at +¥13.9k.

## 2. Basket A — recommended order (grand total ¥112,458 ≈ US$704.70)

| # | Item (qty) | Model | Price (source) | ¥ ext | Principle | Stated accuracy | Calibration need | IP | Hokkaido winter survivability | Battery life |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Capacitive soil-moisture + T probe ×2 | [SenseCAP S2104](https://www.seeedstudio.com/SenseCAP-S2104-LoRaWAN-Soil-Temperature-and-Moisture-Sensor-p-5357.html) | US$121.95 each (Seeed Bazaar) | 38,922 | FDR capacitive VWC + soil T probe | ±3 % VWC (0–50 %), ±5 % (50–100 %); T ±0.5 °C (0–50 °C) | Factory air/water polynomial; **field gravimetric cross-check mandatory before rows earn badges** (protocol §4) | IP66 | −40…+85 °C rated; vendor freeze/waterproof test suite documented; probe body insulated by burial | Up to 10 y claimed (ER34615 Li-SOCl2); **plan 12 mo** at 15-min logging |
| 2 | Air T/RH node | [Dragino LSN50v2-S31](https://shop.elspina.tech/products/lorawan-lsn50v2-31) | ¥15,664 (sale; list ¥19,580) ELSPINA 技適済 | 15,664 | SHT31 capacitive RH + bandgap T, waterproof anti-condensation probe | ±0.2 °C, ±2 %RH class | Factory SHT31; annual RH bench spot-check (protocol §6) | IP65 box; probe anti-condensation | −40…+80 °C; hung in shield **above snow-pack height** (§6 siting) | 8500 mAh Li-SOCl2; 1–2 y at our plan |
| 3 | Generic node (rain + wetness driver) | [Dragino SN50v3-LB](https://shop.elspina.tech/products/lorawan-dragino-sn50v3) | ¥15,400〜 ELSPINA 技適済 | 15,400 | 3× interrupt pins + I2C + ADC; firmware MOD12 = pulse count + SHT31 | Pulse count: digital (no drift); wetness grid qualitative | MOD12 firmware flashing; wetness wet/dry endpoints at install (protocol §5) | IP65, M12 glands | −40…+85 °C; Li-SOCl2 tolerates deep cold | 8500 mAh; 1–2 y at 15-min |
| 4 | Tipping-bucket rain gauge | [misol WH-SP-RG](https://www.hestore.eu/en/prod_10042313.html) (also on [AliExpress JP](https://ja.aliexpress.com/item/1005009819445004.html), [Amazon.co.jp B0G7WNCYC7](https://www.amazon.co.jp/dp/B0G7WNCYC7)) | €30.626 net (HESTORE, stock >25) | 5,380 | Self-emptying bucket, reed pulse **0.2794 mm/tip** (maker data) | Residual ±2–4 % after pour-check (vendor states none — ours is the evidence) | Known-volume pour at install + annually (protocol §5) | Unrated ABS | **Hokkaido rule**: drain + invert over deep winter, else frozen bucket cracks | Passive reed, powered by #3 |
| 5 | Resistive leaf-wetness grid ×2 | [generic wetness module](https://ja.aliexpress.com/item/32831141593.html) | ¥346 (sale ¥311) | 692 | Interdigitated nickel grid; resistance falls when wet | Qualitative wet/dry; coarse index — **never** a film-depth claim | Wet/dry endpoints at install; replace each spring (corrosion) | Bare PCB | Canopy-mounted; snow burial ends the season's reading | Fed from #3 5 V ping |
| 6 | LoRaWAN gateway (SIM-free) | [Dragino LPS8N-JP](https://shop.elspina.tech/products/lorawan-dragino-lps8n) | ¥31,900〜 ELSPINA 技適済 | 31,900 | SX1302 8-ch, AS923; Wi-Fi/Ethernet backhaul to LNS | n/a (network device) | Forwarder config only | IP65 housing | −20…+70 °C indoor-class → **mounted inside shed/eave cavity**, not exposed | Bench PSU (PoE injector incl.) |
| 7 | Outdoor AS923 antenna + 5 m cable | generic 8 dBi fiberglass whip ([cat.](https://www.aliexpress.com/w/wholesale-as923-antenna.html)) | provision ¥2,500 (final at cart) | 2,500 | RF accessory | n/a | none | IP67 body | Mount vertical under eave overhang | n/a |
| 8 | Radiation shield (DIY louvre) | self-made multi-plate | provision ¥500 (filament/UV-tape) | 500 | Natural-draft aspiration of SHT31 (Stevenson principle) | Ventilation → practical ±0.3 °C | Placement discipline IS the calibration (protocol §6) | n/a | PETG printable; pole ≥1.5 m above ground | passive |
| 9 | Mounting misc | clamps, glands, epoxy, desiccant | provision | 1,500 | — | — | — | — | stainless + EPDM | — |
| | **Basket A total** | | | **¥112,458** | | | | | | |

Under the ¥120,000 field-pilot cap with ¥7.5k head-room (consumables buffer
for December mounting surprises).

## 3. Basket B — certification-clean alternative (total ¥126,336)

Identical to Basket A except line 1 becomes:

| Item | Model | Price (source) | ¥ ext | Principle | Stated accuracy | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Dual soil probe + EC + soil T (replaces 2× S2104) | [Dragino SE02-LB](https://shop.elspina.tech/products/lorawan-dragino-se02-lb) | ¥52,800 ELSPINA 技適済 | 52,800 | Two FDR probes, temperature- and EC-compensated | ±3 % (0–53 % V/V), ±5 % (>53 %); EC 2 % FS; soil T <0.3 °C | One node, both mandated probes; EC bonus enables fertility planning (WS3.4); single-BOM-node resilience |

Trade-offs for the human card (§6): Basket A is ¥13.9k cheaper, uses two
independent nodes (spatial redundancy, two failures independent), but asks
procurement to file the S2104 certification evidence at receiving. Basket B
ships with 技適 paperwork attached, adds EC for WS3.4, but couples both
probes to one node/battery and busts the cap by 5.3 %.

Rejected during sourcing, for the record:

- **Seeed SenseCAP M2 Multi-Platform outdoor gateway** — US$99 headline but
  indoor-only accessories at JP stock, and the [outdoor JP-certified
  DLOS8N-JP‑EC25](https://shop.elspina.tech/products/lorawan-dragino-dlos8n)
  landed at **¥128,000** (LTE built-in) — both pushed total >¥190k with
  nodes.
- **Ecowitt WN35 wireless leaf-wetness** ([shop page](https://shop.ecowitt.com/products/wn35)) —
  excellent IP66 sensor but couples to Ecowitt's own 868 MHz gateway
  protocol, fragmenting the kit's single LoRaWAN network.
- **LTE-M trackers** (e.g. [Dragino SN50v3-NB family](https://docs.dragino.com/docs/NB-IoT/rs485-sdi-12-sensor-nodes/sn50v3-nb/)) —
  priced viable in hardware but excluded by §0's coverage/recurring-cost
  argument for Biratori.

## 4. Deployment geometry assumed by this BOM

```
farmhouse shed (power + broadband)
  └─ LPS8N-JP + 8 dBi whip under eave     ← gateway, DNS-kept forwarder → LNS
parcel centre pole (≤ ~600 m LOS)
  ├─ SN50v3-LB + WH-SP-RG + wetness grid   ← MOD12 uplink @15 min
  └─ LSN50v2-S31 in DIY shield @1.5 m      ← T/RH uplink @15 min
soy block A probe (ridge head) @10 cm ... S2104 #1 @15-min uplink
soy block B probe (ridge tail) @30 cm ... S2104 #2 @15-min uplink
```

RSSI walk with a temporary node is part of the RTK field day
([rtk-positioning-plan.md](rtk-positioning-plan.md) §5) so one trip proves
both legs.

## 5. Ops parameters locked by the calibration protocol

Logging/uplink interval: **15 min** for all nodes (see
[calibration-protocol.md §7](calibration-protocol.md)); battery budgets in
the lines above already assume it. Data/QC flags live with each row
(`sf-h01` … `sf-h05`) per [calibration-protocol.md §8](calibration-protocol.md).

## 6. THE one procurement decision for a human card

**Choose Basket A (¥112,458, 2× Seeed S2104, file cert evidence on arrival)
or Basket B (¥126,336, Dragino SE02-LB, all-technically-certified, +EC).**
Nothing is bought. Whichever card signs, the gateway + nodes + gauge +
wetness lines (¥73,536 fixed) are common and go on the same PO.

— end of BOM. Prices in this file were live-checked on 2026-11-17; they rot,
so re-verify at card-signing time.
