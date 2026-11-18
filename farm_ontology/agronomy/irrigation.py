"""FAO-56 dual-Kc irrigation adviser v0 (WS3.2).

Structure follows FAO-56's dual crop coefficient, ``ETc ≈ (Kcb + Ke) × ET0``,
with the basal coefficient driven by the crop stage from
:mod:`farm_ontology.agronomy.phenology` and a simplified surface-evaporation
pulse fed by rainfall. SIMPLIFICATIONS — all declared:

* v0 omits the climate adjustment of Kc_max and the frost/cover
  refinements (FAO-56 Eq. 72 context); Kc_max is a constant.
* Fractional cover is approximated as ``fc ≈ Kcb / Kc_max`` (clipped);
  FAO-56's tabulated fc curves are finer.
* Runoff is handled as a flat 20 % loss on daily rainfall
  (RUNOFF_LOSS_FRACTION), biasing the balance toward MORE irrigation
  demand — the conservative direction for a water-stress adviser. Deep
  percolation is whatever pushes root depletion below zero (discarded).
* Initial conditions are declared, not measured: the season starts at
  INITIAL_ROOT_DEPLETION_MM and a dry surface (De = TEW).

THE HONEST-CLAIMS LADDER
------------------------

* ``grid-support (native NxN km)`` — ALWAYS on the output: the water
  balance itself is computed from gridded ET0/rainfall rows. N is taken
  from the rows' own ``native_resolution_km``; mixed resolutions are a
  gap (a blended support would be a rewritten support).
* ``probe-support (…)`` — added ONLY when :func:`has_calibrated_coverage`
  says a live calibrated soil-moisture row covers the parcel. A point
  probe yields a PROBE FOOTPRINT claim; the text never says hectares
  unless the sensor row itself specifies a coverage area.
* ``parcel-support (…)`` — only when the sensor row itself reports an
  area in hectares. Reserved for rows that explicitly declare
  ``coverage.area_ha``; the engine never converts a probe to hectares.

Soil-moisture probes never CHANGE the grid-derived number in v0; a fresh
probe reading produces a divergence note (model vs probe-implied
depletion) for the human signatory. Uncalibrated, expired-cert or stale
sensor rows are listed as excluded with their reason — the trail is
published, not hidden.

All thresholds are CONFIG with VERIFY-tagged sources. Tests are offline;
timestamps are injected.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Mapping, Sequence

from farm_ontology.agronomy.common import (
    CONFIG_VERSION,
    USE_CLASS_FIELD_OPS,
    AgronomyGap,
    SupportDeclaration,
)
from farm_ontology.agronomy.phenology import (
    DEFAULT_CULTIVAR_PROFILE,
    daily_gdd_contribution,
)
from farm_ontology.model import Observation
from farm_ontology.timeutil import ensure_utc

# ---------------------------------------------------------------------------
# Config constants (VERIFY-tagged; the spec doc reproduces the sources).


@dataclass(frozen=True)
class SoilProfile:
    """Root-zone soil constants for one advisory run. Declared, not measured."""

    theta_fc_m3m3: float = 0.30      # field capacity, volumetric (loam-ish)
    theta_wp_m3m3: float = 0.15      # wilting point, volumetric
    rooting_depth_m: float = 0.7     # Soybean FAO: 0.6–1.5 m; short season
    p_depletion_fraction: float = 0.50   # FAO-56 Table 22 soybean p ≈ 0.50

    @property
    def taw_mm(self) -> float:
        return 1000.0 * (self.theta_fc_m3m3 - self.theta_wp_m3m3) * self.rooting_depth_m

    @property
    def raw_mm(self) -> float:
        return self.p_depletion_fraction * self.taw_mm


@dataclass(frozen=True)
class IrrigationCfg:
    """Numeric knobs of the v0 balance. Each carries its justification."""

    runoff_loss_fraction: float = 0.20   # conservative rain-to-runoff haircut
    initial_root_depletion_mm: float | None = None  # None ⇒ start at RAW
    tew_mm: float = 12.0                 # total evaporable water (surface)
    rew_mm: float = 5.0                  # readily evaporable water
    kc_max: float = 1.20                 # clip ceiling for Kcb + Ke
    kc_min: float = 0.15                 # bare-soil basal floor
    initial_surface_depletion_mm: float | None = None  # None ⇒ dry start (TEW)


# ---------------------------------------------------------------------------
# Running-Kcb anchor tables (D-ENGINE-2, 2026-11-18 recalibration).
#
# Piecewise-linear Kcb over the DAY's RUNNING cumulative GDD — NOT the
# season-final reading's value. This is the fix for the campaign's
# `kcb-static-across-season` artefact (the v0 balance tariffed vegetative
# weeks at the final stage's water use; see the finder's report §4).
#
# Anchor VALUES from FAO-56 Table 17 soybean basal coefficients
# (Kcb_ini ≈ 0.15, Kcb_mid ≈ 1.15, Kcb_end ≈ 0.50; VERIFY [FAO-56-T17]),
# placed on the GDD axis at each profile's stage thresholds (the profile
# is the thing that carries calendar validity; see phenology.py).
# The senescence tail flattens to 0.35 at R8 (harvest-dry canopy).

#: Kcb (gdd_from_sowing, kcb) anchors per cultivar profile.
KCB_ANCHOR_PROFILES: dict[str, tuple[tuple[float, float], ...]] = {
    "hokkaido-short": (
        (0.0, 0.15),
        (90.0, 0.20),    # VE: soil still largely bare
        (395.0, 1.00),   # R1: canopy closing through bloom
        (505.0, 1.15),   # R3: peak — FAO mid
        (715.0, 1.15),   # R5: plateau through beginning seed
        (825.0, 1.05),   # R6: full seed, canopy aging
        (950.0, 0.60),   # R7: beginning maturity, senescing
        (1050.0, 0.35),  # R8: harvest-dry remainder
    ),
    "generic-extension": (
        (0.0, 0.15),
        (90.0, 0.30),
        (830.0, 1.10),   # R1
        (1060.0, 1.15),  # R3
        (1560.0, 1.00),  # R6
        (1850.0, 0.60),  # R7
        (2100.0, 0.30),  # R8
    ),
}

KCB_ANCHORS_SOURCE_NOTE = (
    "VERIFY [FAO-56-T17]: anchor values are the soybean basal coefficients "
    "(0.15 ini / 1.15 mid / 0.50 end) placed per cultivar profile's stage "
    "GDD thresholds; running per-day interpolation replaces the v0 "
    "season-static Kcb (fieldtest defect kcb-static-across-season, 2026-11-18)."
)


def kcb_anchors_for(profile_id: str | None) -> tuple[tuple[float, float], ...]:
    """Registry lookup for the Kcb anchor curve (loud KeyError on unknown)."""
    resolved = profile_id if profile_id is not None else DEFAULT_CULTIVAR_PROFILE
    if resolved not in KCB_ANCHOR_PROFILES:
        raise KeyError(
            f"no Kcb anchor curve for profile {resolved!r}; known: "
            f"{sorted(KCB_ANCHOR_PROFILES)}"
        )
    return KCB_ANCHOR_PROFILES[resolved]


DEFAULT_IRRIGATION_CONFIG = IrrigationCfg()

IRRIGATION_CONFIG_SOURCE_NOTE = (
    "VERIFY [FAO-56]: structure per Allen et al. 1998 (dual Kc, Tables 12/22); "
    "Kcb is a per-day RUNNING curve from FAO-56 T17 anchors placed on the "
    "cultivar profile's GDD thresholds (v0's season-static artefact fixed "
    "2026-11-18); fc≈Kcb/Kc_max and flat 20% runoff are declared v0 "
    "simplifications; soil parameters are generic loam, not a measured "
    "Hokkaido profile. Recalibrate all of these before reliance."
)

#: A soil-moisture row older than this is stale for irrigation purposes.
SENSOR_FRESHNESS = timedelta(hours=72)

#: Depth assumed when a probe row does not carry ``depth_cm``.
DEFAULT_PROBE_DEPTH_CM = 10.0


# ---------------------------------------------------------------------------
# The calibrated-coverage gate (the parcel-claim eligibility).


class CoverageLevel:
    """Rungs of the honest-claims ladder."""

    NONE = "none"
    PROBE_FOOTPRINT = "probe-footprint"
    PARCEL_REPORTED = "parcel-support"


@dataclass(frozen=True)
class CoverageEligibility:
    """WHAT a set of sensor rows honestly entitles the adviser to claim."""

    level: str                       # a CoverageLevel rung
    parcel: str | None
    supporting_sensor_iris: tuple[str, ...]
    excluded: tuple[dict, ...]       # {sensor_iri, reason} for every refusal
    footprint_texts: tuple[str, ...] # claim lines earned, never hectares
    area_ha_claims: tuple[float, ...]  # ONLY sensor-declared areas

    def to_payload(self) -> dict:
        return {
            "level": self.level,
            "parcel": self.parcel,
            "supporting_sensor_iris": list(self.supporting_sensor_iris),
            "excluded": [dict(item) for item in self.excluded],
            "footprint_texts": list(self.footprint_texts),
            "area_ha_claims": list(self.area_ha_claims),
        }


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _phenomenon_end(record: Mapping, key: str) -> datetime | None:
    """Accept an aware datetime or an ISO-8601 string; refuse naive/absent."""
    value = record.get(key)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            return None
        return value
    if isinstance(value, str) and value.strip():
        parsed = _parse_lenient(value)
        return parsed  # None when unparseable
    return None


def _certified_and_fresh(
    row: Mapping, at: datetime, *, store_certified: bool
) -> str | None:
    """Mirror of the sensors-ingest calibration gate, at query time.

    Returns None when the row is eligible, else the exclusion reason.
    Reuses the exact concept from ``farm_ontology.sensors.ingest``: a live
    calibration activity and an unexpired certificate, plus the adviser's
    own freshness window. A store ``Observation`` was ALREADY gated by
    that ingest (uncalibrated and expired-cert rows never became rows),
    so for those only the freshness window is re-checked here; raw
    mappings (pre-store projections, typically deserialised from JSON)
    must self-certify completely, with ISO-string stamps accepted.
    """
    if not store_certified:
        activity = row.get("calibration_activity")
        if not isinstance(activity, str) or not activity.strip():
            return "no-calibration-activity"
        due = row.get("recalibration_due")
        if isinstance(due, str) and due.strip():
            due_parsed = _parse_lenient(due)
            if due_parsed is not None and due_parsed <= at:
                return "calibration-expired"
        elif due is not None:
            return "malformed-recalibration-due"
        else:
            return "no-recalibration-due"
    end = _phenomenon_end(row, "phenomenon_end")
    if end is None:
        return "no-phenomenon-end"
    if end <= at - SENSOR_FRESHNESS:
        return "stale-beyond-freshness-window"
    return None


def _parse_lenient(text: str) -> datetime | None:
    """Aware datetime or None. Mirrors sensors-ingest's expiry reading: a
    bare ``YYYY-MM-DD`` is the strictest honest instant, midnight UTC on
    the day it names. Anything unparseable or naive-with-no-way-home is
    None (the caller decides what that means for each field)."""
    if not isinstance(text, str):
        return None
    normalised = text.replace("Z", "+00:00")
    if len(normalised) == 10 and normalised.count("-") == 2:
        normalised += "T00:00:00+00:00"
    try:
        from farm_ontology.timeutil import parse_time

        return parse_time(normalised)
    except (TypeError, ValueError):
        return None


def has_calibrated_coverage(
    sensor_rows: Iterable[Observation | Mapping],
    parcel: str,
    at: datetime,
    *,
    freshness: timedelta = SENSOR_FRESHNESS,
) -> CoverageEligibility:
    """Honestly decide what sensor rows entitle the adviser to claim.

    ``sensor_rows`` are EITHER store ``Observation`` objects (which carry no
    parcel linkage of their own — the sensors-ingest module deliberately
    never asserts a spatial join) OR row mappings that explicitly declare
    the link::

        {
          "sensor_iri": "...",
          "parcel_iri": "observation/boundary/...",   # explicit link
          "calibration_activity": "activity/...",
          "recalibration_due": "2027-04-21",
          "phenomenon_end": <aware datetime>,
          "probe_radius_m": 2.0,            # OPTIONAL: probe footprint
          "coverage_area_ha": 0.4,          # OPTIONAL: sensor-reported area
          "value": 31.2,                    # %vol for soil-vwc rows
          "depth_cm": 10,
        }

    Outcome per row:
      * missing parcel link ⇒ excluded, reason ``no-parcel-link``;
      * certification/freshness failures ⇒ excluded with the exact reason;
      * a POINT probe ⇒ at most ``probe-footprint``; the footprint text
        names the probe radius when given and otherwise states the extent
        is unspecified — it NEVER states hectares;
      * an area claim ⇒ ``parcel-support`` only because the SENSOR itself
        specified the area; the area is echoed, never computed here.
    """
    moment = ensure_utc(at, "at")
    supporting: list[str] = []
    excluded: list[dict] = []
    footprints: list[str] = []
    areas: list[float] = []
    seen_levels: list[str] = []

    for row in sensor_rows:
        if isinstance(row, Observation):
            sensor_iri = row.sensor_iri or row.iri
            record: dict = {
                "sensor_iri": sensor_iri,
                "calibration_activity": row.calibration_activity,
                # Observation carries no due-date text or parcel link;
                # the adapter refused uncertified rows outright, so a
                # stored observation is certified but is NOT parcel-linked
                # unless a later pipeline says so. Phase the fields in.
                "phenomenon_end": row.phenomenon.end,
            }
            parcel_linked = False
        elif isinstance(row, Mapping):
            sensor_iri = str(row.get("sensor_iri") or "sensor-unnamed")
            record = row
            parcel_linked = row.get("parcel_iri") == parcel
        else:
            raise AgronomyGap(
                "malformed-sensor-row",
                f"sensor row of type {type(row).__name__} is neither an "
                "Observation nor a mapping",
            )
        if not parcel_linked:
            excluded.append(
                {"sensor_iri": str(sensor_iri), "reason": "no-parcel-link"}
            )
            continue
        reason = _certified_and_fresh(
            record, moment, store_certified=isinstance(row, Observation)
        )
        if reason is not None:
            excluded.append({"sensor_iri": str(sensor_iri), "reason": reason})
            continue
        supporting.append(str(sensor_iri))
        area = _number(record.get("coverage_area_ha"))
        radius = _number(record.get("probe_radius_m"))
        if area is not None and area > 0:
            # Hectares appear ONLY because the sensor row declared them.
            areas.append(area)
            seen_levels.append(CoverageLevel.PARCEL_REPORTED)
            footprints.append(
                f"parcel-support (sensor-reported {area:g} ha coverage, "
                f"sensor {sensor_iri})"
            )
        else:
            seen_levels.append(CoverageLevel.PROBE_FOOTPRINT)
            if radius is not None and radius > 0:
                footprints.append(
                    f"probe-support (instrument-point, probe footprint "
                    f"radius {radius:g} m, sensor {sensor_iri})"
                )
            else:
                footprints.append(
                    f"probe-support (instrument-point, probe footprint "
                    f"extent unspecified — no area implied, sensor "
                    f"{sensor_iri})"
                )

    if areas:
        level = CoverageLevel.PARCEL_REPORTED
    elif supporting:
        level = CoverageLevel.PROBE_FOOTPRINT
    else:
        level = CoverageLevel.NONE
    return CoverageEligibility(
        level=level,
        parcel=parcel,
        supporting_sensor_iris=tuple(supporting),
        excluded=tuple(excluded),
        footprint_texts=tuple(footprints),
        area_ha_claims=tuple(areas),
    )


# ---------------------------------------------------------------------------
# The water balance.


def _kcb_for_running(
    cumulative_gdd: float, anchors: tuple[tuple[float, float], ...]
) -> float:
    """Piecewise-linear basal coefficient at the day's RUNNING GDD total."""
    if cumulative_gdd <= anchors[0][0]:
        return anchors[0][1]
    for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
        if cumulative_gdd <= x1:
            span = x1 - x0
            if span <= 0:
                return y1
            share = (cumulative_gdd - x0) / span
            return y0 + share * (y1 - y0)
    return anchors[-1][1]


