"""GFS forecast header.

One forecast header from the page that was already opened. The stored
record is that header. The publisher is National Oceanic and Atmospheric
Administration. The product is Global Forecast System. The citation stays on
https://www.emc.ncep.noaa.gov/emc/pages/numerical_forecast_systems/gfs.php.
https://www.emc.ncep.noaa.gov/ is not the citation.
https://www.emc.ncep.noaa.gov/emc/pages/numerical_forecast_systems/ is not the citation.
https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast-system is not the citation.
The NCEI URL returned HTTP 404.
The document title is GFS.
The image title is Global Forecast System.
U.S. Department of Commerce is a printed name, not a second publisher.
NCEP is a printed name inside the product sentence, not the publisher.
EMC Home is a breadcrumb, not the publisher.
Mark Otto, Jacob Thornton, and Bootstrap contributors is a template credit, not the publisher.
The Bootstrap author line is not the publisher.
producing forecasts up to 16 days in advance is the forecast length.
Four times a day is a run cadence, not the period.
Hourly for the first 120 hours, then 3 hourly, is output frequency, not the period.
12 June 2019 is an implementation date, not the period.
22 March 2021 is an implementation date, not the period.
June 12, 2019 is the printed implementation date, not the period.
March 22, 2021 is the printed implementation date, not the period.
13 km is resolution, not the unit.
127 vertical layers are resolution, not the unit.
Global in the product name is the system name, not a selected area.
The disclaimer page was not opened.
The header is not marked public domain.
JavaScript was not unpacked.
Do not store a forecast value.
A forecast is not a completed harvest.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

GFS_FORECAST_URL = (
    "https://www.emc.ncep.noaa.gov/emc/pages/numerical_forecast_systems/gfs.php"
)

PUBLISHER = "National Oceanic and Atmospheric Administration"
PRODUCT = "Global Forecast System"
PERIOD = "up to 16 days"
NOT_OPENED = "the field was not opened"
KIND = "Global Forecast System"
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
    "disclaimer",
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
    if citation != GFS_FORECAST_URL:
        raise ValueError("citation_url is not the opened forecast page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": NOT_OPENED,
        "administrative_area": NOT_OPENED,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "gfs-forecast.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
