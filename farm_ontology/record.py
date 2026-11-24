"""One local field record for the stdio server and the laptop page.

Observations are built by fieldkit. This module does not change that
function. Weather is optional and stays on the 0.05 degree grid.
"""

from __future__ import annotations

import json
import hashlib
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from farm_ontology.access_control import normalize_farm_id
from farm_ontology.fieldkit import (
    DRY_LATITUDE,
    DRY_LONGITUDE,
    DRY_NOTE,
    GRID_DEG,
    SOYBEAN_ID,
    build_observation,
)
from farm_ontology.manifest import load_manifest
from farm_ontology.policy import CLASS_C_POLICY, class_c_policy
from farm_ontology.record_store import open_backend

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / "docs" / "field-playbook.md"
SOP = ROOT / "docs" / "field-sop.md"


def record_dir() -> Path:
    raw = os.environ.get("FARM_RECORD_DIR", "").strip()
    path = Path(raw) if raw else ROOT / "field-notes"
    path.mkdir(parents=True, exist_ok=True)
    (path / "notes").mkdir(exist_ok=True)
    return path


def _store():
    """Storage for the record; local directory or GCS (see record_store)."""
    return open_backend(record_dir())


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(at: datetime) -> str:
    return at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _farm_prefix(farm_id: str | None) -> str:
    """Return a safe tenant prefix, refusing unscoped production operations.

    Local development and the existing single-tenant command-line tools keep
    their historical root layout unless ``FARM_REQUIRE_TENANT_CONTEXT`` is
    enabled. Hosted field APIs set that flag and must pass an authenticated
    farm identifier for every read and write. Legacy root records are never
    implicitly assigned to a tenant.
    """
    if farm_id is None:
        if os.environ.get("FARM_REQUIRE_TENANT_CONTEXT", "").strip().lower() in {
            "1", "true", "yes", "on"
        }:
            raise ValueError("farm_id is required for this record operation")
        return ""
    normalize_farm_id(farm_id)
    return f"farms/{farm_id}/"


def _request_id(value: str | None) -> str | None:
    """Validate a client UUID and require it for hosted record writes."""
    required = os.environ.get("FARM_REQUIRE_IDEMPOTENCY", "").strip().lower() in {
        "1", "true", "yes", "on"
    }
    if value is None:
        if required:
            raise ValueError("request_id is required for this record operation")
        return None
    pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise ValueError("request_id must be a canonical lowercase UUID")
    return value


