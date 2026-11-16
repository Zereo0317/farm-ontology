"""JMA three-hourly forecast header.

One page from the address that was fetched. The stored record is the
printed document-title segment. The publisher is Japan Meteorological
Agency. The product is Distribution/Three-hourly Forecasts. The
citation stays on
https://www.jma.go.jp/bosai/en_wdist/.
https://www.jma.go.jp/ is not the citation.
https://www.jma.go.jp/jma/indexe.html is not the citation.
https://www.jma.go.jp/jma/kokusai/multi.html is not the citation.
https://www.jma.go.jp/bosai/#lang=en&pattern=forecast is not the citation.
https://www.jma.go.jp/bosai/map.html#contents=forecast&lang=en is not the citation.
https://www.jma.go.jp/bosai/en_wdist is not the citation.
https://www.jma.go.jp/jma/en/copyright.html was not opened.
The document title is Japan Meteorological Agency | Distribution/Three-hourly Forecasts.
Distribution/Three-hourly Forecasts is the document-title segment. It is the product and the kind.
Forecasts is not the kind.
Three-hourly Forecasts is the contents control, not a second kind.
Weather is the map-title cell, not the product.
気象庁 is a printed name, not a second publisher.
The stored period is Valid for 06-09 JST, 17 November; Updated at 05 JST, 17 November 2026.
The slider hours 15, 21, and 03 are not the period.
5 km x 5 km is the grid size, not a unit.
300 km is the map scale, not a unit.
Unit is omitted.
Administrative area is omitted.
Japan inside the publisher name is not an administrative area.
Geospatial Information Authority of Japan is an organization name, not the administrative area.
Local Information was not opened.
Daily Forecasts was not opened.
Two-week Temperature Forecast was not opened.
Seasonal Forecasts was not opened.
Do not store a rainfall amount.
Do not store a temperature number.
A forecast is not a completed harvest.
An index is not a quantity of goods.
The header is not marked public domain.
permits_financial_use stays false.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

JMA_THREE_HOURLY_URL = "https://www.jma.go.jp/bosai/en_wdist/"

PUBLISHER = "Japan Meteorological Agency"
PRODUCT = "Distribution/Three-hourly Forecasts"
PERIOD = (
    "Valid for 06-09 JST, 17 November; "
    "Updated at 05 JST, 17 November 2026"
)
KIND = "Distribution/Three-hourly Forecasts"
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
    "forecasts",
    "three-hourly forecasts",
    "weather",
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
            "trade, or a completed harvest, and a rainfall amount, a "
            "temperature, or a figure is not stored"
        )
    if period is not None:
        raise ValueError("period is not replaced")
    if unit is not None:
        raise ValueError("unit is omitted")
    if administrative_area is not None:
        raise ValueError("administrative_area is omitted")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != JMA_THREE_HOURLY_URL:
        raise ValueError("citation_url is not the fetched page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "jma-three-hourly.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
