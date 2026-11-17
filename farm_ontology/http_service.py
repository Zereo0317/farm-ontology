"""HTTP service for the farm decision record (Cloud Run).

Runs the record against the current-location farm: the Hiroki Tomiyasu
field, Biratori, Hokkaido (pinned on site 2026-11-16). The pin lives in
environment variables so a different deployment points at a different
farm without a code change.

Endpoints
---------
GET /            service banner (use-class Screening, class C closed)
GET /livez       liveness
GET /farm        the farm pin record (identity, tenure unknown stays unknown)
GET /farm/weather    live Open-Meteo current block for the farm point,
                     stored grid support (0.05 deg jma_msm) not the parcel
GET /farm/planet     Planet Labs quick search headers near the farm
GET /farm/ee         Earth Engine REST catalog status for the project
GET /farm/memo       decision memo render at the current time

No secret is echoed. Logs stay off stdout buffers of records. Financial
use stays false. Class C stays closed. A failed upstream answer is
reported as a gap, never as a value.
"""

from __future__ import annotations

import json
import os
import socketserver
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler

FARM = {
    "label": os.environ.get("FARM_LABEL", "Hiroki Tomiyasu field, Biratori, Hokkaido"),
    "latitude": float(os.environ.get("FARM_LAT", "42.7018152")),
    "longitude": float(os.environ.get("FARM_LON", "142.4071291")),
    "crop": "soybean",
    "crop_stage": "harvest",
    "crop_ontology_id": "CO_336",
    "crop_ontology_term": "https://cropontology.org/term/CO_336:ROOT",
    "gps_accuracy": "unknown",
    "tenure": "unknown",
    "pinned_on": "2026-11-16T23:27:23Z",
    "source_pin_maps": "https://maps.app.goo.gl/dKfj9uWuQm8U1aQi9",
}

USE_CLASS = "Screening"
CLASS_C = "closed"
GCP_PROJECT = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT", "seges-ai")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _key_present(name: str) -> bool:
    return bool(os.environ.get(name))


def _get_json(url: str, *, headers: dict | None = None, timeout: int = 20):
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read(int(os.environ.get("SERVICE_MAX_BYTES", "262144")))
        ctype = response.headers.get("content-type", "")
        return response.status, ctype, body


def _open_meteo_current(lat: float, lon: float) -> dict:
    query = urllib.parse.urlencode(
        {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,precipitation,"
            "wind_speed_10m,wind_direction_10m,cloud_cover",
            "models": "jma_msm",
            "wind_speed_unit": "ms",
        }
    )
    url = "https://api.open-meteo.com/v1/forecast?" + query
    status, _ctype, body = _get_json(url)
    doc = json.loads(body.decode("utf-8"))
    current = doc.get("current") or {}
    return {
        "source": "open-meteo",
        "endpoint": "forecast (free tier)",
        "model_requested": "jma_msm",
        "requested_point": {"latitude": lat, "longitude": lon},
        "stored_spatial_support": "grid-cell",
        "native_support_note": (
            "JMA MSM grid is 0.05 deg (about 5 km); the value is the cell, "
            "never the 0.4 ha parcel."
        ),
        "shrunk_to_plant": False,
        "returned": current,
        "retrieved_at": _now(),
        "http_status": status,
        "use_class": USE_CLASS,
        "permits_financial_use": False,
    }


def _planet_post(url: str, body: bytes, key: str, timeout: int = 30):
    """POST with the two schemes Planet documents; returns (status, parsed, scheme)."""
    import base64

    schemes = (
        ("Basic", "Basic " + base64.b64encode(f"{key}:".encode()).decode()),
        ("api-key", f"api-key {key}"),
    )
    last_status, last_body = None, None
    for name, header in schemes:
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Authorization": header, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, json.loads(response.read(262144)), name
        except urllib.error.HTTPError as error:
            last_status, last_body = error.code, error.read(2048).decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_status, last_body = 0, str(error)[:200]
    raise PlanetAuthError(last_status or 0, last_body or "")


class PlanetAuthError(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"Planet HTTP {status}: {body[:200]}")
        self.status = status
        self.body = body


def _planet_search(lat: float, lon: float) -> dict:
    radius_m = float(os.environ.get("PLANET_RADIUS_M", "2000"))
    body = json.dumps(
        {
            "item_types": ["PSScene"],
            "filter": {
                "type": "AndFilter",
                "config": [
                    {
                        "type": "GeometryFilter",
                        "field_name": "geometry",
                        "config": {
                            "type": "Point",
                            "coordinates": [lon, lat],
                        },
                    },
                    {
                        "type": "RangeFilter",
                        "field_name": "cloud_cover",
                        "config": {"lte": float(os.environ.get("PLANET_MAX_CLOUD", "0.25"))},
                    },
                ],
            },
        }
    ).encode("utf-8")
    key = os.environ.get("PLANET_API_KEY", "")
    if not key:
        return {"gap": "PLANET_API_KEY not mounted; refusing to report search headers"}
    try:
        status, doc, scheme = _planet_post(
            "https://api.planet.com/data/v1/quick-search", body, key
        )
    except PlanetAuthError as error:
        return {
            "gap": (
                "Planet rejected the mounted key "
                f"(HTTP {error.status}): {error.body[:160]}"
            ),
            "hint": (
                "Regenerate the key at planet.com/account (My Settings) and update "
                "secret manager entry Planet-labs; the service needs no redeploy."
            ),
            "auth_scheme_tried": ["Basic", "api-key"],
        }
    features = doc.get("features") or []
    headers_rows = []
    for feature in features[:10]:
        props = feature.get("properties") or {}
        headers_rows.append(
            {
                "id": feature.get("id"),
                "acquired": props.get("acquired"),
                "cloud_cover": props.get("cloud_cover"),
                "instrument": props.get("instrument"),
                "publishing_stage": props.get("publishing_stage"),
                "quality_category": props.get("quality_category"),
                "strip_id": props.get("strip_id"),
            }
        )
    return {
        "api": "Planet Data API quick-search (headers only; no pixels downloaded)",
        "matched": len(features),
        "search_center": {"latitude": lat, "longitude": lon},
        "radius_note": f"Point geometry within ~{radius_m:.0f} m scene coverage",
        "auth_scheme": scheme,
        "scenes": headers_rows,
        "retrieved_at": _now(),
        "licence_note": (
            "Planet subscription imagery: quote only scene headers here. "
            "Pixels stay unexported until a licence grant is attached; "
            "permits_financial_use stays false."
        ),
        "use_class": USE_CLASS,
        "permits_financial_use": False,
    }


