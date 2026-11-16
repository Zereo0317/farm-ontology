"""Indonesia BPS food-crop table header.

One opened official table. The stored record is the printed header:
publisher, product, period, unit, and administrative area. It does not
store a yield, a price, a production total, or a trade. A national
table is not a farm. Class C stays closed. This module is not called
from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

CITATION_URL = (
    "https://www.bps.go.id/en/statistics-table/2/MjM0NSMy/"
    "national-production-of-food-crops.html"
)

PUBLISHER = "Badan Pusat Statistik (BPS-Statistics Indonesia)"
PRODUCT = "food crops"
PERIOD = "2020 through 2024"
UNIT = "annual"
ADMINISTRATIVE_AREA = "national"
KIND = "observation"
FORBIDDEN_LABELS = frozenset({"settlement", "yield", "trade"})


def record_table_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a BPS food-crop table is not a settlement, a yield, or a trade"
        )
    if ADMINISTRATIVE_AREA.strip().lower() == "farm":
        raise ValueError("an administrative unit is not a farm")
    citation = str(citation_url).strip()
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": UNIT,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
        "class_c_policy": "closed",
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "indonesia-bps-food-crops.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
