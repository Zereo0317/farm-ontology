"""South African Weather Service forecast header.

One homepage title from the page that was already opened. The stored
record is that title. The publisher is South African Weather Service (SAWS).
The product is Official Weather Forecasts. The citation stays on
https://www.weathersa.co.za/.
The document title is South African Weather Service (SAWS) | Official Weather Forecasts.
South African Weather Service is the site name inside that publisher, not a second publisher.
Get official weather forecasts, warnings and weather information is a description, not a second product.
The body was an empty page shell.
The bundles /assets/index-Dmkf9C-7.js and /assets/index-DvFxhP_Q.css were not unpacked.
Period, unit, area, and licence were not printed.
Last-Modified: Thu, 05 Nov 2026 11:22:38 GMT is a file timestamp, not a forecast period.
The response date Mon, 16 Nov 2026 18:12:38 GMT is not a forecast period.
Do not store a rainfall amount.
A forecast is not a completed harvest.
The header is not marked public domain.
TAMSAT, a news article, and another weather service were not opened.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

SAWS_WEATHER_URL = "https://www.weathersa.co.za/"

PUBLISHER = "South African Weather Service (SAWS)"
PRODUCT = "Official Weather Forecasts"
NOT_OPENED = "the field was not opened"
KIND = "Official Weather Forecasts"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "price",
    "trade",
    "observation",
    "completed harvest",
    "public domain",
    "benchmark",
    "index",
    "rainfall amount",
    "figure",
})


def _stores_figure(label) -> bool:
    return any(character.isdigit() for character in str(label))


def record_series_header(
    directory,
    *,
    citation_url=None,
    label=None,
    period=None,
    unit=None,
    administrative_area=None,
    value=None,
) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and (
        str(label).strip().lower() in FORBIDDEN_LABELS or _stores_figure(label)
    ):
        raise ValueError(
            "a forecast header is not a settlement, a yield, a price, a "
            "trade, an observation, a completed harvest, a benchmark, or "
            "an index, and a rainfall amount or a figure is not stored"
        )
    if period is not None or unit is not None or administrative_area is not None:
        raise ValueError("period, unit, and administrative_area were not opened")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != SAWS_WEATHER_URL:
        raise ValueError("citation_url is not the opened homepage")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": NOT_OPENED,
        "unit": NOT_OPENED,
        "administrative_area": NOT_OPENED,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "saws-weather.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
