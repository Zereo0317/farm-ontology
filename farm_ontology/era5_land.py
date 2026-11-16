"""ERA5-Land reanalysis header.

One dataset header from the page that was already opened. The stored
record is that header. The publisher is Copernicus C3S. The product is
ERA5-Land hourly data from 1950 to present. The citation stays on
https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview.
https://cds.climate.copernicus.eu/ is not the citation.
https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land is not the citation.
The document title is ERA5-Land hourly data from 1950 to present.
ECMWF, the European Union, CDS, and Climate Data Store are printed names, not a second publisher.
Europe's eyes on Earth is logo alt text, not the administrative area.
January 1950 to present is the temporal coverage.
from 1950 to present is the title phrase, not a second period.
Temporal coverage: Past is not the period.
several decades is not the period.
2019-07-12 is the publication date, not the period.
2026-11-16 is the update date, not the period.
0.1° and 9 km are resolution, not the unit.
Hourly is the temporal resolution already named in the product, not a second period.
GRIB is the file format, not the unit.
Soil layers in centimetres are not the unit.
Horizontal coverage is the printed label for Global.
Spatial coverage: Global is the keywords line for the same area.
The ECMWF Confluence page was not opened.
The CC-BY licence button was printed, and the licence text behind it was not opened, so it is not a grant.
Terms of Use is a footer link, not a licence grant.
The header is not marked public domain.
JavaScript was not unpacked.
Do not store a copied value.
A reanalysis is not a completed harvest.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

ERA5_LAND_URL = (
    "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview"
)

PUBLISHER = "Copernicus C3S"
PRODUCT = "ERA5-Land hourly data from 1950 to present"
PERIOD = "January 1950 to present"
NOT_OPENED = "the field was not opened"
ADMINISTRATIVE_AREA = "Global"
KIND = "Reanalysis"
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
    "copied value",
    "cc-by",
    "cc-by licence",
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
            "a reanalysis is not a settlement, a yield, a price, a "
            "trade, a forecast, a completed harvest, a benchmark, or "
            "an index, and a copied value or a figure is not stored"
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
    if citation != ERA5_LAND_URL:
        raise ValueError("citation_url is not the opened dataset page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": NOT_OPENED,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "era5-land.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