def _metadata_token() -> str | None:
    """Access token from the Cloud Run metadata server, or None off-platform."""
    try:
        request = urllib.request.Request(
            "http://metadata.google.internal/computeMetadata/v1/"
            "instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            doc = json.loads(response.read(65536))
            token = doc.get("access_token")
            return str(token) if token else None
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, ValueError):
        return None


def _ee_catalog() -> dict:
    url = f"https://earthengine.googleapis.com/v1/projects/{GCP_PROJECT}/algorithms"
    token = _metadata_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        status, ctype, _body = _get_json(url, headers=headers, timeout=20)
        return {
            "project": GCP_PROJECT,
            "catalog_http_status": status,
            "used_runtime_identity": bool(token),
            "registration_type": "unknown",
            "permits_financial_use": False,
            "cap_note": (
                "Unknown registration forces permitsFinancialUse false and caps "
                "the use class at Screening. No Export task is started."
            ),
            "checked_at": _now(),
        }
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as error:
        return {"gap": f"Earth Engine catalog check failed: {str(error)[:120]}"}


def _memo_text() -> str:
    lines = [
        f"Farm record as of {_now()}",
        f"label: {FARM['label']}",
        f"point: {FARM['latitude']}, {FARM['longitude']} (GPS accuracy unknown)",
        f"crop: {FARM['crop']} ({FARM['crop_stage']}); CO_336 Soybean Ontology",
        f"tenure: unknown stays unknown; operator is not the right-holder",
        f"use_class: {USE_CLASS}; class C: {CLASS_C}; permits_financial_use: false",
        "spatial rule: grid/native values are stored at native support only;",
        "no hectare extrapolation; no boundary copy.",
        "Settlement, hedge, trigger, and nature-unit uses: refused.",
        "Live Earth Engine export: not run.",
    ]
    return "\n".join(lines)


STATUS_JSON = {
    "service": "farm-ontology-decision-record",
    "version": os.environ.get("SERVICE_VERSION", "git-unknown"),
    "project": GCP_PROJECT,
    "use_class": USE_CLASS,
    "class_c": CLASS_C,
    "permits_financial_use": False,
    "farm": {key: value for key, value in FARM.items()},
    "secrets_mounted": {
        "PLANET_API_KEY": _key_present("PLANET_API_KEY"),
    },
    "endpoints": [
        "/livez",
        "/farm",
        "/farm/weather",
        "/farm/planet",
        "/farm/ee",
        "/farm/memo",
    ],
}


def handle_target(path: str) -> tuple[int, dict | str, str]:
    path = urllib.parse.urlparse(path).path
    if path in ("/", ""):
        return 200, STATUS_JSON, "json"
    if path == "/livez":
        return 200, {"status": "live", "at": _now()}, "json"
    if path == "/farm":
        return 200, STATUS_JSON, "json"
    lat, lon = FARM["latitude"], FARM["longitude"]
    if path == "/farm/weather":
        try:
            return 200, _open_meteo_current(lat, lon), "json"
        except (urllib.error.HTTPError, urllib.error.URLError, OSError, ValueError) as error:
            return 200, {"gap": f"weather unreachable: {str(error)[:120]}"}, "json"
    if path == "/farm/planet":
        return 200, _planet_search(lat, lon), "json"
    if path == "/farm/ee":
        return 200, _ee_catalog(), "json"
    if path == "/farm/memo":
        return 200, _memo_text(), "text"
    return 404, {"error": f"no route {path}"}, "json"


class Handler(BaseHTTPRequestHandler):
    server_version = "farm-ontology/1.0"

    def _respond(self, status: int, payload, kind: str) -> None:
        if kind == "text":
            body = (payload + "\n").encode("utf-8")
            ctype = "text/plain; charset=utf-8"
        else:
            body = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            ctype = "application/json; charset=utf-8"
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        status, payload, kind = handle_target(self.path)
        self._respond(status, payload, kind)

    def log_message(self, fmt: str, *args) -> None:  # logs stay quiet but real
        import sys

        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


def main() -> int:
    port = int(os.environ.get("PORT", "8080"))
    with Server(("0.0.0.0", port), Handler) as server:
        server.serve_forever(poll_interval=0.5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
