> GENERATED ARTIFACT: every number below is re-derived by
> `farm_ontology.markets.backtest` at import time; regenerate with the
> command in the Reproduce section. Branch `ws/sprint/backtest-t3`,
> base 3bd7505 (task-14, Sprint-D).

# Backtest T3 — staged selling (40/30/30) vs all-at-once, first honest pass

> **NOT ADVICE — DECISION-SUPPORT EVIDENCE ONLY.** Config `backtest-t3-config-1`; simulated data; grant wall still blocks live trading.

## Headline

Across 5 declared-shape seasons (2021, 2022, 2023, 2024, 2025), staged selling **-$29 per hectare** (-2.4% vs all-at-once mean $1,221/ha), hit rate 20% (1W/4L), worst season -60$/ha, best +55$/ha.

Sizing anchor: 3.0 t/ha = 110.2 bu/ha (1 bu = 27.216 kg). Drawdowns below are price-path drawdowns inside the post-harvest window, not P&L drawdowns.

## Per-season table

| season | all-at-once $/ha | staged $/ha | delta $/ha | window dd (px) | legs fired |
| --- | --- | --- | --- | --- | --- |
| 2021 | 1,213 | 1,153 | -60 | 1.35 | L1@11.00 (harvest_close), L3@10.10 (post_december_wasde), L2@10.10 (breakout_11.40_window_exhausted) |
| 2022 | 1,367 | 1,332 | -35 | 1.35 | L1@12.40 (harvest_close), L2@12.25 (breakout_11.40), L3@11.50 (post_december_wasde) |
| 2023 | 1,213 | 1,160 | -53 | 1.20 | L1@11.00 (harvest_close), L3@10.20 (post_december_wasde), L2@10.20 (breakout_11.40_window_exhausted) |
| 2024 | 1,124 | 1,179 | +55 | 0.98 | L1@10.20 (harvest_close), L2@11.45 (breakout_11.40), L3@10.60 (post_december_wasde) |
| 2025 | 1,190 | 1,138 | -53 | 1.20 | L1@10.80 (harvest_close), L3@10.00 (post_december_wasde), L2@10.00 (breakout_11.40_window_exhausted) |

Mean intra-window price drawdown: 1.217 (worst 1.35). wins per season order: [False, False, False, True, False].

## Method (identities, verifiably coded)

- baseline $/ha = harvest-session close x total bushels/ha;
- staged $/ha = Σ leg-weight x leg-fill-price x bushels/ha;
- triggers AS CODED: L1 40% at the first window session; L2 30% on the first close ≥ 11.40 (derivation: 11.40 USD/bu sits ABOVE the printed AMS northwest cash band (10.7900-11.3400, recorded 2026-11-16 in farm_ontology/ams_soybean_bid.py) by roughly half the band width: crossing it signals the cash market has left the recorded regime. It is a DERIVED THRESHOLD from one printed report, not a fitted signal; re-derivation belongs to a later, evidenced tuning pass.)
- L3 30% on the first close STRICTLY AFTER the declared December-WASDE day; unfired legs exit at the Jan 31 window close, marked window-exhausted in the leg log;
- every number recomputes from the module constants; regenerate with the command at the end.

## Data and provenance (what the RECORD actually contributes)

Source seam (real data, unused by this run): source: stooq.com, citable https://stooq.com/q/d/?s=zs.f; daily (i=d) and intraday intervals (i=60/30/15/5) for the continuous back-adjusted front contract; history depth seen by the recorder was not stored here and is NOT claimed.

Recorded-record anchors, joined via `pit_dataset.matrix` as-of 2026-11-17T02:00:00+00:00 (the leak-proof join: facts appear ONLY after their recording commits):

- AMS northwest cash band: low 10.79, average 11.16, high 11.34 $/bu (metrics present: ('cash_bid_average', 'cash_bid_range_high', 'cash_bid_range_low', 'report_status'));
- WASDE scope: "a forecast of annual balances, revised in later months" (metrics: ('issue_cycle', 'release_rule', 'revision_protocol', 'storage_scope'));
- subjects visible at that instant: ('ams_usda:nw-soybean-cash-bid-current', 'fao_fpi:food-price-index', 'imf_pcps:all-commodity-index', 'usda_wasde:supply-demand-forecast', 'wb_pink:crude-oil-average').

At a 2026-11-16T15:30Z as-of the AMS band is ABSENT from the same join — demonstrating the point-in-time guarantee the pitch leans on.

## Assumptions (each one is a modelling choice, marked as such)

- seasonal shapes: constants in `SIM_SEASON_SHAPES` (harvest px, post-harvest drift, one mid-window spike); NO external price history entered this run;
- calendars: harvest 2021-10-05, 2022-10-05, 2023-10-05, 2024-10-05, 2025-10-05; December WASDE day declared as the 10th (see the wasde_note in `SEASON_CALENDAR` — the recorded header stores no release instant);
- yield: the strategy book's own 3.0 t/ha scenario constant;
- breakout level: derived from the recorded 2026 AMS band (above-band by half a band width); not fitted to the simulated seasons.

## Limitations (BRUTAL, by contract)

- PERFECT KNOWLEDGE: the simulation assumes the trigger (the breakout level and the WASDE day) is knowable in advance — in reality trigger visibility is the open problem, and this backtest does NOT evidence it.
- NO SLIPPAGE, NO COSTS: every simulated sale fills at the session close, fee-free, infinite-depth. Real cash sales move the price and pay basis, handling, and drying discounts.
- SURVIVORSHIP OF RULES: the 40/30/30 split and the 11.40 level are declared, not optimised; any parameter tuned on the same five seasons would flatter itself. Nothing here was fitted, which is the honest compliment — and the reason the result is modest.
- FIVE SEASONS, SMALL SAMPLE: five simulated seasons cannot separate a real rule from luck; the confidence interval around every number here is wider than the numbers.
- SIMULATED PRICES: the seasons are DECLARED SHAPES (constants in this module), not recorded market history; the recorded record contributes only the printed 2026 AMS band anchor via the pit as-of join. Real ZS history enters only through the stooq seam when someone runs a sanctioned capture.
- WINDOW MECHANICS: pending legs sell at the Jan 31 window close when their trigger never fires; that forced exit is generous compared with missing a trigger entirely, and the per-leg log marks it.
- DEGENERATE BREAKOUT: when the harvest price sits ABOVE the breakout level (2022 in this sample), the breakout leg fires at the next session trivially; the level is only meaningful after a downside move. The rule AS CODED is a declared shape, not a tuned signal.
- GRANT WALL: every contributing feed records permits_financial_use=False today (see grants/state.json); until written grants flip the ledger, NONE of this may touch real market execution. The backtest is decision-support EVIDENCE, not tradable-alpha proof.
- NOT ADVICE: this report ranks hypothetical sale policies on synthetic data. It contains no personalised recommendation; the not-advice stamp travels with every derived artefact.

## The grant wall (the reader's standing reminder)

Every recorded feed's `permits_financial_use` is False today (grants/state.json: all reasons `specimen`/`no_grant`). Until the WS6 unlock ledger flips a feed via a written grant, this module's outputs describe what a RULE would have done — they authorize no sale, no hedge, and no product claim of tradable alpha.

## Reproduce

```powershell
python -m unittest tests.test_markets_backtest -v
python -c "from farm_ontology.markets import backtest as bt; from farm_ontology.markets.backtest import render_report; r = bt.run_backtest(bt.simulated_seasons()); print(render_report(r))"  # regenerates this document's numbers
```