def _grid_support(rows: Sequence[Mapping]) -> SupportDeclaration:
    from farm_ontology.agronomy.phenology import _require_native_resolution

    resolution = _require_native_resolution(rows)
    return SupportDeclaration(base=f"grid-support (native {resolution:g} km)")


def irrigation_advisory(
    daily_rows: Sequence[Mapping],
    *,
    reading,  # farm_ontology.agronomy.phenology.PhenologyReading
    sensor_rows: Iterable[Observation | Mapping] = (),
    parcel: str | None = None,
    at: datetime,
    cfg: IrrigationCfg = DEFAULT_IRRIGATION_CONFIG,
    soil: SoilProfile = SoilProfile(),
) -> "IrrigationAdvice":
    """Run the dual-Kc balance and answer with mm + stamped claims.

    Requires a phenology reading (the Kcb curve is stage-driven). Missing
    row fields, mixed grid resolutions, naive ``at``, or a stale/uncertified
    PARCEL-BEHAVING sensor story all surface as named gaps or published
    exclusions — never as silent fallbacks.
    """
    moment = ensure_utc(at, "at")
    if reading is None:
        raise AgronomyGap(
            "missing-stage",
            "irrigation needs a phenology reading to drive the basal Kcb",
            missing=("reading",),
            remediation="produce one with "
            "farm_ontology.agronomy.phenology.phenology_reading",
        )
    if not daily_rows:
        raise AgronomyGap(
            "no-usable-rows", "no daily ET0/rainfall rows were supplied",
            missing=("rows",),
        )
    support = _grid_support(daily_rows)

    # The basal curve walks the DAY's running cumulative GDD (D-ENGINE-2):
    # the reading supplies the cultivar profile that selects the anchor
    # table, not a single season-frozen coefficient.
    profile_id = getattr(reading, "cultivar_profile", None)
    anchors = kcb_anchors_for(profile_id if profile_id else None)

    initial_root = (
        cfg.initial_root_depletion_mm
        if cfg.initial_root_depletion_mm is not None
        else soil.raw_mm
    )
    surface = (
        cfg.initial_surface_depletion_mm
        if cfg.initial_surface_depletion_mm is not None
        else cfg.tew_mm
    )
    root = float(initial_root)
    cumulative = 0.0  # running GDD through THIS trace only

    trace: list[dict] = []
    for index, row in enumerate(daily_rows):
        day = row.get("date")
        eto = _number(row.get("eto_mm"))
        rain = _number(row.get("rain_mm"))
        # Daily-mean temperature: taken from t_mean_c when the row carries
        # it; else derived as (t_max_c + t_min_c)/2 — the textbook daily
        # mean, computed from the SAME row's publisher values, never from
        # neighbouring rows or a climatology. The basis used is DECLARED
        # on every trace row; absent both, the day contributes zero GDD
        # (published in the trace, never interpolated).
        t_mean = _number(row.get("t_mean_c"))
        t_mean_basis = "given" if t_mean is not None else None
        if t_mean is None:
            t_max = _number(row.get("t_max_c"))
            t_min = _number(row.get("t_min_c"))
            if t_max is not None and t_min is not None:
                t_mean = (t_max + t_min) / 2.0
                t_mean_basis = "max-min-average"
        t_contrib = (
            daily_gdd_contribution(t_mean) if t_mean is not None else None
        )
        missing = [
            name
            for name, value in (
                (f"row[{index}].date", day if isinstance(day, str) else None),
                (f"row[{index}].eto_mm", eto),
                (f"row[{index}].rain_mm", rain),
            )
            if value is None
        ]
        if missing:
            raise AgronomyGap(
                "malformed-row",
                f"daily row {index} is missing numeric fields",
                missing=tuple(missing),
            )
        assert day is not None and eto is not None and rain is not None
        effective_rain = max(0.0, rain * (1.0 - cfg.runoff_loss_fraction))
        # Surface layer: wet first, then evaporate.
        surface_after_wetting = max(0.0, surface - effective_rain)
        kr = 1.0
        denominator = cfg.tew_mm - cfg.rew_mm
        if denominator > 0:
            kr = min(1.0, max(0.0, (cfg.tew_mm - surface_after_wetting) / denominator))
        # RUNNING cumulative GDD drives today's basal coefficient (the
        # stage reading remains the announcement authority; this running
        # walk is the WATER-BOOK's development clock).
        kcb = _kcb_for_running(cumulative, anchors)
        ke = min(kr * max(0.0, cfg.kc_max - kcb), cfg.kc_max)
        ke = max(0.0, ke)
        etc_adj = (kcb + ke) * eto
        surface = surface_after_wetting + ke * eto
        root = max(0.0, root - effective_rain + etc_adj)
        if t_contrib is not None:
            cumulative += t_contrib
        trace.append(
            {
                "date": day,
                "eto_mm": eto,
                "rain_mm": rain,
                "t_mean_c": (round(t_mean, 2) if t_mean is not None else None),
                "t_mean_basis": t_mean_basis,
                "gdd_contribution": (
                    round(t_contrib, 2) if t_contrib is not None else None
                ),
                "running_gdd": round(cumulative, 1),
                "effective_rain_mm": round(effective_rain, 2),
                "kcb": round(kcb, 4),
                "ke": round(ke, 4),
                "kc": round(kcb + ke, 4),
                "etc_adj_mm": round(etc_adj, 3),
                "root_depletion_end_mm": round(root, 2),
            }
        )

    deficit = max(0.0, root - soil.raw_mm)
    recommend = deficit > 0.0

    # The sensor story. Without a parcel, only exclusions can be produced
    # honestly (there is nothing for a probe to be linked to).
    coverage: CoverageEligibility
    if parcel is not None:
        coverage = has_calibrated_coverage(sensor_rows, parcel, moment)
    else:
        coverage = has_calibrated_coverage((), "", moment)

    extras: list[str] = []
    notes: list[str] = []
    sensor_payload: dict = {"coverage": coverage.to_payload()}
    if coverage.level != CoverageLevel.NONE:
        extras.extend(coverage.footprint_texts)
    for item in coverage.excluded:
        notes.append(f"sensor-excluded ({item['sensor_iri']}: {item['reason']})")

    probe_note: dict | None = None
    if coverage.level in (CoverageLevel.PROBE_FOOTPRINT, CoverageLevel.PARCEL_REPORTED):
        measured = [
            row
            for row in sensor_rows
            if isinstance(row, Mapping)
            and _number(row.get("value")) is not None
            and row.get("parcel_iri") == parcel
        ]
        if measured and coverage.supporting_sensor_iris:
            probe_row = measured[0]
            vwc_percent = _number(probe_row.get("value")) or 0.0
            implied = soil.taw_mm * (1.0 - min(1.0, max(0.0, vwc_percent / 100.0)))
            probe_note = {
                "kind": "grid-vs-probe-divergence",
                "sensor_iri": coverage.supporting_sensor_iris[0],
                "grid_model_depletion_mm": round(root, 2),
                "probe_implied_depletion_mm": round(implied, 2),
                "assumption": (
                    "single-depth point reading assumed representative of the "
                    "root zone; footprint is the probe, not the parcel"
                ),
            }
            notes.append(
                f"grid model depletion {root:.1f} mm vs probe-implied "
                f"{implied:.1f} mm — reconciled by the human signatory"
            )
            # v0 keeps the grid number; the divergence is evidence only.

    final_support = SupportDeclaration(
        base=support.base,
        extras=tuple(extras),
        notes=tuple(notes) + (IRRIGATION_CONFIG_SOURCE_NOTE,),
    )
    why = (
        f"root depletion {root:.1f} mm {'at or beyond' if recommend else 'below'} "
        f"RAW {soil.raw_mm:.1f} mm at the horizon end"
    )
    return IrrigationAdvice(
        net_irrigation_requirement_mm=round(deficit, 1),
        recommend=recommend,
        why=why,
        root_depletion_mm=round(root, 2),
        raw_mm=soil.raw_mm,
        taw_mm=soil.taw_mm,
        stage=reading.stage,
        daily_trace=tuple(trace),
        support=final_support,
        coverage=coverage,
        probe_divergence=probe_note,
        soil_profile=soil,
        config_version=CONFIG_VERSION,
        source_note=IRRIGATION_CONFIG_SOURCE_NOTE,
        use_class=USE_CLASS_FIELD_OPS,
    )


