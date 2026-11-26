# Backtest T3-R rerun — staged selling on RECORDED CBOT ZS=F (2021-2025)

> **NOT ADVICE — DECISION-SUPPORT EVIDENCE ONLY.** Rendered by `farm_ontology/markets/real_backtest.py` config `real-backtest-t3-1` from RECORDED price rows, in-repo, with point-in-time guards.

> **Evidence hold (still applies):** quote units, threshold comparison, PIT provenance, and this reproduction need independent reconstruction before any downstream claim. The ad-hoc study's dollar values were overstated exactly 100x by a unit mislabel, AND its L2 comparison matched printed cents against the dollar threshold, firing L2 on every session; this rerun converts the printed scale exactly once and evaluates the declared trigger unit-coherently, so the edge MOVES — the comparison section below quantifies it against the documented ad-hoc numbers.

## Headline

Across 5 seasons (2021, 2022, 2023, 2024, 2025), staged selling **$18.60 per hectare** (+1.4% vs all-at-once mean $1,313.22/ha), hit rate 60% (3W/2L), worst season -12.57$/ha, best +71.02$/ha.

Sizing anchor: 3.0 t/ha = 110.2 bu/ha (1 bu = 27.216 kg). Units: closes recorded as printed (US cents per bushel as printed by the Yahoo chart API); fills converted to USD/bu exactly once.

## Per-season table

| season | all-at-once $/ha | staged $/ha | delta $/ha | window dd (printed px) | legs fired |
| --- | --- | --- | --- | --- | --- |
| 2021 | 1,378.42 | 1,373.46 | -4.96 | 72.50 | L1@12.51 (harvest_close), L2@12.42 (breakout_11.40), L3@12.44 (post_december_wasde) |
| 2022 | 1,509.87 | 1,535.99 | +26.12 | 52.50 | L1@13.70 (harvest_close), L2@13.58 (breakout_11.40), L3@14.61 (post_december_wasde) |
| 2023 | 1,411.76 | 1,425.15 | +13.39 | 190.75 | L1@12.81 (harvest_close), L2@12.66 (breakout_11.40), L3@13.36 (post_december_wasde) |
| 2024 | 1,143.90 | 1,131.34 | -12.57 | 86.00 | L1@10.38 (harvest_close), L3@9.96 (post_december_wasde), L2@10.42 (breakout_11.40_window_exhausted) |
| 2025 | 1,122.13 | 1,193.15 | +71.02 | 126.75 | L1@10.18 (harvest_close), L2@11.57 (breakout_11.40), L3@10.94 (post_december_wasde) |

Mean intra-window price drawdown (printed scale): 105.700 (worst 190.75). Wins per season order: [False, True, True, False, True].

## Comparison with the ad-hoc real-data study (2026-11-22, session .tmp scripts)

Documented in `reports/backtest-t3-real-REPORT.md`; restated here as NUMBERS with the pointer, per the no-redistribution rule (its own dollar magnitudes carry the 100x unit mislabel flagged in that report).

| season | ad-hoc delta $/ha | this rerun delta $/ha | win flipped? |
| --- | --- | --- | --- |
| 2021 | -496.00 | -4.96 | no |
| 2022 | +2,612.00 | +26.12 | no |
| 2023 | +1,339.00 | +13.39 | no |
| 2024 | -1,521.00 | -12.57 | no |
| 2025 | +2,488.00 | +71.02 | no |

Why the numbers move: (1) UNIT — the ad-hoc engine consumed printed cents labelled as USD, inflating every revenue 100x; (2) TRIGGER EVALUATION — the ad-hoc L2 compared printed cents against the $11.40 threshold, so L2 fired on the first window session every year, whereas unit-coherent evaluation (close ≥ 11.40 USD/bu ⇔ ≥ 1140 printed cents) makes L2 a real conditional: it exhausts in 2024 (no window close ≥ 1140 cents) and fires mid-window in 2025 (2025-11-17 @ 1157.25). Hit rate is unchanged (3W/2L both runs); the aggregate edge is +1.4% here vs 0.7% documented.

## Method (identities, verifiably coded)

- baseline $/ha = declared-harvest-day close (÷100 printed-scale conversion) × total bushels/ha;
- staged $/ha = Σ leg-weight × leg-fill-price(÷100) × bushels/ha;
- triggers AS CODED (module constants borrowed from `farm_ontology.markets.backtest`): L1 40% at the declared harvest-day session; L2 30% on the first close ≥ $11.40/bu (derivation: 11.40 USD/bu sits ABOVE the printed AMS northwest cash band (10.7900-11.3400, recorded 2026-11-16 in farm_ontology/ams_soybean_bid.py) by roughly half the band width: crossing it signals the cash market has left the recorded regime. It is a DERIVED THRESHOLD from one printed report, not a fitted signal; re-derivation belongs to a later, evidenced tuning pass.); L3 30% on the first close strictly after the declared December-WASDE day; unfired legs exit at the last window close, marked window-exhausted in the leg log;
- calendar-carry: on a declared harvest day with no exchange session, the L1 fill is the last recorded close BEFORE the day, marked `calendar-carry` in the leg note.

## Data and provenance (what makes these rows REAL)

