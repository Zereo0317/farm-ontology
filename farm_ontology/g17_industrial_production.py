"""Federal Reserve G.17 industrial production header.

One opened manufacturing series. The stored record is the printed header:
publisher, product, period, and unit. It does not store an index level,
a price, a yield, or a trade. Class C stays closed. This module is not
called from a field save, and it does not download the release page.
"""

from __future__ import annotations

import json
from pathlib import Path

G17_INDUSTRIAL_PRODUCTION_URL = (
    "https://www.federalreserve.gov/releases/g17/current/default.htm"
)

PUBLISHER = "Board of Governors of the Federal Reserve System"
PRODUCT_VERSION = "G.17 Industrial Production and Capacity Utilization"
SERIES = "Industrial production"
PERIOD = "Monthly, release dated 16 October 2026, covering September"
UNIT = "index"
KIND = "observation"
FORBIDDEN_LABELS = frozenset({"settlement", "yield", "trade"})


def record_series_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a G.17 value is not a settlement, a yield, or a trade")
    citation = str(citation_url).strip()
    if citation != G17_INDUSTRIAL_PRODUCTION_URL:
        raise ValueError("citation_url is not the opened G.17 industrial production release")
    header = {
        "publisher": PUBLISHER,
        "product_version": PRODUCT_VERSION,
        "series": SERIES,
        "period": PERIOD,
        "unit": UNIT,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
        "class_c_policy": "closed",
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "g17-industrial-production.json"
    path.write_text(json.dumps(header, indent=2) + "\n", encoding="utf-8")
    return {"file": path.name, "header": header}
