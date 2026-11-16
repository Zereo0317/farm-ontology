"""Singapore 24-hour weather forecast header.

One dataset header from the page that was already opened. The stored
record is that header. The publisher is National Environment Agency,
Meteorological Service Singapore (MSS). The product is 24-hour Weather
Forecast. The citation stays on
https://data.gov.sg/datasets/d_ce2eb1e307bda31993c533285834ef2b/view.
https://data.gov.sg/ is not the citation.
https://data.gov.sg/open-data-licence was not opened.
NEA (National Environment Agency) is the same agency line, not a second publisher.
The document title 24-hour Weather Forecast (API) | NEA | data.gov.sg is not a second product.
Keep the printed spelling Kilometeres.
The page prints Free forever for personal or commercial use, under the Open Data Licence.
That sentence is a dataset licence on this page.
Commercial reuse of the dataset is not a right to trade, and it does not set permits_financial_use to true.
A forecast is not a completed harvest.
The words Fair, Rain, Showers, and the other forecast labels are labels.
Do not store a rainfall amount.
west, east, central, north, and south are printed region names.
Ang Mo Kio is an example area name.
Do not store them as a rainfall map.
© 2026 Open Government Products is a copyright line, not public domain.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

MSS_WEATHER_URL = (
    "https://data.gov.sg/datasets/d_ce2eb1e307bda31993c533285834ef2b/view"
)

PUBLISHER = "National Environment Agency, Meteorological Service Singapore (MSS)"
PRODUCT = "24-hour Weather Forecast"
PERIOD = "the next 24 hours; Data from Mar 2016 to Nov 2026; Updated every 6 hours"
UNIT = "Degrees Celsius; Percentage; Kilometeres per hour"
ADMINISTRATIVE_AREA = "Singapore"
KIND = "forecast"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "observation",
    "completed harvest",
    "public domain",
    "benchmark",
    "index",
    "fair",
    "rain",
    "showers",
    "rainfall amount",
    "rainfall map",
    "west",
    "east",
    "central",
    "north",
    "south",
    "ang mo kio",
    "figure",
})


def _stores_figure(label) -> bool:
    return any(character.isdigit() for character in str(label))


def record_series_header(
    directory,
    *,
    citation_url=None,
    label=None,
    period=None,
    unit=None,
    administrative_area=None,
    value=None,
    permits_financial_use=None,
) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and (
        str(label).strip().lower() in FORBIDDEN_LABELS or _stores_figure(label)
    ):
        raise ValueError(
            "a weather forecast header is not a settlement, a yield, a "
            "trade, an observation, a completed harvest, a benchmark, or "
            "an index, and a rainfall amount or a figure is not stored"
        )
    if period is not None or unit is not None or administrative_area is not None:
        raise ValueError(
            "period, unit, and administrative_area are not replaced"
        )
    if value is not None:
        raise ValueError("a figure is not stored")
    if permits_financial_use is not None:
        raise ValueError("permits_financial_use is false")
    citation = str(citation_url).strip()
    if citation != MSS_WEATHER_URL:
        raise ValueError("citation_url is not the opened dataset page")
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
    path = folder / "mss-weather.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
