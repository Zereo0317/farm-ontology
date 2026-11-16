"""Open-Meteo forecast adapter.

The free tier is non-commercial (Q9 unanswered). These records are not the
legal meteorological authority. A missing issue time or a grid finer than
the model's native support fails closed. This module does not call the API.
"""

from __future__ import annotations

from datetime import datetime

from farm_ontology.build import degrees, kilometres, millimetres, mint, screening_licence, screening_method
from farm_ontology.model import CommitResult, Interval, Observation
from farm_ontology.store import Store
from farm_ontology.timeutil import parse_time

# Minimum native support stated in the 2026-11-16 forecast note.
# A coarser grid named by a payload is kept. A finer grid is refused.
NATIVE_MIN_KM = {"jma_msm": 5.0, "ecmwf_ifs": 9.0, "icon": 11.0}
NATIVE_DEG = {"jma_msm": 0.05}
ABSENT = frozenset({"windy-point", "predictwind", "windy", "predictwind-point"})


def parse_forecast(store: Store, doc: dict, *, at: datetime) -> CommitResult:
    model = str(doc.get("model") or "")
    if model in ABSENT:
        return store._refuse(
            "R-national",
            model,
            "Windy Point and PredictWind are not on the Taiwan primary manifest",
            at,
        )
    if doc.get("legal_meteorological_authority"):
        return store._refuse(
            "R-property",
            model or "open-meteo",
            "Open-Meteo is not the legal meteorological authority",
            at,
        )
    if doc.get("permits_financial_use"):
        return store._refuse(
            "R-licence",
            model or "open-meteo",
            "Open-Meteo financial use stays false until Q9 attaches a grant",
            at,
        )
    if doc.get("consensus") or doc.get("mean_of_models"):
        return store._refuse(
            "R-foi",
            model or "open-meteo",
            "disagreement is stored as separate results; no consensus hectare value is written",
            at,
        )
    if model == "best_match" and not doc.get("resolved_model_id"):
        return store._refuse(
            "R-property",
            "best_match",
            "best_match alone is not a reproducible pin",
            at,
        )
    resolved = str(doc.get("resolved_model_id") or model)
    if resolved not in NATIVE_MIN_KM:
        return store._refuse(
            "R-support",
            resolved or "open-meteo",
            "unknown model and no native grid; failing closed",
            at,
        )
    native_km = NATIVE_MIN_KM[resolved]
    requested_m = doc.get("requested_resolution_m")
    if requested_m is not None and float(requested_m) < native_km * 1000.0:
        return store._refuse(
            "R-support",
            resolved,
            "a request finer than the native grid is not a finer observation",
            at,
        )
    grid_km = doc.get("grid_km")
    if grid_km is not None and float(grid_km) + 1e-9 < native_km:
        return store._refuse(
            "R-support",
            resolved,
            "the payload grid is finer than the model's native support",
            at,
        )
    grid_deg = doc.get("grid_deg")
    if (
        resolved in NATIVE_DEG
        and grid_deg is not None
        and float(grid_deg) + 1e-9 < NATIVE_DEG[resolved]
    ):
        return store._refuse(
            "R-support",
            resolved,
            "the payload degree grid is finer than the native degree grid",
            at,
        )
    if not doc.get("issue_time"):
        return store._refuse(
            "R-issue",
            resolved,
            "a forecast without an issue time does not load as a backtest input",
            at,
        )
    if doc.get("value_mm") is None:
        return store._refuse("R-property", resolved, "missing result", at)
    issue = parse_time(doc["issue_time"])
    start = parse_time(doc["valid_time"])
    end = parse_time(doc["valid_end"])
    if resolved in NATIVE_DEG and grid_km is None:
        resolution = degrees(float(grid_deg) if grid_deg is not None else NATIVE_DEG[resolved])
    elif grid_km is not None:
        resolution = kilometres(float(grid_km))
    else:
        resolution = kilometres(native_km)
    local = str(doc.get("local") or resolved)
    obs = Observation(
        iri=mint("observation", local),
        phenomenon=Interval(start, end),
        generated_at=issue,
        observed_property=mint(
            "observedProperty", "cf-p07-v95-precipitation-amount-unresolved"
        ),
        feature_of_interest=mint("cell", str(doc.get("feature_local") or local)),
        feature_kind="grid-cell",
        spatial_support="grid-cell",
        procedure=mint("procedure", "forecast"),
        use_class="Screening",
        licence=screening_licence(),
        method=screening_method(
            product_version=f"open-meteo-{resolved}-not-legal-authority"
        ),
        personal_data=False,
        availability_time=issue,
        native_resolution=resolution,
        result=millimetres(float(doc["value_mm"])),
        is_forecast=True,
        issue_time=issue,
        lead_seconds=int((start - issue).total_seconds()),
        product_kind="forecast",
        dry_run=not bool(doc.get("captured_live", False)),
    )
    return store.add_observation(obs, at=at)


def store_series(store: Store, docs: list[dict], *, at: datetime) -> list[CommitResult]:
    if any(doc.get("consensus") or doc.get("mean_of_models") for doc in docs):
        return [
            store._refuse(
                "R-foi",
                "series",
                "disagreement is stored as separate results; no consensus hectare value is written",
                at,
            )
        ]
    return [parse_forecast(store, doc, at=at) for doc in docs]