@dataclass(frozen=True)
class IrrigationAdvice:
    """The adviser's answer: mm, trigger, and the full stamped evidence."""

    net_irrigation_requirement_mm: float
    recommend: bool
    why: str
    root_depletion_mm: float
    raw_mm: float
    taw_mm: float
    stage: str
    daily_trace: tuple[dict, ...]
    support: SupportDeclaration
    coverage: CoverageEligibility
    probe_divergence: dict | None
    soil_profile: SoilProfile
    config_version: str
    source_note: str
    use_class: str

    def to_payload(self) -> dict:
        return {
            "kind": "irrigation-advice",
            "net_irrigation_requirement_mm": self.net_irrigation_requirement_mm,
            "recommend": self.recommend,
            "why": self.why,
            "root_depletion_mm": self.root_depletion_mm,
            "raw_mm": self.raw_mm,
            "taw_mm": self.taw_mm,
            "stage": self.stage,
            "daily_trace": [dict(row) for row in self.daily_trace],
            "support": self.support.to_payload(),
            "coverage": self.coverage.to_payload(),
            "probe_divergence": self.probe_divergence,
            "config_version": self.config_version,
            "use_class": self.use_class,
            "source_note": self.source_note,
        }


__all__ = [
    "DEFAULT_IRRIGATION_CONFIG",
    "IRRIGATION_CONFIG_SOURCE_NOTE",
    "KCB_ANCHOR_PROFILES",
    "KCB_ANCHORS_SOURCE_NOTE",
    "kcb_anchors_for",
    "SENSOR_FRESHNESS",
    "DEFAULT_PROBE_DEPTH_CM",
    "CoverageLevel",
    "CoverageEligibility",
    "SoilProfile",
    "IrrigationAdvice",
    "IrrigationCfg",
    "has_calibrated_coverage",
    "irrigation_advisory",
]
