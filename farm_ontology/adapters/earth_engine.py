"""Earth Engine history adapter.

Plans name a shared CRS and crsTransform. They do not call Earth Engine.
A sidecar that lacks the export identity does not become an observation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from farm_ontology.build import degrees, grid_observation, kilometres, millimetres, mint, screening_licence, screening_method
from farm_ontology.config import MissingConfig, load_settings
from farm_ontology.model import CommitResult, LicenceGrant, Observation
from farm_ontology.store import Store
from farm_ontology.timeutil import parse_time

SERIES = {
    "ERA5-Land": {
        "asset": "ECMWF/ERA5_LAND/DAILY_AGGR",
        "product_kind": "reanalysis",
        "resolution_deg": 0.1,
        "plane": "H",
    },
    "CHIRPS": {
        "asset": "UCSB-CHG/CHIRPS/DAILY",
        "product_kind": "chirps-final",
        "resolution_deg": 0.05,
        "plane": "H",
    },
    "TerraClimate": {
        "asset": "IDAHO_EPSCOR/TERRACLIMATE",
        "product_kind": "climatology",
        "resolution_km": 4.6,
        "plane": "H",
    },
    "WorldClim-BIO": {
        "asset": "WORLDCLIM/V1/BIO",
        "product_kind": "normal",
        "resolution_km": 1.0,
        "plane": "H",
    },
    "Sentinel-2": {
        "asset": "COPERNICUS/S2_SR_HARMONIZED",
        "product_kind": "optical",
        "plane": "H",
        "optical": True,
    },
}

TAIWAN_FORBIDDEN = ("GRIDMET", "DAYMET", "HRRR")
TAIWAN_FORBIDDEN_ASSETS = (
    "IDAHO_EPSCOR/GRIDMET",
    "NASA/ORNL/DAYMET_V4",
    "NOAA/HRRR",
)

SIDECAR_REQUIRED = (
    "task_id",
    "crs",
    "crs_transform",
    "mask_recipe",
    "software_commit",
    "crc32c",
    "ee_registration",
    "product_kind",
    "native_resolution",
)


@dataclass(frozen=True)
class PlanResult:
    ok: bool
    executed: bool
    plan: dict | None
    reason: str


def plan_export(
    series: str,
    *,
    crs: str | None = None,
    crs_transform: list[float] | None = None,
    scale: float | None = None,
    best_effort: bool = False,
    mask_recipe: str | None = None,
    registration_type: str = "unknown",
    confirm_live: bool = False,
    aoi_name: str = "synthetic-taiwan-aoi",
) -> PlanResult:
    try:
        settings = load_settings()
    except MissingConfig as exc:
        return PlanResult(False, False, None, str(exc))
    if series in TAIWAN_FORBIDDEN or series in TAIWAN_FORBIDDEN_ASSETS:
        return PlanResult(
            False,
            False,
            None,
            f"{series} is absent from the Taiwan AOI manifest",
        )
    if best_effort:
        return PlanResult(
            False,
            False,
            None,
            "bestEffort is not an export setting",
        )
    if scale is not None and not crs_transform:
        return PlanResult(
            False,
            False,
            None,
            "scale alone is not the stored grid; crs and crsTransform are required",
        )
    if not crs or not crs_transform:
        return PlanResult(
            False,
            False,
            None,
            "crs and crsTransform are required",
        )
    known = SERIES.get(series)
    if known is None:
        return PlanResult(False, False, None, f"unknown history series {series}")
    if known.get("optical") and not mask_recipe:
        return PlanResult(False, False, None, "Sentinel-2 requires a named mask recipe")
    plan = {
        "series": series,
        "asset": known["asset"],
        "plane": "H",
        "destination": "ee.batch.Export.image.toCloudStorage",
        "gcloud_configuration": settings.gcloud_configuration,
        "gcp_project": settings.gcp_project,
        "aoi_name": aoi_name,
        "crs": crs,
        "crs_transform": list(crs_transform),
        "scale": None,
        "best_effort": False,
        "mask_recipe": mask_recipe or "not-optical; native grid unchanged",
        "ee_registration": registration_type,
        "cloud_optimized": True,
        "skip_empty_tiles": True,
        "executed": False,
        "gcs_uri": None,
        "task_id": None,
    }
    if confirm_live:
        return PlanResult(
            False,
            False,
            plan,
            "live export refused: registration type is not a counsel finding, "
            "the Python Earth Engine client is not a dependency, and this build "
            "does not start Export tasks",
        )
    return PlanResult(True, False, plan, "dry-run only; no Export task was started")


def load_sidecar(store: Store, doc: dict, *, at: datetime) -> CommitResult:
    missing = [key for key in SIDECAR_REQUIRED if doc.get(key) in (None, "", [])]
    if missing:
        return store._refuse(
            "R-sidecar",
            str(doc.get("task_id") or "sidecar"),
            "sidecar missing " + ", ".join(missing),
            at,
        )
    if doc.get("state") == "COMPLETED" and doc.get("coverage_checked") is not True:
        return store._refuse(
            "R-sidecar",
            str(doc["task_id"]),
            "COMPLETED without a coverage check is not a pass",
            at,
        )
    if doc.get("copy_result_to_boundary"):
        return store._refuse(
            "R-foi",
            str(doc["task_id"]),
            "a sidecar cannot copy a cell value onto a boundary",
            at,
        )
    registration = str(doc["ee_registration"])
    financial = bool(doc.get("permits_financial_use", False))
    if registration in {"noncommercial", "unknown"} and financial:
        return store._refuse(
            "R-licence",
            str(doc["task_id"]),
            "noncommercial or unknown registration forces financial use false",
            at,
        )
    if doc.get("nodata_as_zero"):
        return store._refuse(
            "R-zero",
            str(doc["task_id"]),
            "nodata is not stored as zero",
            at,
        )
    resolution = doc["native_resolution"]
    if resolution["unit"] == "deg":
        native = degrees(float(resolution["value"]))
    elif resolution["unit"] == "km":
        native = kilometres(float(resolution["value"]))
    else:
        return store._refuse(
            "R-support",
            str(doc["task_id"]),
            "native resolution unit must be deg or km as stated by the source",
            at,
        )
    kind = doc["product_kind"]
    if kind == "gap-fill" and doc.get("procedure") != "gap-fill":
        return store._refuse(
            "R-gapfill",
            str(doc["task_id"]),
            "a gap-filled index must name the fill procedure",
            at,
        )
    procedure = mint("procedure", doc.get("procedure") or (
        "reanalysis" if kind == "reanalysis" else "gridded-product"
    ))
    if kind == "gap-fill":
        procedure = mint("procedure", "gap-fill")
    phenomenon = (parse_time(doc["phenomenon_start"]), parse_time(doc["phenomenon_end"]))
    availability = parse_time(doc["availability_time"])
    if not doc.get("gap_reason") and doc.get("result_mm") is None:
        return store._refuse(
            "R-property",
            str(doc["task_id"]),
            "a result is required unless the sidecar is a gap",
            at,
        )
    value = doc.get("result_mm")
    if doc.get("gap_reason"):
        result_quantity = None
    else:
        result_quantity = millimetres(float(value))
    licence = screening_licence()
    if financial:
        licence = LicenceGrant(
            instrument=str(doc.get("licence_instrument") or ""),
            permits_financial_use=True,
            permits_redistribution=False,
            attribution=str(doc.get("attribution") or "none stated"),
            purpose="screening",
            territory=str(doc.get("territory") or ""),
            expiry="none stated",
        )
    feature_kind = "pixel" if doc.get("feature_kind") == "pixel" else "grid-cell"
    support = feature_kind
    obs = grid_observation(
        local=str(doc.get("local") or f"sidecar-{doc['task_id']}"),
        feature_local=str(doc.get("feature_local") or f"cell-{doc['task_id']}"),
        resolution=native,
        result=result_quantity if result_quantity is not None else millimetres(0.0),
        phenomenon=phenomenon,
        availability=availability,
        product_kind=kind,
        procedure=procedure,
        licence=licence,
        method=screening_method(
            software_commit=str(doc["software_commit"]),
            product_version=str(doc.get("product_version") or "recorded-dry-run"),
            ee_task_id=str(doc["task_id"]),
            gcs_uri=doc.get("gcs_uri"),
            crs=str(doc["crs"]),
            crs_transform=tuple(float(item) for item in doc["crs_transform"]),
            mask_recipe=str(doc["mask_recipe"]),
            crc32c=str(doc["crc32c"]),
            ee_registration=registration,
        ),
        dry_run=bool(doc.get("dry_run", True)),
        gap_reason=doc.get("gap_reason"),
        operations_observation=bool(doc.get("operations_observation", False)),
        generated_at=parse_time(doc.get("generated_at") or doc["availability_time"]),
    )
    if feature_kind == "pixel":
        obs = Observation(
            **{
                **obs.__dict__,
                "feature_kind": "pixel",
                "spatial_support": "pixel",
            }
        )
    if doc.get("gap_reason"):
        obs = Observation(**{**obs.__dict__, "result": None, "gap_reason": doc["gap_reason"]})
    return store.add_observation(obs, at=at)
