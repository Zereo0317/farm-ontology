"""NOAA STAR vegetation-health header.

One introduction header from the page that was already opened. The stored
record is that header. The publisher is NOAA Center for Satellite Applications
and Research. The product is STAR - Global Vegetation Health Products:
Introduction. The citation stays on
https://www.star.nesdis.noaa.gov/smcd/emb/vci/VH/index.php.
https://www.star.nesdis.noaa.gov/ is not the citation.
https://www.star.nesdis.noaa.gov/smcd/emb/vci/VH/ is not the citation.
https://star.nesdis.noaa.gov/smcd/emb/vci/VH/index.php is not the citation.
The document title is STAR - Global Vegetation Health Products: Introduction.
Dept. of Commerce, NESDIS, and National Oceanic and Atmospheric Administration are printed names, not a second publisher.
1981 to the present is the period for the AVHRR products.
2012 is the VIIRS start, not a replacement for 1981 to the present.
since 1982 is a navigation label, not the period.
September 1994 through February 1995 is a gap, not the period.
30 July 2019 is a page date, not the period.
The response date Mon, 16 Nov 2026 18:25:09 GMT is not the period.
4 km and 7-day are resolution, not the unit.
1 km and 16 km are resolution, not the unit.
% Drought Area is a navigation label, not the unit.
Global in the product title is not a selected area.
The United States map alt is a placeholder, not the area.
130 countries and 4,000 administrative divisions are not one administrative area.
No single administrative area is selected.
Data and images displayed on STAR sites are provided for experimental use only and are not official operational NOAA products.
That notice is not a grant.
The disclaimer page was not opened.
The animated-map image was not opened.
The header is not marked public domain.
JavaScript was not unpacked.
Do not store an index value.
A vegetation index is not a completed harvest.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

VHI_URL = "https://www.star.nesdis.noaa.gov/smcd/emb/vci/VH/index.php"

PUBLISHER = "NOAA Center for Satellite Applications and Research"
PRODUCT = "STAR - Global Vegetation Health Products: Introduction"
PERIOD = "1981 to the present"
NOT_OPENED = "the field was not opened"
KIND = "Vegetation Health Indices (VHI)"
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
    "index value",
    "vegetation index",
    "experimental use",
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
            "a vegetation index is not a settlement, a yield, a price, "
            "a trade, a forecast, a completed harvest, a benchmark, or "
            "an index, and an index value or a figure is not stored"
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
    if citation != VHI_URL:
        raise ValueError("citation_url is not the opened introduction page")
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
    path = folder / "vhi-vegetation.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
