"""Threshold-rule engine over the recorded market series.

Deliverable 7.2 of the decision-infra roadmap: for each monitored feed,
declarative rules — metric, comparator, level, lookback — evaluate
against the point-in-time rows built by ``pit_dataset`` and fire
``ShockFlag`` records. Rules seeded below are calibrated on the
RECORDED fixture magnitudes (the AMS printed band, the recorded cycle
texts) and the engine EMITS NOTHING ELSE: no webhook, no scheduler, no
database write. Feeding a human analyst alert channel is the caller's
job; scheduling belongs to the pipeline workstream (roadmap WS2); the
record store belongs to infra (WS1).

Persisting a flag
-----------------

A ``ShockFlag`` is an analyst-alert record, not an ``Observation`` and
not a published fact. Recommended wiring, in order:

1. Serialise with :func:`flag_payload` (stable, JSON-ready, carries the
   evidence fact_time and citation) — nothing else transforms it.
2. Append the payload to YOUR record store through the existing seams:
   the durable record directory (``FARM_RECORD_DIR`` env seam,
   ``farm_ontology.record.record_dir()``) for file records, or the
   ingest worker's existing Store path when it lands (WS2). Write it as
   an alert record; do not store it as a sosa:Observation, a
   settlement, or any class-C use — class C stays closed and no flag
   promotes anything.
3. Schedule evaluation in the pipeline workstream; this module never
   sleeps, retries, or polls.

Fail-closed semantics
---------------------

Evaluation never fabricates. A threshold rule with no value-bearing
known fact inside its lookback window yields a ``ShockGap``, never a
flag. A text rule compares against the recorded expected text; an
absent series is a gap. Nothing here scores a market, predicts a
price, or advises; the flags describe the RECORD, not a trade.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Sequence

from farm_ontology.markets.pit_dataset import (
    SUBJECT_AMS_BID,
    SUBJECT_FAO,
    SUBJECT_IMF,
    SUBJECT_PINK_CRUDE,
    SUBJECT_WASDE,
    MarketFact,
    latest_per_metric,
    visible_facts,
)
from farm_ontology.timeutil import ensure_utc

RULE_THRESHOLD = "threshold"
RULE_TEXT_CHANGE = "text-change"
RULE_PRESENCE = "presence"
RULE_KINDS = (RULE_THRESHOLD, RULE_TEXT_CHANGE, RULE_PRESENCE)

COMPARATORS = ("<=", "<", ">=", ">", "==")

#: Lookback floors the lookback arithmetic inside the tests.
DEFAULT_LOOKBACK = timedelta(days=45)


@dataclass(frozen=True)
class MarketRule:
    """A declarative monitor over one recorded metric.

    ``threshold`` rules need a numeric ``level`` and comparator and fire
    on value-bearing facts. ``text-change`` rules fire when the newest
    known ``value_text`` differs from ``expected_text``. ``presence``
    rules assert the metric exists at all; absence yields a
    ``ShockGap``. A rule with no known fact in window is a gap, never a
    fabricated flag.
    """

    rule_id: str
    rule_kind: str
    subject: str
    metric: str
    description: str
    comparator: str | None = None
    level: float | None = None
    expected_text: str | None = None
    lookback: timedelta = DEFAULT_LOOKBACK

    def __post_init__(self) -> None:
        if not self.rule_id:
            raise ValueError("a rule carries its rule_id")
        if self.rule_kind not in RULE_KINDS:
            raise ValueError("unknown rule kind")
        if not self.subject or not self.metric:
            raise ValueError("a rule names its subject and metric")
        if self.rule_kind == RULE_THRESHOLD:
            if self.comparator not in COMPARATORS:
                raise ValueError("a threshold rule uses a declared comparator")
            if self.level is None:
                raise ValueError("a threshold rule states its level")
            if self.expected_text is not None:
                raise ValueError("a threshold rule carries no expected text")
        elif self.rule_kind == RULE_TEXT_CHANGE:
            if self.expected_text is None:
                raise ValueError("a text-change rule states its expected text")
            if self.comparator is not None or self.level is not None:
                raise ValueError("a text-change rule carries no comparator or level")
        else:
            if any(
                item is not None
                for item in (self.comparator, self.level, self.expected_text)
            ):
                raise ValueError("a presence rule carries no level or text")


@dataclass(frozen=True)
class ShockFlag:
    """One fired rule, with its evidence. Persisted by the caller."""

    rule_id: str
    rule_kind: str
    subject: str
    metric: str
    fired_at: datetime
    evidence_fact_time: datetime
    description: str
    observed_value: float | None = None
    observed_text: str | None = None
    comparator: str | None = None
    level: float | None = None
    expected_text: str | None = None

    @property
    def flag_id(self) -> str:
        stamp = self.evidence_fact_time.strftime("%Y%m%dT%H%M%SZ")
        return f"shock:{self.rule_id}@{stamp}"


@dataclass(frozen=True)
class ShockGap:
    """A rule that could not be judged. Gaps are surfaced, not hidden."""

    rule_id: str
    subject: str
    metric: str
    reason: str


def _compare(comparator: str, observed: float, level: float) -> bool:
    if comparator == "<=":
        return observed <= level
    if comparator == "<":
        return observed < level
    if comparator == ">=":
        return observed >= level
    if comparator == ">":
        return observed > level
    return observed == level


def evaluate(
    rules: Iterable[MarketRule],
    facts: Iterable[MarketFact],
    as_of: datetime,
) -> tuple[tuple[ShockFlag, ...], tuple[ShockGap, ...]]:
    """Evaluate rules against the known-at rows visible at ``as_of``.

    Returns ``(flags, gaps)``. Flags and gaps are plain records; the
    caller persists them (see the module docstring for the wiring).
    """
    moment = ensure_utc(as_of, "as_of")
    visible = visible_facts(facts, moment)
    newest: dict[tuple[str, str], MarketFact] = {
        row.key: row for row in latest_per_metric(visible)
    }
    flags: list[ShockFlag] = []
    gaps: list[ShockGap] = []
    for rule in rules:
        row = newest.get((rule.subject, rule.metric))
        window_start = moment - rule.lookback
        in_window = row is not None and row.fact_time >= window_start
        if not in_window:
            gaps.append(
                ShockGap(
                    rule_id=rule.rule_id,
                    subject=rule.subject,
                    metric=rule.metric,
                    reason="no fact for the metric inside the lookback window",
                )
            )
            continue
        if rule.rule_kind == RULE_PRESENCE:
            if row.quantitative:
                continue
            gaps.append(
                ShockGap(
                    rule_id=rule.rule_id,
                    subject=rule.subject,
                    metric=rule.metric,
                    reason="the metric is known but stores no value",
                )
            )
            continue
        if rule.rule_kind == RULE_THRESHOLD:
            if not row.quantitative:
                gaps.append(
                    ShockGap(
                        rule_id=rule.rule_id,
                        subject=rule.subject,
                        metric=rule.metric,
                        reason="a threshold rule found no value-bearing fact",
                    )
                )
                continue
            assert row.value is not None
            if _compare(rule.comparator or "==", row.value, rule.level or 0.0):
                flags.append(
                    ShockFlag(
                        rule_id=rule.rule_id,
                        rule_kind=rule.rule_kind,
                        subject=rule.subject,
                        metric=rule.metric,
                        fired_at=moment,
                        evidence_fact_time=row.fact_time,
                        description=rule.description,
                        observed_value=row.value,
                        observed_text=row.value_text,
                        comparator=rule.comparator,
                        level=rule.level,
                    )
                )
            continue
        # text-change: fire only when the newest text differs from the
        # recorded expected text. Absence of a fact was a gap above.
        assert rule.expected_text is not None
        if row.value_text != rule.expected_text:
            flags.append(
                ShockFlag(
                    rule_id=rule.rule_id,
                    rule_kind=rule.rule_kind,
                    subject=rule.subject,
                    metric=rule.metric,
                    fired_at=moment,
                    evidence_fact_time=row.fact_time,
                    description=rule.description,
                    observed_value=row.value,
                    observed_text=row.value_text,
                    expected_text=rule.expected_text,
                )
            )
    deterministic_flags = tuple(
        sorted(flags, key=lambda flag: (flag.rule_id, flag.flag_id))
    )
    deterministic_gaps = tuple(
        sorted(gaps, key=lambda gap: (gap.rule_id, gap.reason))
    )
    return deterministic_flags, deterministic_gaps


#: Seeded monitors. Levels come from the recorded fixture magnitudes —
#: nothing is tuned from an external market view — and the expected
#: texts are the recorded cycle/scope sentences verbatim. Adding a rule
#: means recording it here, with its provenance sentence in
#: ``description``.
SHOCK_RULES: tuple[MarketRule, ...] = (
    MarketRule(
        rule_id="ams-bid-below-recorded-band",
        rule_kind=RULE_THRESHOLD,
        subject=SUBJECT_AMS_BID,
        metric="cash_bid_average",
        comparator="<",
        level=10.79,
        description=(
            "recorded fixture: the northwest country-elevator average "
            "bid printed 11.1600 inside the 10.7900-11.3400 band; a "
            "newer average under the band low is a supply-side signal "
            "worth an analyst look"
        ),
    ),
    MarketRule(
        rule_id="ams-bid-above-recorded-band",
        rule_kind=RULE_THRESHOLD,
        subject=SUBJECT_AMS_BID,
        metric="cash_bid_average",
        comparator=">",
        level=11.34,
        description=(
            "recorded fixture: a newer average above the recorded band "
            "high; analyst look, not advice"
        ),
    ),
    MarketRule(
        rule_id="ams-report-cycle-moved",
        rule_kind=RULE_TEXT_CHANGE,
        subject=SUBJECT_AMS_BID,
        metric="report_status",
        expected_text="Final for report date 11/16/2026",
        description=(
            "recorded fixture: the report status text; any change marks "
            "a new reporting cycle in the record"
        ),
    ),
    MarketRule(
        rule_id="wasde-issue-cycle-moved",
        rule_kind=RULE_TEXT_CHANGE,
        subject=SUBJECT_WASDE,
        metric="issue_cycle",
        expected_text="November 2026 report linked from the page",
        description=(
            "recorded fixture: the WASDE cycle sentence; a changed "
            "cycle means the record saw a new report"
        ),
    ),
    MarketRule(
        rule_id="fao-release-cycle-moved",
        rule_kind=RULE_TEXT_CHANGE,
        subject=SUBJECT_FAO,
        metric="release_cycle",
        expected_text="the 6 November 2026 release page",
        description=(
            "recorded fixture: the FAO release cycle sentence; a "
            "change marks a new monthly release entering the record"
        ),
    ),
    MarketRule(
        rule_id="imf-update-rule-observed",
        rule_kind=RULE_TEXT_CHANGE,
        subject=SUBJECT_IMF,
        metric="update_rule",
        expected_text=(
            "monthly figures are updated in the first full week of the month"
        ),
        description=(
            "recorded fixture: the IMF cadence sentence; keep an eye on "
            "recorded cadence drift"
        ),
    ),
    MarketRule(
        rule_id="pink-sheet-stores-a-level",
        rule_kind=RULE_TEXT_CHANGE,
        subject=SUBJECT_PINK_CRUDE,
        metric="storage_scope",
        expected_text="no price level is stored",
        description=(
            "recorded fixture: the Pink Sheet header stores no price "
            "level; the sentence changing means the record's shape "
            "changed and warrants review before any reuse"
        ),
    ),
    MarketRule(
        rule_id="ams-bid-present",
        rule_kind=RULE_PRESENCE,
        subject=SUBJECT_AMS_BID,
        metric="cash_bid_average",
        description=(
            "recorded fixture: the recorded cash bid is expected to be "
            "present and value-bearing inside the lookback window"
        ),
    ),
)


def flag_payload(flag: ShockFlag) -> dict:
    """A stable, JSON-ready mapping for the caller's record store.

    This serialises; it does not write. Payload keys are fixed so the
    analyst channel and later audits can rely on their presence.
    """
    return {
        "flag_id": flag.flag_id,
        "rule_id": flag.rule_id,
        "rule_kind": flag.rule_kind,
        "subject": flag.subject,
        "metric": flag.metric,
        "fired_at": flag.fired_at.isoformat(),
        "evidence_fact_time": flag.evidence_fact_time.isoformat(),
        "description": flag.description,
        "observed_value": flag.observed_value,
        "observed_text": flag.observed_text,
        "comparator": flag.comparator,
        "level": flag.level,
        "expected_text": flag.expected_text,
    }


def gaps_payload(gaps: Sequence[ShockGap]) -> tuple[dict, ...]:
    """Serialise the gap set the same way, for honesty in the channel."""
    return tuple(
        {
            "rule_id": gap.rule_id,
            "subject": gap.subject,
            "metric": gap.metric,
            "reason": gap.reason,
        }
        for gap in gaps
    )


__all__ = [
    "RULE_KINDS",
    "RULE_PRESENCE",
    "RULE_TEXT_CHANGE",
    "RULE_THRESHOLD",
    "COMPARATORS",
    "DEFAULT_LOOKBACK",
    "SHOCK_RULES",
    "MarketRule",
    "ShockFlag",
    "ShockGap",
    "evaluate",
    "flag_payload",
    "gaps_payload",
]
