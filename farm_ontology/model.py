"""Record types. A spatial join is not an observation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Quantity:
    value: float
    unit_iri: str
    quantity_kind_iri: str
    per_unit_iri: str | None = None


@dataclass(frozen=True)
class Interval:
    start: datetime
    end: datetime


@dataclass(frozen=True)
class LicenceGrant:
    instrument: str
    permits_financial_use: bool
    permits_redistribution: bool
    attribution: str
    purpose: str
    territory: str
    expiry: str
    lawful_basis: str | None = None
    rerun_if_vendor_stops: str | None = None


@dataclass(frozen=True)
class MethodVersion:
    software_commit: str
    ontology_releases: tuple[str, ...]
    product_version: str
    ee_task_id: str | None = None
    gcs_uri: str | None = None
    crs: str | None = None
    crs_transform: tuple[float, ...] | None = None
    mask_recipe: str | None = None
    crc32c: str | None = None
    ee_registration: str | None = None


@dataclass(frozen=True)
class ErrorStatement:
    metric: str
    sample_region: str
    sample_crop: str
    sample_season: str
    citation: str
    held_out: bool
    independent_of_product: bool | None
    value: Quantity | None = None
    vendor_confidence: float | None = None


@dataclass(frozen=True)
class Observation:
    iri: str
    phenomenon: Interval
    generated_at: datetime
    observed_property: str
    feature_of_interest: str
    feature_kind: str
    spatial_support: str
    procedure: str
    use_class: str
    licence: LicenceGrant
    method: MethodVersion
    personal_data: bool
    availability_time: datetime | None = None
    availability_known: bool = True
    native_resolution: Quantity | None = None
    result: Quantity | None = None
    is_forecast: bool = False
    issue_time: datetime | None = None
    lead_seconds: int | None = None
    result_time: datetime | None = None
    revision_of: str | None = None
    product_kind: str | None = None
    error: ErrorStatement | None = None
    gap_reason: str | None = None
    unsupported_reason: str | None = None
    hectare_weather_claim: bool = False
    sensor_iri: str | None = None
    calibration_activity: str | None = None
    nodata: bool = False
    operations_observation: bool = False
    stated_as_recall: bool = False
    dry_run: bool = False


@dataclass(frozen=True)
class BoundaryVersion:
    iri: str
    geometry_iri: str
    wkt: str
    crs: str
    digitising_method: str
    boundary_date: datetime
    accuracy_unknown: bool
    area_method: str
    surveyor: str
    tenure: str
    personal_data: bool
    coordinate_decimals: int
    accuracy_m: float | None = None
    area_ha: float | None = None
    tenure_source: str | None = None
    predecessors: tuple[str, ...] = ()
    eudr_syntactic_claim: bool = False
    accuracy_note: str = ""


@dataclass(frozen=True)
class Holding:
    iri: str
    label: str
    links: tuple[tuple[str, Interval], ...]


@dataclass(frozen=True)
class Party:
    iri: str
    role: str
    label: str
    personal_data: bool


@dataclass(frozen=True)
class Season:
    iri: str
    start: datetime
    end: datetime
    calendar_name: str
    calendar_source: str


@dataclass(frozen=True)
class Cropping:
    iri: str
    boundary: str
    season: str
    crops: tuple[str, ...]
    mix: str


@dataclass(frozen=True)
class SpatialJoin:
    iri: str
    observation: str
    boundary: str
    relation: str
    crs: str
    generated_at: datetime
    activity: str


@dataclass(frozen=True)
class Overlap:
    iri: str
    boundary_a: str
    boundary_b: str
    season: str
    area_ha: float
    method: str
    disposition: str | None = None


@dataclass(frozen=True)
class LabelLink:
    iri: str
    local_iri: str
    concept_iri: str
    relation: str
    language: str


@dataclass(frozen=True)
class JitteredSurveyPoint:
    iri: str
    note: str
    personal_data: bool


@dataclass(frozen=True)
class FitActivity:
    iri: str
    used: tuple[str, ...]
    error_cut: str | None


@dataclass(frozen=True)
class Refusal:
    iri: str
    rule_id: str
    time: datetime
    input_entity: str
    attempted_change: str


@dataclass(frozen=True)
class CommitResult:
    ok: bool
    iri: str | None
    refusal: Refusal | None
