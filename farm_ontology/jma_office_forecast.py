"""Forecast for the printed JMA area code 015000.

The citation page printed 015000 beside Iburi Hidaka Region. The forecast
page for that code is the only page opened. A value is stored only when
that page prints one forecast value, with the area name and period
printed beside it. The opened forecast document prints many weather
lines, probabilities, and temperatures, so nothing is stored from it.
No temperature or rainfall amount is invented. A forecast is not a
completed harvest and not a trade. permits_financial_use stays false.
permits_financial_use_test is not set. Class C stays closed. This
module does not change the header function that rejects a figure. This
module is not called from a field save.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

FORECAST_PAGE_URL = (
    "https://www.jma.go.jp/bosai/forecast/"
    "#area_type=offices&area_code=015000&lang=en"
)
FORECAST_DATA_URL = (
    "https://www.jma.go.jp/bosai/forecast/data/forecast/015000.json"
)
_PAGES = frozenset({FORECAST_PAGE_URL, FORECAST_DATA_URL})
_VALUE_KEYS = frozenset(
    {
        "weathers",
        "winds",
        "waves",
        "pops",
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
        "rainfall amount",
    }
)


def _printed_values(body: str) -> list[tuple[str, str, str]]:
    try:
        document = json.loads(body)
    except json.JSONDecodeError:
        return []
    found: list[tuple[str, str, str]] = []

    def walk(node, period: str, area: str) -> None:
        if isinstance(node, dict):
            times = node.get("timeDefines")
            next_period = period
            if isinstance(times, list) and times:
                next_period = str(times[0])
            next_area = area
            named = node.get("area")
            if isinstance(named, dict) and named.get("name"):
                next_area = str(named["name"])
            for key, value in node.items():
                if key in _VALUE_KEYS and isinstance(value, list):
                    for index, item in enumerate(value):
                        text = str(item).strip()
                        if text == "":
                            continue
                        when = next_period
                        if isinstance(times, list) and index < len(times):
                            when = str(times[index])
                        found.append((text, next_area, when))
                else:
                    walk(value, next_period, next_area)
        elif isinstance(node, list):
            for item in node:
                walk(item, period, area)

    walk(document, "", "")
    return found


def record_office_forecast(
    path: Path,
    page_url: str | None,
    body: str | None = None,
    *,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write one printed forecast, or write nothing."""

    if page_url not in _PAGES:
        raise ValueError("only the forecast page for 015000 is opened")
    if body is None or body.strip() == "":
        raise ValueError("the page prints no forecast value")
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
    found = _printed_values(body)
    if len(found) != 1:
        raise ValueError("the page prints no single forecast value")
    value, area, period = found[0]
    if not area or not period or value == "015000" or re.fullmatch(r"\d{6}", value):
        raise ValueError("the page prints no single forecast value")
    stored = {
        "value": value,
        "area": area,
        "period": period,
        "citation_url": page_url,
        "kind": "forecast",
        "label": "forecast",
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
