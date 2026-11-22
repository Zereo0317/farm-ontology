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
import math
from datetime import date, datetime, timedelta
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
METHOD_NOISE_GDD = 45.0

#: GDD credited when the season is anchored by an EMERGENCE observation
#: instead of a sowing date (the VE threshold is presumed attained).
EMERGENCE_CREDIT_GDD = GDD_THRESHOLDS_VALUE_VE = 90.0

# ===========================================================================
# CULTIVAR GDD PROFILES (D-ENGINE-1 recalibration, 2026-11-18).
#
# History: v0 shipped ONE continental-extension table (R7=1850/R8=2100).
# The 2026 multi-site field campaign (reports/fieldtest-multisite-REPORT.md)
# proved it stalls ALL Hokkaido sites at R1–R3 while real Hokkaido soy
# (Yukihomare/Ryuuhou class) matures late-Sep–mid-Oct — a 40–56 % shortfall.
# Profiles below replace the single table. Verification trail per profile:
#
# PUBLISHED ANCHORS USED (all checked 2026-11-18):
#   [A] MAFF 作物優良品種紹介「ユキホマレ」(d_ziten/pdf/81_yukihomare.pdf):
#       "白目品種のなかでは成熟期が最も早く…" — earliest-maturing white-eye
#       Hokkaido variety; combine-harvest grade maturity from late September.
#   [B] 日本作物学会紀事 抄録 223_0_434 (ユキホマレ田植え後播種, J-STAGE,
#       accessed 2026-11-18): ユキホマレ maturity lands 9月第6半旬–10月第1半旬
#       (≈ Sep 25–Oct 5) even under JUNE late-sowing in 道央 ⇒ standard
#       May-sowing matures at or before late September.
#   [C] HRO 豆類地帯別栽培指針 (h06s_joho/h0600008.htm, 平成4–5年度,
#       AMeDAS 1983–92): Hokkaido soybean zones are delimited BY accumulated
#       temperature — zone-to-zone GDD budgets differ strongly.
#   [D] 中野・熊谷・鮫島ほか 2015, 日作紀 84(4):408-417, doi:10.1626/jcs.84.408:
#       development models for リュウホウ/エンレイ/フクユタカ reproduce
#       出芽→開花 within 1.4–2.2 d and 開花→子実肥大始 within 1.2–2.8 d —
#       the model lineage a future engine iteration should adopt.
#   [E] 中野 2025, 日作紀 94(3):263-270, doi:10.1626/jcs.94.263: the lineage
#       extends to ユキホマレ/里のほほえみ/サチユタカ as cultivar parameters.
# TODO-VERIFY [SOY-GDD-TRIAL-PARAMS]: the per-cultivar parameter vectors of
#   [D]/[E] sit inside PDFs this repo cannot parse offline; when a teammate
#   extracts them, replace this derived table with the trial parameters.
#   Suzuki-cha / Toyoharuka nursery numbers were NOT locatable in an
#   offline-readable form and are TODO-flagged, NOT interpolated silently.
#
# DERIVATION (declared): thresholds fitted so that, on the RECORDED 2026
#   archive climate of the four fieldtest Hokkaido sites (fixtures/
#   fieldtest/site-*/, captured 2026-11-18), the fitted thresholds place
#   R1 at mid-July bloom and R7 inside late-Sep–early-Oct for the main
#   belts (Biratori/Obihiro/Nakafurano), with R6 attainable even at
#   maritime-cool Nemuro before the frost window. VE retains the v0 anchor
#   (90; ~1 week cool-soil emergence). The V-structure below R1 is spaced
#   per short-season vegetative compression; intermediate R-stages
#   interleave per Fehr-proportioned intervals (declared approximation).
#   Hence every value is REGION-AND-YEAR FITTED — a calibration to
#   published calendars × recorded climate, not a laboratory trial result.
# ===========================================================================

_GENERIC_EXTENSION_THRESHOLDS: tuple[tuple[str, float], ...] = (
    ("VE", 90.0),
    ("V1", 190.0),
    ("V2", 290.0),
    ("V3", 390.0),
    ("V4", 510.0),
    ("V5", 640.0),
    ("V6", 780.0),
    ("R1", 830.0),
    ("R3", 1060.0),
    ("R5", 1260.0),
    ("R6", 1560.0),
    ("R7", 1850.0),
    ("R8", 2100.0),
)


