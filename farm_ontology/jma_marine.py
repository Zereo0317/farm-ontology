"""JMA distribution marine forecast header.

One page from the address that was fetched. The publisher is Japan Meteorological Agency.
The product is Distribution Marine Forecasts.
The kind is Forecasts; Wind.
The citation stays on
https://www.jma.go.jp/bosai/en_umimesh/.
https://www.jma.go.jp/ is not the citation.
https://www.jma.go.jp/bosai/ is not the citation.
https://www.jma.go.jp/bosai/en_umimesh is not the citation.
en_umimesh/ is not the citation.
https://www.jma.go.jp/bosai/#lang=en&pattern=forecast is not the citation.
The citation is the printed canonical link.
The map-view hash is omitted because it contains a position.
The document title is Japan Meteorological Agency | Distribution Marine Forecasts.
Distribution Marine Forecasts is the product. Forecasts; Wind is the kind.
Forecasts is not the kind. Wind is not the kind.
海上分布予報 is the icon title, not the product.
Local Information is the menu document title, not the product.
The stored period is Valid for 09 JST, 17 November; Initial time : 03 JST, 17 November; 09 JST, 17; 15 JST, 17; 21 JST, 17; 03 JST, 18.
Unit is omitted.
The stored administrative area is the printed sea-area labels from SEA EAST OF SAKHALIN through SEA SOUTH OF OKINAWA.
Do not store a wave height.
Do not store a wind speed.
Do not store a rainfall amount.
Do not store a temperature.
A forecast is not a completed harvest.
An index is not a quantity of goods.
2019 is the copyright year on the page. It is not stored.
Map source: Geospatial Information Authority of Japan is not stored.
Created by editing GSI Tiles (Digital Topographic Map) is not stored.
The header is not marked public domain.
permits_financial_use stays false.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

JMA_MARINE_URL = "https://www.jma.go.jp/bosai/en_umimesh/"

PUBLISHER = "Japan Meteorological Agency"
PRODUCT = "Distribution Marine Forecasts"
PERIOD = (
    "Valid for 09 JST, 17 November; "
    "Initial time : 03 JST, 17 November; "
    "09 JST, 17; "
    "15 JST, 17; "
    "21 JST, 17; "
    "03 JST, 18"
)
ADMINISTRATIVE_AREA = "; ".join((
    "SEA EAST OF SAKHALIN",
    "SEA WEST OF SAKHALIN",
    "SEA OFF ABASHIRI",
    "SOYA KAIKYO",
    "SEA WEST OF HOKKAIDO",
    "SEA EAST OF HOKKAIDO",
    "SEA OFF KUSHIRO",
    "SEA OFF HIDAKA",
    "TSUGARU KAIKYO",
    "SEA OFF HIYAMA AND TSUGARU",
    "EASTERN SEA OFF SANRIKU",
    "WESTERN SEA OFF SANRIKU",
    "NORTHERN SEA OFF KANTO",
    "SOUTHERN SEA OFF KANTO",
    "SEA OFF SOUTHERN COAST OF MARITIME PROVINCE",
    "SEA OFF AKITA",
    "SEA OFF SADO",
    "SEA OFF NOTO",
    "EASTERN SEA OFF TOKAI",
    "WESTERN SEA OFF TOKAI",
    "SOUTHERN SEA OFF TOKAI",
    "SETONAIKAI",
    "NORTHERN SEA OFF SHIKOKU",
    "SOUTHERN SEA OFF SHIKOKU",
    "NORTHWESTERN PART OF JAPAN SEA",
    "SEA EAST OF OKI SYOTO AND AROUND WAKASA WAN",
    "SEA WEST OF OKI SYOTO",
    "TSUSHIMA KAIKYO",
    "SEA WEST OF CHEJU ISLAND",
    "SEA WEST OF NAGASAKI",
    "SEA SOUTHWEST OF MESHIMA",
    "HYUGA NADA",
    "SEA OFF KAGOSHIMA",
    "SEA AROUND AMAMI",
    "SOUTHERN PART OF EAST CHINA SEA",
    "SEA EAST OF OKINAWA",
    "SEA SOUTH OF OKINAWA",
))
KIND = "Forecasts; Wind"
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
    "wave height",
    "wind speed",
    "rainfall amount",
    "temperature",
    "figure",
    "position",
    "local information",
    "海上分布予報",
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
            "trade, or a completed harvest, and a wave height, a wind "
            "speed, a rainfall amount, a temperature, or a figure is not "
            "stored"
        )
    if period is not None:
        raise ValueError("period is not replaced")
    if unit is not None:
        raise ValueError("unit is omitted")
    if administrative_area is not None:
        raise ValueError("administrative_area is not replaced")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != JMA_MARINE_URL:
        raise ValueError("citation_url is not the fetched page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "jma-marine.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
