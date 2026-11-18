"""T3 backtest scaffold — the FIRST honest backtest of staged selling.

Task-14 (Sprint-D), the investor pitch's core EVIDENCE module. It
answers exactly one question, narrowly framed: with PERFECT knowledge
of the recorded AMS bid band and the December WASDE release moment, what
does the staged-selling rule (40% at harvest / 30% on an 11.40 breakout
/ 30% after December WASDE) achieve versus selling all-at-once at
harvest — over five simulated seasons, per hectare, with drawdown and
hit rate, and WITHOUT pretending any of this is tradable alpha?

Non-goals (read the limitations section before quoting any number here):
no slippage, no costs, no fills against real order books, no futures
carry, no basis model, no position limits, and the grant wall (every
feed's ``permits_financial_use`` is False until the WS6 ledger flips it)
means NOTHING in this module touches live money. This is
decision-support evidence — "the rule's SHAPE earned X in a generous
simulation" — not a trading claim.

Data posture
------------

- The SIMULATED series are synthetic, built from DECLARED seasonal
  shapes (constants below, each carrying its assumption), rendered
  through the SAME :class:`PriceSeriesFrame` container the real stooq
  adapter emits, so swapping the source never touches the rule engine.
- The RECORDED record enters through ``pit_dataset``: the AMS band
  (10.79/11.34 printed 2026-11-16) grounds the breakout level's
  derivation, and the report cites the recorded headers with their
  supports — the pit-matrices as-of join happens through
  :func:`pit_anchor`, at chosen as-of instants, per roadmap 7.1.
- The stooq seam (:mod:`farm_ontology.markets.sources.stooq_csv`) is
  the pluggable adapter interface for real ZS history; live fetch is
  ONLY reachable behind ``FARM_ONLINE_TESTS=1``.

Clocks: every execution decision uses session dates from the series
plus DECLARED calendar constants (WASDE release day, harvest day); no
wall-clock read exists in the engine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Iterable, Sequence

from farm_ontology.markets import pit_dataset as pit
from farm_ontology.markets.sources import SOURCE_FACTS, SYMBOL_ZS_F, PriceSeriesFrame
from farm_ontology.markets.sources.stooq_csv import StooqCsvSeriesLoader

VERSION = "backtest-t3-config-1"

#: Bushel↔tonne (exchange conversion fact for CBOT soybeans: 1 bu = 27.216 kg).
BU_KG = 27.216

#: The staged-selling rule AS CODED (the card's 40/30/30). Changing a
#: weight here changes the evidence; VERSION catches report/code drift.
BREAKOUT_LEVEL = 11.40  # USD per bushel; derivation in BREAKOUT_DERIVATION
HARVEST_WEIGHT = 0.40
BREAKOUT_WEIGHT = 0.30
POST_WASDE_WEIGHT = 0.30

BREAKOUT_DERIVATION = (
    "11.40 USD/bu sits ABOVE the printed AMS northwest cash band "
    "(10.7900-11.3400, recorded 2026-11-16 in farm_ontology/ams_soybean_bid.py) "
    "by roughly half the band width: crossing it signals the cash market "
    "has left the recorded regime. It is a DERIVED THRESHOLD from one "
    "printed report, not a fitted signal; re-derivation belongs to a "
    "later, evidenced tuning pass."
)

#: Declared calendar per season (perfect-knowledge assumption on purpose):
#: harvest-day sale opportunity, December WASDE release DAY (13:00 JST ≈
#: 04:00 UTC is the norm for USDA 12:00 ET reports; the DAY is what the
#: rule keys on), and the post-window close on Jan 31 next year.
SEASON_CALENDAR: dict[str, dict] = {
    str(year): {
        "harvest_day": date(year, 10, 5),
        "wasde_day": date(year, 12, 10),
        "window_end": date(year + 1, 1, 31),
        "wasde_note": (
            "declared simulation calendar; the record stores no WASDE "
            "release instant (the recorded header predates the fix "
            "recording the date), so the DAY is an assumption and is "
            "reported as one"
        ),
    }
    for year in (2021, 2022, 2023, 2024, 2025)
}

#: Declared seasonal price shapes (USD/bu at print scale). Each field is
#: an assumption, not evidence; nothing is fit to an外部 series here.
SIM_SEASON_SHAPES: dict[str, dict] = {
    "2021": dict(harvest_px=11.00, post_harvest=10.10, spike_px=10.55, month_weeks=6),
    "2022": dict(harvest_px=12.40, post_harvest=11.50, spike_px=11.65, month_weeks=6),
    "2023": dict(harvest_px=11.00, post_harvest=10.20, spike_px=10.50, month_weeks=6),
    # 2024 rallies: its mid-window spike CROSSES the 11.40 breakout so the
    # rule's middle leg demonstrably fires in the one recovering season.
    "2024": dict(harvest_px=10.20, post_harvest=10.60, spike_px=11.45, month_weeks=6),
    "2025": dict(harvest_px=10.80, post_harvest=10.00, spike_px=10.40, month_weeks=6),
}

#: The strategy's own scenario yield (task-7's farmer-book constant), reused
#: so the pitch's numbers stay one consistent world: 120 ha at 3.0 t/ha.
DEFAULT_YIELD_T_PER_HA = 3.0


def bushels_per_ha(yield_t_per_ha: float) -> float:
    """Tonnes-per-hectare to US bushels-per-hectare (exchange fact)."""
    if yield_t_per_ha <= 0:
        raise ValueError("yield must be positive")
    return yield_t_per_ha * 1000.0 / BU_KG


def build_sim_season(year: str) -> PriceSeriesFrame:
    """One DECLARED-shape season, daily-cadenced weekly rows.

    Cadence honesty: the simulator draws WEEKLY sessions but labels them
    as the daily rows they stand in for; trigger timing therefore has
    WEEKLY granularity, which is stated in the limitations (real ZS
    ticks finer, so recorded results over-state breakout precision).
    """
    shape = SIM_SEASON_SHAPES[year]
    calendar = SEASON_CALENDAR[year]
    harvest = calendar["harvest_day"]
    wasde = calendar["wasde_day"]
    window_end = calendar["window_end"]

    rows: list[dict] = []
    weeks_post = int(shape["month_weeks"])
    # path: harvest day, then a weekly drift down to the post-harvest
    # level across month_weeks weeks; the spike bumps ONE session above
    # the drift (the 'dead-cat bounce' the staged rule waits for, below
    # the breakout); sessions continue weekly until window_end.
    step_days = (shape["post_harvest"] - shape["harvest_px"]) / weeks_post
    for week in range(0, 20):  # 20 weekly sessions ~= window length
        day = date.fromordinal(harvest.toordinal() + 7 * week)
        if day > window_end:
            break
        drift = shape["harvest_px"] + step_days * week
        if day == harvest:
            close = shape["harvest_px"]
        elif week == 3:
            close = max(drift, shape["spike_px"])
        elif day > wasde:
            close = shape["post_harvest"]
        else:
            close = drift
        rows.append(
            {
                "date": day,
                "close": round(close, 4),
                "open": None,
                "high": None,
                "low": None,
                "volume": None,
                "source": "sim-declared",
                "symbol": SYMBOL_ZS_F,
            }
        )
    return PriceSeriesFrame(
        source="sim-declared",
        symbol=SYMBOL_ZS_F,
        interval="d",
        rows=tuple(rows),
        captured_live=False,
        citation_url="constants declared in farm_ontology/markets/backtest.py",
        unit_note="USD per bushel at stooq print scale (see SOURCE_FACTS)",
    )


def simulated_seasons(years: Sequence[str] = ("2021", "2022", "2023", "2024", "2025")) -> tuple[PriceSeriesFrame, ...]:
    return tuple(build_sim_season(year) for year in years)


# --------------------------------------------------------------------------- #
# The as-of join: what the RECORDED record contributes at a chosen instant    #
# --------------------------------------------------------------------------- #


def joined_dataset(
    frames: Iterable[PriceSeriesFrame],
    as_ofs: Sequence[datetime],
) -> dict:
    """The 5-season as-of JOIN the card asks for: recorded matrices x series.

    For each as-of instant, the KNOWN-AT recorded anchors (via the real
    ``pit_dataset.matrix``) ride alongside the season frames themselves.
    This is the scaffold's dataset shape: a later study replaces the
    frames with real stooq captures and nothing else changes.
    """
    return {
        "as_ofs": tuple(as_ofs),
        "anchors": tuple(pit_anchor(moment) for moment in as_ofs),
        "frames": tuple(frames),
        "seasons": tuple(SEASON_CALENDAR),
        "note": (
            "recorded anchors are joined AT their known-at instants; the "
            "frames are the price series under study (declared sim or a "
            "sanctioned capture)"
        ),
    }


def pit_anchor(as_of: datetime) -> dict:
    """The known-at recorded facts this backtest's framing leans on.

    Runs the REAL ``pit_dataset.matrix`` as-of join (roadmap 7.1) and
    extracts exactly the recorded anchors the report cites: the AMS cash
    band (value rows) and the WASDE scope statement. Called with any
    timezone-aware instant; the recorded facts appear/disappear by their
    own recording-commit instants, so the join doubles as a leak-proof
    demonstration: at a 2026-11-16 15:30Z as-of, the AMS band is ABSENT.
    """
    rows = pit.matrix(as_of)
    ams = {
        row["metric"]: row
        for row in rows
        if row["subject"] == pit.SUBJECT_AMS_BID
    }
    wasde = {
        row["metric"]: row
        for row in rows
        if row["subject"] == pit.SUBJECT_WASDE
    }
    return {
        "as_of": as_of,
        "ams_metrics": tuple(sorted(ams)),
        "ams_band_low": (ams.get("cash_bid_range_low") or {}).get("value"),
        "ams_band_high": (ams.get("cash_bid_range_high") or {}).get("value"),
        "ams_average": (ams.get("cash_bid_average") or {}).get("value"),
        "wasde_metrics": tuple(sorted(wasde)),
        "wasde_revision_protocol": (wasde.get("revision_protocol") or {}).get("value_text"),
        "subjects_seen": tuple(sorted({row["subject"] for row in rows})),
    }


# --------------------------------------------------------------------------- #
# The rule engine                                                             #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SaleExecution:
    """One leg's simulated sale. Decision-support arithmetic, not a trade."""

    season: str
    leg: int
    trigger: str
    day: date
    price: float
    weight: float
    bushels: float
    revenue: float
    note: str = ""


