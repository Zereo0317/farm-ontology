"""Census M3 manufacturers' shipments header.

One survey from the page that was already opened. The stored record is
the printed header. A separate copyright page was not opened. New
orders are a survey of orders. They are not a forecast and not a
futures settlement. Every current month stays preliminary. It does not
store a dollar figure. This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

CENSUS_M3_URL = "https://www.census.gov/manufacturing/m3/index.html"

PUBLISHER = "U.S. Census Bureau"
PRODUCT = "Manufacturers' Shipments, Inventories, and Orders"
PERIOD = (
    "monthly; the dataset list showed M3-mf.zip last updated 3 November 2026; "
    "the public time-series view of total manufacturing shipments displays "
    "years beginning in 1992; every current-month estimate is preliminary "
    "and is superseded later"
)
UNIT = (
    "monthly value of shipments, inventories, new orders, and unfilled orders; "
    "no dollar figure is stored"
)
ADMINISTRATIVE_AREA = "United States manufacturing"
KIND = "survey"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "forecast",
    "public domain",
    "observation",
    "completed harvest",
    "futures settlement",
})


def record_series_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a Census M3 figure is not a settlement, a yield, a trade, "
            "a forecast, a futures settlement, an observation, "
            "or a completed harvest"
        )
    citation = str(citation_url).strip()
    if citation != CENSUS_M3_URL:
        raise ValueError("citation_url is not the opened M3 page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": UNIT,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "manufacturers-shipments-inventories-and-orders.json"
    path.write_text(json.dumps(header, indent=2) + "\n", encoding="utf-8")
    return {"file": path.name, "header": header}
