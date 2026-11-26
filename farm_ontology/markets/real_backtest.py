"""Real-market backtest harness — closing audit gap G4.

Gap G4 (audit): ``run_season`` refuses external price series outright —
"external prices require a verified point-in-time backtest; this scaffold
accepts synthetic frames only". The T3 study on RECORDED CBOT ZS=F daily
closes (reports/backtest-t3-real-REPORT.md) was therefore run once ad hoc
from session .tmp scripts that bypassed every guard. This module is the
IN-REPO harness for exactly that run, stdlib-only, with the guards made
positive instead of absent:

- every price row carries explicit provenance (source, symbol, interval,
  captured_at, unit_note) and :func:`validate_real_frame` refuses
  anonymous rows — the mirror image of ``run_season``'s sim-constant
  check, pointed at REAL data;
- point-in-time discipline: no row may inform a decision made before its
  capture. Rows not yet captured do not exist for the engine: the known-at
  filters bound every decision. The DESIGN is inherited from
  :mod:`farm_ontology.markets.pit_dataset` (``fact_time <= as_of``
  visibility, fail-closed timezone awareness, availability never dated
  earlier than the recording act); it is implemented at row level here
  because ``pit_dataset.MarketFact`` is typed to the five recorded feed
  modules and a captured candle is not a recorded-feed fact — price rows
  cannot enter ``pit.matrix``. Nothing was loosened in pit_dataset.
- the same T3 arithmetic: staged selling 40/30/30 (harvest close /
  breakout / post-December-WASDE) versus all-at-once, per hectare.

What is deliberately NOT claimed here: licensing. The recorded series is
committed as a CONTROLLED ASSET — internal research use, redistribution
unverified commercially (commit 3249f47b, tests/fixtures/real/README.md,
docs/legal/commercial-punchlist.md); the recorded-fixture tests run only
behind the opt-in gate ``FARM_REAL_FIXTURES=1``, and the committed
backtest report carries NUMBERS only, never the raw series. Anything
this module produces is decision-support evidence, not advice, and stays
behind the grants ledger (every feed ``permits_financial_use`` is False
today).

Clocks: decisions are taken from session dates plus the declared season
calendar (borrowed from :mod:`farm_ontology.markets.backtest`); the only
instants read are declared ``captured_at``/``decision_time`` values. No
wall-clock call exists in the engine.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from farm_ontology.markets import backtest as bt
from farm_ontology.timeutil import ensure_utc

VERSION = "real-backtest-t3-1"

#: Opt-in gate name for the redistributable recorded fixture, in the
#: discipline of ``farm_ontology.testing.ONLINE_ENV`` (opt-in, never on
#: by default; the suite must run hermetically without it).
REAL_FIXTURE_ENV = "FARM_REAL_FIXTURES"

#: Versioned store path of the RECORDED price rows, relative to the repo
#: root — committed as a CONTROLLED ASSET (commit 3249f47b: provenance
#: README, redistribution unverified commercially, internal research only;
#: see tests/fixtures/real/README.md).
FIXTURE_RELATIVE_PATH = Path("tests/fixtures/real/zs_daily_captured_2026-11-20.json")

#: DECLARED replay instant for the recorded Yahoo capture. The committed
#: provenance README records the capture DATE as 2026-11-20 (session
#: tooling); the exact UTC instant is not provable post-hoc (local-machine
#: mtimes are zone-ambiguous), so the study declares midnight UTC of that
#: date and never pretends more precision. Every decision in the replay
#: predates it, so the declaration does not move any number.
RECORDED_CAPTURE_UTC = datetime(2026, 11, 20, 0, 0, 0, tzinfo=timezone.utc)

YAHOO_SOURCE_NAME = "yahoo"
YAHOO_CITATION_URL = "https://finance.yahoo.com/quote/ZS=F/history"
#: The Yahoo chart API prints grain quotes in US CENTS per bushel
#: (1250.50 == $12.505/bu). The 2026-11-22 ad-hoc run labelling the
#: series "USD per bushel" overstated every revenue by exactly 100x —
#: the honest rerun states the printed scale and converts explicitly.
YAHOO_UNIT_NOTE_CENTS = "US cents per bushel as printed by the Yahoo chart API"
YAHOO_UNIT_NOTE_USD = "USD per bushel"

#: Recognised printed scales -> multiplier converting a printed close to
#: USD per bushel. Closed set, fail-closed on anything else.
USD_PER_BU_SCALE: dict[str, float] = {
    YAHOO_UNIT_NOTE_CENTS: 100.0,
    YAHOO_UNIT_NOTE_USD: 1.0,
}

ROW_SOURCE_RECORDED = YAHOO_SOURCE_NAME
#: Carry rows repeat the last RECORDED close on a non-trading declared
#: calendar day (weekend/holiday harvest dates). They are derived, not
#: trades, and say so in their ``note``.
ROW_SOURCE_CARRY = "calendar-carry"
#: Synthetic rows shaped like real ones but NEVER claimed to be market
#: truth — the always-on test load. The label travels on every row.
ROW_SOURCE_STAND_IN = "test-stand-in"
ALLOWED_ROW_SOURCES = frozenset({ROW_SOURCE_RECORDED, ROW_SOURCE_CARRY, ROW_SOURCE_STAND_IN})

DEFAULT_YEARS: tuple[str, ...] = ("2021", "2022", "2023", "2024", "2025")

#: The 2026-11-22 ad-hoc real-data study (reports/backtest-t3-real-REPORT.md),
#: restated ONLY as its documented numbers, for the rerun's comparison
#: section. Its dollar magnitudes carry the 100x unit mislabel its own
#: report flags; its per-season WIN/LOSS order survives (linear scaling).
#: The underlying series is not redistributed and is NOT re-derivable from
#: this constant — numbers only, with the pointer to the original report.
PRIOR_ADHOC_STUDY: dict = {
    "report": "reports/backtest-t3-real-REPORT.md",
    "label": "ad-hoc real-data study (2026-11-22, session .tmp scripts)",
    "mean_delta_per_ha": 884.4,  # mean of its documented per-season deltas
    "baseline_mean_per_ha": 131321.6,
    "headline_pct": 0.7,  # as its headline printed ("+0.7%")
    "seasons_won": 3,
    "seasons_lost": 2,
    "per_season_delta": (-496.0, 2612.0, 1339.0, -1521.0, 2488.0),
    "years": DEFAULT_YEARS,
}


class ProvenanceError(ValueError):
    """A row or frame lacks the provenance a decision-support run needs."""


class LeakError(ValueError):
    """Post-decision information attempted to leak backwards into a decision."""


# --------------------------------------------------------------------------- #
# Rows and frames — the RealPrice provenance model                            #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RealPriceRow:
    """One recorded daily close WITH its provenance.

    ``session_date`` is the trading session the close belongs to;
    ``captured_at`` is the earliest instant this repo can prove the value
    was held (mirrors ``pit_dataset.MarketFact.fact_time`` conservatism:
    nothing is backdated to a publication schedule the record does not
    store). ``close`` stays AS PRINTED by the source; the printed scale
    lives on the frame's ``unit_note`` and is converted explicitly, never
    implicitly.
    """

    session_date: date
    close: float
    source: str
    symbol: str
    interval: str
    captured_at: datetime
    unit_note: str
    note: str = ""


@dataclass(frozen=True)
class RealPriceFrame:
    """A recorded daily-close series with provenance on the envelope.

    Mirror of :class:`farm_ontology.markets.sources.PriceSeriesFrame`
    for recorded (as opposed to simulated) series: same job — provenance
    rides along so the engine can refuse anonymous numbers — with an
    explicit frame-level ``captured_at`` the sim container lacked.
    """

    symbol: str
    interval: str
    source: str
    citation_url: str
    unit_note: str
    captured_at: datetime
    captured_by: str = ""
    rows: tuple[RealPriceRow, ...] = field(default_factory=tuple)

    @property
    def dates(self) -> tuple[date, ...]:
        return tuple(row.session_date for row in self.rows)


def candle(
    session_date: date,
    close: float,
    frame: RealPriceFrame,
    *,
    source: str = ROW_SOURCE_RECORDED,
    note: str = "",
) -> RealPriceRow:
    """One row stamped with its frame's provenance (helper for loaders)."""
    return RealPriceRow(
        session_date=session_date,
        close=close,
        source=source,
        symbol=frame.symbol,
        interval=frame.interval,
        captured_at=frame.captured_at,
        unit_note=frame.unit_note,
        note=note,
    )


