"""Grain SA crop estimates index header.

One redistribution from the index page that was already opened. The
stored record is the printed header. Grain SA is the publisher named
here. Grain SA is not the statistical office. It does not store a
provincial estimate. This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

PUBLISHER = "Grain SA"
PRODUCT = "crop estimates index"
PERIOD = (
    "the index shows a 1 November 2026 release among others; "
    "the start of the archive was not read"
)
UNIT = (
    "not a stored figure; the index lists soybean, maize, sunflower, "
    "sorghum, wheat, dry beans, and groundnuts"
)
ADMINISTRATIVE_AREA = "province, for South Africa, as named on the index"
CITATION_URL = "https://grainsa.co.za/applied-economics/crop-estimates/"
KIND = "redistribution"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "official statistical office",
    "observation",
    "completed harvest",
})


def record_crop_index_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a Grain SA index row is not a settlement, a yield, a trade, "
            "an official statistical office, an observation, or a completed harvest"
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
    path = folder / "crop-estimates-index.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
