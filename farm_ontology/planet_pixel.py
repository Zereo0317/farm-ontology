"""One Planet pixel at the Hokkaido point.

The read is PSScene 20261117_011638_27_2570 at 42.7018152, 142.4071291.
Band values are written only when a response prints them, with that scene
id and that point. The asset call for this scene returned no pixel, so
the printed response writes nothing. No reflectance and no yield are
created. This is not the Biratori field harvest and not a trade.
permits_financial_use stays false. permits_financial_use_test is not
set. Class C stays closed. This module is not called from a field save.
The stored key is not read here and is not written.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

SCENE_ID = "20261117_011638_27_2570"
LATITUDE = "42.7018152"
LONGITUDE = "142.4071291"
NO_PIXEL = "Could not find the requested asset, it may not exist or may not be visible."
FORBIDDEN_LABELS = frozenset(
    {
        "yield",
        "trade",
        "harvest",
        "reflectance",
        "completed harvest",
    }
)


def record_planet_pixel(
    path: Path,
    response_text: str | None = None,
    *,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write printed band values, or write nothing."""

    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or any(character.isdigit() for character in label)
    ):
        raise ValueError("a pixel is not a harvest and not a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    if permits_financial_use_test is not None:
        raise ValueError("permits_financial_use_test is not set")
    if not response_text or not response_text.strip():
        raise ValueError("the API returned no pixel")
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError("the API returned no pixel") from exc
    bands = payload.get("bands") if isinstance(payload, dict) else None
    if not isinstance(bands, dict) or not bands:
        message = NO_PIXEL if isinstance(payload, dict) and payload.get("message") == NO_PIXEL else "the API returned no pixel"
        raise ValueError(message)
    if payload.get("scene_id") != SCENE_ID:
        raise ValueError("the API returned no pixel")
    stored_bands = {}
    for name, value in bands.items():
        if name in FORBIDDEN_LABELS or not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("the API returned no pixel")
        stored_bands[str(name)] = value
    stored = {
        "scene_id": SCENE_ID,
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "bands": stored_bands,
        "not_the_biratori_field_harvest": True,
        "not_a_trade": True,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