- source envelope: source=`yahoo`, symbol=`ZS=F`, interval=`1d`, captured_at=`2026-11-20T00:00:00+00:00`, unit_note=`US cents per bushel as printed by the Yahoo chart API`;
- citation: https://finance.yahoo.com/quote/ZS=F/history;
- 1256 recorded daily closes; carry rows on 2024-10-05, 2025-10-05 (non-trading declared harvest days);
- every row passed `validate_real_frame`: symbol/interval/source/unit match the envelope, capture instants are timezone-aware, closes are finite and positive, carry rows repeat the last recorded close, and anonymous rows are refused (audit gap G4 closed in-repo).

## Point-in-time discipline (no hindsight leaks)

- rows carry `captured_at`; the known-at filter (`real_backtest.known_at`) exposes only rows captured at or before the queried instant — the same `facts_at` semantics `pit_dataset` gives recorded feed facts, applied at row level because a captured candle is not a recorded-feed fact (`pit_dataset.MarketFact` is typed to the five recorded feeds).
- every season run cuts its input at `decision_time` (`real_backtest.validate_decision_cut` refuses a frame still carrying rows captured after the decision instant — `LeakError` — and the walk then sees only `known_at` rows), so the engine cannot be handed tomorrow's close by accident.
- the breakout LEVEL's own derivation stays anchored in the recorded present (AMS band via `pit_dataset.matrix` as-of join, as documented in the original T3 report); declaring it as a perfect-knowledge assumption, not as evidence.

## Assumptions (each one declared)

- harvest days: October 5 each season (`SEASON_CALENDAR`), weekends covered by calendar-carry;
- December WASDE day: declared as the 10th; the recorded header stores no release instant;
- yield: the strategy book's own 3.0 t/ha scenario constant;
- the breakout level: derived from the recorded 2026 AMS band, known to fire immediately on futures (see Limitations).

## Limitations (BRUTAL, by contract)

- EVIDENCE HOLD (carried from the 2026-11-22 study): quote units, threshold comparison, point-in-time provenance, and reproduction need independent reconstruction; treat every number as provisional.
- PRINTED SCALE, DECLARED: the chart API prints US cents per bushel; the revenue identity divides by 100 exactly once. The earlier ad-hoc run labelled the same numbers 'USD per bushel' and overstated each harvest-year revenue a hundredfold (percentages were unaffected).
- PERFECT KNOWLEDGE: the breakout level and the December WASDE DAY are declared assumptions (see backtest.SEASON_CALENDAR); trigger visibility in advance is NOT evidenced here.
- NO SLIPPAGE, NO COSTS, INFINITE DEPTH: sales fill at the session close, fee-free; real cash sales move price and pay basis, handling and drying discounts.
- CONTINUOUS FRONT CONTRACT: Yahoo's ZS=F series is the plotted continuous front month, not an exchange-official settlement tape; roll effects are not modelled and closes are not settlement prices.
- L1 CALENDAR-CARRY: on non-trading declared harvest days the whole comparison anchors on the previous session's close (marked calendar-carry in the leg log); the fill is a convention, not a trade.
- DEGENERATE BREAKOUT: 11.40 USD/bu derives from the AMS cash band, but futures traded 9.39-17.69 USD/bu over these seasons, so L2 fires on the first window session almost every year; the measured edge is therefore essentially L3 post-WASDE timing. Re-deriving the level per season is future evidenced work, NOT claimed here.
- SURVIVORSHIP OF RULES: 40/30/30 and 11.40 are declared, not fitted; any parameter tuned on the same five seasons would flatter itself.
- FIVE SEASONS, SMALL SAMPLE: five seasons cannot separate a rule from luck; the confidence interval is wider than the numbers.
- WINDOW MECHANICS: pending legs sell at the last window close when their trigger never fires; that forced exit is generous.
- LICENSING (CONTROLLED ASSET): the recorded series is committed for internal research with COMMERCIAL redistribution unverified (commit 3249f47b; tests/fixtures/real/README.md; docs/legal/commercial-punchlist.md). This report carries NUMBERS only, never the underlying series.
- GRANT WALL: every recorded feed's permits_financial_use is False (grants/state.json); none of this touches live money and nothing here authorises a sale, hedge, or tradable-alpha claim.
- NOT ADVICE: decision-support evidence only; the stamp travels with every derived artefact.

## The grant wall (the reader's standing reminder)

Every recorded feed's `permits_financial_use` is False today (grants/state.json: reasons `specimen`/`no_grant`). This run describes what a RULE would have done on RECORDED closes — it authorises no sale, no hedge, and no product claim of tradable alpha.

## Reproduce

```powershell
python -m unittest tests.test_markets_real_backtest -v
# recorded-fixture rerun (opt-in gate protecting the committed
# controlled asset — see tests/fixtures/real/README.md):
$env:FARM_REAL_FIXTURES='1'; python -m unittest tests.test_markets_real_backtest -v
# regenerate this document from any local capture (the raw series
# itself is never committed outside the controlled fixture):
python -c "from farm_ontology.markets import real_backtest as rb; 
f = rb.load_recorded_frame('<capture-path>', captured_by='<operator>'); 
print(rb.write_report(rb.run_real_backtest((f,), yield_t_per_ha=3.0), 
'reports/backtest-t3-rerun-REPORT.md'))"
```

