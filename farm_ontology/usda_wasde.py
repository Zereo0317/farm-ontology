"""USDA WASDE header.

One forecast from the page that was already opened. The stored record
is the printed header. A separate USDA copyright page was not opened.
The report is a forecast of annual balances and is revised in later
months. It is not scored, and it is not stored as a completed harvest
or as an observation. It does not store a quantity. This module is not
called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

USDA_WASDE_URL = "https://www.usda.gov/oce/commodity-markets/wasde"

PUBLISHER = "World Agricultural Outlook Board, U.S. Department of Agriculture"
PRODUCT = "World Agricultural Supply and Demand Estimates"
PERIOD = (
    "monthly, released at 12:00 p.m. Eastern; the page lists the 2026 and "
    "2027 dates; the November 2026 report was linked from the page; "
    "the first archived edition was not established"
)
UNIT = (
    "annual supply-and-use forecasts for U.S. and world wheat, rice, coarse "
    "grains, oilseeds, and cotton, plus U.S. sugar, meat, poultry, eggs, and "
    "milk, and Mexico's sugar balance; no quantity is stored"
)
ADMINISTRATIVE_AREA = "the published U.S. and world tables; not a farm"
KIND = "forecast"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "observation",
    "completed harvest",
    "public domain",
    "benchmark",
})


def record_series_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a WASDE figure is not a settlement, a yield, a trade, "
            "an observation, a completed harvest, or a benchmark"
        )
    citation = str(citation_url).strip()
    if citation != USDA_WASDE_URL:
        raise ValueError("citation_url is not the opened WASDE page")
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
    path = folder / "world-agricultural-supply-and-demand-estimates.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
