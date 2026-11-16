"""India Meteorological Department forecast header.

One bulletin header from the page that was already opened. The stored
record is that header. The publisher is India Meteorological Department.
The product is All India Weather Forecast Bulletin. The citation stays on
https://mausam.imd.gov.in/responsive/all_india_forcast_bulletin.php.
https://mausam.imd.gov.in/ is not the citation.
https://mausam.imd.gov.in/responsive/disclaimer.php is not the citation.
The printed download link is https://mausam.imd.gov.in/backend/assets/aiwfb_pdf/b486c0d9e22dbb8d627d179337d58f38.pdf.
It is not a rainfall file and it is not a second product.
ALL INDIA WEATHER SUMMARY AND FORECAST BULLETIN is the PDF line, not a second product.
The period sentence is the issue line and the seven-day headings, not one observation.
Forecast and warning for any day is valid from 0830 hours IST of day till 0830 hours IST of next day.
A forecast is not a completed harvest.
The legend categories WS, FWS, SCT, ISOL, and DRY are labels, not millimetre amounts.
No rainfall amount or subdivision row is stored.
Ministry of Earth Sciences and Government of India are printed and are not the publisher.
The New Delhi postal address is not an administrative area.
© Copyright 2026, Developed by IT Team, India Meteorological Department is a copyright line, not public domain.
The disclaimer says the site is not a substitute for independent professional advice.
A separate redistribution grant was not printed.
Do not relabel this header as an index, a yield, or a completed harvest.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

IMD_WEATHER_URL = (
    "https://mausam.imd.gov.in/responsive/all_india_forcast_bulletin.php"
)
DOWNLOAD_LINK = (
    "https://mausam.imd.gov.in/backend/assets/aiwfb_pdf/"
    "b486c0d9e22dbb8d627d179337d58f38.pdf"
)
DISCLAIMER_PAGE = "https://mausam.imd.gov.in/responsive/disclaimer.php"

PUBLISHER = "India Meteorological Department"
PRODUCT = "All India Weather Forecast Bulletin"
PERIOD = (
    "2026-11-16; Time of Issue: 20:35:00 hours IST; (Night); "
    "7 Days Rainfall Forecast; 16 November (Day 1) through "
    "22 November (Day 7)"
)
UNIT = "Legend Category %Stations"
ADMINISTRATIVE_AREA = "All India"
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
    "rainfall amount",
    "subdivision",
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
    citation = str(citation_url).strip()
    if citation != IMD_WEATHER_URL:
        raise ValueError("citation_url is not the opened bulletin page")
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
    path = folder / "imd-weather.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
