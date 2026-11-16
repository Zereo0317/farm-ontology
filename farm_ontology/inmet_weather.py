"""INMET forecast header.

One forecast-page title from the page that was already opened. The
stored record is that title. The publisher is INMET. The product is
Previsão. The citation stays on
https://previsao.inmet.gov.br/.
https://portal.inmet.gov.br/ is not the citation.
Instituto Nacional de Meteorologia - INMET is the homepage title, not the citation.
http://previsao.inmet.gov.br/ is not the citation.
The forecast page title is INMET :: Previsão.
Previsão para Capitais is menu text, not the product.
A news item whose title also begins with Previsão was not opened.
You need to enable JavaScript to run this app.
The bundles /static/js/2.71e1b5f9.chunk.js and /static/js/main.72b31329.chunk.js were not unpacked.
Period, unit, area, and licence were not printed.
Last-Modified: Tue, 10 Mar 2026 18:10:53 GMT is a file timestamp, not a forecast period.
Do not store a rainfall amount.
A forecast is not a completed harvest.
The header is not marked public domain.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

INMET_WEATHER_URL = "https://previsao.inmet.gov.br/"

PUBLISHER = "INMET"
PRODUCT = "Previsão"
NOT_OPENED = "the field was not opened"
KIND = "Previsão"
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
            "a forecast header is not a settlement, a yield, a trade, an "
            "observation, a completed harvest, a benchmark, or an index, "
            "and a rainfall amount or a figure is not stored"
        )
    if period is not None or unit is not None or administrative_area is not None:
        raise ValueError("period, unit, and administrative_area were not opened")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != INMET_WEATHER_URL:
        raise ValueError("citation_url is not the opened forecast page")
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
    path = folder / "inmet-weather.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
