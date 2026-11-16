"""GEOGLAM Crop Monitor for AMIS header.

One consensus condition assessment from the page that was already
opened. The stored record is the printed header. It is not a pixel
yield, not a harvest measurement, and not a supply number. It does not
store a condition class for any place, a percent, or a tonne. This
module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

PUBLISHER = "GEOGLAM Crop Monitor"
PRODUCT = "Crop Monitor for AMIS condition classes"
PERIOD = "eleven reports a year, first Thursday of the month, every month except January"
UNIT = (
    "condition class; the opened rules name exceptional, favourable, "
    "watch, poor, out-of-season, and no data"
)
ADMINISTRATIVE_AREA = "main growing areas, national and subnational units"
CITATION_URL = "https://www.cropmonitor.org/crop-monitor-for-amis"
KIND = "assessment"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "tonne",
    "observation",
    "completed harvest",
})


def record_crop_monitor_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a Crop Monitor class is not a settlement, a yield, a trade, "
            "a tonne, an observation, or a completed harvest"
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
    path = folder / "crop-monitor-for-amis.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