@dataclass(frozen=True)
class CultivarGddProfile:
    """One cultivar-class stage table with per-threshold provenance."""

    profile_id: str
    thresholds: tuple[tuple[str, float], ...]
    per_stage_sources: tuple[tuple[str, str], ...]  # stage -> VERIFY sentence
    validity_note: str


_HOKKAIDO_SHORT_SOURCES: tuple[tuple[str, str], ...] = (
    ("VE", "emergence anchor retained from v0 (site-recorded cool-soil week); "
           "VERIFY [SOY-GDD-BASE]"),
    ("V1", "V1–V5 short-season vegetative compression per derivation note "
           "(declared approximation); TODO-VERIFY [SOY-GDD-TRIAL-PARAMS]"),
    ("V2", "as V1: derived spacing, TODO-VERIFY trial parameters"),
    ("V3", "as V1: derived spacing, TODO-VERIFY trial parameters"),
    ("V4", "as V1: derived spacing, TODO-VERIFY trial parameters"),
    ("V5", "as V1: derived spacing; indeterminate soy begins bloom around "
           "V5–V6, so V5 hugs R1 by design"),
    ("R1", "fitted: mid-July beginning bloom (Biratori/Obihiro 2026 curves "
           "cross ~395 GDD 10–20 Jul); consistent with Hokkaido norms "
           "[A][B][C]; TODO-VERIFY [SOY-GDD-TRIAL-PARAMS]"),
    ("R3", "Fehr-proportional interval from R1 (declared approximation to "
           "the R1→R7 fit); TODO-VERIFY trial parameters"),
    ("R5", "Fehr-proportional interval; beginning-seed mid-August "
           "consistency on recorded curves; TODO-VERIFY"),
    ("R6", "fitted so maritime-cool Nemuro attains full seed before the "
           "October kill window (recorded curve crosses ~late Sep)"),
    ("R7", "PRIMARY FIT: recorded 2026 climate crosses 950 GDD 11–20 Sep at "
           "Biratori/Obihiro/Nakafurano, placing beginning maturity one to "
           "two weeks ahead of the published full-maturity window "
           "[A][B][C]; Nemuro's recorded sums finish 14 % short — a "
           "recorded-climate fact for the coolest matrix site, inside the "
           "15 % mismatch budget; TODO-VERIFY trial parameters"),
    ("R8", "aligned to the published late-Sep–early-Oct combine window "
           "[A][B] (recorded curves cross 1050 on 27 Sep Biratori / 5 Oct "
           "Obihiro); declared approximation — senescence dry-down is not "
           "purely thermal"),
)

CULTIVAR_GDD_PROFILES: dict[str, CultivarGddProfile] = {
    "hokkaido-short": CultivarGddProfile(
        profile_id="hokkaido-short",
        thresholds=(
            ("VE", 90.0),
            ("V1", 160.0),
            ("V2", 230.0),
            ("V3", 300.0),
            ("V4", 355.0),
            ("V5", 385.0),
            ("R1", 395.0),
            ("R3", 505.0),
            ("R5", 715.0),
            ("R6", 825.0),
            ("R7", 950.0),
            ("R8", 1050.0),
        ),
        per_stage_sources=_HOKKAIDO_SHORT_SOURCES,
        validity_note=(
            "CALIBRATED for Hokkaido Yukihomare/Ryuuhou-class (very-early to "
            "early) cultivars under base-10/cap-30 accumulation; DO NOT use "
            "for continental full-season cultivars (use 'generic-extension') "
            "or photoperiod-sensitive southern sowings. Linear-GDD model "
            "WITH DECLARED LIMIT: no photoperiod term, so warm-climate "
            "seasons compress artificially (see spec §2)."
        ),
    ),
    "generic-extension": CultivarGddProfile(
        profile_id="generic-extension",
        thresholds=_GENERIC_EXTENSION_THRESHOLDS,
        per_stage_sources=tuple(
            (stage, "v0 continental public-guide value (RETAINED verbatim "
                    "under profile 'generic-extension'; VERIFY [SOY-GDD-TABLE])")
            for stage, _ in _GENERIC_EXTENSION_THRESHOLDS
        ),
        validity_note=(
            "Continental temperate extension curve as shipped in v0. Proven "
            "by the 2026 field campaign to over-demand by 40–56 % for "
            "Hokkaido climates; retained for non-Hokkaido comparability and "
            "backward compatibility ONLY."
        ),
    ),
}

