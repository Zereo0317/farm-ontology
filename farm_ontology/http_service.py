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
GET /farm/ingest-status
                     WS2 ingest workers' last-run summaries from the
                     record backend (pipelines/run-log); jobs without
                     runs are reported as gaps
GET /farm/observations?limit=N
                     authenticated read of the latest N field
                     observations with their birth-certificate stamps
                     (file, recorded time, support, use class); the
                     token is the same `web-access-token` Secret the
                     web gate uses (WEB_ACCESS_TOKEN), given as the
                     X-Access-Token header.
                     Bad/absent token or unmounted secret: 401 + gap
                     shape. Missing/unreadable record backend: gap.

No secret is echoed. Logs stay off stdout buffers of records. Financial
use stays false. Class C stays closed. A failed upstream answer is
reported as a gap, never as a value.
"""

from __future__ import annotations

import hmac
import json
import os
import socketserver
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler

FARM = {
    "farm_id": os.environ.get("FARM_ID", "biratori-hokkaido"),
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

# Environment flags cannot establish provider rights or open class C. Until
# verified per-feed authorization exists, public metadata is screening-only.
USE_CLASS = "Screening"
CLASS_C = "closed"
GCP_PROJECT = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT", "seges-ai")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _key_present(name: str) -> bool:
    return bool(os.environ.get(name))


def _read_capped(response, cap: int) -> bytes:
    """Stream the whole body, raising IOError past the cap instead of truncating."""
    chunks = []
    total = 0
    while True:
        chunk = response.read(65536)
        if not chunk:
            break
        total += len(chunk)
        if total > cap:
            raise IOError(f"response body exceeded {cap} bytes")
        chunks.append(chunk)
    return b"".join(chunks)


def _get_json(url: str, *, headers: dict | None = None, timeout: int = 20):
    request = urllib.request.Request(url, headers=headers or {})
    cap = int(os.environ.get("SERVICE_MAX_BYTES", "2097152"))
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = _read_capped(response, cap)
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
                cap = int(os.environ.get("SERVICE_MAX_BYTES", "2097152"))
                raw = _read_capped(response, cap)
                return response.status, json.loads(raw.decode("utf-8")), name
        except urllib.error.HTTPError as error:
            last_status, last_body = error.code, error.read(2048).decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_status, last_body = 0, str(error)[:200]
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise PlanetAuthError(0, f"unreadable body: {str(error)[:160]}")
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
                "The key authenticates (the account probe returns 403, not 401) but "
                "its principal has no active Planet Insights subscription. "
                "Activate or purchase a plan for the key's owner at "
                "planet.com/account; then this service needs no redeploy."
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


def _licences_snapshot() -> dict:
    """Expose the grants engine verdicts for the headline feeds (fail-closed view)."""
    from datetime import datetime, timezone as _tz

    try:
        from farm_ontology.licences.grants import evaluate

        FEEDS = (
            "earth-engine.export",
            "jma.hazard",
            "open-meteo.jma-msm",
            "planet.planetary-variable.soil-water-content",
            "planet.psscene",
            "usdm.hazard",
        )
        at = datetime.now(_tz.utc)
        feeds = {}
        for feed in FEEDS:
            financial_allowed, _grant, fin_reason = evaluate(feed, "settlement", at)
            screening_allowed, _grant2, scr_reason = evaluate(feed, "screening", at)
            feeds[feed] = {
                "settlement_allowed": bool(financial_allowed),
                "settlement_reason": fin_reason,
                "screening_allowed": bool(screening_allowed),
                "screening_reason": scr_reason,
            }
        return {
            "grant_registry": "grants/ (specimens never unlock; fail closed)",
            "evaluated_at": _now(),
            "feeds": feeds,
            "note": (
                "Specimen certificates exist but never unlock a feed. "
                "Commercial punch-list: docs/legal/commercial-punchlist.md"
            ),
        }
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {"gap": f"grants state unreadable: {str(error)[:160]}"}


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
        "WEB_ACCESS_TOKEN": _key_present("WEB_ACCESS_TOKEN"),
    },
    "endpoints": [
        "/livez",
        "/farm",
        "/farm/weather",
        "/farm/planet",
        "/farm/{farm_id}/weather",
        "/farm/{farm_id}/planet",
        "/farm/{farm_id}/licences",
        "/farm/ee",
        "/farm/memo",
        "/farm/licences",
        "/farm/ingest-status",
        "/farm/observations (token-gated)",
    ],
}


def _ingest_status_snapshot() -> dict:
    """WS2 ingest observability read through the record backend (gap-honest).

    Carries ``backend`` + ``env_seen`` so a misconfigured deployment names
    itself: prod rev 00054 reported every job as an empty-store gap purely
    because its env lacked the record-backend vars; the payload must be
    able to show that at a glance instead of hiding behind the gaps.
    """
    from datetime import datetime, timezone as _tz

    from farm_ontology import ingest_core
    from farm_ontology.ingest_status import ingest_status

    now = datetime.now(_tz.utc)
    try:
        backend = ingest_core.open_pipe_backend()
        status = ingest_status(backend, now=now)
        return {
            **status,
            "backend": ingest_core.describe_backend(backend),
            "env_seen": {
                "FARM_RECORD_BACKEND": bool(os.environ.get("FARM_RECORD_BACKEND", "").strip()),
                "FARM_RECORD_BUCKET": bool(os.environ.get("FARM_RECORD_BUCKET", "").strip()),
            },
        }
    except (OSError, ValueError, RuntimeError) as error:
        return {"gap": f"ingest-status unreadable: {str(error)[:160]}"}


OBSERVATIONS_ROUTE = "/farm/observations"
OBSERVATIONS_DEFAULT_LIMIT = 20
OBSERVATIONS_MAX_LIMIT = 100


def _latest_observations(limit: int) -> list[dict]:
    """Latest observation stamps straight from the record backend.

    Deliberately reads THROUGH the same record-store seam the writer
    uses (record.record_dir -> record_store.open_backend), so an
    operator sees exactly what durability serves — local directory or
    GCS alike. Failures propagate as exceptions and surface as a gap.
    """
    from farm_ontology.record import record_dir
    from farm_ontology.record_store import open_backend

    store = open_backend(record_dir())
    names = sorted(store.list_paths("", "obs-*.json"))[-limit:]
    stamps = []
    for name in reversed(names):
        document = json.loads(store.read_text(name))
        weather = document.get("weather") or {}
        stamps.append(
            {
                "file": name,
                "recorded_at": document.get("phenomenon_time"),
                "availability_time": document.get("availability_time"),
                "support": {
                    "native_resolution_deg": weather.get("native_resolution_deg"),
                    "spatial_support": weather.get("spatial_support"),
                    "shrunk_to_plant": weather.get("shrunk_to_plant"),
                    "gps_accuracy": document.get("gps_accuracy"),
                },
                "use_class": document.get("use_class"),
                "class_c_policy": document.get("class_c_policy"),
                "permits_financial_use": document.get("permits_financial_use"),
                "dry_run": document.get("dry_run"),
            }
        )
    return stamps


def _observations_route(token: str | None, limit_raw: str | None) -> tuple[int, dict, str]:
    """Token-gated record read: fail closed, 401+gap on anything unworthy."""
    expected = os.environ.get("WEB_ACCESS_TOKEN", "").strip()
    given = (token or "").strip()
    if not expected:
        return (
            401,
            {
                "gap": (
                    "observations not served: WEB_ACCESS_TOKEN is not "
                    "mounted on this revision; the route fails closed"
                )
            },
            "json",
        )
    if not given or not hmac.compare_digest(given, expected):
        return (
            401,
            {"gap": "observations not served: a valid access token is required (X-Access-Token)"},
            "json",
        )
    try:
        limit = int(limit_raw) if limit_raw is not None else OBSERVATIONS_DEFAULT_LIMIT
    except (TypeError, ValueError):
        limit = OBSERVATIONS_DEFAULT_LIMIT
    limit = max(1, min(OBSERVATIONS_MAX_LIMIT, limit))
    try:
        stamps = _latest_observations(limit)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        return 200, {"gap": f"record backend unreadable: {str(error)[:160]}"}, "json"
    return (
        200,
        {
            "count": len(stamps),
            "limit": limit,
            "observations": stamps,
            "note": (
                "latest observations with their birth-certificate stamps; "
                "the record never shrinks native support to the plant, and "
                "financial use stays false"
            ),
        },
        "json",
    )


def handle_target(path: str, *, token: str | None = None) -> tuple[int, dict | str, str]:
    split = urllib.parse.urlsplit(path)
    path = split.path
    query = urllib.parse.parse_qs(split.query)
    if path in ("/", ""):
        return 200, STATUS_JSON, "json"
    if path == "/livez":
        return 200, {"status": "live", "at": _now()}, "json"
    if path == "/farm":
        return 200, STATUS_JSON, "json"
    parts = [part for part in path.split("/") if part]
    if len(parts) == 3 and parts[0] == "farm":
        requested_farm = parts[1]
        try:
            from farm_ontology.access_control import normalize_farm_id

            normalize_farm_id(requested_farm)
        except ValueError:
            return 404, {"gap": True, "reason": "invalid farm identifier"}, "json"
        if requested_farm != FARM["farm_id"]:
            return 404, {"gap": True, "reason": "farm feeds are not configured"}, "json"
        lat, lon = FARM["latitude"], FARM["longitude"]
        if parts[2] == "weather":
            try:
                return 200, _open_meteo_current(lat, lon), "json"
            except (urllib.error.HTTPError, urllib.error.URLError, OSError, ValueError) as error:
                return 200, {"gap": f"weather unreachable: {str(error)[:120]}"}, "json"
        if parts[2] == "planet":
            return 200, _planet_search(lat, lon), "json"
        if parts[2] == "licences":
            return 200, _licences_snapshot(), "json"
        return 404, {"gap": True, "reason": "unknown farm feed"}, "json"
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
    if path == "/farm/licences":
        return 200, _licences_snapshot(), "json"
    if path == "/farm/ingest-status":
        return 200, _ingest_status_snapshot(), "json"
    if path in (OBSERVATIONS_ROUTE, "/leads") and "token" in urllib.parse.parse_qs(split.query, keep_blank_values=True):
        return 400, {"gap": "query-string credentials are not accepted; use X-Access-Token"}, "json"
    if path == OBSERVATIONS_ROUTE:
        return _observations_route(
            token=token,
            limit_raw=(query.get("limit") or [None])[0],
        )
    if path == "/farm/memo":
        return 200, _memo_text(), "text"
    if path == "/leads":
        return _leads_admin(token=token)
    return 404, {"error": f"no route {path}"}, "json"


def _token_ok(candidate: str | None) -> bool:
    expected = os.environ.get("WEB_ACCESS_TOKEN", "")
    if not expected or not candidate:
        return False
    import hmac as _hmac

    return _hmac.compare_digest(candidate.strip(), expected.strip())


def _leads_admin(*, token: str | None) -> tuple[int, dict | str, str]:
    from farm_ontology.leads import list_leads

    if not _token_ok(token):
        return (
            401,
            {"gap": "leads are an admin route: pass the access token (X-Access-Token)"},
            "json",
        )
    try:
        return 200, list_leads(), "json"
    except (OSError, ValueError, TypeError) as error:
        return 200, {"gap": f"lead registry unreadable: {str(error)[:140]}"}, "json"


def handle_lead_post(body: bytes, *, origin: str | None) -> tuple[int, dict, dict]:
    """POST /leads: validate, hash, store. Returns (status, payload, extra_headers)."""
    from farm_ontology.leads import cors_preflight, submit_lead

    if not body:
        return 422, {"gap": "empty body"}, cors_preflight(origin)
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return 422, {"gap": f"body was not json: {str(error)[:120]}"}, cors_preflight(origin)
    if not isinstance(payload, dict):
        return 422, {"gap": "body must be a json object"}, cors_preflight(origin)
    try:
        row = submit_lead(payload, origin=origin)
    except ValueError as error:
        return 422, {"gap": str(error)[:240]}, cors_preflight(origin)
    except OSError as error:
        return 502, {"gap": f"lead store unwritable: {str(error)[:140]}"}, cors_preflight(origin)
    headers = cors_preflight(origin)
    headers["Access-Control-Allow-Origin"] = headers.get("Access-Control-Allow-Origin", origin or "*")
    return 200, row, headers


class Handler(BaseHTTPRequestHandler):
    server_version = "farm-ontology/1.0"

    def _respond(self, status: int, payload, kind: str, extra_headers: dict | None = None) -> None:
        if kind == "text":
            body = (payload + "\n").encode("utf-8")
            ctype = "text/plain; charset=utf-8"
        else:
            body = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            ctype = "application/json; charset=utf-8"
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802 (http.server API)
        from farm_ontology.leads import cors_preflight

        origin = self.headers.get("Origin")
        self.send_response(204)
        for key, value in cors_preflight(origin).items():
            self.send_header(key, value)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802 (http.server API)
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(min(length, 65536)) if length else b""
            if urllib.parse.urlsplit(self.path).path == "/leads":
                status, payload, headers = handle_lead_post(body, origin=self.headers.get("Origin"))
                self._respond(status, payload, "json", headers)
                return
            self._respond(404, {"error": f"no POST route {urllib.parse.urlsplit(self.path).path}"}, "json")
        except Exception as error:  # keep the connection alive, publish the gap
            self._respond(200, {"gap": f"handler error: {str(error)[:200]}"}, "json")

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        try:
            header_token = self.headers.get("X-Access-Token")
            status, payload, kind = handle_target(self.path, token=header_token)
        except Exception as error:  # a gap is reported; the connection survives
            status, payload, kind = 200, {"gap": f"handler error: {str(error)[:200]}"}, "json"
        self._respond(status, payload, kind)

    def log_message(self, fmt: str, *args) -> None:  # logs stay quiet but real
        import re
        import sys

        line = fmt % args
        # House rule: never print key material in logs — redact token=
        # query values (X-Access-Token headers never reach this line).
        line = re.sub(r"(token=)[^&\s]+", r"\1<redacted>", line)
        sys.stderr.write("%s - %s\n" % (self.address_string(), line))


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
