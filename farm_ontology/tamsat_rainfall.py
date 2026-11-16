"""TAMSAT rainfall header.

One rainfall-page header from the page that was already opened. The
stored record is that header. The publisher is University of Reading.
The product is TAMSAT Rainfall. The citation stays on
https://ourresearch.reading.ac.uk/tamsat/rainfall/.
https://ourresearch.reading.ac.uk/tamsat/ is not the citation.
https://ourresearch.reading.ac.uk/tamsat/faq-rainfall/ is not the citation.
https://www.reading.ac.uk is not the citation.
TAMSAT Rainfall – TAMSAT is the document title, not a second product.
v3.1 released 1st July 2020 is the printed version, not the period.
The 1983-2012 climatology is not the period.
The time steps are daily, pentadal, dekadal, monthly, and seasonal.
Latency is within 2 days after each pentad.
Spatial resolution 0.0375° is the grid spacing, not the unit.
The variables rfe and rfe_filled are names.
Do not store a rainfall amount.
A rainfall estimate is not a completed harvest and it is not a weather forecast.
The page prints CC BY 4.0 and says the data are released for operational, research and commercial use.
That commercial sentence does not set permits_financial_use to true.
The deed page https://creativecommons.org/licenses/by/4.0/ was named by URL and was not opened as a second product.
© Copyright University of Reading is a copyright line, not public domain.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

TAMSAT_RAINFALL_URL = "https://ourresearch.reading.ac.uk/tamsat/rainfall/"

PUBLISHER = "University of Reading"
PRODUCT = "TAMSAT Rainfall"
PERIOD = "1st January 1983 to present day"
UNIT = "mm"
ADMINISTRATIVE_AREA = (
    "African continent, including Madagascar "
    "(N: 38.025°, S: -35.9625°, W: -19.012°, E:51.975°)"
)
KIND = "rainfall estimate"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "forecast",
    "completed harvest",
    "public domain",
    "benchmark",
    "index",
    "rainfall amount",
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
            "a rainfall estimate is not a settlement, a yield, a trade, "
            "a forecast, a completed harvest, a benchmark, or an index, "
            "and a rainfall amount or a figure is not stored"
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
    if citation != TAMSAT_RAINFALL_URL:
        raise ValueError("citation_url is not the opened rainfall page")
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
    path = folder / "tamsat-rainfall.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
