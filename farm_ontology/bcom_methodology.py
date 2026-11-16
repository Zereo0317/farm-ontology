"""Bloomberg Commodity Index methodology header.

One methodology from the PDF that was already opened. The stored record
is the printed header. The publisher is Bloomberg Index Services Limited
("BISL"). The product is Bloomberg Commodity Index. The kind is Index
Methodology. The citation stays on
https://assets.bbhub.io/professional/sites/27/BCOM-Methodology-OCT-2026.pdf.
https://www.bloomberg.com/ is not the citation.
https://www.bloomberg.com/professional/products/indices/ is not the citation.
October 2026 is a change date in the document, not a data period.
The London postal address is not an administrative area.
Period, unit, and administrative area were not opened.
The document and its contents may not be forwarded or redistributed without the prior consent of Bloomberg.
The document is factual information rather than financial product advice.
It is not possible to invest directly in an index.
A licensing contact was printed and is not a grant.
A target-weight file was not opened.
The viewer title CONFIDENTIAL is not body text.
No index level, weight, price, or trade is stored.
The methodology is not marked public domain.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

BCOM_METHODOLOGY_URL = (
    "https://assets.bbhub.io/professional/sites/27/BCOM-Methodology-OCT-2026.pdf"
)

PUBLISHER = 'Bloomberg Index Services Limited ("BISL")'
PRODUCT = "Bloomberg Commodity Index"
NOT_OPENED = "the field was not opened"
KIND = "Index Methodology"
CHANGE_DATE = "October 2026"
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
    "london",
    "united kingdom",
    "confidential",
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
    if citation != BCOM_METHODOLOGY_URL:
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
    path = folder / "bcom-methodology.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
