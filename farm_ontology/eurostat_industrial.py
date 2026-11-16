"""Eurostat industrial production header.

One navigation label from the response that was already opened. The
stored record is that label. The publisher is Eurostat. The product is
Production in industry - monthly data. The citation stays on
https://ec.europa.eu/eurostat/databrowser-backend/api/public/navtree/en/getCategoryTree/icts/sts?notFullId=true&showProduct=all.
https://ec.europa.eu/eurostat/databrowser/product/page/sts_inpr_m did not print the product title, so it is not the citation.
https://ec.europa.eu/eurostat is not the citation.
The metadata page https://ec.europa.eu/eurostat/cache/metadata/en/sts_esms.htm was not opened.
The folder path Short-term business statistics > Industry > Production in industry was printed in the navigation response.
Period, unit, administrative area, and kind were not opened.
Do not relabel this header as an index, a yield, a forecast, or a completed harvest.
No index value, growth rate, or trade is stored.
Licence text was not opened.
The header is not marked public domain.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

EUROSTAT_INDUSTRIAL_URL = (
    "https://ec.europa.eu/eurostat/databrowser-backend/api/public/navtree/en/"
    "getCategoryTree/icts/sts?notFullId=true&showProduct=all"
)

PUBLISHER = "Eurostat"
PRODUCT = "Production in industry - monthly data"
NOT_OPENED = "the field was not opened"
DATA_BROWSER_PAGE = (
    "https://ec.europa.eu/eurostat/databrowser/product/page/sts_inpr_m"
)
METADATA_PAGE = "https://ec.europa.eu/eurostat/cache/metadata/en/sts_esms.htm"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "forecast",
    "observation",
    "completed harvest",
    "public domain",
    "benchmark",
    "index",
    "index value",
    "growth",
    "growth rate",
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
    kind=None,
    value=None,
) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and (
        str(label).strip().lower() in FORBIDDEN_LABELS or _stores_figure(label)
    ):
        raise ValueError(
            "an industrial production header is not a settlement, a yield, "
            "a trade, a forecast, an observation, a completed harvest, a "
            "benchmark, or an index, and an index value, a growth rate, or "
            "a figure is not stored"
        )
    if (
        period is not None
        or unit is not None
        or administrative_area is not None
        or kind is not None
    ):
        raise ValueError(
            "period, unit, administrative_area, and kind were not opened"
        )
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != EUROSTAT_INDUSTRIAL_URL:
        raise ValueError("citation_url is not the opened navigation response")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": NOT_OPENED,
        "unit": NOT_OPENED,
        "administrative_area": NOT_OPENED,
        "citation_url": citation,
        "kind": NOT_OPENED,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "eurostat-industrial.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
