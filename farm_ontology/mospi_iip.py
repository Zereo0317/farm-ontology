"""MoSPI Index of Industrial Production header.

One index from the product page that was already opened. The stored
record is the printed header. The latest-release title prints Press
Release on Quick Estimates of all India Index of Industrial Production
(IIP) base year 2022-23 for September 2026. The base year 2022-23 stays
inside that title and is not copied into unit. The same response also
has reference_period 2026. Period stays September 2026. The product
metadata prints The Index of Industrial Production is a quantitative
index. That is why kind is index. It is not a quantity of goods. No
index number is stored. A bulk history file was not opened. The index
is not a trading right. This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

MOSPI_IIP_URL = (
    "https://www.mospi.gov.in/themes/product/54-index-of-industrial-production"
)

PUBLISHER = "Ministry of Statistics and Programme Implementation"
PRODUCT = "Index of Industrial Production"
PERIOD = "September 2026"
UNIT = "the field was not opened"
ADMINISTRATIVE_AREA = "all India"
KIND = "index"
COPYRIGHT_NOTICE = "© 2025 Ministry of Statistics & Programme Implementation"
SOURCE_LINE = (
    "Index of Industrial Production data is available on the e-Sankhyiki "
    "portal developed by the Ministry of Statistics and Programme Implementation."
)
RELEASE_TITLE = (
    "Press Release on Quick Estimates of all India Index of Industrial "
    "Production (IIP) base year 2022-23 for September 2026"
)
PRODUCT_NOTE = "The Index of Industrial Production is a quantitative index."
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "forecast",
    "observation",
    "completed harvest",
    "public domain",
    "benchmark",
    "quantity of goods",
    "trading right",
    "index number",
})


def _stores_index_number(label) -> bool:
    text = str(label).strip().lower()
    if text in {"index number", "base year"}:
        return True
    return any(character.isdigit() for character in text)


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
        str(label).strip().lower() in FORBIDDEN_LABELS or _stores_index_number(label)
    ):
        raise ValueError(
            "an IIP figure is not a settlement, a yield, a trade, a forecast, "
            "an observation, a completed harvest, or a benchmark, and an "
            "index number is not stored"
        )
    if unit is not None:
        raise ValueError("unit was not opened")
    if period is not None or administrative_area is not None or value is not None:
        raise ValueError("an index number is not stored")
    citation = str(citation_url).strip()
    if citation != MOSPI_IIP_URL:
        raise ValueError("citation_url is not the opened IIP product page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": UNIT,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
        "copyright_notice": COPYRIGHT_NOTICE,
        "source_line": SOURCE_LINE,
        "release_title": RELEASE_TITLE,
        "product_note": PRODUCT_NOTE,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "mospi-iip.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
