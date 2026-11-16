"""Open-Meteo forecast adapter.

The free tier is non-commercial (Q9 unanswered). These records are not the
legal meteorological authority. A missing issue time or a grid finer than
the model's native support fails closed.

The free forecast endpoint does not return a model-run time. A live sample
is taken from the single-runs endpoint only for a run that endpoint accepts.
Tests load the recorded capture and do not call the network. No API key is
sent.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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
    availability = (
        parse_time(doc["availability_time"]) if doc.get("availability_time") else issue
    )
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
        generated_at=availability,
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
        availability_time=availability,
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


# Published sample point from the 2026-11-16 weather note (lat, lon).
SAMPLE_LATITUDE = 23.5
SAMPLE_LONGITUDE = 121.0
SAMPLE_MODEL = "jma_msm"
FORECAST_ENDPOINT = "https://api.open-meteo.com/v1/forecast"
SINGLE_RUN_ENDPOINT = "https://single-runs-api.open-meteo.com/v1/forecast"
_USER_AGENT = "farm-ontology/0.1 (research; non-commercial)"


def build_live_document(capture: dict) -> dict:
    """Turn a recorded single-run response into an adapter document.

    The grid size is the capture's published model grid. The response has
    no grid field, and this function does not invent a finer one.
    """
    body = capture["response"]
    if body.get("utc_offset_seconds") != 0 or body.get("timezone") != "GMT":
        raise ValueError("Open-Meteo clock is not UTC; failing closed")
    units = body.get("hourly_units") or {}
    if units.get("precipitation") != "mm":
        raise ValueError("precipitation unit is not mm; failing closed")
    if "grid_deg" not in capture:
        raise ValueError("the published model grid is missing; failing closed")
    issue = parse_time(capture["issue_time"])
    availability = parse_time(capture["availability_time"])
    times = body["hourly"]["time"]
    values = body["hourly"]["precipitation"]
    chosen_start = None
    chosen_value = None
    for stamp, value in zip(times, values):
        start = parse_time(f"{stamp}+00:00")
        if start > issue:
            chosen_start = start
            chosen_value = value
            break
    if chosen_start is None:
        raise ValueError("no phenomenon hour strictly after the model run")
    if chosen_value is None:
        raise ValueError("null precipitation is not stored as zero")
    return {
        "captured_live": True,
        "model": capture["model"],
        "issue_time": issue.isoformat(),
        "availability_time": availability.isoformat(),
        "valid_time": chosen_start.isoformat(),
        "valid_end": (chosen_start + timedelta(hours=1)).isoformat(),
        "value_mm": chosen_value,
        "grid_deg": capture["grid_deg"],
        "permits_financial_use": False,
        "legal_meteorological_authority": False,
        "local": capture["local"],
        "feature_local": capture["feature_local"],
    }


def _query(endpoint: str, params: dict) -> str:
    return endpoint + "?" + urlencode(params)


def _read(url: str) -> tuple[str, dict]:
    request = Request(
        url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"}
    )
    try:
        with urlopen(request, timeout=60) as response:
            http_date = response.headers["Date"]
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        raise ValueError(
            f"Open-Meteo refused the request ({error.code}): {detail}"
        ) from error
    if not http_date:
        raise ValueError("Open-Meteo response has no Date header; failing closed")
    return http_date, body


def fetch_live_sample(
    *,
    latitude: float = SAMPLE_LATITUDE,
    longitude: float = SAMPLE_LONGITUDE,
    model: str = SAMPLE_MODEL,
) -> dict:
    """Call the free forecast API, then store only a run with an issue time.

    The plain forecast JSON has no model-run field. The newest run the
    single-runs endpoint accepts is the issue time. No key is added.
    """
    if model not in NATIVE_DEG:
        raise ValueError("no published degree grid for this model; failing closed")
    common = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "precipitation,temperature_2m",
        "models": model,
        "timezone": "GMT",
        "cell_selection": "nearest",
        "forecast_days": 2,
    }
    forecast_date, _forecast_body = _read(_query(FORECAST_ENDPOINT, common))
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    candidate = now.replace(hour=now.hour - (now.hour % 3))
    accepted_stamp = None
    accepted_issue = None
    accepted_date = None
    accepted_body = None
    for _step in range(8):
        stamp = candidate.strftime("%Y-%m-%dT%H:%M")
        params = dict(common)
        params["run"] = stamp
        try:
            accepted_date, accepted_body = _read(
                _query(SINGLE_RUN_ENDPOINT, params)
            )
            accepted_stamp = stamp
            accepted_issue = candidate
            break
        except ValueError as error:
            if "not available" not in str(error):
                raise
            candidate -= timedelta(hours=3)
    if (
        accepted_issue is None
        or accepted_body is None
        or accepted_date is None
        or accepted_stamp is None
    ):
        raise ValueError("no JMA MSM run was available; failing closed")
    received = parsedate_to_datetime(accepted_date).astimezone(timezone.utc)
    return {
        "model": model,
        "issue_time": accepted_issue.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "availability_time": received.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "grid_deg": NATIVE_DEG[model],
        "published_support": "0.05 degree, about 5 km",
        "published_support_url": "https://open-meteo.com/en/docs/jma-api",
        "requested_latitude": latitude,
        "requested_longitude": longitude,
        "cell_selection": "nearest",
        "local": "jma-msm-live-" + accepted_issue.strftime("%Y%m%dt%Hz"),
        "feature_local": "jma-msm-005deg-2350n-12100e",
        "endpoint": SINGLE_RUN_ENDPOINT,
        "run_parameter": accepted_stamp,
        "http_date": accepted_date,
        "forecast_endpoint_http_date": forecast_date,
        "response": accepted_body,
    }
