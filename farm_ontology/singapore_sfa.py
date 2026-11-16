"""Singapore Food Agency food statistics header.

One city food-statistics publication from the page that was already
opened. The stored record is the printed header. Soybean is not a local
crop in those pages. It is not a farm yield and not a trade. It does
not store an import share or a tonne figure. This module is not called
from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

PUBLISHER = "Singapore Food Agency"
PRODUCT = "Singapore Food Statistics"
PERIOD = "2025 publication"
UNIT = (
    "not printed as one unit; the publication lists local vegetables, "
    "beansprouts, mushrooms, eggs, and seafood"
)
ADMINISTRATIVE_AREA = "Singapore"
CITATION_URL = (
    "https://www.sfa.gov.sg/docs/default-source/publication/sg-food-statistics/"
    "sgfs-2025-publication_060526-fa.pdf"
)
KIND = "observation"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "soybean crop",
    "completed harvest",
})


def record_sfa_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a Singapore Food Statistics figure is not a settlement, a yield, "
            "a trade, a soybean crop, or a completed harvest"
        )
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
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "singapore-food-statistics.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
