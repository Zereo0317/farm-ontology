"""Hidaka rows from the printed JMA forecast for area code 015000.

The only file opened is
https://www.jma.go.jp/bosai/forecast/data/forecast/015000.json.
No area name in that file contains 平取. The stored rows are the
printed forecast values for 日高地方, the Hidaka portion of the Iburi
Hidaka forecast. Each row keeps the printed area, time, and value.
A forecast is not a completed harvest and not a trade.
permits_financial_use stays false. permits_financial_use_test is not
set. Class C stays closed. This module does not change a header
function that rejects a number. This module is not called from a
field save.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

FORECAST_DATA_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/015000.json"
FORBIDDEN_LABELS = frozenset(
    {
        "trade",
        "completed harvest",
        "harvest",
        "yield",
    }
)


def _area_names(node) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        area = node.get("area")
        if isinstance(area, dict) and area.get("name"):
            found.append(str(area["name"]))
        for value in node.values():
            found.extend(_area_names(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_area_names(item))
    return found


def _keeps(name: str, biratori: bool) -> bool:
    if biratori:
        return "平取" in name
    return "日高" in name and "胆振" not in name


def _rows(document) -> list[dict[str, str]]:
    names = _area_names(document)
    biratori = any("平取" in name for name in names)
    found: list[dict[str, str]] = []

    def walk(node, times) -> None:
        if isinstance(node, dict):
            current = times
            defines = node.get("timeDefines")
            if isinstance(defines, list):
                current = defines
            area = node.get("area")
            if isinstance(area, dict) and _keeps(str(area.get("name", "")), biratori):
                name = str(area["name"])
                for key, value in node.items():
                    if not isinstance(value, list):
                        continue
                    for index, item in enumerate(value):
                        if isinstance(item, (dict, list)) or item is None:
                            continue
                        text = str(item).strip()
                        if text == "":
                            continue
                        if not isinstance(current, list) or index >= len(current):
                            continue
                        found.append(
                            {
                                "area": name,
                                "time": str(current[index]),
                                "series": key,
                                "value": text,
                                "kind": "forecast",
                                "label": "forecast",
                            }
                        )
            for value in node.values():
                walk(value, current)
        elif isinstance(node, list):
            for item in node:
                walk(item, times)

    walk(document, None)
    return found


def record_hidaka_rows(
    path: Path,
    page_url: str | None,
    body: str | None = None,
    *,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed Hidaka rows, or the 平取 rows when those are printed."""

    if page_url != FORECAST_DATA_URL:
        raise ValueError("only the 015000 forecast file is opened")
    if body is None or body.strip() == "":
        raise ValueError("the file prints no forecast row")
    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or any(character.isdigit() for character in label)
    ):
        raise ValueError("a forecast is not a completed harvest and not a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    if permits_financial_use_test is not None:
        raise ValueError("permits_financial_use_test is not set")
    try:
        document = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError("the file prints no forecast row") from exc
    rows = _rows(document)
    if not rows:
        raise ValueError("the file prints no forecast row")
    stored = {
        "rows": rows,
        "citation_url": FORECAST_DATA_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