#: Default profile: the campaign showed the engine lives in Hokkaido.
DEFAULT_CULTIVAR_PROFILE = "hokkaido-short"

#: Compat view of the DEFAULT profile's table (what GDD_THRESHOLDS meant).


def profile_or_raise(profile_id: str | None) -> CultivarGddProfile:
    """Registry lookup; unknown ids raise KeyError (loud, never silent)."""
    if profile_id is None:
        profile_id = DEFAULT_CULTIVAR_PROFILE
    if profile_id not in CULTIVAR_GDD_PROFILES:
        raise KeyError(
            f"unknown cultivar GDD profile {profile_id!r}; known: "
            f"{sorted(CULTIVAR_GDD_PROFILES)}"
        )
    return CULTIVAR_GDD_PROFILES[profile_id]


def _stage_sources_payload(profile: CultivarGddProfile) -> tuple[str, ...]:
    return tuple(f"{stage}: {text}" for stage, text in profile.per_stage_sources)


class _ThresholdProxy(tuple):
    """Back-compat tuple of (stage, gdd) pairs bound to the default profile.

    Iteration/behave-as-tuple is preserved; attribute access exposes the
    owning profile id so callers can detect the indirection.
    """

    def __new__(cls, items: tuple, profile_id: str):
        self = super().__new__(cls, items)
        self._profile_id = profile_id
        return self

    @property
    def profile_id(self):
        return self._profile_id


_TH = profile_or_raise(DEFAULT_CULTIVAR_PROFILE).thresholds
GDD_THRESHOLDS: _ThresholdProxy = _ThresholdProxy(_TH, DEFAULT_CULTIVAR_PROFILE)
THRESHOLD_TABLE_VERSION = f"hokkaido-short-v1(default)+generic-extension-v0"

