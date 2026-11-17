"""One local field record for the stdio server and the laptop page.

Observations are built by fieldkit. This module does not change that
function. Weather is optional and stays on the 0.05 degree grid.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

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


def read_playbook() -> str:
    return PLAYBOOK.read_text(encoding="utf-8")


def read_sop() -> str:
    return SOP.read_text(encoding="utf-8")


def status() -> dict:
    document = load_manifest()
    folder = record_dir()
    store = _store()
    observations = sorted(store.list_paths("", "obs-*.json"))
    notes = sorted(store.list_paths("notes/", "note-*.json"))
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
    at: datetime | None = None,
) -> dict:
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
    store = _store()
    name = f"obs-{_stamp(moment)}.json"
    if store.exists(name):
        name = f"obs-{_stamp(moment)}-{store.mtime_ns(name)}.json"
    store.write(name, (json.dumps(document, indent=2) + "\n").encode("utf-8"))
    return {"file": name, "observation": document}


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
    at: datetime | None = None,
) -> dict:
    if kind not in {"verification", "feedback"}:
        raise ValueError("note kind is verification or feedback")
    body = text.strip()
    if not body:
        raise ValueError("note text is empty")
    target = _note_name(observation_file)
    if target is not None and not _store().exists(target):
        raise ValueError("that observation file is not in the record")
    moment = at or _now()
    note = {
        "kind": kind,
        "text": body,
        "time": moment.astimezone(timezone.utc).isoformat(),
        "observation_file": target,
        "class_c_policy": CLASS_C_POLICY,
        "permits_financial_use": False,
        "trade_signal": False,
    }
    store = _store()
    name = f"notes/note-{kind}-{_stamp(moment)}.json"
    if store.exists(name):
        name = f"notes/note-{kind}-{_stamp(moment)}-2.json"
    store.write(name, (json.dumps(note, indent=2) + "\n").encode("utf-8"))
    return {"file": PurePosixPath(name).name, "note": note}


def list_notes() -> dict:
    store = _store()
    observations = []
    for name in sorted(store.list_paths("", "obs-*.json")):
        document = json.loads(store.read_text(name))
        weather = document.get("weather") or {}
        observations.append(
            {
                "file": name,
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
    for name in sorted(store.list_paths("notes/", "note-*.json")):
        note_body = json.loads(store.read_text(name))
        notes.append({"file": PurePosixPath(name).name, **note_body})
    return {"observations": observations, "notes": notes}
