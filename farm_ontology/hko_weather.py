"""Hong Kong Observatory forecast header.

One model-chart header from the page that was already opened. The stored
record is that header. The publisher is Hong Kong Observatory(HKO). The
product is HKO Non-Hydrostatic Model. The citation stays on
https://www.hko.gov.hk/en/nhm/prodinfo.htm.
https://www.hko.gov.hk/ is not the citation.
The page heading is Product information.
The document title is Product information｜Hong Kong Observatory(HKO)｜Weather Forecast.
The document title ends with Weather Forecast.
The model row is HKO Non-Hydrostatic Model.
Numerical Weather Prediction Model is the row label, not a second product.
A forecast is not a completed harvest.
Model resolution 10 km is a printed resolution label. It is not the unit and it is not a rainfall amount.
The product-types table cells are labels. No rainfall amount is stored.
Chart area is the row name. The stored area is the printed coordinate pair.
Header and footer scripts were not opened.
Unit was not opened.
Licence text was not printed.
The header is not marked public domain.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

HKO_WEATHER_URL = "https://www.hko.gov.hk/en/nhm/prodinfo.htm"

PUBLISHER = "Hong Kong Observatory(HKO)"
PRODUCT = "HKO Non-Hydrostatic Model"
PERIOD = (
    "Forecast hours 03 to 72 hour in 3-hour interval "
    "(surface Weather forecast from 06 hour); "
    "Update frequency Updated four times daily based on analysis at "
    "00, 06, 12, and 18 UTC (08, 14, 20, and 02 HKT).; "
    "Update time table Updated at 03 HKT, 09 HKT, 15 HKT, 21 HKT everyday."
)
NOT_OPENED = "the field was not opened"
ADMINISTRATIVE_AREA = "8-46.5 N, 85-148 E"
KIND = "forecast"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "observation",
    "completed harvest",
    "public domain",
    "benchmark",
    "index",
    "rainfall amount",
    "10 km",
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
            "a weather forecast header is not a settlement, a yield, a "
            "trade, an observation, a completed harvest, a benchmark, or "
            "an index, and a rainfall amount or a figure is not stored"
        )
    if unit is not None:
        raise ValueError("unit was not opened")
    if period is not None or administrative_area is not None:
        raise ValueError("period and administrative_area are not replaced")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != HKO_WEATHER_URL:
        raise ValueError("citation_url is not the opened product page")
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
    path = folder / "hko-weather.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