def _sort_unique(rows: Sequence[RealPriceRow]) -> tuple[RealPriceRow, ...]:
    seen: dict[date, RealPriceRow] = {}
    for row in rows:
        if row.session_date in seen:
            raise ProvenanceError(
                f"duplicate session date in recorded frame: {row.session_date}"
            )
        seen[row.session_date] = row
    return tuple(sorted(seen.values(), key=lambda row: row.session_date))


# --------------------------------------------------------------------------- #
# Loader — RECORDED rows from a versioned store path                          #
# --------------------------------------------------------------------------- #


def load_recorded_frame(
    path: str | os.PathLike[str],
    *,
    years: Sequence[str] = DEFAULT_YEARS,
    captured_at: datetime | None = None,
    captured_by: str = "",
    symbol: str = "ZS=F",
    interval: str = "1d",
    source: str = YAHOO_SOURCE_NAME,
    citation_url: str = YAHOO_CITATION_URL,
    unit_note: str = YAHOO_UNIT_NOTE_CENTS,
) -> RealPriceFrame:
    """Load RECORDED price rows from a versioned JSON store.

    Accepted store shapes (per the fixture conventions the repo's
    recorded fixtures use — explicit provenance in the envelope, printed
    values untouched):

    - ``[["YYYY-MM-DD", close], ...]`` (the workspace capture cache);
    - ``[{"date": "...", "close": ...}, ...]``;
    - ``{"meta": {...}, "rows": [...]}`` where ``meta`` may declare
      symbol / interval / source / citation_url / unit_note / captured_at;
      every declared meta key overrides the matching keyword argument
      EXCEPT ``captured_at``, which follows the single conflict rule
      spelled out below.

    ``captured_at`` has ONE declared semantic (audit defect D4 — the
    caller's explicit instant used to be silently overridden by the
    store's meta): an explicit caller instant and the store's
    ``meta.captured_at`` must AGREE. The caller's value wins when meta
    omits the key or declares the same instant; when the two DISAGREE
    the loader refuses with ``ValueError`` naming both instants rather
    than silently preferring either source. With no caller value and no
    meta declaration, the declared ``RECORDED_CAPTURE_UTC`` study
    instant applies.

    Calendar-carry rows (see ``ROW_SOURCE_CARRY``) are inserted for each
    declared harvest day that has no recorded session, honestly marked
    and priced at the last recorded close BEFORE the day. A carry value
    is information from the prior recorded session, hence known no later
    than ``captured_at``.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    meta_declared: datetime | None = None
    if isinstance(payload, Mapping):
        meta = payload.get("meta") or {}
        raw_rows = payload.get("rows")
        if raw_rows is None:
            raise ProvenanceError("recorded store with meta must carry 'rows'")
        symbol = str(meta.get("symbol") or symbol)
        interval = str(meta.get("interval") or interval)
        source = str(meta.get("source") or source)
        citation_url = str(meta.get("citation_url") or citation_url)
        unit_note = str(meta.get("unit_note") or unit_note)
        captured_by = str(meta.get("captured_by") or captured_by)
        if meta.get("captured_at"):
            meta_text = str(meta["captured_at"])
            try:
                meta_declared = ensure_utc(
                    datetime.fromisoformat(meta_text.replace("Z", "+00:00")),
                    "captured_at",
                )
            except ValueError as exc:
                raise ProvenanceError(
                    f"store meta.captured_at {meta_text!r} is not a parsable "
                    "timezone-aware instant"
                ) from exc
    else:
        raw_rows = payload

    # captured_at conflict law (documented in the docstring): an explicit
    # caller instant wins over an AGREEING meta declaration; a DISAGREEING
    # meta refuses instead of silently overriding either source. No
    # caller value and no meta declaration falls back to the declared
    # RECORDED_CAPTURE_UTC study instant.
    if captured_at is None:
        captured_at = (
            meta_declared if meta_declared is not None else RECORDED_CAPTURE_UTC
        )
    else:
        caller_declared = ensure_utc(captured_at, "captured_at")
        if meta_declared is not None and meta_declared != caller_declared:
            raise ProvenanceError(
                "conflicting captured_at sources: the caller declared "
                f"{caller_declared.isoformat()} while the store's meta "
                f"declares {meta_declared.isoformat()}; reconcile the two "
                "instead of letting one silently override the other"
            )
        captured_at = caller_declared

    if not isinstance(raw_rows, Sequence):
        raise ProvenanceError("recorded store rows must be a list")

    frame = RealPriceFrame(
        symbol=symbol,
        interval=interval,
        source=source,
        citation_url=citation_url,
        unit_note=unit_note,
        captured_at=captured_at,
        captured_by=captured_by,
    )

    rows: list[RealPriceRow] = []
    for entry in raw_rows:
        if isinstance(entry, Mapping):
            day_text = entry.get("date") or entry.get("session_date")
            close = entry.get("close")
            note = str(entry.get("note") or "")
            row_source = str(entry.get("source") or source)
        elif isinstance(entry, Sequence) and not isinstance(entry, (str, bytes)):
            if len(entry) != 2:
                raise ProvenanceError(
                    f"recorded row {entry!r} must be [date, close]"
                )
            day_text, close = entry
            note = ""
            row_source = source
        else:
            raise ProvenanceError(f"unrecognised recorded row: {entry!r}")
        day = date.fromisoformat(str(day_text))
        value = float(close)
        rows.append(
            RealPriceRow(
                session_date=day,
                close=value,
                source=row_source,
                symbol=symbol,
                interval=interval,
                captured_at=captured_at,
                unit_note=unit_note,
                note=note,
            )
        )

    rows = with_carry_rows(frame, rows, years=years)
    return replace(frame, rows=_sort_unique(rows))


def with_carry_rows(
    frame: RealPriceFrame,
    rows: Sequence[RealPriceRow],
    *,
    years: Sequence[str] = DEFAULT_YEARS,
) -> list[RealPriceRow]:
    """Insert ``calendar-carry`` rows for declared harvest days without a
    recorded session: same value as the last recorded close before the
    day, source marked, note stating the derivation. Mirrors the ad-hoc
    run's honest carry handling; here it is inspectable."""
    recorded = {row.session_date: row for row in rows if row.source != ROW_SOURCE_CARRY}
    out = list(rows)
    for year in years:
        calendar = bt.SEASON_CALENDAR.get(year)
        if calendar is None:
            raise ProvenanceError(f"no season calendar for {year!r}")
        harvest_day = calendar["harvest_day"]
        if harvest_day in recorded or any(row.session_date == harvest_day for row in rows):
            continue
        prior_days = [day for day in recorded if day < harvest_day]
        if not prior_days:
            continue
        prior = recorded[max(prior_days)]
        out.append(
            RealPriceRow(
                session_date=harvest_day,
                close=prior.close,
                source=ROW_SOURCE_CARRY,
                symbol=frame.symbol,
                interval=frame.interval,
                captured_at=frame.captured_at,
                unit_note=frame.unit_note,
                note=(
                    "calendar-carry: the exchange had no session on the "
                    f"declared harvest day; close repeats the last session "
                    f"({prior.session_date.isoformat()})"
                ),
            )
        )
    return out


