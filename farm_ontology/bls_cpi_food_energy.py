"""BLS CPI food and energy header.

One index from the CPI data page that was already opened. The stored
record is the printed header. A BLS copyright URL tried in this pass
returned 404, and a direct request to bls.gov returned 403, so the
reuse sentence was not re-read from a live BLS page. The series is not
given a public-domain label. The handbook history page was retrieved.
1913 is program history for a national extension that used food prices
only; it is not the start of the current food and energy item codes.
It does not store an index level. This module is not called from a
field save.
"""

from __future__ import annotations

import json
from pathlib import Path

BLS_CPI_FOOD_ENERGY_URL = "https://www.bls.gov/cpi/data.htm"

PUBLISHER = "U.S. Bureau of Labor Statistics"
PRODUCT = "Consumer Price Index, food and energy"
PERIOD = (
    "monthly program; the start month of the current food and energy item "
    "codes was not read from cu.series; the CPI handbook says BLS began "
    "publishing city indexes in 1919, began regular publication of the U.S. "
    "city average in 1921, and estimated that national index back to 1913; "
    "it also says the 1913-21 national extension used food prices only; that "
    "is program history, not a claim that today's food and energy series "
    "codes are continuous from 1913"
)
UNIT = (
    "CPI for all urban consumers, including all items, food, and energy; the "
    "publication-level appendix lists item code SA0 for all items and SA0E "
    "for energy, both published for the U.S. city average; food is a "
    "published major group; these are consumer prices, not commodity export "
    "prices; no index level is stored"
)
ADMINISTRATIVE_AREA = (
    "U.S. city average; not a farm price and not an export price"
)
KIND = "index"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "forecast",
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
            "a CPI food and energy figure is not a settlement, a yield, "
            "a trade, a forecast, an observation, a completed harvest, "
            "or a benchmark"
        )
    citation = str(citation_url).strip()
    if citation != BLS_CPI_FOOD_ENERGY_URL:
        raise ValueError("citation_url is not the opened CPI data page")
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
    path = folder / "cpi-food-energy.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
