"""Soybean GDD phenology tracker (WS3.1).

Growing-degree-days accumulate from the sowing anchor with a 10 °C base
(Unirosse and tenki.jp soybean growing guides and the common Japanese
soybean-culture guideline both use base 10 °C) and a documented cap on the
daily contribution.

MODELLING CHOICES — every one is declared, none is silent
---------------------------------------------------------

* BASE 10 °C. VERIFY [SOY-GDD-BASE]: standard for Japanese soybean
  guidelines; recalibrate per cultivar before agronomic reliance.
* CAP-AT-30 °C: a daily MEAN above 30 °C contributes no more than a 30 °C
  mean would (``t_mean − base`` clamped to 20.0). Heat above 30 °C buys
  little development and stresses the crop; capping the contribution keeps
  a hot spell from vaulting the stage table. This is a modelling choice,
  not a measured physiological limit.
* THRESHOLD TABLE: coarse V/R buckets for a temperate short-season
  soybean, VALUES ARE ROUNDED APPROXIMATIONS assembled from public soybean
  GDD guides (vegetative stages every ~100 GDD after emergence; R-stage
  spacings from common extension curves). VERIFY [SOY-GDD-TABLE]:
  recalibrate against local Hokkaido variety trials before any agronomic
  reliance; the table is CONFIG exactly so that recalibration is a data
  edit, not a code edit.
* UNCERTAINTY: the midpoint between this stage's threshold and the next
  one is treated as the empirical centre of the announced stage. The
  reading carries an uncertainty of ±max(method noise, |cum − centre|)
  GDD — widest near stage boundaries, tightest mid-stage — plus a date
  equivalent divided by the mean realised daily contribution. The date
  equivalent is published only when the mean contribution is large enough
  to divide by (otherwise that field is None: a gap, not a zero).
* ANCHORS: GDD counts from the SOWING date. If only an EMERGENCE
  observation exists, accumulation starts at the emergence day and the VE
  threshold is credited at the start (EMERGENCE_CREDIT_GDD) — declared,
  and the reading's anchor field says which happened. When both anchors
  exist, sowing is used and the credit implied by the emergence date is
  cross-checked; a mismatch beyond the method noise sets
  ``anchor_conflict`` on the reading (never corrected silently).

Missing anchors ⇒ :class:`AgronomyGap` with a named gap. Malformed rows
(their index named), duplicated dates and date regressions are gaps too —
never silently skipped. Temperatures arrive as native-support GRID rows
(synthetic fixtures or, later, WS2 ingests); every reading carries the
native resolution onward. Tests are offline; no wall clock is read.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Mapping, Sequence

from farm_ontology.agronomy.common import (
    CONFIG_VERSION,
    USE_CLASS_FIELD_OPS,
    AgronomyGap,
    SupportDeclaration,
)
from farm_ontology.timeutil import ensure_utc

#: Base temperature for soybean GDD. VERIFY [SOY-GDD-BASE].
GDD_BASE_C = 10.0

#: Cap on the daily-mean contribution, i.e. "cap-at-30 °C" (30 − base 10).
#: A daily mean hotter than 30 °C contributes as if it were exactly 30 °C.
GDD_CAP_CONTRIBUTION_C = 20.0

#: Method noise floor on any stage announcement, in GDD. The threshold
#: table is coarse; the announcement never pretends to be tighter than this.
METHOD_NOISE_GDD = 40.0

#: GDD credited when the season is anchored by an EMERGENCE observation
#: instead of a sowing date (the VE threshold is presumed attained).
EMERGENCE_CREDIT_GDD = GDD_THRESHOLDS_VALUE_VE = 90.0

#: Coarse soybean stage thresholds, cumulative GDD (°C·d) from sowing.
#: VERIFY [SOY-GDD-TABLE] — rounded public-guide values, not local trials.
GDD_THRESHOLDS: tuple[tuple[str, float], ...] = (
    ("VE", 90.0),   # emergence
    ("V1", 190.0),  # first trifoliolate
    ("V2", 290.0),
    ("V3", 390.0),
    ("V4", 510.0),
    ("V5", 640.0),
    ("V6", 780.0),
    ("R1", 830.0),  # beginning bloom
    ("R3", 1060.0), # beginning pod
    ("R5", 1260.0), # beginning seed
    ("R6", 1560.0), # full seed
    ("R7", 1850.0), # beginning maturity
    ("R8", 2100.0), # full maturity
)

#: Identifier of the table above, carried on every reading.
THRESHOLD_TABLE_VERSION = "soybean-gdd-coarse-v0"

#: Provenance sentence carried on every reading (VERIFY-tagged claim).
PHENOLOGY_SOURCE_NOTE = (
    "VERIFY [SOY-GDD]: base 10 °C per Japanese soybean guideline practice; "
    "threshold table is a coarse rounded public-guide approximation "
    "(temperate short-season soybean), recalibrate against local variety "
    "trials; cap-at-30 °C daily contribution is a declared modelling choice."
)

#: Mean realised daily contribution below which the days-uncertainty
#: conversion is refused (a division by a near-zero rate invents dates).
MIN_MEAN_RATE_FOR_DAYS_BAND = 1.0


@dataclass(frozen=True)
class PhenologyReading:
    """One stage announcement with its uncertainty band and support stamp."""

    stage: str
    stage_index: int
    cumulative_gdd: float
    gdd_base_c: float
    cap_contribution_c: float
    threshold_used: float
    threshold_next: float | None
    midpoint_centre: float
    uncertainty_gdd: float
    mean_daily_contribution: float | None
    uncertainty_days: float | None
    anchor: str              # "sowing" | "emergence"
    anchor_conflict: bool
    days_counted: int
    first_date: str
    last_date: str
    method_noise_gdd: float
    threshold_table_version: str
    config_version: str
    source_note: str
    support: SupportDeclaration
    use_class: str = USE_CLASS_FIELD_OPS

    def to_payload(self) -> dict:
        return {
            "stage": self.stage,
            "stage_index": self.stage_index,
            "cumulative_gdd": self.cumulative_gdd,
            "uncertainty_gdd": self.uncertainty_gdd,
            "uncertainty_days": self.uncertainty_days,
            "mean_daily_contribution": self.mean_daily_contribution,
            "anchor": self.anchor,
            "anchor_conflict": self.anchor_conflict,
            "days_counted": self.days_counted,
            "first_date": self.first_date,
            "last_date": self.last_date,
            "threshold_used": self.threshold_used,
            "threshold_next": self.threshold_next,
            "threshold_table_version": self.threshold_table_version,
            "config_version": self.config_version,
            "support": self.support.to_payload(),
            "use_class": self.use_class,
            "source_note": self.source_note,
        }


def _parse_date(text: object, index: int) -> date:
    if isinstance(text, date) and not isinstance(text, datetime):
        return text
    if not isinstance(text, str):
        raise AgronomyGap(
            "malformed-row",
            f"row {index}: 'date' must be an ISO YYYY-MM-DD string",
            missing=("date",),
        )
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise AgronomyGap(
            "malformed-row",
            f"row {index}: unparseable date {text!r}: {error}",
            missing=("date",),
        ) from error


def _t_mean(row: Mapping, index: int) -> float:
    value = row.get("t_mean_c")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AgronomyGap(
            "malformed-row",
            f"row {index}: 't_mean_c' must be a number",
            missing=("t_mean_c",),
        )
    return float(value)


def daily_gdd_contribution(t_mean_c: float) -> float:
    """Clamped daily contribution: max(0, min(t_mean − base, cap))."""
    return max(0.0, min(float(t_mean_c) - GDD_BASE_C, GDD_CAP_CONTRIBUTION_C))


def _require_native_resolution(rows: Sequence[Mapping]) -> float:
    """The grid support must be declared; mixed resolutions are refused.

    Joins never rewrite support (roadmap §1 rule 2): a balance or a reading
    assembled from rows of DIFFERENT native resolutions would be exactly
    such a rewrite, so it is a gap instead.
    """
    resolutions: set[float] = set()
    for index, row in enumerate(rows):
        value = row.get("native_resolution_km")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise AgronomyGap(
                "missing-native-resolution",
                f"row {index}: 'native_resolution_km' is required so the "
                "reading carries its native support",
                missing=(f"row[{index}].native_resolution_km",),
            )
        resolutions.add(float(value))
    if len(resolutions) > 1:
        raise AgronomyGap(
            "grid-resolution-mixed",
            "rows mix native resolutions "
            f"{sorted(resolutions)}; a reading never blends supports",
        )
    return resolutions.pop()


def phenology_reading(
    rows: Sequence[Mapping],
    *,
    sowing: datetime | None,
    emergence: datetime | None,
    at: datetime | None = None,
) -> PhenologyReading:
    """Classify the soybean stage from daily rows and a season anchor.

    Rows are daily maps with ``date`` (ISO) and ``t_mean_c``; every row must
    also carry ``native_resolution_km``. Accumulation starts at the sowing
    date inclusive, or — when sowing is unknown but an emergence observation
    exists — at the emergence date with the VE threshold credited.

    Raises :class:`AgronomyGap` (named gaps) for missing anchors, malformed
    rows, duplicated/regressive dates, zero usable rows, or missing native
    resolution. ``at`` is optional context; it is validated aware but does
    not change the mathematics.
    """
    del at  # accepted for call-site symmetry; the maths is date-driven
    if sowing is None and emergence is None:
        raise AgronomyGap(
            "missing-sowing-anchor",
            "phenology needs a sowing date or an emergence observation; "
            "without an anchor no stage can ever be announced",
            missing=("sowing", "emergence"),
            remediation="pass sowing=<aware datetime>, or emergence=<aware "
            "datetime> from an observed emergence record",
        )
    for name, moment in (("sowing", sowing), ("emergence", emergence)):
        if moment is not None:
            ensure_utc(moment, name)
    if not rows:
        raise AgronomyGap(
            "no-usable-rows",
            "no daily temperature rows were supplied",
            missing=("rows",),
        )
    resolution_km = _require_native_resolution(rows)

    anchor_at = (sowing if sowing is not None else emergence)
    assert anchor_at is not None
    # Anchor DAY is taken in the anchor datetime's own timezone: a local
    # JST sowing date must stay that calendar day. ensure_utc above has
    # already refused naive datetimes.
    anchor_date = anchor_at.date()

    ordered: list[tuple[date, float]] = []
    seen: set[date] = set()
    previous: date | None = None
    for index, row in enumerate(rows):
        day = _parse_date(row.get("date"), index)
        if day in seen:
            raise AgronomyGap(
                "duplicate-date",
                f"row {index}: date {day.isoformat()} appears twice",
            )
        if previous is not None and day <= previous:
            raise AgronomyGap(
                "regressive-dates",
                f"row {index}: date {day.isoformat()} does not advance "
                f"beyond {previous.isoformat()}",
            )
        previous = day
        seen.add(day)
        ordered.append((day, _t_mean(row, index)))

    usable = [(day, value) for day, value in ordered if day >= anchor_date]
    if not usable:
        raise AgronomyGap(
            "no-usable-rows",
            f"no daily rows on or after the {anchor_date.isoformat()} anchor",
            missing=(f"rows-after-{anchor_date.isoformat()}",),
        )

    anchor = "sowing" if sowing is not None else "emergence"
    anchor_conflict = False
    cumulative = 0.0
    if anchor == "emergence":
        cumulative = EMERGENCE_CREDIT_GDD
    else:
        # Cross-check: the implied VE credit at the emergence date (if one
        # is also given) must lie inside the method noise, else flag.
        if emergence is not None:
            implied = 0.0
            for day, value in usable:
                if day >= emergence.date():
                    break
                implied += daily_gdd_contribution(value)
            if abs(implied - EMERGENCE_CREDIT_GDD) > METHOD_NOISE_GDD:
                anchor_conflict = True

    contributions: list[float] = []
    for _, value in usable:
        contribution = daily_gdd_contribution(value)
        contributions.append(contribution)
        cumulative += contribution

    stage, stage_index, threshold_used = _classify(cumulative)
    next_threshold = (
        GDD_THRESHOLDS[stage_index + 1][1]
        if stage_index + 1 < len(GDD_THRESHOLDS)
        else None
    )
    if next_threshold is None:
        centre = threshold_used + (threshold_used - GDD_THRESHOLDS[-2][1]) / 2.0
    else:
        centre = (threshold_used + next_threshold) / 2.0
    uncertainty = max(METHOD_NOISE_GDD, abs(cumulative - centre))

    nonzero = [value for value in contributions if value > 0]
    mean_rate = (sum(nonzero) / len(nonzero)) if nonzero else None
    if mean_rate is not None and mean_rate >= MIN_MEAN_RATE_FOR_DAYS_BAND:
        days_band = round(uncertainty / mean_rate, 1)
    else:
        days_band = None  # a gap on the days conversion, never a fake date

    support = SupportDeclaration(
        base=f"grid-support (native {resolution_km:g} km)",
        notes=(PHENOLOGY_SOURCE_NOTE,),
    )
    return PhenologyReading(
        stage=stage,
        stage_index=stage_index,
        cumulative_gdd=round(cumulative, 1),
        gdd_base_c=GDD_BASE_C,
        cap_contribution_c=GDD_CAP_CONTRIBUTION_C,
        threshold_used=threshold_used,
        threshold_next=next_threshold,
        midpoint_centre=centre,
        uncertainty_gdd=round(uncertainty, 1),
        mean_daily_contribution=(round(mean_rate, 2) if mean_rate is not None else None),
        uncertainty_days=days_band,
        anchor=anchor,
        anchor_conflict=anchor_conflict,
        days_counted=len(usable),
        first_date=usable[0][0].isoformat(),
        last_date=usable[-1][0].isoformat(),
        method_noise_gdd=METHOD_NOISE_GDD,
        threshold_table_version=THRESHOLD_TABLE_VERSION,
        config_version=CONFIG_VERSION,
        source_note=PHENOLOGY_SOURCE_NOTE,
        support=support,
    )


def _classify(cumulative: float) -> tuple[str, int, float]:
    """Highest coarse stage whose threshold the cumulative GDD has reached."""
    stage, index, used = GDD_THRESHOLDS[0][0], 0, GDD_THRESHOLDS[0][1]
    for position, (name, threshold) in enumerate(GDD_THRESHOLDS):
        if cumulative >= threshold:
            stage, index, used = name, position, threshold
    return stage, index, used


__all__ = [
    "GDD_BASE_C",
    "GDD_CAP_CONTRIBUTION_C",
    "GDD_THRESHOLDS",
    "THRESHOLD_TABLE_VERSION",
    "PHENOLOGY_SOURCE_NOTE",
    "METHOD_NOISE_GDD",
    "EMERGENCE_CREDIT_GDD",
    "MIN_MEAN_RATE_FOR_DAYS_BAND",
    "PhenologyReading",
    "daily_gdd_contribution",
    "phenology_reading",
]