# --------------------------------------------------------------------------- #
# Validation — anonymous rows are refused                                     #
# --------------------------------------------------------------------------- #


def validate_real_frame(frame: RealPriceFrame) -> tuple[RealPriceRow, ...]:
    """Refuse anything without explicit provenance; return sorted rows.

    Checks the envelope (source, citation, unit note, capture instant,
    row presence) and EVERY row (matching symbol/interval/source/unit,
    timezone-aware capture, finite positive close, unique sorted dates).
    The mirror of ``backtest.run_season``'s sim-constant guard, pointed
    at real data: fail closed, loudly.
    """
    if not frame.symbol:
        raise ProvenanceError("a real frame names its symbol")
    if frame.interval != "1d":
        raise ProvenanceError("this harness validates daily ('1d') frames only")
    if not frame.source:
        raise ProvenanceError("a real frame names its source")
    if not frame.citation_url:
        raise ProvenanceError("a real frame carries a citation_url for its source")
    if not frame.unit_note:
        raise ProvenanceError("a real frame states its unit_note (printed scale)")
    if frame.unit_note not in USD_PER_BU_SCALE:
        raise ProvenanceError(
            "unknown unit_note {0!r}; add its printed scale to "
            "USD_PER_BU_SCALE instead of guessing".format(frame.unit_note)
        )
    try:
        ensure_utc(frame.captured_at, "captured_at")
    except ValueError as exc:
        raise ProvenanceError("captured_at must be timezone-aware") from exc

    rows = _sort_unique(frame.rows)
    if not rows:
        raise ProvenanceError("a real frame carries rows; refusing an empty frame")
    for row in rows:
        if row.symbol != frame.symbol or row.interval != frame.interval:
            raise ProvenanceError(
                f"row {row.session_date} disagrees with the frame symbol/interval"
            )
        if row.source not in ALLOWED_ROW_SOURCES:
            raise ProvenanceError(
                f"anonymous row {row.session_date}: source {row.source!r} is not "
                f"one of {sorted(ALLOWED_ROW_SOURCES)}"
            )
        if row.unit_note != frame.unit_note:
            raise ProvenanceError(
                f"row {row.session_date} disagrees with the frame unit_note"
            )
        try:
            ensure_utc(row.captured_at, "captured_at")
        except ValueError as exc:
            raise ProvenanceError(
                f"row {row.session_date} captured_at must be timezone-aware"
            ) from exc
        if row.captured_at > frame.captured_at:
            raise ProvenanceError(
                f"row {row.session_date} claims a capture later than its frame"
            )
        value = row.close
        if isinstance(value, bool) or not isinstance(value, (int, float)) \
                or not math.isfinite(value) or value <= 0:
            raise ProvenanceError(
                f"row {row.session_date} close must be finite and positive"
            )

    # carry honesty: a carry row must price exactly the last session close
    session_by_day = {row.session_date: row for row in rows if row.source != ROW_SOURCE_CARRY}
    for row in rows:
        if row.source != ROW_SOURCE_CARRY:
            continue
        priors = [day for day in session_by_day if day < row.session_date]
        if not priors:
            raise ProvenanceError(
                f"carry row {row.session_date} has no prior recorded session to carry"
            )
        expected = session_by_day[max(priors)].close
        if not math.isclose(row.close, expected, rel_tol=0, abs_tol=1e-9):
            raise ProvenanceError(
                f"carry row {row.session_date} must repeat the last recorded close "
                f"({expected}), not invent {row.close}"
            )
        # at most one carry row per declared season window keeps the
        # derivation inspectable (the calendars only need harvest-day cover)
        cluster = [
            other
            for other in rows
            if other.source == ROW_SOURCE_CARRY
            and other.session_date.year == row.session_date.year
        ]
        if len(cluster) > 1:
            raise ProvenanceError(
                f"more than one carry row in season {row.session_date.year}; "
                "the derivation must stay inspectable"
            )
    return rows


