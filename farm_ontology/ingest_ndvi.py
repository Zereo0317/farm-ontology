"""WS2.3 Sandbox NDVI weekly baseline: Sentinel-2 (Sandbox) 10 m statistics.

OVERVIEW AND WHY IT IS GUARDED OFF
----------------------------------

The Statistical API on the Planet Insights Platform (Sentinel-Hub
based) returns zonal statistics for the farm cell at Sentinel-2's
native 10 m. Per the roadmap the stored row must keep ITS OWN 10 m
support — never mixed with, shrunk into, or averaged against the 5 km
jma_msm grid or any coarser product (support honesty, roadmap §1.2).

REAL CALL PREREQUISITE (OAuth client, from the task-6/Insights
tracking): the Statistical API authenticates with a Sentinel-Hub style
OAuth CLIENT — a client id + secret minted on the Insights Platform
account. As recorded in ``docs/backend-live.md`` (2026-11-17), that
account's UI had NOT yet surfaced OAuth client creation. When it does
(the WS6/trial punch-list item), store the pair in Secret Manager and
set the environment seam below. Until then any attempt at the real
call fails LOUDLY rather than pretending:

- ``FARM_SANDBOX_STAT_API`` : base URL of the Statistical API endpoint
  (required to arm the real call);
- ``FARM_SANDBOX_CLIENT``   : name of the mounted secret holding
  ``client_id:client_secret`` (required to arm the real call);
- ``FARM_SANDBOX_TOKEN_URL``: OAuth2 token endpoint override (optional).

This module NEVER fetches credentials and NEVER invents token flows.
Without the env seam armed, calling the real API raises ``RuntimeError``
and the weekly run logs the refusal honestly. WITH the seam armed (an
integration step, deliberately NOT exercised by offline tests) the
request body below is exactly what the API documents for a statistical
 NDVI aggregation over a single cell-size geometry.

OFFLINE CONTRACT (tests)
------------------------

``statistical_ndvi(geometry, from_, to)``, and therefore the weekly
job, accepts an INJECTED transport. Offline tests and CI always pass a
stub (a recorded fixture response — see
``tests/test_ingest_ndvi.py``), so the network is never touched. The
default transport raises unless the env seam is armed.

Row honesty
-----------

Stored NDVI rows carry: the statistics returned, the geometry bbox, the
closed 10 m support label ``sentinel-2-10m``, ``statistical_api`` as the
procedure, and the permit/class flags. NDVI is a vegetation index: it
is never a settlement, a yield, or a trade signal (mirrors the recorded
MODIS NDVI posture).
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

from farm_ontology import ingest_core

NDVI_JOB = "ndvi-weekly"

NDVI_SUPPORT = "sentinel-2-10m"

BASE_URL_ENV = "FARM_SANDBOX_STAT_API"
CLIENT_SECRET_NAME_ENV = "FARM_SANDBOX_CLIENT"
TOKEN_URL_ENV = "FARM_SANDBOX_TOKEN_URL"
DEFAULT_TOKEN_URL = "https://services.sentinel-hub.com/oauth/token"

# Farm cell: a 10 m-square window around the pinned point is the honest
# minimal footprint for a statistical query; the record keeps the cell,
# never a parcel (the polygon belongs to the boundary workstream).
CELL_SIZE_DEG = 0.0001  # ~= 10 m at Biratori latitude
WINDOW_DAYS = 7

NDVI_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {input: ["B04", "B08"], output: {bands: 1, sampleType: "FLOAT32"}}
}
function evaluatePixel(sample) {
  return [(sample.B08 - sample.B04) / (sample.B08 + sample.B04)]
}
"""


def cell_geometry(latitude: float, longitude: float) -> dict:
    half = CELL_SIZE_DEG / 2.0
    return {
        "type": "Polygon",
        "coordinates": [[
            [longitude - half, latitude - half],
            [longitude + half, latitude - half],
            [longitude + half, latitude + half],
            [longitude - half, latitude + half],
            [longitude - half, latitude - half],
        ]],
    }


def statistical_request(
    geometry: dict, *, from_: datetime, to: datetime
) -> dict:
    """The request body exactly as the Statistical API documents it."""
    return {
        "input": {
            "bounds": {"geometry": geometry},
            "data": [
                {
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "timeRange": {
                            "from": ingest_core.iso(from_),
                            "to": ingest_core.iso(to),
                        },
                        "maxCloudCoverage": 30,
                    },
                }
            ],
        },
        "aggregation": {
            "timeRange": {
                "from": ingest_core.iso(from_),
                "to": ingest_core.iso(to),
            },
            "aggregationInterval": {"of": f"P{WINDOW_DAYS}D"},
            "aggregationType": "simple",
            "resolution": "10m",
        },
        "calculations": {
            "ndvi": {
                "bands": ["B04", "B08"],
                "indices": {"ndvi": "(B08 - B04) / (B08 + B04)"},
            }
        },
    }