def _request_fingerprint(operation: str, payload: dict) -> str:
    encoded = json.dumps(
        {"operation": operation, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_record_once(
    store,
    name: str,
    document: dict,
    *,
    request_id: str | None,
    payload_fingerprint: str,
) -> dict:
    """Create a record, returning the original on an exact request retry."""
    if request_id is not None:
        document["idempotency"] = {
            "request_id": request_id,
            "payload_sha256": payload_fingerprint,
        }
    data = (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    try:
        store.write_once(name, data)
        return document
    except FileExistsError:
        if request_id is None:
            raise
        existing = json.loads(store.read_text(name))
        expected = {"request_id": request_id, "payload_sha256": payload_fingerprint}
        if existing.get("idempotency") != expected:
            raise ValueError("request_id was reused with a different payload")
        return existing


def read_playbook() -> str:
    return PLAYBOOK.read_text(encoding="utf-8")


def read_sop() -> str:
    return SOP.read_text(encoding="utf-8")


def status(*, farm_id: str | None = None) -> dict:
    document = load_manifest()
    folder = record_dir()
    store = _store()
    prefix = _farm_prefix(farm_id)
    observations = sorted(store.list_paths(prefix, "obs-*.json"))
    notes = sorted(store.list_paths(f"{prefix}notes/", "note-*.json"))
    return {
        "crop": "soybean",
        "crop_stage": "harvest",
        "crop_ontology_id": SOYBEAN_ID,
        "class_c_policy": class_c_policy(),
        "permits_financial_use": False,
        "trade_signal": False,
        "weather_model": "jma_msm",
        "native_resolution_deg": GRID_DEG,
        "spatial_support": "grid-cell",
        "farm_id": farm_id,
        "shrunk_to_plant": False,
        "iri_base": document["iri_base"],
        "iri_base_status": document["iri_base_status"],
        "intended_domain": document.get("intended_domain"),
        "domain_attached": document.get("domain_attached"),
        "observation_count": len(observations),
        "note_count": len(notes),
        "record_dir": str(folder),
    }


def _attach_weather(document: dict) -> dict:
    from farm_ontology.adapters.open_meteo import build_live_document, fetch_live_sample

    capture = fetch_live_sample(
        latitude=float(document["latitude"]),
        longitude=float(document["longitude"]),
        feature_local="jma-msm-native-grid-cell",
    )
    live = build_live_document(capture)
    if float(live["grid_deg"]) != GRID_DEG:
        raise ValueError("refusing a weather grid that is not 0.05 degrees")
    weather = dict(document["weather"])
    weather["value"] = live["value_mm"]
    weather["unit"] = "mm"
    weather["quantity"] = "precipitation"
    weather["issue_time"] = live["issue_time"]
    weather["valid_time"] = live["valid_time"]
    weather["native_resolution_deg"] = GRID_DEG
    weather["spatial_support"] = "grid-cell"
    weather["shrunk_to_plant"] = False
    weather["cell_selection"] = "nearest"
    updated = dict(document)
    updated["weather"] = weather
    updated["class_c_policy"] = CLASS_C_POLICY
    updated["permits_financial_use"] = False
    updated["trade_signal"] = False
    return updated


def record_observation(
    *,
    latitude: float | None,
    longitude: float | None,
    note: str = "",
    metres: float | None = None,
    sample_id: str | None = None,
    photo_path: str | None = None,
    harvest_unit: str | None = None,
    moisture: float | None = None,
    dry_run: bool = False,
    attach_weather: bool = False,
    farm_id: str | None = None,
    request_id: str | None = None,
    at: datetime | None = None,
) -> dict:
    prefix = _farm_prefix(farm_id)
    request_id = _request_id(request_id)
    moment = at or _now()
    if dry_run:
        latitude = DRY_LATITUDE
        longitude = DRY_LONGITUDE
        note = DRY_NOTE
        metres = None
        sample_id = None
        photo_path = None
        harvest_unit = None
        moisture = None
    if latitude is None or longitude is None:
        raise ValueError("latitude and longitude are required")
    payload_fingerprint = _request_fingerprint(
        "observation",
        {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "note": note,
            "metres": metres,
            "sample_id": sample_id,
            "photo_path": photo_path,
            "harvest_unit": harvest_unit,
            "moisture": moisture,
            "dry_run": dry_run,
            "attach_weather": attach_weather,
            "farm_id": farm_id,
        },
    )
    document = build_observation(
        latitude=float(latitude),
        longitude=float(longitude),
        note=note,
        at=moment,
        dry_run=dry_run,
        metres=metres,
        sample_id=sample_id,
        photo_path=photo_path,
        harvest_unit=harvest_unit,
        moisture=moisture,
    )
    if attach_weather:
        try:
            document = _attach_weather(document)
        except (OSError, ValueError, KeyError) as error:
            weather = dict(document["weather"])
            weather["value"] = None
            weather["shrunk_to_plant"] = False
            weather["attach_error"] = str(error)
            document = dict(document)
            document["weather"] = weather
    if document["class_c_policy"] != "closed" or document["permits_financial_use"]:
        raise RuntimeError("the field record refuses an open class C or a financial use")
    if farm_id is not None:
        document["farm_id"] = farm_id
    store = _store()
    name = (
        f"obs-request-{request_id}.json"
        if request_id is not None
        else f"obs-{_stamp(moment)}-{uuid.uuid4().hex}.json"
    )
    stored = _write_record_once(
        store,
        f"{prefix}{name}",
        document,
        request_id=request_id,
        payload_fingerprint=payload_fingerprint,
    )
    return {"file": name, "observation": stored}


def _note_name(name: str | None) -> str | None:
    if name is None or name == "":
        return None
    if Path(name).name != name or name.startswith("."):
        raise ValueError("observation file must be a file name in the record")
    return name


def add_note(
    *,
    kind: str,
    text: str,
    observation_file: str | None = None,
    farm_id: str | None = None,
    request_id: str | None = None,
    at: datetime | None = None,
) -> dict:
    prefix = _farm_prefix(farm_id)
    request_id = _request_id(request_id)
    if kind not in {"verification", "feedback"}:
        raise ValueError("note kind is verification or feedback")
    body = text.strip()
    if not body:
        raise ValueError("note text is empty")
    target = _note_name(observation_file)
    if target is not None and not _store().exists(f"{prefix}{target}"):
        raise ValueError("that observation file is not in the record")
    moment = at or _now()
    payload_fingerprint = _request_fingerprint(
        "note",
        {
            "kind": kind,
            "text": body,
            "observation_file": PurePosixPath(target).name if target else None,
            "farm_id": farm_id,
        },
    )
    note = {
        "kind": kind,
        "text": body,
        "time": moment.astimezone(timezone.utc).isoformat(),
        "observation_file": target,
        "class_c_policy": CLASS_C_POLICY,
        "permits_financial_use": False,
        "trade_signal": False,
    }
    if farm_id is not None:
        note["farm_id"] = farm_id
    store = _store()
    name = (
        f"notes/note-request-{request_id}.json"
        if request_id is not None
        else f"notes/note-{kind}-{_stamp(moment)}-{uuid.uuid4().hex}.json"
    )
    stored = _write_record_once(
        store,
        f"{prefix}{name}",
        note,
        request_id=request_id,
        payload_fingerprint=payload_fingerprint,
    )
    return {"file": PurePosixPath(name).name, "note": stored}


def list_notes(*, farm_id: str | None = None) -> dict:
    prefix = _farm_prefix(farm_id)
    store = _store()
    observations = []
    for name in sorted(store.list_paths(prefix, "obs-*.json")):
        document = json.loads(store.read_text(name))
        weather = document.get("weather") or {}
        observations.append(
            {
                "file": PurePosixPath(name).name,
                "farm_id": document.get("farm_id"),
                "phenomenon_time": document.get("phenomenon_time"),
                "crop": document.get("crop"),
                "crop_ontology_id": document.get("crop_ontology_id"),
                "dry_run": document.get("dry_run"),
                "sample_id": document.get("row_or_sample_id"),
                "latitude": document.get("latitude"),
                "longitude": document.get("longitude"),
                "weather_value": weather.get("value"),
                "shrunk_to_plant": weather.get("shrunk_to_plant"),
                "class_c_policy": document.get("class_c_policy"),
                "permits_financial_use": document.get("permits_financial_use"),
                "trade_signal": document.get("trade_signal"),
            }
        )
    notes = []
    for name in sorted(store.list_paths(f"{prefix}notes/", "note-*.json")):
        note_body = json.loads(store.read_text(name))
        notes.append({"file": PurePosixPath(name).name, **note_body})
    return {"observations": observations, "notes": notes}


# ---------------------------------------------------------------------------
# Boundary walk (2026-11-19): corners pinned on site become the record's
# first parcel polygons. A walk = one field, ordered corners + optional
# centre; accuracy travels verbatim per pin (never averaged); tenure stays
# unknown until a human sources it. Points are recorded as OBSERVATIONS
# (reuse of the governed obs pipeline), the assembled polygon is a separate
# boundary-walk document — one walk, one file; retry deduplication requires
# an explicit request id and is not yet provided.


def record_boundary_walk(
    *,
    parcel_name: str,
    crop: str = "soybean",
    corners: list[dict],
    centre: dict | None = None,
    note: str = "",
    operator: str | None = None,
    dry_run: bool = False,
    farm_id: str | None = None,
    request_id: str | None = None,
    at: datetime | None = None,
) -> dict:
    """Turn ordered corner pins into a governed boundary-walk record.

    Each corner: ``{"corner": "NW"|"NE"|"SE"|"SW", "lat": float,
    "lon": float, "accuracy_m": float|None}``. Accuracy is REQUIRED from
    the device screen (it exists on every phone); a walk whose pins all
    lack metres is refused — "unknown" only ever applies to a pin that
    declares it saw no figure, and a polygon built entirely of those is
    an unknown-accuracy polygon, which this record prints as such rather
    than averaging into fairy metres.
    """
    prefix = _farm_prefix(farm_id)
    request_id = _request_id(request_id)
    name = parcel_name.strip()
    if not name:
        raise ValueError("parcel name is empty")
    if len(corners) < 3:
        raise ValueError("a boundary walk needs at least three corners")
    moment = at or _now()
    seen_corners = []
    points = []
    for index, corner in enumerate(corners):
        label = str(corner.get("corner") or "").strip().upper()
        if label not in {"NW", "NE", "SE", "SW"}:
            raise ValueError(f"corner {index}: corner must be one of NW/NE/SE/SW, got {label!r}")
        if label in seen_corners:
            raise ValueError(f"corner {index}: {label} appears twice")
        seen_corners.append(label)
        lat = corner.get("lat")
        lon = corner.get("lon")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            raise ValueError(f"corner {index}: numeric lat/lon required")
        if not (-90 <= float(lat) <= 90) or not (-180 <= float(lon) <= 180):
            raise ValueError(f"corner {index}: lat/lon out of range")
        accuracy = corner.get("accuracy_m")
        accuracy_state = "unknown"
        accuracy_value = None
        if isinstance(accuracy, (int, float)) and not isinstance(accuracy, bool) and accuracy > 0:
            accuracy_state = "metres"
            accuracy_value = round(float(accuracy), 2)
        points.append(
            {
                "corner": label,
                "latitude": float(lat),
                "longitude": float(lon),
                "gps_accuracy": accuracy_state,
                "gps_accuracy_m": accuracy_value,
            }
        )

    centre_point = None
    if centre is not None:
        clat, clon = centre.get("lat"), centre.get("lon")
        if not isinstance(clat, (int, float)) or not isinstance(clon, (int, float)):
            raise ValueError("centre: numeric lat/lon required")
        c_acc = centre.get("accuracy_m")
        centre_point = {
            "corner": "CENTRE",
            "latitude": float(clat),
            "longitude": float(clon),
            "gps_accuracy": "metres" if isinstance(c_acc, (int, float)) and not isinstance(c_acc, bool) and c_acc > 0 else "unknown",
            "gps_accuracy_m": round(float(c_acc), 2) if isinstance(c_acc, (int, float)) and not isinstance(c_acc, bool) and c_acc > 0 else None,
        }

    # a rough area estimate ONLY when all four corners pin metred accuracy:
    # shoelace on the square-ish order NW/NE/SE/SW, printed as an ESTIMATE
    # at the pins' support, never as a surveyed cadastral figure. (The
    # centre pin is welcome but not required — it does not gate the maths.)
    area_estimate_ha = None
    accuracy_note = "mixed or unknown pin accuracy"
    if len(points) == 4:
        accuracies = [p["gps_accuracy_m"] for p in points]
        if all(a is not None for a in accuracies):
            order = {c: i for i, c in enumerate(("NW", "NE", "SE", "SW"))}
            ring = sorted(points, key=lambda p: order[p["corner"]])
            lat_mid = sum(p["latitude"] for p in ring) / 4
            metres_per_deg_lat = 111_132.0
            metres_per_deg_lon = 111_320.0 * __import__("math").cos(__import__("math").radians(lat_mid))
            area = 0.0
            for i in range(4):
                a, b = ring[i], ring[(i + 1) % 4]
                area += (a["longitude"] * metres_per_deg_lon) * (b["latitude"] * metres_per_deg_lat)
                area -= (b["longitude"] * metres_per_deg_lon) * (a["latitude"] * metres_per_deg_lat)
            area_estimate_ha = round(abs(area) / 2 / 10_000, 4)
            worst = max(accuracies)
            accuracy_note = f"closed quadrilateral; worst pin accuracy {worst:g} m"

    document = {
        "record_type": "boundary-walk",
        "parcel_name": name,
        "crop": crop,
        "pinned_at": moment.astimezone(timezone.utc).isoformat(),
        "pinned_by": operator or "field-operator",
        "dry_run": bool(dry_run),
        "points": points,
        "centre": centre_point,
        "corner_count": len(points),
        "area_estimate_ha": area_estimate_ha,
        "area_estimate_basis": "shoelace on the four ordered pins; ESTIMATE at pin support" if area_estimate_ha is not None else None,
        "accuracy_note": accuracy_note,
        "tenure": "unknown",
        "note": note.strip(),
        "use_class": "Screening",
        "class_c_policy": CLASS_C_POLICY,
        "permits_financial_use": False,
        "trade_signal": False,
    }
    if farm_id is not None:
        document["farm_id"] = farm_id
    store = _store()
    payload_fingerprint = _request_fingerprint(
        "boundary_walk",
        {
            "parcel_name": name,
            "crop": crop,
            "corners": corners,
            "centre": centre,
            "note": note,
            "operator": operator,
            "dry_run": dry_run,
            "farm_id": farm_id,
        },
    )
    name_ = (
        f"boundary/walk-request-{request_id}.json"
        if request_id is not None
        else f"boundary/walk-{_stamp(moment)}-{uuid.uuid4().hex}.json"
    )
    if not dry_run:
        document = _write_record_once(
            store,
            f"{prefix}{name_}",
            document,
            request_id=request_id,
            payload_fingerprint=payload_fingerprint,
        )
    return {"file": PurePosixPath(name_).name, "walk": document}


def list_boundary_walks(*, farm_id: str | None = None) -> dict:
    prefix = _farm_prefix(farm_id)
    store = _store()
    walks = []
    for name in sorted(store.list_paths(f"{prefix}boundary/", "walk-*.json")):
        body = json.loads(store.read_text(name))
        walks.append(
            {
                "file": PurePosixPath(name).name,
                "farm_id": body.get("farm_id"),
                "parcel_name": body.get("parcel_name"),
                "pinned_at": body.get("pinned_at"),
                "corner_count": body.get("corner_count"),
                "area_estimate_ha": body.get("area_estimate_ha"),
                "accuracy_note": body.get("accuracy_note"),
                "dry_run": body.get("dry_run"),
            }
        )
    return {"walks": walks}