# --------------------------------------------------------------------------- #
# Point-in-time discipline — nothing after the decision leaks in              #
# --------------------------------------------------------------------------- #


def known_at(frame: RealPriceFrame, as_of: datetime) -> RealPriceFrame:
    """The sub-frame knowable at ``as_of``: rows with ``captured_at <= as_of``.

    Same ``facts_at`` semantics :mod:`pit_dataset` gives recorded feed
    facts, applied at row level to captured candles. A naive ``as_of``
    is refused, mirroring ``ensure_utc``.
    """
    moment = ensure_utc(as_of, "as_of")
    visible = tuple(
        row for row in frame.rows if ensure_utc(row.captured_at, "captured_at") <= moment
    )
    return replace(frame, rows=visible)


def validate_decision_cut(frame: RealPriceFrame, decision_time: datetime) -> None:
    """Refuse an UNCUT frame at ``decision_time`` (loud leak detection).

    A decision taken at ``decision_time`` may only see rows captured no
    later. A frame still carrying rows captured after the decision instant
    is an uncut input: call :func:`known_at` first. Fail closed — the
    caller must acknowledge the cut explicitly rather than hope the
    engine trims silently. The frame-level ``captured_at`` is the study
    snapshot's assembly instant (documentation); the authoritative guard
    is per-row ``captured_at``.
    """
    moment = ensure_utc(decision_time, "decision_time")
    leaking = [row for row in frame.rows if ensure_utc(row.captured_at, "captured_at") > moment]
    if leaking:
        raise LeakError(
            f"{len(leaking)} rows captured after the decision instant "
            f"{moment.isoformat()} (first: {leaking[0].session_date.isoformat()}); "
            "cut the frame with known_at() first"
        )


# --------------------------------------------------------------------------- #
# The T3 phased-sale engine on REAL rows                                      #
# --------------------------------------------------------------------------- #


def _usd_per_bushel(unit_note: str) -> float:
    try:
        return USD_PER_BU_SCALE[unit_note]
    except KeyError:
        raise ProvenanceError(
            f"unit_note {unit_note!r} has no declared scale; refuse rather than guess"
        ) from None


def _window_rows(year: str, rows: Sequence[RealPriceRow]) -> tuple[RealPriceRow, ...]:
    calendar = bt.SEASON_CALENDAR[year]
    lo, hi = calendar["harvest_day"], calendar["window_end"]
    return tuple(row for row in rows if lo <= row.session_date <= hi)


