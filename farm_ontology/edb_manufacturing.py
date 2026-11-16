"""EDB monthly manufacturing performance header.

One report from the EDB page that was already opened. The stored record
is the printed header. The citation stays on
https://www.edb.gov.sg/en/corporate-news/monthly-manufacturing-performance.
SingStat's manufacturing page prints that statistics on the manufacturing
sector are compiled by the Economic Development Board, including the
monthly index of industrial production. That sentence is from
https://www.singstat.gov.sg/find-data/explore-data-themes/industry/manufacturing/latest-news-data
and is not the citation. The page title prints Singapore EDB. The address
prints Singapore 179101. The linked Terms of use page was not opened.
The page lists spreadsheet downloads and those files were not opened. A
bulk history file was not opened. Unit was not opened and is not filled.
No index value is stored. The note is not a quantity of goods and is not
a trading right. This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

EDB_MANUFACTURING_URL = (
    "https://www.edb.gov.sg/en/corporate-news/monthly-manufacturing-performance"
)

PUBLISHER = "Singapore Economic Development Board (EDB)"
PRODUCT = "Monthly manufacturing performance (September 2026)"
PERIOD = "September 2026"
UNIT = "the field was not opened"
ADMINISTRATIVE_AREA = "Singapore"
KIND = "report"
COPYRIGHT_NOTICE = "© 2026 Singapore Economic Development Board"
DATELINE = "26 Oct 2026"
LAST_UPDATED = "16 Nov 2026"
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
    "index value",
})


def _stores_index_value(label) -> bool:
    text = str(label).strip()
    if "=" in text:
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
        str(label).strip().lower() in FORBIDDEN_LABELS or _stores_index_value(label)
    ):
        raise ValueError(
            "an EDB manufacturing figure is not a settlement, a yield, "
            "a trade, a forecast, an observation, a completed harvest, or a "
            "benchmark, and an index value is not stored"
        )
    if unit is not None:
        raise ValueError("unit was not opened")
    if (
        period is not None
        or administrative_area is not None
        or value is not None
    ):
        raise ValueError("an index value is not stored")
    citation = str(citation_url).strip()
    if citation != EDB_MANUFACTURING_URL:
        raise ValueError("citation_url is not the opened EDB manufacturing page")
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
        "dateline": DATELINE,
        "last_updated": LAST_UPDATED,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "edb-manufacturing.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
