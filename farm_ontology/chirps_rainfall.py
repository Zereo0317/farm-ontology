"""CHIRPS rainfall header.

One data-page header from the page that was already opened. The stored
record is that header. The publisher is Climate Hazards Center - UC Santa Barbara.
The product is CHIRPS: Rainfall Estimates from Rain Gauge and Satellite Observations.
The citation stays on
https://www.chc.ucsb.edu/data/chirps.
https://www.chc.ucsb.edu/ is not the citation.
The CHIRPS v3 page was not opened.
Climate Hazards Group InfraRed Precipitation with Station data (CHIRPS2) version 2 is not the stored product.
Production of CHIRPS v2 will end after December 2026. December 2026 is not the data period.
The stored period is 1981 to near-present. Since 1999 is not the period.
a 35+ year quasi-global rainfall data set is the overview sentence, not the stored period.
0.05° is the satellite-imagery resolution, not a rainfall unit.
Spanning 50°S-50°N (and all longitudes) is a latitude band, not the administrative area.
Santa Barbara, CA 93106 is the footer address, not the administrative area.
the United States is the place of publication in the waiver, not the administrative area.
The public-domain waiver by Pete Peterson is a licence sentence, not the kind, and it does not set permits_financial_use to true.
To the extent possible under the law, Pete Peterson has waived all copyright and related or neighboring rights to CHIRPS. CHIRPS data is in the public domain as registered with Creative Commons.
©2026 The Regents of the University of California. All Rights Reserved. is a copyright line, not a grant of financial use.
Do not store a rainfall amount.
A rainfall estimate is not a completed harvest.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

CHIRPS_RAINFALL_URL = "https://www.chc.ucsb.edu/data/chirps"

PUBLISHER = "Climate Hazards Center - UC Santa Barbara"
PRODUCT = "CHIRPS: Rainfall Estimates from Rain Gauge and Satellite Observations"
PERIOD = "1981 to near-present"
NOT_OPENED = "the field was not opened"
KIND = "Rainfall Estimates"
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
    "rainfall amount",
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
            "a rainfall estimate is not a settlement, a yield, a price, "
            "a trade, a forecast, a completed harvest, a benchmark, or "
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
    if citation != CHIRPS_RAINFALL_URL:
        raise ValueError("citation_url is not the opened data page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": NOT_OPENED,
        "administrative_area": NOT_OPENED,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "chirps-rainfall.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
