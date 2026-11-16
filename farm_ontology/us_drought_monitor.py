"""U.S. Drought Monitor header.

One classification from the map page that was already opened. The
stored record is the printed header. The permission page allows
commercial and non-commercial use, including redistribution and
derivatives, when credit is given to the Drought Monitor and NDMC.
The Standardized Precipitation Index from 1895 and the Palmer index
reconstruction are different series and are not stored. This
classification is not a yield and not a settlement. It does not store
a percent or an index value. This module is not called from a field
save.
"""

from __future__ import annotations

import json
from pathlib import Path

US_DROUGHT_MONITOR_URL = "https://droughtmonitor.unl.edu/"

PUBLISHER = (
    "National Drought Mitigation Center at the University of Nebraska-Lincoln, "
    "with USDA, NOAA, and NASA"
)
PRODUCT = "U.S. Drought Monitor"
PERIOD = (
    "weekly; the map page says the data cutoff is Tuesday at 7:00 a.m. Eastern "
    "and the map is released Thursday at 8:30 a.m. Eastern; the map that was "
    "opened was released 12 November 2026 for data valid 10 November 2026; "
    "Drought.gov says the Drought Monitor files in its historical tool run "
    "from 2000 to the present"
)
UNIT = (
    "an expert classification of drought intensity; percent of area and a "
    "drought-severity index are named on the page; no percent and no index "
    "value is stored"
)
ADMINISTRATIVE_AREA = (
    "the United States, Puerto Rico, the Pacific islands, and the Virgin Islands"
)
KIND = "classification"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
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
            "a Drought Monitor class is not a settlement, a yield, a trade, "
            "an observation, a forecast, or a completed harvest"
        )
    citation = str(citation_url).strip()
    if citation != US_DROUGHT_MONITOR_URL:
        raise ValueError("citation_url is not the opened Drought Monitor page")
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
    path = folder / "us-drought-monitor.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
