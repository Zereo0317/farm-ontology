"""MAFF prefecture soybean table header.

One opened official table. The stored record is the printed header:
publisher, product, period, unit, and administrative area. It does not
store a yield, a price, a production total, or a trade. A prefecture is
not a farm. Class C stays closed. This module is not called from a
field save.
"""

from __future__ import annotations

import json
from pathlib import Path

CITATION_URL = (
    "https://www.e-stat.go.jp/stat-search/files?layout=dataset"
    "&stat_infid=000040286486&tclass1=000001032288&tclass2=000001032753"
    "&toukei=00500215&tstat=000001013427"
)

PUBLISHER = (
    "Ministry of Agriculture, Forestry and Fisheries (農林水産省), "
    "disseminated on the Portal Site of Official Statistics of Japan"
)
PRODUCT = "soybean (dried seed)"
PERIOD = "2024 and 2025 crop year"
UNIT = "area and harvest"
ADMINISTRATIVE_AREA = "prefecture"
KIND = "observation"
FORBIDDEN_LABELS = frozenset({"settlement", "yield", "trade"})


def record_table_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a soybean table value is not a settlement, a yield, or a trade")
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
    path = folder / "soybean-prefecture.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
