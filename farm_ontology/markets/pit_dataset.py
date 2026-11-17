"""Point-in-time dataset builder over the recorded market feeds.

Deliverable 7.1 of the decision-infrastructure roadmap: a tidy row set
with known-at (``fact_time``), publication/issue basis, value, unit, and
support per feed, and an ``as_of`` view that reproduces exactly what was
knowable at a timestamp. It exists so a later backtest replays history
under ``facts_at`` semantics and cannot peek.

Where the times come from
-------------------------

This builder does not open pages and does not fetch. It builds rows from
the five feed modules the record already committed: ``usda_wasde``,
``ams_soybean_bid``, ``fao_food_price_index``, ``imf_pcps``, and
``pink_sheet``. Each module stores the printed header (or, for AMS, the
printed cash bid) and carries its own caveats; those caveats travel into
every row unchanged.

Two kinds of recorded-act instants anchor the timeline:

- ``CAPTURE_UTC`` — the instant each module entered this record, from
  ``git log -1 --follow -- farm_ontology/<module>.py`` at authoring
  (2026-11-16/17 Asia/Tokyo offsets normalised to UTC). A header fact
  cannot be known before its own recording commit. The tests pin these
  constants so a rebase cannot silently drift them.
- Printed access and release days inside the module docstrings (the AMS
  PDF "opened on 17 Nov 2026" for the 11/16/2026 Final report; the FAO
  page opened as the 6 November 2026 release) stay printed text in
  ``publication_basis``. They are not promoted to invented clock times.

Known-at conservatism
---------------------

A fact row's ``fact_time`` is the earliest instant this repo can prove
the fact was knowable. Nothing is backdated to a source-site publication
schedule the record does not store, and no fill, estimate, or rounding
is introduced: where a feed explicitly does not store a level (WASDE,
FAO-FPI, IMF-PCPS, Pink Sheet), the fact set carries an explicit
``storage_scope`` row with ``value=None`` instead of an imagined number.

Outputs
-------

``matrix(as_of)`` returns one tidy dict row per feed fact knowable at
``as_of`` — the latest revision per ``(subject, metric)`` — sorted
deterministically. ``purge_overlapping`` groups facts by publication
group and drops or trims overlapping revision windows between groups,
emitting ``(fact, until)`` coverage pairs prepared for cross-sectional
backtests.

Nothing here turns a screening record into a financial use. Every row
repeats the recorded ``permits_financial_use`` state of its feed;
raising that state is the licences workstream's job, through written
grants, never this module's.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable, Mapping

from farm_ontology import (
    ams_soybean_bid,
    fao_food_price_index,
    imf_pcps,
    pink_sheet,
    usda_wasde,
)
from farm_ontology.timeutil import ensure_utc

FEED_USDA_WASDE = "usda_wasde"
FEED_AMS_SOYBEAN_BID = "ams_soybean_bid"
FEED_FAO_FPI = "fao_food_price_index"
FEED_IMF_PCPS = "imf_pcps"
FEED_PINK_SHEET = "pink_sheet"

FEEDS = (
    FEED_USDA_WASDE,
    FEED_AMS_SOYBEAN_BID,
    FEED_FAO_FPI,
    FEED_IMF_PCPS,
    FEED_PINK_SHEET,
)

#: Recording-act instants, pinned from the module commits, UTC. The
#: tests assert these individually against the values recorded here.
CAPTURE_UTC = {
    FEED_USDA_WASDE: datetime(2026, 11, 16, 16, 15, 11, tzinfo=timezone.utc),
    FEED_AMS_SOYBEAN_BID: datetime(2026, 11, 17, 1, 59, 46, tzinfo=timezone.utc),
    FEED_FAO_FPI: datetime(2026, 11, 16, 16, 6, 25, tzinfo=timezone.utc),
    FEED_IMF_PCPS: datetime(2026, 11, 16, 16, 30, 12, tzinfo=timezone.utc),
    FEED_PINK_SHEET: datetime(2026, 11, 16, 15, 16, 44, tzinfo=timezone.utc),
}

SOURCE_COMMITS = {
    FEED_USDA_WASDE: "5c4308897cc30ee58b81ed60f318286775690261",
    FEED_AMS_SOYBEAN_BID: "46493abcbd66f8fa3f8a1543c009e5447a7e7d82",
    FEED_FAO_FPI: "3d06e0a53e61c4f845ed5598d1df289d2f4f8113",
    FEED_IMF_PCPS: "24b324ae1fdbdd13aa4f08fbf504717050dc554a",
    FEED_PINK_SHEET: "dadfcae9e2fcbfc705b852e040e0d41b8955fe7c",
}

CITATIONS = {
    FEED_USDA_WASDE: usda_wasde.USDA_WASDE_URL,
    FEED_AMS_SOYBEAN_BID: ams_soybean_bid.AMS_URL,
    FEED_FAO_FPI: fao_food_price_index.FAO_FOOD_PRICE_INDEX_URL,
    FEED_IMF_PCPS: imf_pcps.IMF_PCPS_URL,
    FEED_PINK_SHEET: pink_sheet.PINK_SHEET_MONTHLY_URL,
}

#: The recorded permit state printed by every recorded header. These
#: stay False until the licences workstream attaches a written grant
#: (task-6). Feeding these rows into a backtest does not change it.
_PERMITTED = {
    FEED_USDA_WASDE: False,
    FEED_AMS_SOYBEAN_BID: False,
    FEED_FAO_FPI: False,
    FEED_IMF_PCPS: False,
    FEED_PINK_SHEET: False,
}

_MATRIX_COLUMNS = (
    "feed",
    "group",
    "subject",
    "metric",
    "fact_time",
    "publication_time",
    "publication_basis",
    "value",
    "value_text",
    "unit",
    "recorded_act",
    "citation_url",
    "permits_financial_use",
    "capture_commit",
)


@dataclass(frozen=True)
class MarketFact:
    """One known-at row over a recorded feed.

    ``value`` carries the printed number where the record stores one
    (today, only the AMS printed cash bid). ``value_text`` carries
    printed labels, protocols, and scope sentences; it is shortened, not
    numerically altered. Quantitative rows carry a value and a unit;
    qualitative rows carry only ``value_text``; the recorded support
    sentence stays in ``publication_basis`` for both.
    """

    feed: str
    group: str
    subject: str
    metric: str
    fact_time: datetime
    recorded_act: str
    publication_basis: str
    value: float | None = None
    value_text: str | None = None
    unit: str | None = None
    publication_time: datetime | None = None
    citation_url: str = ""
    permits_financial_use: bool = False
    capture_commit: str = ""

    def __post_init__(self) -> None:
        if self.feed not in FEEDS:
            raise ValueError("a market fact cites a recorded feed")
        if self.fact_time.tzinfo is None or self.fact_time.tzinfo.utcoffset(self.fact_time) is None:
            raise ValueError("fact_time must be timezone-aware")
        if not self.subject or not self.metric:
            raise ValueError("a market fact names its subject and its metric")
        if self.value is None and self.value_text is None:
            raise ValueError(
                "a market fact without a stored value stores the explicit "
                "scope sentence instead; it does not guess"
            )
        if self.value is not None and not self.unit:
            raise ValueError("a quantitative market fact prints its unit")

    @property
    def quantitative(self) -> bool:
        return self.value is not None

    @property
    def key(self) -> tuple[str, str]:
        return (self.subject, self.metric)


SUBJECT_AMS_BID = "ams_usda:nw-soybean-cash-bid-current"
SUBJECT_WASDE = "usda_wasde:supply-demand-forecast"
SUBJECT_FAO = "fao_fpi:food-price-index"
SUBJECT_IMF = "imf_pcps:all-commodity-index"
SUBJECT_PINK_CRUDE = "wb_pink:crude-oil-average"

GROUP_AMS = "usda_mnreports"
GROUP_WASDE = "usda_waob"
GROUP_FAO = "fao_release"
GROUP_IMF = "imf_pcps_faq"
GROUP_PINK = "world_bank_pink"

_ACT_AMS = (
    "PDF ams_3225.pdf opened 17 Nov 2026; Grain Report for 11/16/2026 "
    "- Final; US #1 Soybeans (Bulk), Country Elevators - Conventional, "
    "Northwest, sale type Bid, delivery Current"
)
_BASIS_AMS = (
    "printed Grain Report for 11/16/2026 - Final; the report date is the "
    "phenomenon day; the block headed Closing Settlement Prices is not "
    "stored"
)


def _fact(
    *,
    feed: str,
    group: str,
    subject: str,
    metric: str,
    act: str,
    basis: str,
    fact_time: datetime,
    **rest,
) -> MarketFact:
    return MarketFact(
        feed=feed,
        group=group,
        subject=subject,
        metric=metric,
        fact_time=ensure_utc(fact_time, "fact_time"),
        recorded_act=act,
        publication_basis=basis,
        citation_url=CITATIONS[feed],
        permits_financial_use=_PERMITTED[feed],
        capture_commit=SOURCE_COMMITS[feed],
        **rest,
    )


def _ams_facts() -> tuple[MarketFact, ...]:
    t = CAPTURE_UTC[FEED_AMS_SOYBEAN_BID]
    kwargs = dict(group=GROUP_AMS, subject=SUBJECT_AMS_BID, fact_time=t, act=_ACT_AMS, basis=_BASIS_AMS)
    return (
        _fact(
            feed=FEED_AMS_SOYBEAN_BID,
            metric="cash_bid_average",
            value=float(ams_soybean_bid.AVERAGE),
            unit=ams_soybean_bid.UNIT,
            **kwargs,
        ),
        _fact(
            feed=FEED_AMS_SOYBEAN_BID,
            metric="cash_bid_range_low",
            value=10.79,
            unit=ams_soybean_bid.UNIT,
            **kwargs,
        ),
        _fact(
            feed=FEED_AMS_SOYBEAN_BID,
            metric="cash_bid_range_high",
            value=11.34,
            unit=ams_soybean_bid.UNIT,
            **kwargs,
        ),
        _fact(
            feed=FEED_AMS_SOYBEAN_BID,
            metric="report_status",
            value_text="Final for report date 11/16/2026",
            **kwargs,
        ),
    )


_ACT_WASDE = (
    "WASDE page opened with the printed header recorded in "
    "farm_ontology/usda_wasde.py; the November 2026 report was linked "
    "from the page"
)
_BASIS_WASDE = (
    "monthly, released at 12:00 p.m. Eastern; annual balances revised in "
    "later months; not scored, not stored as a completed harvest"
)


def _wasde_facts() -> tuple[MarketFact, ...]:
    t = CAPTURE_UTC[FEED_USDA_WASDE]
    kwargs = dict(
        group=GROUP_WASDE,
        subject=SUBJECT_WASDE,
        fact_time=t,
        act=_ACT_WASDE,
        basis=_BASIS_WASDE,
        feed=FEED_USDA_WASDE,
    )
    return (
        _fact(metric="issue_cycle", value_text="November 2026 report linked from the page", **kwargs),
        _fact(metric="release_rule", value_text="monthly, released at 12:00 p.m. Eastern", **kwargs),
        _fact(
            metric="revision_protocol",
            value_text="a forecast of annual balances, revised in later months",
            **kwargs,
        ),
        _fact(metric="storage_scope", value_text="no quantity is stored", **kwargs),
    )


_ACT_FAO = (
    "FAO Food Price Index release page opened; the stored record is the "
    "printed header in farm_ontology/fao_food_price_index.py"
)
_BASIS_FAO = (
    "the page opened was the 6 November 2026 release; the official "
    "monthly nominal index runs from 1990; the 1961 annual file is a "
    "spliced extension and is not this index"
)


def _fao_facts() -> tuple[MarketFact, ...]:
    t = CAPTURE_UTC[FEED_FAO_FPI]
    kwargs = dict(
        group=GROUP_FAO,
        subject=SUBJECT_FAO,
        fact_time=t,
        act=_ACT_FAO,
        basis=_BASIS_FAO,
        feed=FEED_FAO_FPI,
    )
    return (
        _fact(metric="release_cycle", value_text="the 6 November 2026 release page", **kwargs),
        _fact(
            metric="coverage_month_open",
            value_text=(
                "October 2026 as printed on the opened release; recent "
                "meat months mix projected and observed prices and can "
                "be revised"
            ),
            **kwargs,
        ),
        _fact(
            metric="coverage_start",
            value_text="official monthly nominal index runs from 1990",
            **kwargs,
        ),
        _fact(metric="storage_scope", value_text="no index level is stored", **kwargs),
    )


_ACT_IMF = (
    "IMF Primary Commodity Price System FAQ page opened; the stored "
    "record is the printed header plus the partly-rendered copyright "
    "note in farm_ontology/imf_pcps.py"
)
_BASIS_IMF = (
    "the FAQ was last updated 21 November 2025; monthly figures update "
    "in the first full week of the month; where a release lags the IMF "
    "inserts a random-walk estimate and later replaces it, and that "
    "fill is not stored"
)


def _imf_facts() -> tuple[MarketFact, ...]:
    t = CAPTURE_UTC[FEED_IMF_PCPS]
    kwargs = dict(
        group=GROUP_IMF,
        subject=SUBJECT_IMF,
        fact_time=t,
        act=_ACT_IMF,
        basis=_BASIS_IMF,
        feed=FEED_IMF_PCPS,
    )
    return (
        _fact(
            metric="update_rule",
            value_text="monthly figures are updated in the first full week of the month",
            **kwargs,
        ),
        _fact(
            metric="coverage_start",
            value_text="all-commodity index starts in January 1992; 2016=100",
            **kwargs,
        ),
        _fact(
            metric="projection_absence",
            value_text="two-year projections live in the World Economic Outlook and are not stored or scored here",
            **kwargs,
        ),
        _fact(metric="storage_scope", value_text="no price and no index level is stored", **kwargs),
    )


_ACT_PINK = (
    "World Bank CMO Historical Data Monthly workbook location recorded; "
    "the stored record is the printed series header in "
    "farm_ontology/pink_sheet.py"
)
_BASIS_PINK = (
    "series Crude oil, average; period 1960 to present; unit dollars "
    "per barrel as printed; the workbook body itself is not ingested "
    "into this record"
)


def _pink_facts() -> tuple[MarketFact, ...]:
    t = CAPTURE_UTC[FEED_PINK_SHEET]
    kwargs = dict(
        group=GROUP_PINK,
        subject=SUBJECT_PINK_CRUDE,
        fact_time=t,
        act=_ACT_PINK,
        basis=_BASIS_PINK,
        feed=FEED_PINK_SHEET,
    )
    return (
        _fact(
            metric="series_scope",
            value_text=f"{pink_sheet.SERIES}, {pink_sheet.PERIOD}",
            **kwargs,
        ),
        _fact(metric="unit_scope", value_text=pink_sheet.UNIT, **kwargs),
        _fact(metric="storage_scope", value_text="no price level is stored", **kwargs),
    )


_BUILDERS: dict[str, tuple[Callable[[], tuple[MarketFact, ...]], ...]] = {
    FEED_AMS_SOYBEAN_BID: (_ams_facts,),
    FEED_USDA_WASDE: (_wasde_facts,),
    FEED_FAO_FPI: (_fao_facts,),
    FEED_IMF_PCPS: (_imf_facts,),
    FEED_PINK_SHEET: (_pink_facts,),
}


def facts_for_feed(feed: str) -> tuple[MarketFact, ...]:
    """Rows of one recorded feed, ordered deterministically."""
    builders = _BUILDERS.get(feed)
    if builders is None:
        raise ValueError("facts_for_feed is called on an unrecorded feed")
    rows: list[MarketFact] = []
    for build in builders:
        rows.extend(build())
    return tuple(sorted(rows, key=lambda row: (row.metric, row.fact_time)))


def all_facts() -> tuple[MarketFact, ...]:
    """Every recorded market fact, one tidy row set, deterministic order."""
    rows: list[MarketFact] = []
    for feed in FEEDS:
        rows.extend(facts_for_feed(feed))
    return tuple(
        sorted(rows, key=lambda row: (row.subject, row.metric, row.fact_time, row.feed))
    )


def visible_facts(facts: Iterable[MarketFact], as_of: datetime) -> tuple[MarketFact, ...]:
    """The known-at filter, ``facts_at`` semantics for market facts.

    A fact is visible at ``as_of`` only when ``fact_time <= as_of``.
    Timezone-naive ``as_of`` raises, mirroring ``ensure_utc``.
    """
    moment = ensure_utc(as_of, "as_of")
    ordered = sorted(
        facts, key=lambda row: (row.subject, row.metric, row.fact_time, row.feed)
    )
    return tuple(row for row in ordered if row.fact_time <= moment)


def latest_per_metric(facts: Iterable[MarketFact]) -> tuple[MarketFact, ...]:
    """Collapse a visible fact set to the newest known-at row per key."""
    latest: dict[tuple[str, str], MarketFact] = {}
    for row in sorted(
        facts, key=lambda row: (row.subject, row.metric, row.fact_time, row.feed)
    ):
        latest[(row.subject, row.metric)] = row
    return tuple(
        sorted(latest.values(), key=lambda row: (row.subject, row.metric, row.fact_time))
    )


def matrix(as_of: datetime, facts: Iterable[MarketFact] | None = None) -> list[dict]:
    """The analyst matrix at ``as_of``: every subject, latest revisions.

    Columns are the ``_MATRIX_COLUMNS`` names. A subject missing at
    ``as_of`` simply has no rows; nothing is interpolated, nothing is
    forward-filled from a later act. This is the leak-proof property:
    ``matrix(t)`` is exactly the record knowable at ``t``.
    """
    if facts is None:
        facts = all_facts()
    visible = latest_per_metric(visible_facts(facts, as_of))
    rows = []
    for row in visible:
        entry = {column: getattr(row, column) for column in _MATRIX_COLUMNS}
        entry["fact_time"] = row.fact_time
        entry["publication_time"] = row.publication_time
        rows.append(entry)
    return rows


def matrix_row_keys(as_of: datetime, facts: Iterable[MarketFact] | None = None) -> tuple[tuple[str, str], ...]:
    """Just the ``(subject, metric)`` keys the matrix exposes at ``as_of``."""
    if facts is None:
        facts = all_facts()
    return tuple((row.subject, row.metric) for row in latest_per_metric(visible_facts(facts, as_of)))


@dataclass(frozen=True)
class PurgeTrim:
    """The surviving validity window of one fact after purging.

    ``until`` is exclusive. ``None`` means "open until a later revision
    in the same group". Trimmed facts keep their rows but lose the
    contested tail of their window, so a backtest cannot double-count a
    revision across two feeds that proxy the same series.
    """

    fact: MarketFact
    until: datetime | None

    @property
    def dropped_entirely(self) -> bool:
        return self.until is not None and self.until <= self.fact.fact_time


def purge_overlapping(
    facts: Iterable[MarketFact],
    *,
    group_of: Mapping[str, str] | None = None,
) -> tuple[PurgeTrim, ...]:
    """Group-aware purge of overlapping publication windows.

    Partition the facts by ``(subject, metric)``. Inside a partition,
    each publication group chains its own revisions: a fact's coverage
    runs from its ``fact_time`` to the next fact's ``fact_time`` inside
    the same group, else open-ended. Where a rival group publishes the
    same key at a strictly later instant inside our window, the later
    publication wins from that instant on: our window is trimmed to the
    rival's start, and a row whose window collapses onto its start is
    reported with ``dropped_entirely``. Equal publication instants are
    shared, not overlapping: neither side trims.

    ``group_of`` remaps feed ids to group labels, letting a caller fuse
    feeds that proxy the same series into one competing group. Ordering
    of the result is deterministic.
    """
    moment_groups = group_of or {}

    def group_label(row: MarketFact) -> str:
        return moment_groups.get(row.feed, row.group)

    partitions: dict[tuple[str, str], list[MarketFact]] = {}
    for row in facts:
        partitions.setdefault((row.subject, row.metric), []).append(row)

    trims: list[PurgeTrim] = []
    for key in sorted(partitions):
        rows = sorted(
            partitions[key],
            key=lambda row: (row.fact_time, group_label(row)),
        )
        # Chain revisions inside each group; the chain end trims each
        # window to the next same-group revision.
        coverage: dict[str, list[list]] = {}
        for row in rows:
            windows = coverage.setdefault(group_label(row), [])
            if windows and windows[-1][1] is None:
                windows[-1][1] = row.fact_time
            windows.append([row.fact_time, None, row])

        for group_name, windows in sorted(coverage.items()):
            for start, end, row in windows:
                effective_end = end
                rivals_join_at = sorted(
                    rival_start
                    for rival_name, rival_windows in coverage.items()
                    if rival_name != group_name
                    for rival_start, _rival_end, _rival_row in rival_windows
                    if rival_start > start
                )
                challenge = rivals_join_at[0] if rivals_join_at else None
                if challenge is not None and (
                    effective_end is None or challenge < effective_end
                ):
                    effective_end = challenge
                trims.append(PurgeTrim(fact=row, until=effective_end))
    return tuple(
        sorted(
            trims,
            key=lambda trim: (
                trim.fact.subject,
                trim.fact.metric,
                trim.fact.fact_time,
                trim.fact.feed,
            ),
        )
    )


def purged_matrix(
    as_of: datetime,
    facts: Iterable[MarketFact] | None = None,
    *,
    group_of: Mapping[str, str] | None = None,
) -> list[dict]:
    """``matrix`` restricted to surviving post-purge coverage.

    A fact row is emitted when ``as_of`` lies inside its surviving
    window; rows dropped entirely never appear; trimmed rows appear only
    before the trim instant. Equal-instant ties survive (a shared
    publication instant is not an overlap).
    """
    if facts is None:
        facts = all_facts()
    moment = ensure_utc(as_of, "as_of")
    survivors: list[MarketFact] = []
    for trim in purge_overlapping(list(facts), group_of=group_of):
        if trim.dropped_entirely:
            continue
        if trim.fact.fact_time > moment:
            continue
        if trim.until is not None and moment >= trim.until:
            continue
        survivors.append(trim.fact)
    visible = latest_per_metric(survivors)
    return [
        {column: getattr(row, column) for column in _MATRIX_COLUMNS}
        for row in sorted(visible, key=lambda row: (row.subject, row.metric))
    ]


def subject_metrics() -> tuple[str, ...]:
    """Every recorded subject, sorted. Dashboard and test plumbing."""
    return tuple(sorted({row.subject for row in all_facts()}))


__all__ = [
    "FEEDS",
    "CAPTURE_UTC",
    "SOURCE_COMMITS",
    "CITATIONS",
    "SUBJECT_AMS_BID",
    "SUBJECT_WASDE",
    "SUBJECT_FAO",
    "SUBJECT_IMF",
    "SUBJECT_PINK_CRUDE",
    "GROUP_AMS",
    "GROUP_WASDE",
    "GROUP_FAO",
    "GROUP_IMF",
    "GROUP_PINK",
    "MarketFact",
    "PurgeTrim",
    "facts_for_feed",
    "all_facts",
    "visible_facts",
    "latest_per_metric",
    "matrix",
    "matrix_row_keys",
    "purge_overlapping",
    "purged_matrix",
    "subject_metrics",
]
