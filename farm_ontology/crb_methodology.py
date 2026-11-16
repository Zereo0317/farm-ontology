"""FTSE/CoreCommodity CRB methodology header.

One methodology from the PDF that was already opened. The stored record
is the printed header. The publisher is FTSE International Limited. The
product is FTSE/CoreCommodity CRB® Index Methodology. The kind is
Methodology. The citation stays on
https://www.lseg.com/content/dam/ftse-russell/en_us/documents/ground-rules/ftse-corecommodity-crb-index-methodology.pdf.
https://www.lseg.com/ is not the citation.
https://www.lseg.com/en/ftse-russell/indices/commodity-indices is not the citation.
May 2026 and Effective Date 08 May 2026 are document dates, not a data period.
v1.2 is a document version, not an index level.
Document Classification: Public is the cover label and is not public domain.
Period, unit, and administrative area were not opened.
No part may be reproduced without the prior written permission of the applicable member of LSEG.
Use and distribution of LSEG data requires a licence from LSEG and/or its licensors.
The document says it is not investment advice and that indices cannot be invested in directly.
No index level, weight, price, or trade is stored.
The methodology is not marked public domain.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

CRB_METHODOLOGY_URL = (
    "https://www.lseg.com/content/dam/ftse-russell/en_us/documents/ground-rules/"
    "ftse-corecommodity-crb-index-methodology.pdf"
)

PUBLISHER = "FTSE International Limited"
PRODUCT = "FTSE/CoreCommodity CRB\u00ae Index Methodology"
NOT_OPENED = "the field was not opened"
KIND = "Methodology"
DOCUMENT_DATES = ("May 2026", "08 May 2026")
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
            "a methodology is not a settlement, a yield, a trade, a forecast, "
            "an observation, a completed harvest, or a benchmark, and an "
            "index level, weight, price, or figure is not stored"
        )
    if period is not None or unit is not None or administrative_area is not None:
        raise ValueError("period, unit, and administrative_area were not opened")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != CRB_METHODOLOGY_URL:
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
    path = folder / "crb-methodology.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