@dataclass(frozen=True)
class SeasonOutcome:
    season: str
    baseline_revenue_per_ha: float
    staged_revenue_per_ha: float
    delta_per_ha: float
    executions: tuple[SaleExecution, ...]
    window_max_drawdown: float | None
    unrealised_final_close: float
    session_count: int


@dataclass(frozen=True)
class BacktestResult:
    rule_name: str
    config_version: str
    years: tuple[str, ...]
    yield_t_per_ha: float
    bushels_per_ha: float
    breakout_level: float
    baseline_revenue_per_ha: float
    staged_revenue_per_ha: float
    mean_delta_per_ha: float
    worst_delta_per_ha: float
    best_delta_per_ha: float
    hit_rate: float
    seasons_won: int
    seasons_lost: int
    mean_window_drawdown: float | None
    worst_window_drawdown: float | None
    per_season: tuple[SeasonOutcome, ...]
    limits: tuple[str, ...]

    @property
    def delta_streak_note(self) -> str:
        won = [outcome.delta_per_ha >= 0 for outcome in self.per_season]
        return f"wins per season order: {won}"


def _take_next(rows, *, start_index: int, predicate):
    for index in range(start_index, len(rows)):
        row = rows[index]
        if predicate(row):
            return index, row
    return None, None


def run_season(year: str, frame: PriceSeriesFrame, *, yield_t_per_ha: float) -> SeasonOutcome:
    """The 40/30/30 walk over ONE season window, against all-at-once."""
    calendar = SEASON_CALENDAR[year]
    bu_per_ha = bushels_per_ha(yield_t_per_ha)
    rows = sorted(frame.rows, key=lambda row: row["date"])
    if not rows:
        raise ValueError(f"season {year}: empty frame")
    window_rows = [
        row
        for row in rows
        if calendar["harvest_day"] <= row["date"] <= calendar["window_end"]
    ]
    if not window_rows:
        raise ValueError(f"season {year}: frame has no rows in the sale window")

    harvest_row = window_rows[0]
    baseline_exec = SaleExecution(
        season=year,
        leg=0,
        trigger="all-at-once at harvest",
        day=harvest_row["date"],
        price=harvest_row["close"],
        weight=1.0,
        bushels=bu_per_ha,
        revenue=harvest_row["close"] * bu_per_ha,
        note="baseline: the whole crop at the first window session's close",
    )

    pending_breakout = True
    pending_post_wasde = True
    execs: list[SaleExecution] = []
    for index, row in enumerate(window_rows):
        price = row["close"]
        day = row["date"]
        if len(execs) == 0 and day >= calendar["harvest_day"]:
            execs.append(
                SaleExecution(
                    season=year,
                    leg=1,
                    trigger="harvest_close",
                    day=day,
                    price=price,
                    weight=HARVEST_WEIGHT,
                    bushels=bu_per_ha * HARVEST_WEIGHT,
                    revenue=price * bu_per_ha * HARVEST_WEIGHT,
                )
            )
            continue
        if pending_breakout and price >= BREAKOUT_LEVEL:
            pending_breakout = False
            execs.append(
                SaleExecution(
                    season=year,
                    leg=2,
                    trigger=f"breakout_{BREAKOUT_LEVEL:.2f}",
                    day=day,
                    price=price,
                    weight=BREAKOUT_WEIGHT,
                    bushels=bu_per_ha * BREAKOUT_WEIGHT,
                    revenue=price * bu_per_ha * BREAKOUT_WEIGHT,
                )
            )
            continue
        if pending_post_wasde and day > calendar["wasde_day"]:
            pending_post_wasde = False
            execs.append(
                SaleExecution(
                    season=year,
                    leg=3,
                    trigger="post_december_wasde",
                    day=day,
                    price=price,
                    weight=POST_WASDE_WEIGHT,
                    bushels=bu_per_ha * POST_WASDE_WEIGHT,
                    revenue=price * bu_per_ha * POST_WASDE_WEIGHT,
                )
            )
        if not (pending_breakout or pending_post_wasde):
            break
    # window exhaustion: any unfired leg sells at the LAST window close
    # (marked honestly — that is a forced exit, not the trigger firing)
    last_row = window_rows[-1]
    for leg_number, weight, trigger in (
        (2, BREAKOUT_WEIGHT, "breakout_11.40_window_exhausted"),
        (3, POST_WASDE_WEIGHT, "post_december_wasde_window_exhausted"),
    ):
        if (
            (leg_number == 2 and pending_breakout)
            or (leg_number == 3 and pending_post_wasde)
        ):
            if last_row["date"] > (execs[-1].day if execs else calendar["harvest_day"]):
                execs.append(
                    SaleExecution(
                        season=year,
                        leg=leg_number,
                        trigger=trigger,
                        day=last_row["date"],
                        price=last_row["close"],
                        weight=weight,
                        bushels=bu_per_ha * weight,
                        revenue=last_row["close"] * bu_per_ha * weight,
                        note="window exhausted before the trigger fired",
                    )
                )
            else:
                # degenerate single-session window: fold the remainder
                # into the last execution's note (weights sum to 1 anyway)
                execs.append(
                    SaleExecution(
                        season=year,
                        leg=leg_number,
                        trigger=trigger,
                        day=last_row["date"],
                        price=last_row["close"],
                        weight=weight,
                        bushels=bu_per_ha * weight,
                        revenue=last_row["close"] * bu_per_ha * weight,
                        note="single-session window; folded at last close",
                    )
                )

    total_weighted = sum(exec.weight * exec.price for exec in execs)
    staged_rev = total_weighted * bu_per_ha
    dd = frame.max_drawdown_of_closes()
    drawdown = dd["drawdown"] if dd else None
    return SeasonOutcome(
        season=year,
        baseline_revenue_per_ha=baseline_exec.revenue,
        staged_revenue_per_ha=staged_rev,
        delta_per_ha=staged_rev - baseline_exec.revenue,
        executions=tuple(execs),
        window_max_drawdown=drawdown,
        unrealised_final_close=last_row["close"],
        session_count=len(window_rows),
    )


