"""India DES cells from the third advance estimate.

The rice record is the rice total cell. The wheat record is the one
printed wheat cell, season Rabi, and it is not a total. The unit is the
unit line printed on that page. The page does not name a place, so the
administrative area is the words "not printed on the page". It does not
store a yield or a trade. Class C stays closed. This module is not
called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

CITATION_URL = (
    "https://desagri.gov.in/wp-content/uploads/2026/06/"
    "Time-Series-3rd-AE-2025-26-English.pdf"
)

PUBLISHER = (
    "Ministry of Agriculture & Farmers Welfare, "
    "Department of Agriculture & Farmers Welfare (DA&FW)"
)
SERIES = "rice total"
PRODUCT = SERIES
PERIOD = "2025-26 third advance estimates"
UNIT = "Production in Lakh Tonnes"
VALUE = "1540.24"
WHEAT_SERIES = "wheat"
WHEAT_SEASON = "Rabi"
WHEAT_VALUE = "1206.57"
ADMINISTRATIVE_AREA = "not printed on the page"
KIND = "observation"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "kharif",
    "rabi",
    "summer",
    "india",
    "all india",
    "state",
})
PLACE_LABELS = frozenset({"india", "all india", "state", "farm"})


def record_table_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if UNIT.strip() == "":
        raise ValueError("the unit is not printed on the page")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a DES crop estimate is not a settlement, a yield, a trade, "
            "a seasonal cell, or a place name"
        )
    area = ADMINISTRATIVE_AREA.strip().lower()
    if area in PLACE_LABELS:
        raise ValueError("the page does not name a place")
    citation = str(citation_url).strip()
    header = {
        "publisher": PUBLISHER,
        "series": SERIES,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": UNIT,
        "value": VALUE,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
        "class_c_policy": "closed",
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "india-des-estimates.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    wheat = {
        "publisher": PUBLISHER,
        "series": WHEAT_SERIES,
        "product": WHEAT_SERIES,
        "season": WHEAT_SEASON,
        "period": PERIOD,
        "unit": UNIT,
        "value": WHEAT_VALUE,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
        "class_c_policy": "closed",
    }
    wheat_path = folder / "india-des-wheat.json"
    wheat_path.write_text(
        json.dumps(wheat, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header, "wheat_file": wheat_path.name, "wheat": wheat}
