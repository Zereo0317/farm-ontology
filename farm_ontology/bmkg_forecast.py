"""BMKG public weather forecast header.

One forecast from the page that was already opened. The stored record
is the printed header. It is not a field observation, not a harvest,
and not a supply number. It does not store a temperature, a wind
reading, or any other measurement. This module is not called from a
field save.
"""

from __future__ import annotations

import json
from pathlib import Path

PUBLISHER = "Badan Meteorologi, Klimatologi, dan Geofisika"
PRODUCT = "public weather forecast"
PERIOD = "3 days, eight steps per day, updated twice a day; page updated 3 September 2025"
UNIT = (
    "not one stored reading; the page names air temperature, humidity, "
    "weather description, wind speed and direction, cloud cover, and visibility"
)
ADMINISTRATIVE_AREA = (
    "kelurahan or desa, requested by the level-IV administrative code"
)
CITATION_URL = "https://data.bmkg.go.id/prakiraan-cuaca/"
KIND = "forecast"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "observation",
    "completed harvest",
})


def record_forecast_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a BMKG forecast is not a settlement, a yield, a trade, "
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
    path = folder / "public-weather-forecast.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