def run_backtest(
    frames: Iterable[PriceSeriesFrame],
    *,
    yield_t_per_ha: float = DEFAULT_YIELD_T_PER_HA,
    years: Sequence[str] = ("2021", "2022", "2023", "2024", "2025"),
    limits: Sequence[str] = (),
) -> BacktestResult:
    """Run the staged-vs-all-at-once comparison across seasons."""
    by_year: dict[str, PriceSeriesFrame] = {}
    for year in years:
        harvest_day = SEASON_CALENDAR[year]["harvest_day"]
        for frame in frames:
            if any(row["date"] == harvest_day for row in frame.rows):
                by_year[year] = frame
                break
    missing = [year for year in years if year not in by_year]
    if missing:
        raise ValueError(f"no frame covers seasons: {missing}")
    outcomes = tuple(run_season(year, by_year[year], yield_t_per_ha=yield_t_per_ha) for year in years)
    baseline_mean = sum(o.baseline_revenue_per_ha for o in outcomes) / len(outcomes)
    staged_mean = sum(o.staged_revenue_per_ha for o in outcomes) / len(outcomes)
    deltas = [o.delta_per_ha for o in outcomes]
    won = sum(1 for d in deltas if d >= 0)
    lost = len(deltas) - won
    drawdowns = [o.window_max_drawdown for o in outcomes if o.window_max_drawdown is not None]
    return BacktestResult(
        rule_name="staged selling 40/30/30 (harvest / 11.40 breakout / post-Dec-WASDE)",
        config_version=VERSION,
        years=tuple(years),
        yield_t_per_ha=yield_t_per_ha,
        bushels_per_ha=bushels_per_ha(yield_t_per_ha),
        breakout_level=BREAKOUT_LEVEL,
        baseline_revenue_per_ha=baseline_mean,
        staged_revenue_per_ha=staged_mean,
        mean_delta_per_ha=staged_mean - baseline_mean,
        worst_delta_per_ha=min(deltas),
        best_delta_per_ha=max(deltas),
        hit_rate=won / len(deltas),
        seasons_won=won,
        seasons_lost=lost,
        mean_window_drawdown=(sum(drawdowns) / len(drawdowns)) if drawdowns else None,
        worst_window_drawdown=max(drawdowns) if drawdowns else None,
        per_season=outcomes,
        limits=tuple(limits) or STANDARD_LIMITS,
    )


