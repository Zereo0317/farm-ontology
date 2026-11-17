"""Two printed Planet scene headers.

One search is the point 42.7018152, 142.4071291. The other search sends
the China extent 73.66 E, 18.16 N to 135.05 E, 53.56 N as its geometry
filter. That extent is not a farm coordinate. The stored key is not read here
and is not written. A scene id, item type, and acquired time are stored
only when the response prints them. A refused region stores no scene.
No pixel, reflectance, or yield is stored. Neither result is the
Biratori field harvest or a trade. permits_financial_use stays false.
permits_financial_use_test is not set. Class C stays closed. This
module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

HOKKAIDO_LATITUDE = "42.7018152"
HOKKAIDO_LONGITUDE = "142.4071291"
SCENE_FIELDS = ("scene_id", "item_type", "acquired")
FORBIDDEN_LABELS = frozenset(
    {
        "yield",
        "trade",
        "harvest",
        "pixel",
        "reflectance",
        "completed harvest",
    }
)


def _region(name: str, payload: dict) -> dict:
    stored = {"region": name}
    if name == "hokkaido":
        stored["search"] = "point"
        stored["latitude"] = HOKKAIDO_LATITUDE
        stored["longitude"] = HOKKAIDO_LONGITUDE
        stored["not_the_biratori_field_harvest"] = True
    else:
        stored["search"] = "country extent"
        stored["not_a_farm_coordinate"] = True
    stored["not_a_trade"] = True
    status = payload.get("http_status")
    if isinstance(status, int):
        stored["http_status"] = status
    if status == 200 and payload.get("feature_count"):
        printed = {
            field: payload[field]
            for field in SCENE_FIELDS
            if isinstance(payload.get(field), str) and payload[field].strip()
        }
        if len(printed) == len(SCENE_FIELDS):
            stored.update(printed)
    return stored


def record_planet_scenes(
    path: Path,
    response_text: str | None = None,
    *,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write printed scene headers, or write nothing."""

    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or any(character.isdigit() for character in label)
    ):
        raise ValueError("a scene header is not a harvest and not a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    if permits_financial_use_test is not None:
        raise ValueError("permits_financial_use_test is not set")
    if not response_text or not response_text.strip():
        raise ValueError("the response prints no scene")
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError("the response prints no scene") from exc
    regions = []
    for name in ("hokkaido", "china"):
        region = payload.get(name)
        if isinstance(region, dict):
            regions.append(_region(name, region))
    if not regions:
        raise ValueError("the response prints no scene")
    stored = {
        "regions": regions,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
