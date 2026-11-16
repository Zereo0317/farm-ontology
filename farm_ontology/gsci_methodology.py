"""S&P GSCI methodology header.

One methodology from the PDF that was already opened. The stored record
is the printed header. The publisher is S&P Dow Jones Indices. The
product is S&P GSCI Methodology. The kind is Index Methodology. The
citation stays on
https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-gsci.pdf.
https://www.spglobal.com/spdji/en/ is not the citation.
https://www.spglobal.com/spdji/en/methodology/article/sp-gsci-methodology/ is not the citation.
August 2026 is the methodology edition line, not a data period.
Period, unit, and administrative area were not opened.
Redistribution or reproduction needs the prior written permission of S&P Dow Jones Indices LLC.
A licence is required to display, create derivative works of, or distribute anything that uses S&P Dow Jones Indices and/or index data.
No index level, weight, price, or trade is stored.
The methodology is not marked public domain.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

GSCI_METHODOLOGY_URL = (
    "https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-gsci.pdf"
)

PUBLISHER = "S&P Dow Jones Indices"
PRODUCT = "S&P GSCI Methodology"
NOT_OPENED = "the field was not opened"
KIND = "Index Methodology"
EDITION_LINE = "August 2026"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "forecast",
    "observation",
    "completed harvest",
    "public domain",
    "benchmark",
    "price",
    "weight",
    "index level",
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
            "an index methodology is not a settlement, a yield, a trade, a "
            "forecast, an observation, a completed harvest, or a benchmark, "
            "and an index level, weight, price, or figure is not stored"
        )
    if period is not None or unit is not None or administrative_area is not None:
        raise ValueError("period, unit, and administrative_area were not opened")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != GSCI_METHODOLOGY_URL:
        raise ValueError("citation_url is not the opened methodology PDF")
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
    path = folder / "gsci-methodology.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
