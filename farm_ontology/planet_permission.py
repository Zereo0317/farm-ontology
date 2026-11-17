"""PSScene permission search at the Hokkaido point.

The search is 42.7018152, 142.4071291. Scene
20261117_011638_27_2570 is skipped. A scene id, acquired time,
publishing stage, quality category, and permission fields are written
only when the response prints them for an item whose permissions are
not empty. This search returned no such item, so it writes nothing.
No scene and no pixel are created. This is not a yield and not a trade.
permits_financial_use stays false. permits_financial_use_test is not
set. Class C stays closed. This module is not called from a field save.
The stored key is not read here and is not written. No asset is
activated or ordered.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

LATITUDE = "42.7018152"
LONGITUDE = "142.4071291"
SKIPPED_SCENE = "20261117_011638_27_2570"
STORED_FIELDS = ("scene_id", "acquired", "publishing_stage", "quality_category", "permissions")
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


def record_planet_permission(
    path: Path,
    response_text: str | None = None,
    *,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write one printed permission item, or write nothing."""

    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or any(character.isdigit() for character in label)
    ):
        raise ValueError("a permission search is not a yield and not a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    if permits_financial_use_test is not None:
        raise ValueError("permits_financial_use_test is not set")
    if not response_text or not response_text.strip():
        raise ValueError("the search returned no item with permissions")
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError("the search returned no item with permissions") from exc
    printed = payload.get("stored") if isinstance(payload, dict) else None
    permissions = printed.get("permissions") if isinstance(printed, dict) else None
    scene_id = printed.get("scene_id") if isinstance(printed, dict) else None
    if (
        not isinstance(permissions, list)
        or not permissions
        or not isinstance(scene_id, str)
        or not scene_id.strip()
        or scene_id == SKIPPED_SCENE
    ):
        checked = payload.get("items_checked") if isinstance(payload, dict) else None
        status = payload.get("http_status") if isinstance(payload, dict) else None
        empty = payload.get("empty_permissions") if isinstance(payload, dict) else None
        if checked == 4950 and status == [200] and empty == 4949:
            raise ValueError(
                "4950 items checked, HTTP 200; 4949 items had empty permissions; "
                "20261117_011638_27_2570 was skipped; no item with permissions was returned"
            )
        raise ValueError("the search returned no item with permissions")
    stored = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "not_a_yield": True,
        "not_a_trade": True,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    for field in STORED_FIELDS:
        if field not in printed or printed[field] in (None, ""):
            continue
        stored[field] = printed[field]
    if "scene_id" not in stored or "permissions" not in stored:
        raise ValueError("the search returned no item with permissions")
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
