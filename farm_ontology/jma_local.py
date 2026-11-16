"""JMA local-information header.

One page from the address that was fetched. The stored record is the
printed document-title segment. The publisher is Japan Meteorological
Agency. The product is Local Information. The citation stays on
https://www.jma.go.jp/bosai/#lang=en&pattern=forecast.
https://www.jma.go.jp/ is not the citation.
https://www.jma.go.jp/jma/indexe.html is not the citation.
https://www.jma.go.jp/jma/kokusai/multi.html is not the citation.
The page did not print a separate canonical URL.
The document title is Japan Meteorological Agency | Local Information.
Local Information is the document-title segment. It is not one of the forecast menu titles.
気象庁 is a printed name, not a second publisher.
Weather is the group name, not the product.
Daily Forecasts was not opened.
Three-hourly Forecasts was not opened.
Two-week Temperature Forecast was not opened.
Seasonal Forecasts was not opened.
Localized Torrential Rain Forecast Map was not opened.
Precipitation Analysis/Forecasts was not opened.
Snow Analysis/Forecasts was not opened.
Marine Warnings/Forecasts was not opened.
Distribution Marine Forecasts was not opened.
Volcanic Ash Fall Forecasts was not opened.
Daily, Three-hourly, Two-week, and Seasonal are not a period.
Period is omitted.
Unit is omitted.
The stored administrative area is Nationwide information.
Choose Your Town is not the administrative area.
Select Prefecture is not the administrative area.
GPS area identification is not the administrative area.
Hokkaido, Tokyo, and Okinawa are prefecture names. They are not the administrative area.
Do not store a rainfall amount.
Do not store a temperature.
A forecast is not a completed harvest.
The header is not marked public domain.
permits_financial_use stays false.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

JMA_LOCAL_URL = "https://www.jma.go.jp/bosai/#lang=en&pattern=forecast"

PUBLISHER = "Japan Meteorological Agency"
PRODUCT = "Local Information"
ADMINISTRATIVE_AREA = "Nationwide information"
KIND = "Local Information"
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
    "temperature",
    "figure",
    "daily",
    "three-hourly",
    "two-week",
    "seasonal",
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
            "an index, and a rainfall amount, a temperature, or a figure "
            "is not stored"
        )
    if period is not None or unit is not None:
        raise ValueError("period and unit are omitted")
    if administrative_area is not None:
        raise ValueError("administrative_area is not replaced")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != JMA_LOCAL_URL:
        raise ValueError("citation_url is not the fetched page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "jma-local.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
