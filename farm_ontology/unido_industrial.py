"""UNIDO industrial statistics header.

One database description from the page that was already opened. The
stored record is that header. The publisher is UNIDO. The product is
The UNIDO Industrial Statistics (INDSTAT) Revision 4 Database. The citation stays on
https://stat.unido.org/data/database-descriptions.
The page title is Database Descriptions | UNIDO Statistics Portal.
The product heading also prints INDSTAT Revision 4.
https://stat.unido.org/ is not the citation.
The period sentence is the database span, not one observation.
The unit sentence is the printed price basis, not a stored value.
Worldwide is the printed coverage word.
About 110 economies is the same coverage sentence and is not a second area.
The database is updated annually.
The (Access database) link was not opened.
Kind was not opened.
Do not relabel this header as an index, a yield, a forecast, or a completed harvest.
No index value, growth rate, or trade is stored.
Licence text was not printed.
The header is not marked public domain.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

UNIDO_INDUSTRIAL_URL = "https://stat.unido.org/data/database-descriptions"

PUBLISHER = "UNIDO"
PRODUCT = "The UNIDO Industrial Statistics (INDSTAT) Revision 4 Database"
PERIOD = "annual data from 2005 to 2020"
UNIT = "current prices, in both national currency and United States dollars"
ADMINISTRATIVE_AREA = "worldwide"
NOT_OPENED = "the field was not opened"
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
            "an industrial statistics header is not a settlement, a yield, "
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
            "period, unit, administrative_area, and kind are not replaced"
        )
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != UNIDO_INDUSTRIAL_URL:
        raise ValueError("citation_url is not the opened database description")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": UNIT,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": NOT_OPENED,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "unido-industrial.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
