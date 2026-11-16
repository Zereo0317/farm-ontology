"""EIA Short-Term Energy Outlook header.

One forecast from the release page that was already opened. The stored
record is the printed header plus EIA's statement on its own
publications. That statement is not permission to trade. The outlook is
not scored, and it is not stored as a completed supply, an observation,
or a settlement. A point-in-time store of past vintages was not
established. It does not store a price or a quantity. This module is
not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

EIA_STEO_URL = "https://www.eia.gov/outlooks/steo/"

PUBLISHER = "U.S. Energy Information Administration"
PRODUCT = "Short-Term Energy Outlook"
PERIOD = (
    "monthly; the page opened was the 10 November 2026 release, which says "
    "the forecast was completed on 5 November 2026 and does not specifically "
    "account for market events after that day; the next release date printed "
    "on that page is 8 December 2026; a complete archive of past forecast "
    "vintages was not inventoried"
)
UNIT = (
    "a monthly outlook for energy supply, inventories, and prices, including "
    "petroleum; no price and no quantity is stored"
)
ADMINISTRATIVE_AREA = (
    "the outlook's published coverage; this record is not a stored world balance"
)
KIND = "forecast"
COPYRIGHT_STATEMENT = (
    "EIA states that U.S. government publications on its site are in the "
    "public domain and are not subject to copyright, and asks for a dated "
    "acknowledgment. Third-party items on the site can still be protected."
)
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "observation",
    "completed harvest",
    "benchmark",
})


def record_series_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a Short-Term Energy Outlook figure is not a settlement, a yield, "
            "a trade, an observation, a completed harvest, or a benchmark"
        )
    citation = str(citation_url).strip()
    if citation != EIA_STEO_URL:
        raise ValueError("citation_url is not the opened Short-Term Energy Outlook page")
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
    path = folder / "short-term-energy-outlook.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
