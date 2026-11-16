"""NOAA Oceanic Niño Index header.

One index from the page that was already opened. The stored record is
the printed header. This record is the Oceanic Niño Index. It does not
store a RONI value and it is not labeled as the current official
monitoring series. A separate NOAA license page was not opened. It is
not a crop yield, an oil balance, or a manufacturing index. The latest
values are an estimate because of the ERSSTv5 filter and are not stored
as finished. It does not store an anomaly value. This module is not
called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

NOAA_ONI_URL = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v5/"

PUBLISHER = "NOAA Climate Prediction Center"
PRODUCT = "Oceanic Niño Index"
PERIOD = (
    "seasonal; the ASCII file that was opened begins with DJF 1950; "
    "the episode page is titled 1950 to present; the page says the index "
    "is updated by the 5th of each month; the latest values can change for "
    "up to two months after the first real-time posting"
)
UNIT = (
    "a three-month running mean of ERSSTv5 sea-surface temperature anomalies "
    "in the Niño 3.4 region, in degrees Celsius; no anomaly value is stored"
)
ADMINISTRATIVE_AREA = "the Niño 3.4 region; not a country and not a crop area"
KIND = "index"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "oil balance",
    "manufacturing index",
    "observation",
    "forecast",
    "public domain",
    "completed harvest",
})


def record_series_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "an Oceanic Niño Index figure is not a settlement, a yield, "
            "a trade, an oil balance, a manufacturing index, an observation, "
            "a forecast, or a completed harvest"
        )
    citation = str(citation_url).strip()
    if citation != NOAA_ONI_URL:
        raise ValueError("citation_url is not the opened Oceanic Niño Index page")
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
    path = folder / "oceanic-nino-index.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