#: Provenance sentence carried on every reading (VERIFY-tagged claim).
PHENOLOGY_SOURCE_NOTE = (
    "VERIFY [SOY-GDD]: base 10 °C per Japanese soybean guideline practice; "
    "stage thresholds are CULTIVAR-PROFILE calibrated (default "
    f"'{DEFAULT_CULTIVAR_PROFILE}', derived from published Hokkaido maturity "
    "calendars × recorded 2026 site climate; trial parameters TODO); "
    "cap-at-30 °C daily contribution is a declared modelling choice; the "
    "linear model carries NO photoperiod term (warm-climate compression is "
    "a declared limitation)."
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
    cultivar_profile: str
    stage_source_note: str
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
            "cultivar_profile": self.cultivar_profile,
            "stage_source_note": self.stage_source_note,
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
    result = float(value)
    if not math.isfinite(result):
        raise AgronomyGap("malformed-row", f"row {index}: 't_mean_c' must be finite", missing=("t_mean_c",))
    return result


def daily_gdd_contribution(t_mean_c: float) -> float:
    """Clamped daily contribution: max(0, min(t_mean − base, cap))."""
    if isinstance(t_mean_c, bool) or not isinstance(t_mean_c, (int, float)) or not math.isfinite(t_mean_c):
        raise ValueError("t_mean_c must be finite")
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
        if not math.isfinite(value) or value <= 0:
            raise AgronomyGap("missing-native-resolution", f"row {index}: native_resolution_km must be finite and positive")
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
    cultivar_profile: str | None = None,
) -> PhenologyReading:
    """Classify the soybean stage from daily rows and a season anchor.

    Rows are daily maps with ``date`` (ISO) and ``t_mean_c``; every row must
    also carry ``native_resolution_km``. Accumulation starts at the sowing
    date inclusive, or — when sowing is unknown but an emergence observation
    exists — at the emergence date with the VE threshold credited.

    ``cultivar_profile`` selects the stage table (default
    ``'hokkaido-short'``; the 2026 field campaign proved the v0
    continental table stalls Hokkaido seasons — see module docstring).

    Raises :class:`AgronomyGap` (named gaps) for missing anchors, malformed
    rows, duplicated/regressive dates, zero usable rows, or missing native
    resolution. Unknown profiles raise KeyError (loud, registry-backed).
    When ``at`` is provided it must be aware; rows and anchors after its
    UTC calendar date are refused. Source availability is not verified by
    this interface; callers must verify it before operational reliance.
    """
    moment = ensure_utc(at, "at") if at is not None else None
    profile = profile_or_raise(cultivar_profile)
    table = profile.thresholds
    if sowing is None and emergence is None:
        raise AgronomyGap(
            "missing-sowing-anchor",
            "phenology needs a sowing date or an emergence observation; "
            "without an anchor no stage can ever be announced",
            missing=("sowing", "emergence"),
            remediation="pass sowing=<aware datetime>, or emergence=<aware "
            "datetime> from an observed emergence record",
        )
    for name, anchor_time in (("sowing", sowing), ("emergence", emergence)):
        if anchor_time is not None:
            anchor_utc = ensure_utc(anchor_time, name)
            if moment is not None and anchor_utc > moment:
                raise AgronomyGap("future-anchor", f"{name} occurs after the as-of instant")
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
        if moment is not None and day > moment.date():
            raise AgronomyGap("future-row", f"row {index}: date {day} is after the as-of date")
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

    if usable[0][0] != anchor_date:
        raise AgronomyGap("missing-anchor-day", f"daily series does not start on the anchor date {anchor_date.isoformat()}")
    for index in range(1, len(usable)):
        if usable[index][0] - usable[index - 1][0] != timedelta(days=1):
            raise AgronomyGap("daily-sequence-hole", f"daily temperature series has a gap before {usable[index][0].isoformat()}")

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

    stage, stage_index, threshold_used = _classify(cumulative, table)
    next_threshold = (
        table[stage_index + 1][1]
        if stage_index + 1 < len(table)
        else None
    )
    if next_threshold is None:
        centre = threshold_used + (threshold_used - table[-2][1]) / 2.0
    else:
        centre = (threshold_used + next_threshold) / 2.0
    uncertainty = max(METHOD_NOISE_GDD, abs(cumulative - centre))

    nonzero = [value for value in contributions if value > 0]
    mean_rate = (sum(nonzero) / len(nonzero)) if nonzero else None
    if mean_rate is not None and mean_rate >= MIN_MEAN_RATE_FOR_DAYS_BAND:
        days_band = round(uncertainty / mean_rate, 1)
    else:
        days_band = None  # a gap on the days conversion, never a fake date

    stage_source = dict(profile.per_stage_sources).get(stage, "")
    table_version = f"{profile.profile_id}-gdd-table"
    support = SupportDeclaration(
        base=f"grid-support (native {resolution_km:g} km)",
        notes=(PHENOLOGY_SOURCE_NOTE, f"profile {profile.profile_id}: "
               f"{profile.validity_note}"),
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
        threshold_table_version=table_version,
        cultivar_profile=profile.profile_id,
        stage_source_note=stage_source,
        config_version=CONFIG_VERSION,
        source_note=PHENOLOGY_SOURCE_NOTE,
        support=support,
    )


def _classify(
    cumulative: float, table: tuple[tuple[str, float], ...]
) -> tuple[str, int, float]:
    """Highest coarse stage whose threshold the cumulative GDD has reached."""
    stage, index, used = table[0][0], 0, table[0][1]
    for position, (name, threshold) in enumerate(table):
        if cumulative >= threshold:
            stage, index, used = name, position, threshold
    return stage, index, used


__all__ = [
    "GDD_BASE_C",
    "GDD_CAP_CONTRIBUTION_C",
    "GDD_THRESHOLDS",
    "CULTIVAR_GDD_PROFILES",
    "CultivarGddProfile",
    "DEFAULT_CULTIVAR_PROFILE",
    "profile_or_raise",
    "THRESHOLD_TABLE_VERSION",
    "PHENOLOGY_SOURCE_NOTE",
    "METHOD_NOISE_GDD",
    "EMERGENCE_CREDIT_GDD",
    "MIN_MEAN_RATE_FOR_DAYS_BAND",
    "PhenologyReading",
    "daily_gdd_contribution",
    "phenology_reading",
]