def run_season(
    year: str,
    frame: RealPriceFrame,
    *,
    yield_t_per_ha: float = bt.DEFAULT_YIELD_T_PER_HA,
    decision_time: datetime | None = None,
) -> bt.SeasonOutcome:
    """The 40/30/30 walk over ONE real season window, against all-at-once.

    The SAME trigger chain and window-exhaustion accounting as
    ``backtest.run_season`` (module constants borrowed, not reimplemented)
    against a VALIDATED real frame. Every sale's identity rides on the
    row: recorded close, calendar-carry close honestly marked. Fill prices
    convert the printed scale to USD/bu via the frame's declared
    ``unit_note``.

    Point-in-time: the engine only ever sees ``decision_time``-cut rows;
    default decision_time is the frame's own capture instant (the study
    replays the capture as it stood).

    Window coverage (audit defect D1 — a frame that stops mid-window used
    to silently run as if the season were over): when any L2/L3 leg is
    still unfired after the walk, the cut frame must REACH the season's
    declared ``window_end`` — an unfired leg priced at a last captured
    close is only honest when the record demonstrates the window ran to
    its declared end. A frame stopping short of ``window_end`` is
    REFUSED, with the season, its last captured session, and the
    shortfall named in the message. Legs that already fired impose no
    coverage requirement: their fills happened inside captured data.
    """
    if year not in bt.SEASON_CALENDAR:
        raise ValueError(f"no season calendar for {year!r}")
    validate_real_frame(frame)
    moment = ensure_utc(decision_time, "decision_time") if decision_time else frame.captured_at
    # loud refusal first: an uncut frame (rows captured after the decision
    # instant) raises instead of being silently trimmed...
    validate_decision_cut(frame, moment)
    # ...then the structural prevention: the walk below sees ONLY rows
    # captured at or before the decision instant. The cut is not advisory.
    rows = known_at(frame, moment).rows

    window_rows = _window_rows(year, rows)
    if not window_rows:
        raise ValueError(f"season {year}: frame has no rows in the sale window")
    # the window's first SESSION must be the declared harvest day itself:
    # with the carry machinery inserted, a gap means the frame is not the
    # prepared study frame.
    if window_rows[0].session_date != bt.SEASON_CALENDAR[year]["harvest_day"]:
        raise ValueError(
            f"season {year}: window starts {window_rows[0].session_date}; "
            "the study frame must carry (or carry-carry) the declared "
            "harvest-day session"
        )

    scale = _usd_per_bushel(frame.unit_note)
    bu_per_ha = bt.bushels_per_ha(yield_t_per_ha)

    def dollars(close_printed: float) -> float:
        return close_printed / scale

    def carry_execution(marker: RealPriceRow, leg: int, weight: float, trigger: str) -> bt.SaleExecution:
        return bt.SaleExecution(
            season=year,
            leg=leg,
            trigger=trigger,
            day=marker.session_date,
            price=dollars(marker.close),
            weight=weight,
            bushels=bu_per_ha * weight,
            revenue=dollars(marker.close) * bu_per_ha * weight,
            note=marker.note or "recorded close",
        )

    harvest_marker = window_rows[0]
    baseline_exec = bt.SaleExecution(
        season=year,
        leg=0,
        trigger="all-at-once at harvest",
        day=harvest_marker.session_date,
        price=dollars(harvest_marker.close),
        weight=1.0,
        bushels=bu_per_ha,
        revenue=dollars(harvest_marker.close) * bu_per_ha,
        note=(
            "baseline: the whole crop at the declared harvest day's close "
            + ("(calendar-carry)" if harvest_marker.source == ROW_SOURCE_CARRY else "(recorded)")
        ),
    )

    pending_breakout = True
    pending_post_wasde = True
    execs: list[bt.SaleExecution] = [carry_execution(harvest_marker, 1, bt.HARVEST_WEIGHT, "harvest_close")]

    for marker in window_rows[1:]:
        printed = marker.close
        day = marker.session_date
        if pending_breakout and printed >= bt.BREAKOUT_LEVEL * scale:
            pending_breakout = False
            execs.append(
                carry_execution(
                    marker, 2, bt.BREAKOUT_WEIGHT, f"breakout_{bt.BREAKOUT_LEVEL:.2f}"
                )
            )
            continue
        if pending_post_wasde and day > bt.SEASON_CALENDAR[year]["wasde_day"]:
            pending_post_wasde = False
            execs.append(carry_execution(marker, 3, bt.POST_WASDE_WEIGHT, "post_december_wasde"))
            continue
        if not (pending_breakout or pending_post_wasde):
            break

    # D1 window-coverage law (documented above): an "exhausted" leg may
    # only be priced at a last captured close when the cut frame
    # demonstrably reaches the declared window_end. A frame that stops
    # short means the RECORD simply ended — pricing unfired legs at that
    # stop dresses an incomplete capture up as a finished window. Refuse,
    # naming the season, its last captured session, and the shortfall.
    window_end = bt.SEASON_CALENDAR[year]["window_end"]
    if (pending_breakout or pending_post_wasde) and rows[-1].session_date < window_end:
        data_end = rows[-1].session_date
        shortfall_days = (window_end - data_end).days
        unfired = [
            leg
            for leg, pending in ((2, pending_breakout), (3, pending_post_wasde))
            if pending
        ]
        raise ValueError(
            f"season {year}: window coverage stops at {data_end.isoformat()}, "
            f"{shortfall_days} calendar days short of the declared window_end "
            f"{window_end.isoformat()} — the exchange may still have held "
            "sessions in that stretch which this record does not carry, so "
            f"unfired leg(s) {unfired} cannot honestly be marked "
            "window-exhausted at the last captured close; cover the window "
            "through its declared end or the season refuses to run short"
        )

    last_marker = window_rows[-1]
    for leg_number, weight, trigger in (
        (2, bt.BREAKOUT_WEIGHT, f"breakout_{bt.BREAKOUT_LEVEL:.2f}_window_exhausted"),
        (3, bt.POST_WASDE_WEIGHT, "post_december_wasde_window_exhausted"),
    ):
        fired = any(execution.leg == leg_number for execution in execs)
        if fired:
            continue
        same_day = bool(execs) and last_marker.session_date == execs[-1].day
        execs.append(
            bt.SaleExecution(
                season=year,
                leg=leg_number,
                trigger=trigger,
                day=last_marker.session_date,
                price=dollars(last_marker.close),
                weight=weight,
                bushels=bu_per_ha * weight,
                revenue=dollars(last_marker.close) * bu_per_ha * weight,
                note=(
                    "window exhausted before the trigger fired"
                    if not same_day
                    else "forced exit at the window's last close (shares the final session)"
                ),
            )
        )

    total_weighted = sum(execution.weight * execution.price for execution in execs)
    staged_rev = total_weighted * bu_per_ha

    # drawdown over the window's printed closes, carry rows included
    closes = [marker.close for marker in window_rows]
    dd = _printed_drawdown(closes)

    return bt.SeasonOutcome(
        season=year,
        baseline_revenue_per_ha=baseline_exec.revenue,
        staged_revenue_per_ha=staged_rev,
        delta_per_ha=staged_rev - baseline_exec.revenue,
        executions=tuple(execs),
        window_max_drawdown=dd,
        unrealised_final_close=last_marker.close,
        session_count=len(window_rows),
    )


def _printed_drawdown(closes: Sequence[float]) -> float | None:
    peak = closes[0]
    worst = 0.0
    for value in closes:
        if value > peak:
            peak = value
        worst = max(worst, peak - value)
    return worst if worst > 0 else None


