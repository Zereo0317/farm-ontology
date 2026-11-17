"""JMA precipitation analysis and forecast header.

One page from the address that was fetched. The publisher is Japan Meteorological Agency.
The product is Precipitation Analysis/Forecasts.
The kind is Analysis; Forecasts.
The citation stays on
https://www.jma.go.jp/bosai/en_kaikotan/.
https://www.jma.go.jp/ is not the citation.
https://www.jma.go.jp/bosai/ is not the citation.
https://www.jma.go.jp/bosai/en_kaikotan is not the citation.
en_kaikotan/ is not the citation.
https://www.jma.go.jp/bosai/#lang=en&pattern=forecast is not the citation.
https://www.jma.go.jp/bosai/en_kaikotan/#zoom:5/lat:35.173808/lon:134.011230/colordepth:normal/elements:rasrf&slmcs is not the citation.
https://www.jma.go.jp/bosai/en_kaikotan/#elements:sjfcstmap is not the citation.
The citation is the printed canonical link.
The map-view hash is omitted.
The document title is Japan Meteorological Agency | Analysis and Forecasts of Precipitation.
Precipitation Analysis/Forecasts is the product. Analysis; Forecasts is the kind.
Analysis and Forecasts of Precipitation is the document-title segment, not the product.
Localized Torrential Rain Forecast Map is not the product.
Local Information is the menu document title, not the product.
Information on Disaster Mitigation is the group heading, not a stored field.
The stored period is 1-hour. precipitation; 09:00 JST, 17 November 2026; 09:00; 21:00; 00:00; 03:00; 06:00; 09:00; 11:50; 15:00; 18:00; 21:00; updated every 10 minutes; up to 6 hours ahead; from 7 to 15 hours ahead; updated every hour.
The stored unit is mm/h.
A unit is not a rainfall amount.
Legend scale amounts are not stored.
Administrative area is omitted.
The map subtitle is omitted.
Map source: Geospatial Information Authority of Japan is not stored.
Created by editing GSI Tiles (Digital Topographic Map) is not stored.
2020 is the copyright year on the page. It is not stored.
Do not store a rainfall amount.
Do not store a temperature.
A forecast is not a completed harvest.
An analysis is not a quantity of goods.
An index is not a quantity of goods.
The header is not marked public domain.
permits_financial_use stays false.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

JMA_PRECIPITATION_URL = "https://www.jma.go.jp/bosai/en_kaikotan/"

PUBLISHER = "Japan Meteorological Agency"
PRODUCT = "Precipitation Analysis/Forecasts"
PERIOD = (
    "1-hour. precipitation; "
    "09:00 JST, 17 November 2026; "
    "09:00; "
    "21:00; "
    "00:00; "
    "03:00; "
    "06:00; "
    "09:00; "
    "11:50; "
    "15:00; "
    "18:00; "
    "21:00; "
    "updated every 10 minutes; "
    "up to 6 hours ahead; "
    "from 7 to 15 hours ahead; "
    "updated every hour"
)
UNIT = "mm/h"
KIND = "Analysis; Forecasts"
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
    "position",
    "local information",
    "disaster mitigation",
    "localized torrential rain forecast map",
    "analysis and forecasts of precipitation",
    "mm",
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
        raise ValueError("unit is not replaced")
    if administrative_area is not None:
        raise ValueError("administrative_area is omitted")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != JMA_PRECIPITATION_URL:
        raise ValueError("citation_url is not the fetched page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": UNIT,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "jma-precipitation.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
