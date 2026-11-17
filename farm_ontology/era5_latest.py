"""Latest ERA5-Land daily image the catalog printed.

The catalog list printed ECMWF/ERA5_LAND/DAILY_AGGR/20261108.
A list starting the next day printed no image id.
That printed id was the image sent to value:compute.
The client exposed the request URL.
The citation is that request URL.
A catalog page is not the citation.
The pin is 42.7018152 N, 142.4071291 E.
temperature_2m was returned.
u_component_of_wind_10m was returned.
v_component_of_wind_10m was returned.
dewpoint_temperature_2m was returned.
The dewpoint band is dewpoint.
It is not relative humidity.
Relative humidity was not calculated.
20261115 was not printed.
20261116 was not printed.
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

ERA5_LATEST_URL = (
    "https://earthengine.googleapis.com/v1/projects/seges-ai/"
    "value:compute?prettyPrint=false&alt=json"
)

IMAGE_ID = "ECMWF/ERA5_LAND/DAILY_AGGR/20261108"
BANDS = (
    {"band": "temperature_2m", "value": 273.0963548024495},
    {"band": "u_component_of_wind_10m", "value": 2.654146194458008},
    {"band": "v_component_of_wind_10m", "value": -1.241633415222168},
    {"band": "dewpoint_temperature_2m", "value": 268.03877385457355},
)
FORBIDDEN_LABELS = frozenset({
    "yield",
    "price",
    "trade",
    "completed harvest",
    "relative humidity",
    "humidity",
})


def record_latest_bands(
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
    if citation != ERA5_LATEST_URL:
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
    path = folder / "era5-latest.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