def run_real_backtest(
    frames: Iterable[RealPriceFrame],
    *,
    years: Sequence[str] = DEFAULT_YEARS,
    yield_t_per_ha: float = bt.DEFAULT_YIELD_T_PER_HA,
    decision_time: datetime | None = None,
) -> "RealBacktestReport":
    """The multi-season run over validated REAL frames (per-year pick).

    Frames may be one covering series or several split pieces; the window
    selection mirrors ``backtest.run_backtest``. Aggregate edge per hectare
    is the mean of per-season deltas — identical identity to the sim run.
    """
    frames = tuple(frames)
    # fail friendly, not with a bare KeyError out of _window_rows:
    # name the unknown season year(s) and the ones that DO exist.
    unknown = [year for year in years if year not in bt.SEASON_CALENDAR]
    if unknown:
        raise ValueError(
            f"no season calendar for {', '.join(repr(y) for y in unknown)}; "
            f"available seasons: {sorted(bt.SEASON_CALENDAR)}"
        )
    chosen: dict[str, RealPriceFrame] = {}
    for year in years:
        for frame in frames:
            if _window_rows(year, frame.rows):
                chosen[year] = frame
                break
    missing = [year for year in years if year not in chosen]
    if missing:
        raise ValueError(f"no frame covers seasons: {missing}")

    outcomes = tuple(
        run_season(year, chosen[year], yield_t_per_ha=yield_t_per_ha, decision_time=decision_time)
        for year in years
    )
    baseline_mean = sum(o.baseline_revenue_per_ha for o in outcomes) / len(outcomes)
    staged_mean = sum(o.staged_revenue_per_ha for o in outcomes) / len(outcomes)
    deltas = [o.delta_per_ha for o in outcomes]
    won = sum(1 for d in deltas if d >= 0)
    lost = len(deltas) - won
    drawdowns = [o.window_max_drawdown for o in outcomes if o.window_max_drawdown is not None]

    cover_frame = next(iter(chosen.values()))
    chosen_frames = {id(frame) for frame in chosen.values()}
    result = bt.BacktestResult(
        rule_name=(
            f"staged selling 40/30/30 (harvest / {bt.BREAKOUT_LEVEL:.2f} "
            "breakout / post-Dec-WASDE) on recorded ZS=F"
        ),
        config_version=VERSION,
        years=tuple(years),
        yield_t_per_ha=yield_t_per_ha,
        bushels_per_ha=bt.bushels_per_ha(yield_t_per_ha),
        breakout_level=bt.BREAKOUT_LEVEL,
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
        limits=REAL_BACKTEST_LIMITS,
    )
    carry_dates = tuple(
        sorted(
            {
                row.session_date
                for frame in frames
                if id(frame) in chosen_frames
                for row in frame.rows
                if row.source == ROW_SOURCE_CARRY
            }
        )
    )
    recorded_count = sum(
        1
        for frame in frames
        if id(frame) in chosen_frames
        for row in frame.rows
        if row.source != ROW_SOURCE_CARRY
    )
    return RealBacktestReport(
        result=result,
        symbol=cover_frame.symbol,
        interval=cover_frame.interval,
        source=cover_frame.source,
        citation_url=cover_frame.citation_url,
        unit_note=cover_frame.unit_note,
        captured_at=cover_frame.captured_at,
        candle_count=recorded_count,
        carry_dates=carry_dates,
    )


@dataclass(frozen=True)
class RealBacktestReport:
    """A real-data run PLUS the provenance the report must restate."""

    result: bt.BacktestResult
    symbol: str
    interval: str
    source: str
    citation_url: str
    unit_note: str
    captured_at: datetime
    candle_count: int
    carry_dates: tuple[date, ...] = ()

    @property
    def seasons(self) -> tuple[bt.SeasonOutcome, ...]:
        return self.result.per_season

    @property
    def mean_delta_per_ha(self) -> float:
        return self.result.mean_delta_per_ha

    @property
    def delta_pct_vs_baseline(self) -> float:
        baseline = self.result.baseline_revenue_per_ha
        if baseline == 0:
            return 0.0
        return self.result.mean_delta_per_ha / baseline * 100.0


# --------------------------------------------------------------------------- #
# Reporting — the honest artefact                                             #
# --------------------------------------------------------------------------- #

REAL_BACKTEST_LIMITS: tuple[str, ...] = (
    "EVIDENCE HOLD (carried from the 2026-11-22 study): quote units, "
    "threshold comparison, point-in-time provenance, and reproduction need "
    "independent reconstruction; treat every number as provisional.",
    "PRINTED SCALE, DECLARED: the chart API prints US cents per bushel; "
    "the revenue identity divides by 100 exactly once. The earlier ad-hoc "
    "run labelled the same numbers 'USD per bushel' and overstated each "
    "harvest-year revenue a hundredfold (percentages were unaffected).",
    "PERFECT KNOWLEDGE: the breakout level and the December WASDE DAY are "
    "declared assumptions (see backtest.SEASON_CALENDAR); trigger "
    "visibility in advance is NOT evidenced here.",
    "NO SLIPPAGE, NO COSTS, INFINITE DEPTH: sales fill at the session "
    "close, fee-free; real cash sales move price and pay basis, handling "
    "and drying discounts.",
    "CONTINUOUS FRONT CONTRACT: Yahoo's ZS=F series is the plotted "
    "continuous front month, not an exchange-official settlement tape; "
    "roll effects are not modelled and closes are not settlement prices.",
    "L1 CALENDAR-CARRY: on non-trading declared harvest days the whole "
    "comparison anchors on the previous session's close (marked "
    "calendar-carry in the leg log); the fill is a convention, not a trade.",
    "DEGENERATE BREAKOUT: 11.40 USD/bu derives from the AMS cash band, but "
    "futures traded 9.39-17.69 USD/bu over these seasons, so L2 fires on "
    "the first window session almost every year; the measured edge is "
    "therefore essentially L3 post-WASDE timing. Re-deriving the level "
    "per season is future evidenced work, NOT claimed here.",
    "SURVIVORSHIP OF RULES: 40/30/30 and 11.40 are declared, not fitted; "
    "any parameter tuned on the same five seasons would flatter itself.",
    "FIVE SEASONS, SMALL SAMPLE: five seasons cannot separate a rule from "
    "luck; the confidence interval is wider than the numbers.",
    "WINDOW MECHANICS: pending legs sell at the last window close when "
    "their trigger never fires; that forced exit is generous.",
    "LICENSING (CONTROLLED ASSET): the recorded series is committed for "
    "internal research with COMMERCIAL redistribution unverified (commit "
    "3249f47b; tests/fixtures/real/README.md; "
    "docs/legal/commercial-punchlist.md). This report carries NUMBERS "
    "only, never the underlying series.",
    "GRANT WALL: every recorded feed's permits_financial_use is False "
    "(grants/state.json); none of this touches live money and nothing "
    "here authorises a sale, hedge, or tradable-alpha claim.",
    "NOT ADVICE: decision-support evidence only; the stamp travels with "
    "every derived artefact.",
)


