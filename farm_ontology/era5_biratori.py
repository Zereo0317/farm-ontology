"""ERA5-Land wind and temperature at the pin.

One Earth Engine value compute returned the bands.
The client exposed the request URL.
The citation is that request URL.
A catalog page is not the citation.
The image id is ECMWF/ERA5_LAND/DAILY_AGGR/20261108.
The pin is 42.7018152 N, 142.4071291 E.
temperature_2m was returned.
u_component_of_wind_10m was returned.
v_component_of_wind_10m was returned.
time_start was returned and is not a band, so it is not stored.
Relative humidity was not derived.
Dewpoint was not requested.
Do not store a soil-moisture value.
Do not store a yield.
Do not store a price.
Do not store a trade.
A reanalysis is not a completed harvest.
permits_financial_use stays false.
Class C stays closed.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

ERA5_BIRATORI_URL = (
    "https://earthengine.googleapis.com/v1/projects/seges-ai/"
    "value:compute?prettyPrint=false&alt=json"
)

IMAGE_ID = "ECMWF/ERA5_LAND/DAILY_AGGR/20261108"
BANDS = (
    {"band": "temperature_2m", "value": 273.0963548024495},
    {"band": "u_component_of_wind_10m", "value": 2.654146194458008},
    {"band": "v_component_of_wind_10m", "value": -1.241633415222168},
)
FORBIDDEN_LABELS = frozenset({
    "yield",
    "price",
    "trade",
    "completed harvest",
    "relative humidity",
    "dewpoint",
    "soil-moisture value",
})


def record_era5_bands(
    directory,
    *,
    citation_url=None,
    label=None,
    value=None,
    permits_financial_use=None,
    class_c_policy=None,
) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a reanalysis band is not a yield, a price, or a trade")
    if value is not None:
        raise ValueError("a returned band is not replaced")
    if permits_financial_use is not None:
        raise ValueError("permits_financial_use stays false")
    if class_c_policy is not None:
        raise ValueError("class C stays closed")
    citation = str(citation_url).strip()
    if citation != ERA5_BIRATORI_URL:
        raise ValueError("citation_url is not the request the client made")
    bands = [
        {
            "band": item["band"],
            "value": item["value"],
            "citation_url": citation,
        }
        for item in BANDS
    ]
    header = {
        "image_id": IMAGE_ID,
        "bands": bands,
        "permits_financial_use": False,
        "class_c_policy": "closed",
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "era5-biratori.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