def _armed_env() -> dict:
    base = os.environ.get(BASE_URL_ENV, "").strip()
    client = os.environ.get(CLIENT_SECRET_NAME_ENV, "").strip()
    return {"base": base, "client": client, "token_url": os.environ.get(TOKEN_URL_ENV, "").strip()}


def _default_transport(request_body: dict, *, now: datetime) -> dict:
    """The REAL call: only when the OAuth client seam is armed.

    Raises loudly otherwise; a mounted Secret Manager client never lives
    in this repository (house rule). Token exchange mirrors the API's
    OAuth2 client-credentials contract.
    """
    env = _armed_env()
    if not env["base"] or not env["client"]:
        raise RuntimeError(
            "Statistical API is not armed: set "
            f"{BASE_URL_ENV} and {CLIENT_SECRET_NAME_ENV} (the OAuth client "
            "secret mount from the task-6/Insights punch-list) before "
            "enabling the real call. Offline runs must inject the transport."
        )
    del now  # the transport uses no clock; callers inject stamps
    secret = os.environ.get(env["client"], "").strip()
    if not secret or ":" not in secret:
        raise RuntimeError(
            f"client secret {env['client']} is not mounted as 'id:secret'"
        )
    client_id, client_secret = secret.split(":", 1)
    token_body = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
    ).encode("utf-8")
    token_url = env["token_url"] or DEFAULT_TOKEN_URL
    token_request = urllib.request.Request(
        token_url,
        data=token_body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(token_request, timeout=30) as response:
        token = json.loads(response.read(65_536))["access_token"]
    request = urllib.request.Request(
        env["base"].rstrip("/") + "/statistics",
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read(2_097_152))


def run_ndvi_job(
    backend,
    *,
    now: datetime,
    latitude: float,
    longitude: float,
    transport=None,
) -> dict:
    """One weekly baseline run against an injected backend.

    ``transport(request_body, now)`` overrides the Statistics call; the
    stub responses (recorded fixtures) drive offline tests and CI. With
    transport=None the armed-env real call runs; unarmed environments
    fail the run honestly — the run row records the refusal, 3 strikes
    fire the standard alert.
    """
    started = now
    window_start = now - timedelta(days=WINDOW_DAYS)
    written: str | None = None
    row_count = 0
    error: str | None = None
    geometry = cell_geometry(latitude, longitude)
    request_body = statistical_request(geometry, from_=window_start, to=now)
    try:
        if transport is None:
            statistics = _default_transport(request_body, now=now)
        else:
            statistics = transport(request_body, now=now)
        row = {
            "kind": NDVI_JOB,
            "source": "planet-insights-statistical-api (Sentinel-2 L2A)",
            "index": "ndvi",
            "support": NDVI_SUPPORT,
            "native_resolution_m": 10,
            "geometry_bbox_ccw": geometry["coordinates"][0][:4],
            "window_from": ingest_core.iso(window_start),
            "window_to": ingest_core.iso(now),
            "statistics": statistics,
            "unit": "dimensionless index (no ndvi-as-yield, no settlement, no trade)",
            "permits_financial_use": False,
            "support_note": (
                "stored as its own 10 m Sentinel-2 support; never mixed with, "
                "averaged into, or shrunk from the 0.05 deg weather grid"
            ),
            "mixed_into_coarse_support": False,
        }
        day = ingest_core.day_stamp(now)
        name = f"ndvi-{day}-cell.json"
        written = ingest_core.write_data_row(backend, "ndvi", name, row, job=NDVI_JOB, now=now)
        row_count = 1
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as caught:
        error = f"ndvi-weekly failed: {caught}"
    finished = now
    ingest_core.append_run(
        backend,
        job=NDVI_JOB,
        now=finished,
        started=started,
        finished=finished,
        ok=error is None,
        row_count=row_count,
        error=error,
        window_days=WINDOW_DAYS,
        support=NDVI_SUPPORT,
        transport=("injected" if transport is not None else "armed-default"),
        backend_desc=ingest_core.describe_backend(backend),
    )
    result = {
        "job": NDVI_JOB,
        "ok": error is None,
        "row_count": row_count,
        "written_row": written,
        "error": error,
    }
    result.update(ingest_core.on_run_finished(backend, job=NDVI_JOB, now=finished, run={
        "ok": error is None,
        "error": error,
        "row_count": row_count,
        "started": ingest_core.iso(started),
        "finished": ingest_core.iso(finished),
        "file": "",
    }))
    return result


__all__ = [
    "NDVI_JOB",
    "NDVI_SUPPORT",
    "BASE_URL_ENV",
    "CLIENT_SECRET_NAME_ENV",
    "TOKEN_URL_ENV",
    "DEFAULT_TOKEN_URL",
    "CELL_SIZE_DEG",
    "WINDOW_DAYS",
    "NDVI_EVALSCRIPT",
    "cell_geometry",
    "statistical_request",
    "run_ndvi_job",
]