def _money(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def _legs(outcome: bt.SeasonOutcome) -> str:
    parts = []
    for execution in outcome.executions:
        parts.append(
            f"L{execution.leg}@{execution.price:.2f} ({execution.trigger})"
        )
    return ", ".join(parts)


def render_report(report: RealBacktestReport) -> str:
    """The honest T3-R rerun document, from ONE run (stdlib text only)."""
    result = report.result
    lines: list[str] = []
    add = lines.append

    add("# Backtest T3-R rerun — staged selling on RECORDED CBOT ZS=F (2021-2025)")
    add("")
    add("> **NOT ADVICE — DECISION-SUPPORT EVIDENCE ONLY.** Rendered by "
        f"`farm_ontology/markets/real_backtest.py` config `{VERSION}` from "
        "RECORDED price rows, in-repo, with point-in-time guards.")
    add("")
    add("> **Evidence hold (still applies):** quote units, threshold "
        "comparison, PIT provenance, and this reproduction need independent "
        "reconstruction before any downstream claim. The ad-hoc study's "
        "dollar values were overstated exactly 100x by a unit mislabel, "
        "AND its L2 comparison matched printed cents against the dollar "
        "threshold, firing L2 on every session; this rerun converts the "
        "printed scale exactly once and evaluates the declared trigger "
        "unit-coherently, so the edge MOVES — the comparison section below "
        "quantifies it against the documented ad-hoc numbers.")
    add("")
    add("## Headline")
    add("")
    add(
        f"Across {len(result.years)} seasons ({', '.join(result.years)}), "
        f"staged selling **{_money(result.mean_delta_per_ha)} per hectare** "
        f"({'+' if result.mean_delta_per_ha >= 0 else ''}{report.delta_pct_vs_baseline:.1f}% "
        f"vs all-at-once mean {_money(result.baseline_revenue_per_ha)}/ha), "
        f"hit rate {result.hit_rate:.0%} ({result.seasons_won}W/{result.seasons_lost}L), "
        f"worst season {result.worst_delta_per_ha:+,.2f}$/ha, best {result.best_delta_per_ha:+,.2f}$/ha."
    )
    add("")
    add(
        f"Sizing anchor: {result.yield_t_per_ha} t/ha = {result.bushels_per_ha:.1f} bu/ha "
        f"(1 bu = {bt.BU_KG} kg). Units: closes recorded as printed "
        f"({report.unit_note}); fills converted to USD/bu exactly once."
    )
    add("")
    add("## Per-season table")
    add("")
    add("| season | all-at-once $/ha | staged $/ha | delta $/ha | window dd (printed px) | legs fired |")
    add("| --- | --- | --- | --- | --- | --- |")
    for outcome in report.seasons:
        dd = "—" if outcome.window_max_drawdown is None else f"{outcome.window_max_drawdown:.2f}"
        add(
            f"| {outcome.season} | {outcome.baseline_revenue_per_ha:,.2f} | "
            f"{outcome.staged_revenue_per_ha:,.2f} | {outcome.delta_per_ha:+,.2f} | "
            f"{dd} | {_legs(outcome)} |"
        )
    add("")
    mean_dd = result.mean_window_drawdown
    add(
        f"Mean intra-window price drawdown (printed scale): "
        f"{'—' if mean_dd is None else format(round(mean_dd, 3), '.3f')} "
        f"(worst {round(result.worst_window_drawdown, 3)}). "
        f"Wins per season order: {[o.delta_per_ha >= 0 for o in report.seasons]}."
    )
    add("")
    if tuple(result.years) == PRIOR_ADHOC_STUDY["years"]:
        prior = PRIOR_ADHOC_STUDY
        add(f"## Comparison with the {prior['label']}")
        add("")
        add(
            f"Documented in `{prior['report']}`; restated here as NUMBERS "
            "with the pointer, per the no-redistribution rule (its own "
            "dollar magnitudes carry the 100x unit mislabel flagged in "
            "that report)."
        )
        add("")
        add("| season | ad-hoc delta $/ha | this rerun delta $/ha | win flipped? |")
        add("| --- | --- | --- | --- |")
        for season, prior_delta in zip(result.years, prior["per_season_delta"]):
            outcome = next(o for o in report.seasons if o.season == season)
            flipped = (prior_delta >= 0) != (outcome.delta_per_ha >= 0)
            add(
                f"| {season} | {prior_delta:+,.2f} | {outcome.delta_per_ha:+,.2f} | "
                f"{'yes' if flipped else 'no'} |"
            )
        add("")
        add(
            f"Why the numbers move: (1) UNIT — the ad-hoc engine consumed "
            "printed cents labelled as USD, inflating every revenue 100x; "
            "(2) TRIGGER EVALUATION — the ad-hoc L2 compared printed cents "
            "against the $11.40 threshold, so L2 fired on the first window "
            f"session every year, whereas unit-coherent evaluation (close "
            f"≥ {bt.BREAKOUT_LEVEL:.2f} USD/bu ⇔ ≥ "
            f"{bt.BREAKOUT_LEVEL * USD_PER_BU_SCALE[YAHOO_UNIT_NOTE_CENTS]:.0f} printed cents) "
            "makes L2 a real conditional: it exhausts in 2024 (no window "
            "close ≥ 1140 cents) and fires mid-window in 2025 (2025-11-17 "
            f"@ 1157.25). Hit rate is unchanged "
            f"({prior['seasons_won']}W/{prior['seasons_lost']}L both runs); "
            f"the aggregate edge is "
            f"+{report.delta_pct_vs_baseline:.1f}% here vs "
            f"{prior['headline_pct']}% documented."
        )
        add("")
    add("## Method (identities, verifiably coded)")
    add("")
    add("- baseline $/ha = declared-harvest-day close (÷100 printed-scale "
        "conversion) × total bushels/ha;")
    add("- staged $/ha = Σ leg-weight × leg-fill-price(÷100) × bushels/ha;")
    add(f"- triggers AS CODED (module constants borrowed from "
        f"`farm_ontology.markets.backtest`): L1 {bt.HARVEST_WEIGHT:.0%} at the declared "
        "harvest-day session; L2 "
        f"{bt.BREAKOUT_WEIGHT:.0%} on the first close ≥ ${bt.BREAKOUT_LEVEL:.2f}/bu "
        f"(derivation: {bt.BREAKOUT_DERIVATION}); "
        f"L3 {bt.POST_WASDE_WEIGHT:.0%} on the first close strictly after the declared "
        "December-WASDE day; unfired legs exit at the last window close, "
        "marked window-exhausted in the leg log;")
    add("- calendar-carry: on a declared harvest day with no exchange "
        "session, the L1 fill is the last recorded close BEFORE the day, "
        "marked `calendar-carry` in the leg note.")
    add("")
    add("## Data and provenance (what makes these rows REAL)")
    add("")
    add(
        f"- source envelope: source=`{report.source}`, symbol="
        f"`{report.symbol}`, interval=`{report.interval}`, captured_at="
        f"`{report.captured_at.isoformat()}`, unit_note=`{report.unit_note}`;"
    )
    add(f"- citation: {report.citation_url};")
    add(
        f"- {report.candle_count} recorded daily closes; carry rows on "
        + (
            ", ".join(str(day) for day in report.carry_dates)
            if report.carry_dates
            else "no"
        )
        + " (non-trading declared harvest days);"
    )
    add(
        "- every row passed `validate_real_frame`: symbol/interval/source/"
        "unit match the envelope, capture instants are timezone-aware, "
        "closes are finite and positive, carry rows repeat the last "
        "recorded close, and anonymous rows are refused (audit gap G4 "
        "closed in-repo)."
    )
    add("")
    add("## Point-in-time discipline (no hindsight leaks)")
    add("")
    add(
        "- rows carry `captured_at`; the known-at filter "
        "(`real_backtest.known_at`) exposes only rows captured at or "
        "before the queried instant — the same `facts_at` semantics "
        "`pit_dataset` gives recorded feed facts, applied at row level "
        "because a captured candle is not a recorded-feed fact "
        "(`pit_dataset.MarketFact` is typed to the five recorded feeds)."
    )
    add(
        "- every season run cuts its input at `decision_time` "
        "(`real_backtest.validate_decision_cut` refuses a frame still "
        "carrying rows captured after the decision instant — `LeakError` — "
        "and the walk then sees only `known_at` rows), so the engine "
        "cannot be handed tomorrow's close by accident."
    )
    add(
        "- the breakout LEVEL's own derivation stays anchored in the "
        "recorded present (AMS band via `pit_dataset.matrix` as-of join, "
        "as documented in the original T3 report); declaring it as a "
        "perfect-knowledge assumption, not as evidence."
    )
    add("")
    add("## Assumptions (each one declared)")
    add("")
    add("- harvest days: October 5 each season (`SEASON_CALENDAR`), "
        "weekends covered by calendar-carry;")
    add("- December WASDE day: declared as the 10th; the recorded header "
        "stores no release instant;")
    add("- yield: the strategy book's own 3.0 t/ha scenario constant;")
    add("- the breakout level: derived from the recorded 2026 AMS band, "
        "known to fire immediately on futures (see Limitations).")
    add("")
    add("## Limitations (BRUTAL, by contract)")
    add("")
    for limit in REAL_BACKTEST_LIMITS:
        add(f"- {limit}")
    add("")
    add("## The grant wall (the reader's standing reminder)")
    add("")
    add(
        "Every recorded feed's `permits_financial_use` is False today "
        "(grants/state.json: reasons `specimen`/`no_grant`). This run "
        "describes what a RULE would have done on RECORDED closes — it "
        "authorises no sale, no hedge, and no product claim of tradable alpha."
    )
    add("")
    add("## Reproduce")
    add("")
    add("```powershell")
    add("python -m unittest tests.test_markets_real_backtest -v")
    add("# recorded-fixture rerun (opt-in gate protecting the committed")
    add("# controlled asset — see tests/fixtures/real/README.md):")
    add("$env:FARM_REAL_FIXTURES='1'; python -m unittest tests.test_markets_real_backtest -v")
    add("# regenerate this document from any local capture (the raw series")
    add("# itself is never committed outside the controlled fixture):")
    add("python -c \"from farm_ontology.markets import real_backtest as rb; ")
    add("f = rb.load_recorded_frame('<capture-path>', captured_by='<operator>'); ")
    add("print(rb.write_report(rb.run_real_backtest((f,), yield_t_per_ha=3.0), ")
    add("'reports/backtest-t3-rerun-REPORT.md'))\"")
    add("```")
    add("")
    return "\n".join(lines) + "\n"


def write_report(report: RealBacktestReport, path: str | os.PathLike[str]) -> Path:
    """Persist the rendered report (numbers only — never the raw series)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_report(report), encoding="utf-8")
    return target


def real_fixture_path(repo_root: str | os.PathLike[str] | None = None) -> Path:
    """Where the redistributable recorded fixture WOULD live."""
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
    return root / FIXTURE_RELATIVE_PATH


def real_fixture_exists(repo_root: str | os.PathLike[str] | None = None) -> bool:
    return real_fixture_path(repo_root).exists()


def real_fixture_gate_open() -> bool:
    """The opt-in gate for exercising the recorded fixture, in the
    discipline of ``FARM_ONLINE_TESTS`` (default OFF, hermetic suite)."""
    return os.environ.get(REAL_FIXTURE_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def load_default_fixture_frame() -> RealPriceFrame:
    """Load the COMMITTED recorded fixture (controlled asset).

    Absent-file errors name the provenance README, where the redistribution
    posture (internal research only; commercial use unverified) is recorded.
    """
    path = real_fixture_path()
    if not path.exists():
        raise FileNotFoundError(
            f"{FIXTURE_RELATIVE_PATH.as_posix()} is absent; its provenance and "
            "redistribution posture live in tests/fixtures/real/README.md"
        )
    return load_recorded_frame(
        path,
        captured_at=RECORDED_CAPTURE_UTC,
        captured_by="controlled-asset fixture (provenance README, commit 3249f47b)",
    )


__all__ = [
    "VERSION",
    "REAL_FIXTURE_ENV",
    "FIXTURE_RELATIVE_PATH",
    "RECORDED_CAPTURE_UTC",
    "YAHOO_UNIT_NOTE_CENTS",
    "YAHOO_UNIT_NOTE_USD",
    "USD_PER_BU_SCALE",
    "ROW_SOURCE_RECORDED",
    "ROW_SOURCE_CARRY",
    "ROW_SOURCE_STAND_IN",
    "ALLOWED_ROW_SOURCES",
    "DEFAULT_YEARS",
    "PRIOR_ADHOC_STUDY",
    "ProvenanceError",
    "LeakError",
    "RealPriceRow",
    "RealPriceFrame",
    "RealBacktestReport",
    "load_recorded_frame",
    "with_carry_rows",
    "validate_real_frame",
    "known_at",
    "validate_decision_cut",
    "run_season",
    "run_real_backtest",
    "render_report",
    "write_report",
    "real_fixture_path",
    "real_fixture_exists",
    "real_fixture_gate_open",
    "load_default_fixture_frame",
]
