"""Stats SA manufacturing production and sales header.

One report from the September 2026 release that was already opened. The
stored record is the printed header plus the copyright sentence. That
sentence is not a financial-use grant. The opened release is statistical
release P3041.2, marked (Preliminary), embargoed until 10 November 2026
13:00. The letterhead prints Private Bag X44, Pretoria, 0001, South
Africa. The release says Stats SA conducts a monthly survey of the
manufacturing industry. The base and the rand unit are printed labels.
No index value and no rand amount is stored. The October 2026 PDF was
not opened because it returned 404. A bulk history file was not opened.
A separate licence name was not printed. The release is not a quantity
of goods and is not a trading right. This module is not called from a
field save.
"""

from __future__ import annotations

import json
from pathlib import Path

STATS_SA_MANUFACTURING_URL = (
    "https://www.statssa.gov.za/publications/P30412/P30412September2026.pdf"
)

PUBLISHER = "Statistics South Africa (Stats SA)"
PRODUCT = "Manufacturing: Production and sales"
PERIOD = "September 2026"
UNIT = "(Base: 2019=100) and (R million)"
ADMINISTRATIVE_AREA = "South Africa"
KIND = "report"
COPYRIGHT_NOTICE = (
    "Stats SA has copyright on this publication. Users may apply the "
    "information as they wish, provided that they acknowledge Stats SA as "
    "the source of the basic data wherever they process, apply, utilise, "
    "publish or distribute the data; and also that they specify that the "
    "relevant application and analysis (where applicable) result from their "
    "own processing of the data."
)
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
})


def _stores_number(label) -> bool:
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
        str(label).strip().lower() in FORBIDDEN_LABELS or _stores_number(label)
    ):
        raise ValueError(
            "a Stats SA manufacturing figure is not a settlement, a yield, "
            "a trade, a forecast, an observation, a completed harvest, or a "
            "benchmark, and a number is not stored"
        )
    if (
        period is not None
        or unit is not None
        or administrative_area is not None
        or value is not None
    ):
        raise ValueError("a number is not stored")
    citation = str(citation_url).strip()
    if citation != STATS_SA_MANUFACTURING_URL:
        raise ValueError("citation_url is not the opened September 2026 release")
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
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "stats-sa-manufacturing.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
