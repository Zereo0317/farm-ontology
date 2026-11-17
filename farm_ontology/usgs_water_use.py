"""USGS total water use header.

The page https://www.usgs.gov/mission-areas/water-resources/science/total-water-use
was fetched.
The final URL is that address.
The citation is the URL that was fetched.
The product is Total Water Use.
The publisher is U.S. Geological Survey.
The page prints a 2015 total of 322,000 million gallons per day.
That printed figure is the withdrawal.
322 billion gallons per day is the printed equivalent, not a second withdrawal.
361,000 thousand acre-feet per year is the printed equivalent, not a second withdrawal.
No volume was guessed.
Do not store a yield.
Do not store a price.
Do not store a trade.
permits_financial_use stays false.
Class C stays closed.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

USGS_WATER_USE_URL = (
    "https://www.usgs.gov/mission-areas/water-resources/science/total-water-use"
)

PUBLISHER = "U.S. Geological Survey"
PRODUCT = "Total Water Use"
PERIOD = "2015"
WITHDRAWAL = "322,000 million gallons per day"
UNIT = "million gallons per day"
FORBIDDEN_LABELS = frozenset({
    "yield",
    "price",
    "trade",
    "harvest",
    "completed harvest",
})


def record_water_use(
    directory,
    *,
    citation_url=None,
    label=None,
    withdrawal=None,
    permits_financial_use=None,
    class_c_policy=None,
) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a withdrawal figure is not a yield or a trade")
    if withdrawal is not None:
        raise ValueError("the printed withdrawal is not replaced")
    if permits_financial_use is not None:
        raise ValueError("permits_financial_use stays false")
    if class_c_policy is not None:
        raise ValueError("class C stays closed")
    citation = str(citation_url).strip()
    if citation != USGS_WATER_USE_URL:
        raise ValueError("citation_url is not the fetched page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "withdrawal": WITHDRAWAL,
        "unit": UNIT,
        "citation_url": citation,
        "permits_financial_use": False,
        "class_c_policy": "closed",
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "usgs-water-use.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
