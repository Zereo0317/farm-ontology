"""OPEC Monthly Oil Market Report header.

One report from the publications page that was already opened. The
stored record is the printed header. The January 2025 PDF disclaimer
says the report is informational, is not a substitute for professional
advice, and is not a benchmark or an input to a benchmark. Full
reproduction needs the Secretariat's written permission. Educational
and other non-commercial use is allowed without prior permission if
OPEC is acknowledged as the copyright holder. Balances in the report
include an outlook. That outlook is not scored and is not stored as a
completed supply. It does not store a quantity. This module is not
called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

OPEC_MOMR_URL = "https://www.opec.org/monthly-oil-market-report.html"

PUBLISHER = "Organization of the Petroleum Exporting Countries"
PRODUCT = "Monthly Oil Market Report"
PERIOD = (
    "monthly; the November 2026 issue was the current file when the "
    "publications reader was opened; the public HTML page lists issues back "
    "through 2025 in the portion retrieved; a machine-readable history of "
    "every edition since the report began was not found"
)
UNIT = (
    "narrative and tables on world oil demand, non-OPEC supply, OPEC "
    "production, the balance, stocks, and rigs; no quantity is stored"
)
ADMINISTRATIVE_AREA = (
    "the report's published world and country tables; "
    "this record is not a stored world balance"
)
KIND = "report"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "benchmark",
    "yield",
    "trade",
    "observation",
    "forecast",
    "public domain",
    "completed harvest",
})


def record_series_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "an OPEC report figure is not a settlement, a benchmark, a yield, "
            "a trade, an observation, a forecast, or a completed harvest"
        )
    citation = str(citation_url).strip()
    if citation != OPEC_MOMR_URL:
        raise ValueError("citation_url is not the opened Monthly Oil Market Report page")
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
    path = folder / "monthly-oil-market-report.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
