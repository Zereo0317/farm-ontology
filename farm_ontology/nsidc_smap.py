"""NSIDC SMAP collection header.

One collection header from the page that was already opened. The stored
record is that header. The publisher is National Snow and Ice Data Center.
The product is Soil Moisture Active Passive Data (SMAP). The citation stays on
https://nsidc.org/data/smap.
https://nsidc.org/ is not the citation.
https://nsidc.org/data/smap/ is not the citation.
https://smap.jpl.nasa.gov/ is not the citation.
The document title is SMAP.
NSIDC, NSIDC DAAC, CIRES, and the University of Colorado Boulder are printed names, not a second publisher.
NASA is a footer image alt, not the publisher.
April 2015 is when the mission began operating.
in July 2015, the radar failed. July 2015 is the radar failure, not the period end.
every two to three days is a cadence, not the period.
everywhere on Earth is not the administrative area.
Geographic coverage is the printed label for Global.
Level-1 through Level-4 are collection names, not a soil-moisture value.
The response date Mon, 16 Nov 2026 18:21:31 GMT is not the period.
Data Policies and Citation Policies were linked and do not print a redistribution sentence.
© 2026, National Snow and Ice Data Center - Advancing knowledge of Earth's frozen regions is a copyright line, not a licence grant.
The header is not marked public domain.
JavaScript was not unpacked.
Do not store a soil-moisture value.
A soil-moisture product is not a completed harvest.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

NSIDC_SMAP_URL = "https://nsidc.org/data/smap"

PUBLISHER = "National Snow and Ice Data Center"
PRODUCT = "Soil Moisture Active Passive Data (SMAP)"
PERIOD = "April 2015"
NOT_OPENED = "the field was not opened"
ADMINISTRATIVE_AREA = "Global"
KIND = "Soil Moisture Active Passive Data"
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
    if citation != NSIDC_SMAP_URL:
        raise ValueError("citation_url is not the opened collection page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": NOT_OPENED,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "nsidc-smap.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
