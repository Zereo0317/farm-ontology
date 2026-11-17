"""JMA snow analysis and forecast header.

One page from the address that was fetched. The publisher is Japan Meteorological Agency.
The product is Snow Analysis/Forecasts.
The kind is Analysis; Forecasts.
The citation stays on
https://www.jma.go.jp/bosai/en_snow/.
https://www.jma.go.jp/ is not the citation.
https://www.jma.go.jp/bosai/ is not the citation.
https://www.jma.go.jp/bosai/en_snow is not the citation.
en_snow/ is not the citation.
https://www.jma.go.jp/bosai/#lang=en&pattern=forecast is not the citation.
https://www.jma.go.jp/bosai/en_snow/#area_type=japan&area_code=010000 is not the citation.
https://www.jma.go.jp/bosai/en_kaikotan/ is not the citation.
The citation is the printed canonical link.
The map-view hash is omitted.
The document title is Japan Meteorological Agency | Analysis and Forecasts of Snow.
Snow Analysis/Forecasts is the product. Analysis; Forecasts is the kind.
Analysis and Forecasts of Snow is the document-title segment, not the product.
Snow depth is the map title line, not a stored field.
Local Information is the menu document title, not the product.
Information on Disaster Mitigation is the group heading, not a stored field.
The stored period is 08 JST, 17 November 2026; 08 JST; 09; 12; 15; 18; 21; 00; 03; 06; 09; 12; periods of 3, 6, 12, 24, 48 and 72 hours.
The stored unit is cm; 300 km.
A unit is not a snowfall amount.
Legend scale amounts are not stored.
Administrative area is omitted.
area_type=japan and area_code=010000 are not an administrative area.
Map source: Geospatial Information Authority of Japan is not stored.
Created by editing GSI Tiles (Digital Topographic Map) is not stored.
2019 is the copyright year on the page. It is not stored.
Do not store a snowfall amount.
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

JMA_SNOW_URL = "https://www.jma.go.jp/bosai/en_snow/"

PUBLISHER = "Japan Meteorological Agency"
PRODUCT = "Snow Analysis/Forecasts"
PERIOD = (
    "08 JST, 17 November 2026; "
    "08 JST; "
    "09; "
    "12; "
    "15; "
    "18; "
    "21; "
    "00; "
    "03; "
    "06; "
    "09; "
    "12; "
    "periods of 3, 6, 12, 24, 48 and 72 hours"
)
UNIT = "cm; 300 km"
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
    "snowfall amount",
    "rainfall amount",
    "temperature",
    "figure",
    "position",
    "local information",
    "disaster mitigation",
    "snow depth",
    "analysis and forecasts of snow",
    "cm",
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
            "trade, or a completed harvest, and a snowfall amount, a "
            "rainfall amount, a temperature, or a figure is not stored"
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
    if citation != JMA_SNOW_URL:
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
    path = folder / "jma-snow.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
