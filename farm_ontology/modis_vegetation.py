"""MODIS vegetation-index header.

One catalog header from the page that was already opened. The stored
record is that header. The publisher is Earth Science Data Systems, NASA.
The product is MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061.
The citation stays on
https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13q1-061.
https://www.earthdata.nasa.gov/ is not the citation.
https://lpdaac.usgs.gov/products/mod13q1v061/ is not the citation.
https://earthdata.nasa.gov/data/catalog/lpcloud-mod13q1-061 is not the citation.
The document title is MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061.
Land Processes DAAC, NASA Earthdata, and NASA Home are printed names, not a second publisher.
The Goddard Space Flight Center line is a data partner, not a second publisher.
The GSFC MOD13 page was not opened.
2000-02-18 to Present is the temporal extent.
16 Day is temporal resolution, not a second period.
every 16 days is a cadence, not the period.
2021-02-16 is a catalogue date, not the period.
The response date Mon, 16 Nov 2026 18:26:11 GMT is not the period.
NDVI is the stored unit.
EVI is a layer name, not a pixel value, and it does not replace NDVI.
Julian day, Rank, and N/A are other unit cells, not the stored unit.
250 Meters is resolution, not the unit.
HDF-EOS2 is the data format, not the unit.
Fill values, valid ranges, and scale factors are not stored.
Location prints GLOBAL for the same area.
Spatial extent bounds are not a second area.
This dataset is openly shared, without restriction, in accordance with the EOSDIS Data Use and Citation Guidance.
That sentence is not a right to trade.
The EOSDIS guidance page was not opened.
The header is not marked public domain.
JavaScript was not unpacked.
Do not store a pixel value.
A vegetation index is not a completed harvest.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

MODIS_URL = "https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13q1-061"

PUBLISHER = "Earth Science Data Systems, NASA"
PRODUCT = "MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061"
PERIOD = "2000-02-18 to Present"
UNIT = "NDVI"
ADMINISTRATIVE_AREA = "Global"
KIND = "Vegetation Indices"
NOT_OPENED = "the field was not opened"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "price",
    "trade",
    "forecast",
    "completed harvest",
    "public domain",
    "benchmark",
    "index",
    "index value",
    "pixel value",
    "evi",
    "without restriction",
    "openly shared",
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
    permits_financial_use=None,
) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and (
        str(label).strip().lower() in FORBIDDEN_LABELS or _stores_figure(label)
    ):
        raise ValueError(
            "a vegetation index is not a settlement, a yield, a price, "
            "a trade, a forecast, a completed harvest, a benchmark, or "
            "an index, and a pixel value or a figure is not stored"
        )
    if period is not None or unit is not None or administrative_area is not None:
        raise ValueError(
            "period, unit, and administrative_area are not replaced"
        )
    if value is not None:
        raise ValueError("a figure is not stored")
    if permits_financial_use is not None:
        raise ValueError("permits_financial_use is false")
    citation = str(citation_url).strip()
    if citation != MODIS_URL:
        raise ValueError("citation_url is not the opened catalog page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": UNIT,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "modis-vegetation.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
