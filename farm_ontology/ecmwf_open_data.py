"""ECMWF open-data header.

One dataset header from the page that was already opened. The stored
record is that header. The publisher is ECMWF. The product is Open data.
The citation stays on
https://www.ecmwf.int/en/forecasts/datasets/open-data.
https://www.ecmwf.int/ is not the citation.
https://www.ecmwf.int/en/forecasts/datasets is not the citation.
https://doi.org/10.21957/open-data is not the citation.
https://api.open-meteo.com/v1/forecast is not the citation.
The Open-Meteo adapter is not this header.
The document title is Open data | ECMWF.
The h1 is Open data.
© European Centre for Medium-Range Weather Forecasts is a footer line, not a second publisher.
20 October 2026 is a change date, not the period.
The rolling-archive sentence describes forecast runs, not the period.
0.1° and 0.25 degrees are grid resolution, not the unit.
GRIB2 is a file format, not the unit.
For improved global accessibility is about access, not the administrative area.
Forecast steps, parameters, and file-name tokens were not copied.
The product description names a Catalogue of Real-time Products. Those words are not the stored product.
The DOI page was not opened.
Creative Commons CC-BY-4.0 licence is not a right to trade.
This means that the data may be redistributed and used commercially, subject to appropriate attribution. That sentence is not a right to trade.
ECMWF Terms of Use is not a right to trade.
The View licence target was not opened.
The Service Charges page was not opened.
The Service Agreement page was not opened.
The header is not marked public domain.
JavaScript was not unpacked.
Do not store a forecast value.
A forecast is not a completed harvest.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

ECMWF_OPEN_DATA_URL = "https://www.ecmwf.int/en/forecasts/datasets/open-data"

PUBLISHER = "ECMWF"
PRODUCT = "Open data"
NOT_OPENED = "the field was not opened"
KIND = "Open data"
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
    "forecast value",
    "cc-by-4.0",
    "commercially",
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
            "a forecast is not a settlement, a yield, a price, a trade, "
            "a completed harvest, a benchmark, or an index, and a "
            "forecast value or a figure is not stored"
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
    if citation != ECMWF_OPEN_DATA_URL:
        raise ValueError("citation_url is not the opened open-data page")
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
    path = folder / "ecmwf-open-data.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
