"""Argentina agricultural estimates header.

One official estimate from the catalog that was already opened. The
stored record is the printed header. An in-season campaign is not a
completed harvest census and not a farm yield. It does not store an
area, a production figure, or a yield. This module is not called from
a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

PUBLISHER = "Dirección de Estimaciones Agrícolas"
PRODUCT = "Estimaciones agrícolas"
PERIOD = (
    "catalog coverage starts 1969-01-01 and is updated twice a year; "
    "the catalog end date is also 1969-01-01 and is not the last campaign"
)
UNIT = (
    "not a stored figure; the catalog names sown area, harvested area, "
    "production in tonnes, and yield in kg/ha"
)
ADMINISTRATIVE_AREA = "province and partido or department"
CITATION_URL = "https://www.datos.gob.ar/dataset/estimaciones-agricolas"
KIND = "estimate"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "observation",
    "completed harvest",
})


def record_estimates_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "an Argentina estimate is not a settlement, a yield, a trade, "
            "an observation, or a completed harvest"
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
    path = folder / "estimaciones-agricolas.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
