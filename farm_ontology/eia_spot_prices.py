"""Two EIA spot-price cells from the printed daily prices page.

The page opened on 17 Nov 2026 is:

https://www.eia.gov/todayinenergy/prices.php

The page date prints November 16, 2026. In the table "Select Spot
Prices for Delivery Today", the Louisiana row prints natural gas 3.26
under ($/million Btu) and electricity 29.75 under ($/MWh). The futures table is not stored. A cell that prints NA is not stored. The spark spread is not stored.
permits_financial_use stays false. Class C stays closed. A missing
citation writes nothing. These cells are not a settlement and not a
trade.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

EIA_URL = "https://www.eia.gov/todayinenergy/prices.php"

PAGE_DATE = "November 16, 2026"
TABLE = "Select Spot Prices for Delivery Today"
CELLS = (
    {
        "region": "Louisiana",
        "product": "Natural Gas",
        "value": 3.26,
        "unit": "$/million Btu",
    },
    {
        "region": "Louisiana",
        "product": "Electricity",
        "value": 29.75,
        "unit": "$/MWh",
    },
)

FORBIDDEN_LABELS = frozenset(
    {
        "futures",
        "settlement",
        "trade",
        "na",
        "yield",
        "harvest",
        "completed harvest",
    }
)


def record_eia_spot_prices(
    path: Path,
    citation_url: str | None,
    *,
    cells: object = None,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed Louisiana spot cells, or write nothing."""

    if citation_url is None or citation_url.strip() == "":
        raise ValueError("a spot cell is not stored without a citation_url")
    if citation_url != EIA_URL:
        raise ValueError("a spot cell is not stored for a different citation")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a spot cell is not a futures cell, settlement, or trade")
    if any(item is not None for item in (cells, permits_financial_use, class_c_policy)):
        raise ValueError("a spot cell is not stored with a different value")
    stored = [dict(cell) for cell in CELLS if cell["value"] != "NA"]
    if not stored:
        raise ValueError("an NA cell is not stored")
    header = {
        "page_date": PAGE_DATE,
        "table": TABLE,
        "cells": stored,
        "citation_url": EIA_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
