"""JMA daily-forecast reading.

The cited page is

https://www.jma.go.jp/bosai/#lang=en&pattern=forecast.

Its script names the Daily Forecasts map

https://www.jma.go.jp/bosai/map.html#contents=forecast&lang=en.

That map page prints Daily Forecasts as a translation. Its visible text
is a load failure and a loading line. It does not print one forecast
value together with a named area. Nothing is stored. A forecast is
stored only when one sentence prints one named area and one value. No
reproduction sentence is required. A value that is not printed is not
invented. A forecast is not a completed harvest and not a trade.
permits_financial_use stays false. Class C stays closed. This module
does not change the header function that rejects a figure. This module
is not called from a field save.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from farm_ontology.jma_daily import JMA_DAILY_URL
from farm_ontology.jma_local import JMA_LOCAL_URL
from farm_ontology.policy import CLASS_C_POLICY

_FORECAST = re.compile(
    r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)*) forecast is (\d+(?:\.\d+)?)\b"
)
FORBIDDEN_LABELS = frozenset(
    {
        "trade",
        "completed harvest",
        "harvest",
        "rainfall amount",
        "temperature",
        "settlement",
        "yield",
    }
)


def _plain(body: str) -> str:
    text = re.sub(r"<[^>]+>", " ", body.replace("\xa0", " "))
    return " ".join(text.split())


def _printed_forecast(body: str) -> tuple[str, str]:
    found: list[tuple[str, str]] = []
    for piece in re.split(r"(?<!\d)\.\s+", _plain(body)):
        numbers = re.findall(r"\d+(?:\.\d+)?", piece)
        match = _FORECAST.search(piece)
        if match is None or len(numbers) != 1:
            continue
        found.append((match.group(1), match.group(2)))
    if len(found) != 1:
        raise ValueError("the page prints no single forecast value")
    return found[0]


def record_forecast_reading(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    source_url: str | None = None,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write one printed daily-forecast value, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("a forecast is not stored without the cited page")
    if citation_url != JMA_LOCAL_URL:
        raise ValueError("a forecast is not stored for a different citation")
    if source_url not in (None, JMA_DAILY_URL):
        raise ValueError("only the Daily Forecasts page is opened")
    if body is None or body.strip() == "":
        raise ValueError("the page prints no single forecast value")
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
    area, value = _printed_forecast(body)
    stored = {
        "value": value,
        "administrative_area": area,
        "kind": "forecast",
        "citation_url": JMA_LOCAL_URL,
        "forecast_page": JMA_DAILY_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
