"""Current JMA two-week page from the cited English address.

The refetch of

https://www.data.jma.go.jp/cpd/twoweek/en/

returned HTTP 200. The page title prints
Japan Meteorological Agency | Two-week Temperature Forecast.
The page prints no temperature value. The title is stored and no
number is stored. A temperature is not invented. A request that
fails writes nothing.
permits_financial_use stays false. Class C stays closed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

JMA_TWO_WEEK_URL = "https://www.data.jma.go.jp/cpd/twoweek/en/"

FORBIDDEN_LABELS = frozenset(
    {
        "trade",
        "settlement",
        "yield",
        "harvest",
        "completed harvest",
        "rainfall",
    }
)


def _title(body: str) -> str:
    match = re.search(r"<title>\s*([^<]+?)\s*</title>", body)
    if match is None or match.group(1).strip() == "":
        raise ValueError("the page prints no title")
    return " ".join(match.group(1).split())


def _printed_temperature(body: str) -> dict | None:
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*(°C|℃)", body)
    if match is None or not re.search(r"period", body, re.IGNORECASE):
        return None
    value = match.group(1)
    number = float(value) if "." in value else int(value)
    if json.dumps(number) != value:
        number = value
    return {"value": number, "unit": match.group(2)}


def record_jma_two_week_current(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    request_failed: bool = False,
    label: str | None = None,
    value: object = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed title, or a printed temperature, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("the page is not stored without a response")
    if citation_url != JMA_TWO_WEEK_URL:
        raise ValueError("the page is not stored for a different citation")
    if body is None or body.strip() == "":
        raise ValueError("the page prints no title")
    if value is not None or (label is not None and label.strip().lower() in FORBIDDEN_LABELS):
        raise ValueError("a temperature is not invented")
    if permits_financial_use not in (None, False) or class_c_policy not in (None, CLASS_C_POLICY):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    stored = {"title": _title(body)}
    temperature = _printed_temperature(body)
    if temperature is not None:
        stored["value"] = temperature["value"]
        stored["unit"] = temperature["unit"]
    stored["citation_url"] = JMA_TWO_WEEK_URL
    stored["permits_financial_use"] = False
    stored["class_c_policy"] = CLASS_C_POLICY
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
