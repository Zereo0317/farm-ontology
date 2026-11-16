"""SMAP soil-moisture header.

One homepage title from the page that was already opened. The stored
record is that title. The publisher is NASA. The product is
SMAP | Soil Moisture Active Passive. The citation stays on
https://smap.jpl.nasa.gov/.
https://smap.jpl.nasa.gov/data/ returned HTTP 404 and was not a product title.
The page you were looking for doesn't exist (404).
Jet Propulsion Laboratory and California Institute of Technology are printed names, not a second publisher.
The document title is SMAP.
January 31, 2015 is a launch countdown, not the period.
TIME SINCE LAUNCH is the countdown title, not the period.
og:updated_time 2014-06-02 17:12:34 -0700 is not the period.
The response dates Mon, 16 Nov 2026 18:18:50 GMT and Mon, 16 Nov 2026 18:19:32 GMT are not the period.
Privacy is a footer link, not a licence.
Licence was not opened.
The header is not marked public domain.
NSIDC was not opened.
Do not store a soil-moisture value.
A soil-moisture product is not a completed harvest.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

SMAP_SOIL_MOISTURE_URL = "https://smap.jpl.nasa.gov/"

PUBLISHER = "NASA"
PRODUCT = "SMAP | Soil Moisture Active Passive"
NOT_OPENED = "the field was not opened"
KIND = "Soil Moisture Active Passive"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "price",
    "trade",
    "forecast",
    "completed harvest",
    "public domain",
    "benchmark",
    "index",
    "soil-moisture value",
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
            "a soil-moisture product is not a settlement, a yield, a "
            "price, a trade, a forecast, a completed harvest, a "
            "benchmark, or an index, and a soil-moisture value or a "
            "figure is not stored"
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
    if citation != SMAP_SOIL_MOISTURE_URL:
        raise ValueError("citation_url is not the opened homepage")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": NOT_OPENED,
        "unit": NOT_OPENED,
        "administrative_area": NOT_OPENED,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "smap-soil-moisture.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
