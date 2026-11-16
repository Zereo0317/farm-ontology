"""C&SD industrial production index header.

One index from the subject page that was already opened. The stored
record is the printed product line. The page heading is Manufacturing,
Energy Supply and Waste Management. The publisher name is the title of
https://www.censtatd.gov.hk/en/. The citation stays on
https://www.censtatd.gov.hk/en/scode310.html. A parenthetical figure on
the product line was not copied. The linked web table page loaded with
the printed heading Web Table only. Table 610-65001 was not printed as
a title. Period, unit, administrative area, and a copyright sentence
were not opened. A bulk history file was not opened. No figure is
stored. The index is not a quantity of goods and is not a trading
right. This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

CSD_INDUSTRIAL_URL = "https://www.censtatd.gov.hk/en/scode310.html"

PUBLISHER = "Census and Statistics Department"
PRODUCT = (
    "Index of Industrial Production for Manufacturing and Waste Management Sectors"
)
NOT_OPENED = "the field was not opened"
KIND = "index"
PAGE_HEADING = "Manufacturing, Energy Supply and Waste Management"
PUBLISHER_TITLE_URL = "https://www.censtatd.gov.hk/en/"
WEB_TABLE_HEADING = "Web Table"
TABLE_NOT_A_TITLE = "610-65001"
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
            "an industrial production index figure is not a settlement, a "
            "yield, a trade, a forecast, an observation, a completed harvest, "
            "or a benchmark, and a figure is not stored"
        )
    if period is not None or unit is not None or administrative_area is not None:
        raise ValueError("period, unit, and administrative_area were not opened")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != CSD_INDUSTRIAL_URL:
        raise ValueError("citation_url is not the opened subject page")
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
    path = folder / "csd-industrial.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
