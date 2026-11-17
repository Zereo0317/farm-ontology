"""ERA5-Land dewpoint at the pin.

One Earth Engine value compute requested only dewpoint_temperature_2m.
The image is ECMWF/ERA5_LAND/DAILY_AGGR/20261108.
The pin is 42.7018152 N, 142.4071291 E.
The client exposed the request URL.
The citation is that request URL.
A catalog page is not the citation.
The returned value is labeled dewpoint.
It is not relative humidity.
Relative humidity was not calculated.
Temperature was not requested.
Wind was not requested.
Do not store a yield.
Do not store a price.
Do not store a trade.
A reanalysis is not a harvest.
permits_financial_use stays false.
Class C stays closed.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

ERA5_DEWPOINT_URL = (
    "https://earthengine.googleapis.com/v1/projects/seges-ai/"
    "value:compute?prettyPrint=false&alt=json"
)

IMAGE_ID = "ECMWF/ERA5_LAND/DAILY_AGGR/20261108"
BAND = "dewpoint_temperature_2m"
LABEL = "dewpoint"
VALUE = 268.03877385457355
FORBIDDEN_LABELS = frozenset({
    "yield",
    "price",
    "trade",
    "relative humidity",
    "humidity",
    "harvest",
    "completed harvest",
})


def record_dewpoint(
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
        raise ValueError("dewpoint is not relative humidity, a yield, or a trade")
    if value is not None:
        raise ValueError("the returned dewpoint is not replaced")
    if permits_financial_use is not None:
        raise ValueError("permits_financial_use stays false")
    if class_c_policy is not None:
        raise ValueError("class C stays closed")
    citation = str(citation_url).strip()
    if citation != ERA5_DEWPOINT_URL:
        raise ValueError("citation_url is not the request the client made")
    header = {
        "image_id": IMAGE_ID,
        "band": BAND,
        "label": LABEL,
        "value": VALUE,
        "citation_url": citation,
        "permits_financial_use": False,
        "class_c_policy": "closed",
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "era5-dewpoint.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