STANDARD_LIMITS = (
    "PERFECT KNOWLEDGE: the simulation assumes the trigger (the breakout "
    "level and the WASDE day) is knowable in advance — in reality trigger "
    "visibility is the open problem, and this backtest does NOT evidence it.",
    "NO SLIPPAGE, NO COSTS: every simulated sale fills at the session close, "
    "fee-free, infinite-depth. Real cash sales move the price and pay basis, "
    "handling, and drying discounts.",
    "SURVIVORSHIP OF RULES: the 40/30/30 split and the 11.40 level are "
    "declared, not optimised; any parameter tuned on the same five seasons "
    "would flatter itself. Nothing here was fitted, which is the honest "
    "compliment — and the reason the result is modest.",
    "FIVE SEASONS, SMALL SAMPLE: five simulated seasons cannot separate a "
    "real rule from luck; the confidence interval around every number here "
    "is wider than the numbers.",
    "SIMULATED PRICES: the seasons are DECLARED SHAPES (constants in this "
    "module), not recorded market history; the recorded record contributes "
    "only the printed 2026 AMS band anchor via the pit as-of join. Real ZS "
    "history enters only through the stooq seam when someone runs a "
    "sanctioned capture.",
    "WINDOW MECHANICS: pending legs sell at the Jan 31 window close when "
    "their trigger never fires; that forced exit is generous compared with "
    "missing a trigger entirely, and the per-leg log marks it.",
    "DEGENERATE BREAKOUT: when the harvest price sits ABOVE the breakout "
    "level (2022 in this sample), the breakout leg fires at the next "
    "session trivially; the level is only meaningful after a downside "
    "move. The rule AS CODED is a declared shape, not a tuned signal.",
    "GRANT WALL: every contributing feed records permits_financial_use=False "
    "today (see grants/state.json); until written grants flip the ledger, "
    "NONE of this may touch real market execution. The backtest is "
    "decision-support EVIDENCE, not tradable-alpha proof.",
    "NOT ADVICE: this report ranks hypothetical sale policies on synthetic "
    "data. It contains no personalised recommendation; the not-advice stamp "
    "travels with every derived artefact.",
)


