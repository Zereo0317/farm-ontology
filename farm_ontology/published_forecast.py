"""USDA PSD open-marketing-year header.

One published forecast named in the survey note. The stored record is
the printed header: publisher, product, period, and unit. It does not
store a forecast number, a price, a yield, or a trade. A forecast is
not a completed harvest. Class C stays closed. This module is not
called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

PSD_CITATION_URL = "https://apps.fas.usda.gov/psdonline/app/index.html"

PUBLISHER = "United States Department of Agriculture, Foreign Agricultural Service"
PRODUCT_VERSION = "Production, Supply and Distribution (PSD)"
SERIES = "open marketing year"
PERIOD = "Current and coming marketing years"
UNIT = "Country"
KIND = "forecast"
FORBIDDEN_LABELS = frozenset({"harvest", "yield", "settlement", "trade"})


def record_series_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a PSD forecast is not a harvest, a yield, a settlement, or a trade"
        )
    citation = str(citation_url).strip()
    if citation != PSD_CITATION_URL:
        raise ValueError("citation_url is not the opened PSD forecast")
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
    path = folder / "psd-open-marketing-year.json"
    path.write_text(json.dumps(header, indent=2) + "\n", encoding="utf-8")
    return {"file": path.name, "header": header}
