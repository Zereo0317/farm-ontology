"""Synthetic identity. Unknown tenure stays unknown. No real person is loaded."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

from farm_ontology.build import mint
from farm_ontology.model import (
    BoundaryVersion,
    Cropping,
    Holding,
    Interval,
    Party,
    Season,
)
from farm_ontology.store import Store

AT = datetime(2026, 11, 16, tzinfo=timezone.utc)
SEASON_START = datetime(2024, 5, 1, tzinfo=timezone.utc)
SEASON_END = datetime(2024, 10, 31, tzinfo=timezone.utc)
BOUNDARY_DAY = datetime(2024, 4, 1, tzinfo=timezone.utc)


@dataclass(frozen=True)
class Pilot:
    holding: str
    operator: str
    right_holder: str
    season: str
    parcel: str
    phone: str
    surveyed: str
    split_parent: str
    split_a: str
    split_b: str
    merge_a: str
    merge_b: str
    merged: str
    overlap_a: str
    overlap_b: str
    unknown_tenure: str
    customary: str
    operator_only: str
    mixed: str
    overlap: str


def equirectangular_overlap_ha(
    box_a: tuple[float, float, float, float],
    box_b: tuple[float, float, float, float],
    lat_deg: float,
) -> float:
    """Axis-aligned overlap in hectares. The method name is stored with the area.

    This is an equirectangular approximation for synthetic boxes, not a
    geodesic survey.
    """
    min_lon = max(box_a[0], box_b[0])
    min_lat = max(box_a[1], box_b[1])
    max_lon = min(box_a[2], box_b[2])
    max_lat = min(box_a[3], box_b[3])
    if max_lon <= min_lon or max_lat <= min_lat:
        return 0.0
    lat_m = 111_132.0
    lon_m = 111_320.0 * math.cos(math.radians(lat_deg))
    width_m = (max_lon - min_lon) * lon_m
    height_m = (max_lat - min_lat) * lat_m
    return (width_m * height_m) / 10_000.0


def _boundary(
    local: str,
    *,
    wkt: str,
    tenure: str,
    accuracy_m: float | None,
    accuracy_unknown: bool,
    area_ha: float,
    digitising_method: str,
    tenure_source: str | None = None,
    predecessors: tuple[str, ...] = (),
    accuracy_note: str = "",
    decimals: int = 6,
) -> BoundaryVersion:
    return BoundaryVersion(
        iri=mint("boundary", local),
        geometry_iri=mint("geometry", local),
        wkt=wkt,
        crs="EPSG:4326",
        digitising_method=digitising_method,
        boundary_date=BOUNDARY_DAY,
        accuracy_unknown=accuracy_unknown,
        area_method="stated-by-fixture",
        surveyor=mint("agent", "synthetic-digitiser"),
        tenure=tenure,
        personal_data=False,
        coordinate_decimals=decimals,
        accuracy_m=accuracy_m,
        area_ha=area_ha,
        tenure_source=tenure_source,
        predecessors=predecessors,
        eudr_syntactic_claim=False,
        accuracy_note=accuracy_note,
    )


def _box(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> str:
    return (
        f"POLYGON (({min_lon:.6f} {min_lat:.6f}, {max_lon:.6f} {min_lat:.6f}, "
        f"{max_lon:.6f} {max_lat:.6f}, {min_lon:.6f} {max_lat:.6f}, "
        f"{min_lon:.6f} {min_lat:.6f}))"
    )


def load_synthetic_pilot(store: Store) -> Pilot:
    """Load the synthetic pilot, including the bad records the gate must refuse."""
    season_iri = mint("season", "synthetic-monsoon-2024")
    store.add_season(
        Season(
            iri=season_iri,
            start=SEASON_START,
            end=SEASON_END,
            calendar_name="synthetic-monsoon",
            calendar_source=mint("calendar", "synthetic-monsoon"),
        ),
        at=AT,
    )
    store.add_season(
        Season(
            iri=mint("season", "calendar-year-2024"),
            start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end=datetime(2025, 1, 1, tzinfo=timezone.utc),
            calendar_name="calendar-year",
            calendar_source=mint("calendar", "gregorian"),
        ),
        at=AT,
    )

    operator = mint("party", "synthetic-operator-1")
    right_holder = mint("party", "synthetic-right-holder-1")
    store.add_party(
        Party(operator, "operator", "synthetic-operator-1", False), at=AT
    )
    store.add_party(
        Party(right_holder, "right-holder", "synthetic-right-holder-1", False),
        at=AT,
    )
    store.copy_operator_to_right_holder(operator, at=AT)

    parcel = _boundary(
        "parcel-0-4ha",
        wkt=_box(120.10, 23.10, 120.1006, 23.1006),
        tenure="unknown",
        accuracy_m=None,
        accuracy_unknown=True,
        area_ha=0.4,
        digitising_method="synthetic-polygon",
    )
    phone = _boundary(
        "phone-point",
        wkt="POINT (120.123456 23.654321)",
        tenure="unknown",
        accuracy_m=None,
        accuracy_unknown=True,
        area_ha=0.3,
        digitising_method="phone-point",
    )
    surveyed = _boundary(
        "surveyed-polygon",
        wkt=_box(120.20, 23.20, 120.21, 23.21),
        tenure="unknown",
        accuracy_m=5.0,
        accuracy_unknown=False,
        area_ha=5.2,
        digitising_method="stated-metre-fixture",
    )
    parent = _boundary(
        "split-parent",
        wkt=_box(120.30, 23.30, 120.32, 23.32),
        tenure="unknown",
        accuracy_m=None,
        accuracy_unknown=True,
        area_ha=2.0,
        digitising_method="synthetic-polygon",
    )
    split_a = _boundary(
        "split-a",
        wkt=_box(120.30, 23.30, 120.31, 23.32),
        tenure="unknown",
        accuracy_m=None,
        accuracy_unknown=True,
        area_ha=1.0,
        digitising_method="split",
        predecessors=(parent.iri,),
    )
    split_b = _boundary(
        "split-b",
        wkt=_box(120.31, 23.30, 120.32, 23.32),
        tenure="unknown",
        accuracy_m=None,
        accuracy_unknown=True,
        area_ha=1.0,
        digitising_method="split",
        predecessors=(parent.iri,),
    )
    merge_a = _boundary(
        "merge-a",
        wkt=_box(120.40, 23.40, 120.41, 23.41),
        tenure="unknown",
        accuracy_m=None,
        accuracy_unknown=True,
        area_ha=1.0,
        digitising_method="synthetic-polygon",
    )
    merge_b = _boundary(
        "merge-b",
        wkt=_box(120.41, 23.40, 120.42, 23.41),
        tenure="unknown",
        accuracy_m=None,
        accuracy_unknown=True,
        area_ha=1.0,
        digitising_method="synthetic-polygon",
    )
    merged = _boundary(
        "merged",
        wkt=_box(120.40, 23.40, 120.42, 23.41),
        tenure="unknown",
        accuracy_m=None,
        accuracy_unknown=True,
        area_ha=2.0,
        digitising_method="merge",
        predecessors=(merge_a.iri, merge_b.iri),
    )
    box_a = (120.50, 23.50, 120.52, 23.52)
    box_b = (120.51, 23.51, 120.53, 23.53)
    overlap_a = _boundary(
        "overlap-a",
        wkt=_box(*box_a),
        tenure="unknown",
        accuracy_m=None,
        accuracy_unknown=True,
        area_ha=4.0,
        digitising_method="synthetic-polygon",
    )
    overlap_b = _boundary(
        "overlap-b",
        wkt=_box(*box_b),
        tenure="unknown",
        accuracy_m=None,
        accuracy_unknown=True,
        area_ha=4.0,
        digitising_method="synthetic-polygon",
    )
    unknown = _boundary(
        "tenure-unknown",
        wkt=_box(120.60, 23.60, 120.61, 23.61),
        tenure="unknown",
        accuracy_m=None,
        accuracy_unknown=True,
        area_ha=1.0,
        digitising_method="synthetic-polygon",
    )
    customary = _boundary(
        "tenure-customary",
        wkt=_box(120.70, 23.70, 120.71, 23.71),
        tenure="customary",
        accuracy_m=None,
        accuracy_unknown=True,
        area_ha=1.0,
        digitising_method="synthetic-polygon",
        tenure_source="synthetic-customary-statement",
    )
    operator_only = _boundary(
        "tenure-operator-only",
        wkt=_box(120.80, 23.80, 120.81, 23.81),
        tenure="operator-only",
        accuracy_m=None,
        accuracy_unknown=True,
        area_ha=1.0,
        digitising_method="synthetic-polygon",
    )
    titled = _boundary(
        "tenure-titled-no-source",
        wkt=_box(120.90, 23.90, 120.91, 23.91),
        tenure="titled",
        accuracy_m=None,
        accuracy_unknown=True,
        area_ha=1.0,
        digitising_method="synthetic-polygon",
        tenure_source=None,
    )
    survey = _boundary(
        "household-survey-point",
        wkt="POINT (121.000000 24.000000)",
        tenure="unknown",
        accuracy_m=None,
        accuracy_unknown=True,
        area_ha=1.0,
        digitising_method="household-survey",
        accuracy_note="0-5 km, privacy displacement",
    )

    kept = []
    for item in (
        parcel,
        phone,
        surveyed,
        parent,
        split_a,
        split_b,
        merge_a,
        merge_b,
        merged,
        overlap_a,
        overlap_b,
        unknown,
        customary,
        operator_only,
    ):
        result = store.add_boundary(item, at=AT)
        if not result.ok:
            raise RuntimeError(result.refusal.attempted_change if result.refusal else item.iri)
        kept.append(item.iri)
    store.add_boundary(titled, at=AT)
    store.add_boundary(survey, at=AT)
    store.add_jittered_survey_point("0-5 km, privacy displacement", at=AT)

    interval = Interval(SEASON_START, SEASON_END)
    holding = mint("holding", "synthetic-holding-1")
    store.add_holding(
        Holding(
            iri=holding,
            label="synthetic-holding-1",
            links=tuple((iri, interval) for iri in kept),
        ),
        at=AT,
    )

    area = equirectangular_overlap_ha(box_a, box_b, 23.51)
    overlap = store.add_overlap(
        boundary_a=overlap_a.iri,
        boundary_b=overlap_b.iri,
        season=season_iri,
        area_ha=area,
        method="equirectangular-box-overlap",
        disposition=None,
        at=AT,
    )

    rice = mint("crop", "rice")
    maize = mint("crop", "maize")
    mixed = mint("cropping", "mixed-rice-maize")
    store.add_cropping(
        Cropping(mixed, parcel.iri, season_iri, (rice, maize), "mixed"),
        at=AT,
    )
    store.add_cropping(
        Cropping(
            mint("cropping", "mono-two-crops"),
            parcel.iri,
            season_iri,
            (rice, maize),
            "mono",
        ),
        at=AT,
    )
    return Pilot(
        holding=holding,
        operator=operator,
        right_holder=right_holder,
        season=season_iri,
        parcel=parcel.iri,
        phone=phone.iri,
        surveyed=surveyed.iri,
        split_parent=parent.iri,
        split_a=split_a.iri,
        split_b=split_b.iri,
        merge_a=merge_a.iri,
        merge_b=merge_b.iri,
        merged=merged.iri,
        overlap_a=overlap_a.iri,
        overlap_b=overlap_b.iri,
        unknown_tenure=unknown.iri,
        customary=customary.iri,
        operator_only=operator_only.iri,
        mixed=mixed,
        overlap=overlap.iri or "",
    )