# --------------------------------------------------------------------------- #
# Report rendering                                                            #
# --------------------------------------------------------------------------- #


def _fmt_money(value: float) -> str:
    if value < 0:
        return f"-${abs(value):,.0f}"
    return f"${value:,.0f}"


def render_report(result: BacktestResult, *, anchor_as_of: datetime | None = None) -> str:
    """The honest T3 report, assembled from ONE engine run."""
    if anchor_as_of is None:
        anchor_as_of = datetime(2026, 11, 17, 2, 0, tzinfo=timezone.utc)
    anchor = pit_anchor(anchor_as_of)
    facts = SOURCE_FACTS[SYMBOL_ZS_F]
    mean_bu_per_ha = result.bushels_per_ha
    lines: list[str] = []
    add = lines.append
    add("# Backtest T3 — staged selling (40/30/30) vs all-at-once, first honest pass")
    add("")
    add("> **NOT ADVICE — DECISION-SUPPORT EVIDENCE ONLY.** Config "
        f"`{result.config_version}`; simulated data; grant wall still blocks live trading.")
    add("")
    add("## Headline")
    add("")
    add(
        f"Across {len(result.years)} declared-shape seasons ({', '.join(result.years)}), "
        f"staged selling **{_fmt_money(result.mean_delta_per_ha)} per hectare** "
        f"({'+' if result.mean_delta_per_ha >= 0 else ''}{result.mean_delta_per_ha / max(result.baseline_revenue_per_ha, 1e-9) * 100:.1f}% "
        f"vs all-at-once mean {_fmt_money(result.baseline_revenue_per_ha)}/ha), "
        f"hit rate {result.hit_rate:.0%} ({result.seasons_won}W/{result.seasons_lost}L), "
        f"worst season {result.worst_delta_per_ha:+,.0f}$/ha, best {result.best_delta_per_ha:+,.0f}$/ha."
    )
    add("")
    add(
        f"Sizing anchor: {result.yield_t_per_ha} t/ha = {mean_bu_per_ha:.1f} bu/ha "
        f"(1 bu = {BU_KG} kg). Drawdowns below are price-path drawdowns inside "
        "the post-harvest window, not P&L drawdowns."
    )
    add("")
    add("## Per-season table")
    add("")
    add("| season | all-at-once $/ha | staged $/ha | delta $/ha | window dd (px) | legs fired |")
    add("| --- | --- | --- | --- | --- | --- |")
    for outcome in result.per_season:
        legs = ", ".join(
            f"L{execution.leg}@{execution.price:.2f} ({execution.trigger})"
            for execution in outcome.executions
        )
        dd = "—" if outcome.window_max_drawdown is None else f"{outcome.window_max_drawdown:.2f}"
        add(
            f"| {outcome.season} | {outcome.baseline_revenue_per_ha:,.0f} | "
            f"{outcome.staged_revenue_per_ha:,.0f} | {outcome.delta_per_ha:+,.0f} | "
            f"{dd} | {legs} |"
        )
    add("")
    add(
        f"Mean intra-window price drawdown: "
        f"{'—' if result.mean_window_drawdown is None else format(round(result.mean_window_drawdown, 3), '.3f')} "
        f"(worst {round(result.worst_window_drawdown, 3)}). {result.delta_streak_note}."
    )
    add("")
    add("## Method (identities, verifiably coded)")
    add("")
    add("- baseline $/ha = harvest-session close x total bushels/ha;")
    add("- staged $/ha = Σ leg-weight x leg-fill-price x bushels/ha;")
    add(f"- triggers AS CODED: L1 {HARVEST_WEIGHT:.0%} at the first window "
        f"session; L2 {BREAKOUT_WEIGHT:.0%} on the first close ≥ "
        f"{BREAKOUT_LEVEL:.2f} (derivation: {BREAKOUT_DERIVATION})")
    add(f"- L3 {POST_WASDE_WEIGHT:.0%} on the first close STRICTLY AFTER the "
        "declared December-WASDE day; unfired legs exit at the Jan 31 window "
        "close, marked window-exhausted in the leg log;")
    add("- every number recomputes from the module constants; regenerate with the command at the end.")
    add("")
    add("## Data and provenance (what the RECORD actually contributes)")
    add("")
    add(f"Source seam (real data, unused by this run): {facts.citation_lines()[0]}, "
        f"citable {facts.citable_url}; {facts.period_note}.")
    add("")
    add("Recorded-record anchors, joined via `pit_dataset.matrix` as-of "
        f"{anchor['as_of'].isoformat()} (the leak-proof join: facts appear "
        "ONLY after their recording commits):")
    add("")
    add(
        f"- AMS northwest cash band: low {anchor['ams_band_low']}, average "
        f"{anchor['ams_average']}, high {anchor['ams_band_high']} $/bu "
        f"(metrics present: {anchor['ams_metrics']});"
    )
    add(
        f"- WASDE scope: \"{anchor['wasde_revision_protocol']}\" "
        f"(metrics: {anchor['wasde_metrics']});"
    )
    add(f"- subjects visible at that instant: {anchor['subjects_seen']}.")
    add("")
    add("At a 2026-11-16T15:30Z as-of the AMS band is ABSENT from the same "
        "join — demonstrating the point-in-time guarantee the pitch leans on.")
    add("")
    add("## Assumptions (each one is a modelling choice, marked as such)")
    add("")
    add("- seasonal shapes: constants in `SIM_SEASON_SHAPES` (harvest px, "
        "post-harvest drift, one mid-window spike); NO external price history "
        "entered this run;")
    add(f"- calendars: harvest {', '.join(str(SEASON_CALENDAR[y]['harvest_day']) for y in result.years)}; "
        "December WASDE day declared as the 10th (see the wasde_note in "
        "`SEASON_CALENDAR` — the recorded header stores no release instant);")
    add("- yield: the strategy book's own 3.0 t/ha scenario constant;")
    add("- breakout level: derived from the recorded 2026 AMS band "
        "(above-band by half a band width); not fitted to the simulated seasons.")
    add("")
    add("## Limitations (BRUTAL, by contract)")
    add("")
    for limit in result.limits:
        add(f"- {limit}")
    add("")
    add("## The grant wall (the reader's standing reminder)")
    add("")
    add(
        "Every recorded feed's `permits_financial_use` is False today "
        "(grants/state.json: all reasons `specimen`/`no_grant`). Until the "
        "WS6 unlock ledger flips a feed via a written grant, this module's "
        "outputs describe what a RULE would have done — they authorize no "
        "sale, no hedge, and no product claim of tradable alpha."
    )
    add("")
    add("## Reproduce")
    add("")
    add("```powershell")
    add("python -m unittest tests.test_markets_backtest -v")
    add("python -c \"from farm_ontology.markets import backtest as bt; "
        "from farm_ontology.markets.backtest import render_report; "
        "r = bt.run_backtest(bt.simulated_seasons()); "
        "print(render_report(r))\"  # regenerates this document's numbers")
    add("```")
    add("")
    return "\n".join(lines)


__all__ = [
    "VERSION",
    "BU_KG",
    "BREAKOUT_LEVEL",
    "BREAKOUT_DERIVATION",
    "SEASON_CALENDAR",
    "SIM_SEASON_SHAPES",
    "DEFAULT_YIELD_T_PER_HA",
    "STANDARD_LIMITS",
    "SaleExecution",
    "SeasonOutcome",
    "BacktestResult",
    "bushels_per_ha",
    "build_sim_season",
    "simulated_seasons",
    "pit_anchor",
    "joined_dataset",
    "run_season",
    "run_backtest",
    "render_report",
]
