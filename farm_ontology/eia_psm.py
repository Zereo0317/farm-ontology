"""EIA Petroleum Supply Monthly header.

One report from the release page that was already opened. The stored
record is the printed header plus EIA's statement on its own
publications. That statement is not permission to trade. The latest
months stay preliminary. This report is not a forecast, a settlement,
a completed supply, or a world balance. It does not store a quantity.
The same page was refetched on 17 November 2026. It prints "With Data
for August 2026" and table titles for supply, stocks, production,
imports, and exports. It prints no quantity with a month, so no figure
is written. Reading the stored record writes no trade.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

EIA_PSM_URL = "https://www.eia.gov/petroleum/supply/monthly/"

PUBLISHER = "U.S. Energy Information Administration"
PRODUCT = "Petroleum Supply Monthly"
PERIOD = (
    "monthly; the page opened was the release with data for August 2026, "
    "release date 30 October 2026, next release 30 November 2026; the landing "
    "page does not state the first year of the continuous file; these monthly "
    "figures are preliminary, and final monthly data appear in Petroleum "
    "Supply Annual, Volume 2"
)
UNIT = (
    "monthly supply, disposition, and ending stocks of crude oil and petroleum "
    "products: production, imports, exports, refinery runs, stocks, and "
    "movements; no quantity is stored"
)
ADMINISTRATIVE_AREA = (
    "the United States and PAD districts; this record is not a world balance"
)
KIND = "report"
COPYRIGHT_STATEMENT = (
    "EIA states that U.S. government publications on its site are in the "
    "public domain and are not subject to copyright, and asks for a dated "
    "acknowledgment. Third-party items on the site can still be protected."
)
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "forecast",
    "observation",
    "completed harvest",
    "benchmark",
})


def record_series_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a Petroleum Supply Monthly figure is not a settlement, a yield, "
            "a trade, a forecast, an observation, a completed harvest, or a benchmark"
        )
    citation = str(citation_url).strip()
    if citation != EIA_PSM_URL:
        raise ValueError("citation_url is not the opened Petroleum Supply Monthly page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": UNIT,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
        "copyright_statement": COPYRIGHT_STATEMENT,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "petroleum-supply-monthly.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}


def read_stored_record(directory) -> dict:
    """Read the stored header. Reading writes no file and no trade."""
    path = Path(directory) / "petroleum-supply-monthly.json"
    header = json.loads(path.read_text(encoding="utf-8"))
    if header.get("permits_financial_use") is not False:
        raise ValueError("permits_financial_use stays false")
    if "trade" in header:
        raise ValueError("a Petroleum Supply Monthly figure is not a trade")
    return header
