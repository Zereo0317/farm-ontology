"""Urakawa temperatures from the printed JMA forecast.

The only file opened is
https://www.jma.go.jp/bosai/forecast/data/forecast/015000.json.
The stored rows are the printed temperature values whose area name is
浦河. The area is 浦河. It is not 平取 and not 日高地方. 室蘭 is not
stored. No temperature is invented. A temperature is a forecast, not a
completed harvest and not a trade. permits_financial_use stays false.
permits_financial_use_test is not set. Class C stays closed. This
module does not change a header function that rejects a number. This
module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

FORECAST_DATA_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/015000.json"
AREA = "浦河"
_TEMPERATURE_KEYS = frozenset(
    {
        "temps",
        "tempsMin",
        "tempsMax",
        "tempsMinUpper",
        "tempsMinLower",
        "tempsMaxUpper",
        "tempsMaxLower",
    }
)
FORBIDDEN_LABELS = frozenset(
    {
        "trade",
        "completed harvest",
        "harvest",
        "yield",
        "平取",
        "日高地方",
        "室蘭",
    }
)


def _rows(document) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []

    def walk(node, times) -> None:
        if isinstance(node, dict):
            current = times
            defines = node.get("timeDefines")
            if isinstance(defines, list):
                current = defines
            area = node.get("area")
            if isinstance(area, dict) and area.get("name") == AREA:
                for key, value in node.items():
                    if key not in _TEMPERATURE_KEYS or not isinstance(value, list):
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
                                "area": AREA,
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


def record_urakawa_temperatures(
    path: Path,
    page_url: str | None,
    body: str | None = None,
    *,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed 浦河 temperature rows, or write nothing."""

    if page_url != FORECAST_DATA_URL:
        raise ValueError("only the 015000 forecast file is opened")
    if body is None or body.strip() == "":
        raise ValueError("the file prints no Urakawa temperature")
    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or label.strip() in FORBIDDEN_LABELS
        or any(character.isdigit() for character in label)
    ):
        raise ValueError("a temperature is a forecast, not a completed harvest and not a trade")
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
        raise ValueError("the file prints no Urakawa temperature") from exc
    rows = _rows(document)
    if not rows:
        raise ValueError("the file prints no Urakawa temperature")
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
