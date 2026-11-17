"""Fertility planner SKELETON (WS3.4) — refuses without soil chemistry.

This is deliberately a skeleton with house humility: it does not compute
fertiliser doses. It reads soil-chemistry rows (pH, EC, available N-P-K,
organic matter), refuses with a named ``needs-soil-chemistry`` gap that
ENUMERATES the missing analytes when any are absent, and when the data is
complete produces a REVIEW-REQUIRED note set — interpretations an
agronomist signs, never doses.

REFERENCE BANDS (VERIFY-tagged, coarse)
---------------------------------------
* Soybean pH comfort band ≈ 6.0–7.0; below 6.0 liming is a discussion an
  agronomist has with the lab numbers in hand. Hokkaido Andosols commonly
  sit acidic; the engine observes, it does not prescribe lime tonnage.
* EC above ~2 dS/m asks for a salinity look. (Coarse screening level.)
* Available N-P-K and OM are echoed with their sampling depth and lab
  method for the human interpretation; the engine adds NO thresholds that
  pretend to be local (Hokkaido prefecture fertiliser standards govern
  locally, and this repo has not ingested them).

Stale chemistry (older than STALE_AFTER) is a gap too — old soil truth is
not truth. Every output carries use_class and the input rows' support. No
network, no clock reads, deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Mapping, Sequence

from farm_ontology.agronomy.common import (
    CONFIG_VERSION,
    USE_CLASS_FIELD_OPS,
    AgronomyGap,
    SupportDeclaration,
)
from farm_ontology.timeutil import ensure_utc

#: Analytes the planner REQUIRES before it says anything at all.
REQUIRED_SOIL_ANALYTES: tuple[str, ...] = (
    "ph",
    "ec",
    "n_available",
    "p_available",
    "k_available",
    "om_percent",
)

#: Analyte → human label for the enumeration in gaps and notes.
ANALYTE_LABELS: dict[str, str] = {
    "ph": "soil pH",
    "ec": "electrical conductivity",
    "n_available": "available nitrogen",
    "p_available": "available phosphorus",
    "k_available": "available potassium",
    "om_percent": "organic matter",
}

#: Soil chemistry older than this is refused (soils drift; liming shifts pH).
STALE_AFTER = timedelta(days=3 * 365)

PH_FERTILITY_COMFORT_LOW = 6.0
PH_FERTILITY_COMFORT_HIGH = 7.0
EC_SALINITY_WATCH_DS_M = 2.0

SOURCE_NOTE = (
    "VERIFY [SOIL-CHEM]: pH comfort band 6.0-7.0 for soybean; EC watch level "
    "2 dS/m is a coarse screening bound; N-P-K/OM have NO engine thresholds "
    "on purpose — Hokkaido prefecture fertiliser standards govern locally and "
    "are not yet ingested. An agronomist signs every dose; this engine "
    "produces none (v0)."
)


@dataclass(frozen=True)
class SoilReading:
    """The REVIEW-REQUIRED interpretation set. No doses exist in it."""

    analytes: tuple[str, ...]
    values: tuple[dict, ...]          # echo of each accepted row (trimmed)
    missing: tuple[str, ...]          # empty only when complete
    review_required: bool
    notes: tuple[str, ...]
    support: SupportDeclaration
    config_version: str = CONFIG_VERSION
    source_note: str = SOURCE_NOTE
    use_class: str = USE_CLASS_FIELD_OPS

    def to_payload(self) -> dict:
        return {
            "analytes": list(self.analytes),
            "values": [dict(item) for item in self.values],
            "missing": list(self.missing),
            "review_required": self.review_required,
            "notes": list(self.notes),
            "support": self.support.to_payload(),
            "config_version": self.config_version,
            "source_note": self.source_note,
            "use_class": self.use_class,
        }


def _sampled_at(value: object, index: int) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise AgronomyGap(
            "malformed-row",
            f"soil row {index}: 'sampled_at' must be an ISO-8601 string",
            missing=(f"soil[{index}].sampled_at",),
        )
    try:
        return ensure_utc(
            datetime.fromisoformat(value.replace("Z", "+00:00")),
            f"soil[{index}].sampled_at",
        )
    except ValueError as error:
        raise AgronomyGap(
            "malformed-row",
            f"soil row {index}: unparseable sampled_at {value!r}: {error}",
        ) from error


def _require_support(rows: Sequence[Mapping]) -> str:
    """Every soil row must declare its support; homogeneous only."""
    supports: set[str] = set()
    for index, row in enumerate(rows):
        value = row.get("native_support")
        if not isinstance(value, str) or not value.strip():
            raise AgronomyGap(
                "missing-native-support",
                f"soil row {index} lacks 'native_support'",
                missing=(f"soil[{index}].native_support",),
            )
        supports.add(value)
    if len(supports) > 1:
        raise AgronomyGap(
            "support-mixed",
            f"soil rows mix native supports {sorted(supports)}; a note never "
            "blends supports",
        )
    return supports.pop()


def soil_fertility_note(
    rows: Sequence[Mapping],
    *,
    at: datetime,
) -> SoilReading:
    """Interpret soil chemistry or refuse with an enumerated gap.

    Rows: ``{analyte, value, unit, sampled_at, native_support, depth_cm?,
    lab?, method?}``. The ``analyte`` must be one of
    :data:`REQUIRED_SOIL_ANALYTES`; anything else is refused as unknown —
    guessing is banned in both directions.
    """
    moment = ensure_utc(at, "at")
    if not rows:
        raise AgronomyGap(
            "needs-soil-chemistry",
            "no soil-chemistry rows supplied; the fertility planner refuses "
            "to speak without them",
            missing=REQUIRED_SOIL_ANALYTES,
            remediation="supply lab rows for " + ", ".join(REQUIRED_SOIL_ANALYTES),
        )
    support_text = _require_support(rows)

    seen: dict[str, dict] = {}
    unknown: list[str] = []
    for index, row in enumerate(rows):
        analyte = row.get("analyte")
        if not isinstance(analyte, str) or analyte not in REQUIRED_SOIL_ANALYTES:
            unknown.append(str(analyte))
            continue
        if analyte in seen:
            raise AgronomyGap(
                "duplicate-analyte",
                f"soil row {index}: analyte {analyte!r} appears twice",
            )
        value = row.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise AgronomyGap(
                "malformed-row",
                f"soil row {index}: analyte {analyte!r} needs a numeric value",
                missing=(f"soil[{index}].value",),
            )
        sampled = _sampled_at(row.get("sampled_at"), index)
        if sampled <= moment - STALE_AFTER:
            raise AgronomyGap(
                "soil-chemistry-stale",
                f"soil row {index} ({analyte}) was sampled "
                f"{sampled.date().isoformat()}, beyond the "
                f"{STALE_AFTER.days // 365}-year staleness window",
            )
        seen[analyte] = {
            "analyte": analyte,
            "value": float(value),
            "unit": str(row.get("unit") or ""),
            "sampled_at": sampled.isoformat(),
            "depth_cm": row.get("depth_cm"),
            "lab": row.get("lab"),
            "method": row.get("method"),
            "native_support": support_text,
        }

    if unknown:
        raise AgronomyGap(
            "unknown-analyte",
            f"soil rows carry analytes this skeleton does not know: "
            f"{sorted(set(unknown))}; refusing rather than ignoring",
            missing=tuple(),  # enumerated separately below
        )

    missing = tuple(a for a in REQUIRED_SOIL_ANALYTES if a not in seen)
    if missing:
        raise AgronomyGap(
            "needs-soil-chemistry",
            "the fertility planner requires the full chemistry set before it "
            "interprets anything; a partial set invites half-truths",
            missing=missing,
            remediation="supply lab rows for " + ", ".join(missing),
        )

    notes: list[str] = []
    ph = seen["ph"]["value"]
    if ph < PH_FERTILITY_COMFORT_LOW:
        notes.append(
            f"pH {ph:g} below the soybean comfort band "
            f"[{PH_FERTILITY_COMFORT_LOW:g}, {PH_FERTILITY_COMFORT_HIGH:g}] — "
            "liming is a discussion for the agronomist with the lab sheet; "
            "this engine computes no lime dose"
        )
    elif ph > PH_FERTILITY_COMFORT_HIGH:
        notes.append(
            f"pH {ph:g} above the soybean comfort band "
            f"[{PH_FERTILITY_COMFORT_LOW:g}, {PH_FERTILITY_COMFORT_HIGH:g}] — "
            "REVIEW REQUIRED by the agronomist"
        )
    ec = seen["ec"]["value"]
    if ec > EC_SALINITY_WATCH_DS_M:
        notes.append(
            f"EC {ec:g} dS/m above the {EC_SALINITY_WATCH_DS_M:g} dS/m watch "
            "level — salinity look, REVIEW REQUIRED"
        )
    for analyte in ("n_available", "p_available", "k_available", "om_percent"):
        row = seen[analyte]
        notes.append(
            f"{ANALYTE_LABELS[analyte]} {row['value']:g} {row['unit']} — echo "
            "for human interpretation; Hokkaido prefecture standards govern "
            "locally and are not ingested; agronomist signs any dose"
        )

    notes.append("REVIEW REQUIRED: an agronomist signs every dose (v0)")

    return SoilReading(
        analytes=tuple(seen.keys()),
        values=tuple(seen[a] for a in REQUIRED_SOIL_ANALYTES),
        missing=(),
        review_required=True,
        notes=tuple(notes),
        support=SupportDeclaration(base=support_text, notes=(SOURCE_NOTE,)),
    )


__all__ = [
    "REQUIRED_SOIL_ANALYTES",
    "ANALYTE_LABELS",
    "STALE_AFTER",
    "SoilReading",
    "soil_fertility_note",
]
