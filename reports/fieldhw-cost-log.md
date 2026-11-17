# WS4 cost log — fieldhw (sensor kit + positioning pilot)

Owner: `fieldhw` · Task: `task-4` · Status: **PLAN ONLY — NOTHING PURCHASED**
as of 2026-11-17. Procurement requires the human card described in
[`sensor-kit-bom.md §6`](../hardware/sensor-kit-bom.md); this log gains a
receipt row per real purchase AFTER that signature.

FX basis (snapshot 2026-11-17 00:02 UTC,
[open.er-api.com](https://open.er-api.com/v6/latest/USD)): **1 USD =
159.58 JPY · 1 EUR = 0.908584 USD (= 1.1006 USD/EUR → ~144.99 JPY/EUR
effective)**. Rows in JPY-native are immune to the USD rate.

## 1. Planned purchases — Basket A (recommended), grand total ¥112,458 ≈ US$704.70

| # | Line | Model / MPN | Source & URL | Native price | ¥ ext | Cost kind |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 2× soil VWC+T probe | SenseCAP S2104 | [Seeed Bazaar](https://www.seeedstudio.com/SenseCAP-S2104-LoRaWAN-Soil-Temperature-and-Moisture-Sensor-p-5357.html) — US$121.95 ea (2026-11-17) | $243.90 | 38,922 | one-off |
| 2 | Air T/RH node | Dragino LSN50v2-S31 | [ELSPINA Dear IoT](https://shop.elspina.tech/products/lorawan-lsn50v2-31) — ¥15,664 sale (list ¥19,580) 技適済 | ¥15,664 | 15,664 | one-off |
| 3 | Universal node (rain+wetness) | Dragino SN50v3-LB | [ELSPINA](https://shop.elspina.tech/products/lorawan-dragino-sn50v3) — ¥15,400〜 技適済 | ¥15,400 | 15,400 | one-off |
| 4 | Tipping-bucket gauge | misol WH-SP-RG (0.2794 mm/tip) | [HESTORE](https://www.hestore.eu/en/prod_10042313.html) — €30.626 net (≈€37.13 inc VAT class); alt sellers [AliExpress JP](https://ja.aliexpress.com/item/1005009819445004.html), [Amazon.co.jp](https://www.amazon.co.jp/dp/B0G7WNCYC7) | €30.63 | 5,380 | one-off |
| 5 | 2× leaf-wetness grid | generic LM393 grid module | [AliExpress JP](https://ja.aliexpress.com/item/32831141593.html) — ¥346 (sale ¥311) | ¥692 | 692 | consumable |
| 6 | LoRaWAN gateway (SIM-free) | Dragino LPS8N-JP (AS923, PoE, 技適済) | [ELSPINA](https://shop.elspina.tech/products/lorawan-dragino-lps8n) — ¥31,900〜 | ¥31,900 | 31,900 | one-off |
| 7 | Outdoor AS923 antenna + cable | 8 dBi fiberglass whip | AliExpress JP category — provision, final at cart | ¥2,500 | 2,500 | provision |
| 8 | Radiation shield (DIY) | self-printed louvre | filament/UV-tape on hand | ¥500 | 500 | provision |
| 9 | Mounting misc | clamps/glands/desiccant | local hardware run | ¥1,500 | 1,500 | provision |
| | **TOTAL A** | | | | **112,458** | |

Head-room vs the ¥120,000 field-pilot cap: **¥7,542**.

## 2. Alternative — Basket B (certification-clean), total ¥126,336 ≈ US$791.72

Line 1 swaps to one Dragino SE02-LB dual soil probe
([ELSPINA](https://shop.elspina.tech/products/lorawan-dragino-se02-lb),
¥52,800, 技適済, FDR ±3 %/±5 %, EC bonus). Difference vs A: **+¥13,878**;
cap overshoot ¥6,336 (5.3 %). Fixed portion common to BOTH baskets
(total − soil line) = **¥73,536**.

## 3. Positioning pilot — planned spends (separate envelope)

| Action | Amount | Trigger |
| --- | --- | --- |
| NTRIP trial weekend (option A) | **¥0** (free demo casts/trial windows, checked 2026-11-17) | after kit order lands |
| Paid regional RTK service if cast absent | ¥1,500–6,000/yr | decision tree [rtk-positioning-plan.md §6](../hardware/rtk-positioning-plan.md) |
| Secondhand ZED-F9P rover + antenna (option B, only if A fails) | ¥53,000–75,000 | human card #2 |
| Survey base rental week (option B add-on) | ¥8,000–15,000 | human card #2 |
| Permanent farm base (DEFERRED, priced) | ≈¥75,000 | Year-2 route |

## 4. Recurring-cost bookkeeping (LoRaWAN decision dividend)

| Item | Monthly |
| --- | --- |
| LoRaWAN network server (TTN community tier) | ¥0 |
| Backhaul (existing farm broadband) | ¥0 incremental |
| Optional LTE dongle + MVNO SIM fallback (BOM optional line) | ~¥1,000 when activated |
| Contingency battery/probe consumables yr-1 | ~¥1,400/mo amortised (ER34615 spare + wetness grids) |

The kit adds **¥0/mo unavoidable** — the LTE-M alternative would have
started a ¥400–1,000/mo per-device subscription; declined per
[BOM §0](../hardware/sensor-kit-bom.md).

## 5. Purchase-order discipline (WS4 ground rule)

1. Human card picks Basket A or B (single decision; everything else on
   the PO is common).
2. `fieldhw` or operator executes the buy; **every receipt** appends a
   row to §1.1-table style below with invoice date and paid price.
3. Any price drift > 10 % between card-signature and purchase pauses the
   buy for re-confirmation (prices rot; checked-stamps in
   [`bom.csv`](../hardware/bom.csv) are 2026-11-17).
4. Certification evidence (S2104 TELEC/Japan docs, if Basket A) scans
   into `hardware/` the day the parcel arrives.

**Purchase rows (live log — empty until the card):**

| date | item | qty | paid | currency | vendor | invoice ref | recorder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| — | (nothing purchased as of 2026-11-17) | | | | | | |
