"""JMA daily-forecast header.

One page from the address that was fetched. The stored record is the
printed document-title segment. The publisher is Japan Meteorological
Agency. The product is Daily Forecasts. The citation stays on
https://www.jma.go.jp/bosai/map.html#contents=forecast&lang=en.
https://www.jma.go.jp/ is not the citation.
https://www.jma.go.jp/jma/indexe.html is not the citation.
https://www.jma.go.jp/jma/kokusai/multi.html is not the citation.
https://www.jma.go.jp/bosai/#lang=en&pattern=forecast is not the citation.
https://www.jma.go.jp/bosai/map.html is not the citation.
https://www.jma.go.jp/jma/en/copyright.html was not opened.
The page did not print a separate canonical URL.
The response title is 気象庁｜統合地図ページ.
The document title is Japan Meteorological Agency｜Daily Forecasts.
Daily Forecasts is the document-title segment.
気象庁 is a printed name, not a second publisher.
The stored period is Daily weather forecasts for the week ahead in map form; Issued at 22 JST, 16 Nov. 2026.
Daily forecasts are updated at 5:00, 11:00 and 17:00 JST every day and at other times as necessary. That update schedule is not the period and is not a separate series.
16 Nov., Weather is not the period.
16(Mon), 17(Tue), 18(Wed), 19(Thu), 20(Fri), 21(Sat), 22(Sun), and 23(Mon) are slider labels. They are not the period.
Unit is omitted.
The stored administrative area is Japan (list).
Tokyo, Ogasawara Islands, Niigata, Osaka, Fukuoka, Kagoshima, Naha, Ishigakijima Island, Asahikawa, Sapporo, and Sendai are map panel titles. They are not the administrative area.
Local Information was not opened.
Three-hourly Forecasts was not opened.
Two-week Temperature Forecast was not opened.
Seasonal Forecasts was not opened.
Do not store a rainfall amount.
Do not store a temperature.
A forecast is not a completed harvest.
The header is not marked public domain.
permits_financial_use stays false.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

JMA_DAILY_URL = "https://www.jma.go.jp/bosai/map.html#contents=forecast&lang=en"

PUBLISHER = "Japan Meteorological Agency"
PRODUCT = "Daily Forecasts"
PERIOD = (
    "Daily weather forecasts for the week ahead in map form; "
    "Issued at 22 JST, 16 Nov. 2026"
)
ADMINISTRATIVE_AREA = "Japan (list)"
KIND = "Daily Forecasts"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "price",
    "trade",
    "observation",
    "completed harvest",
    "public domain",
    "benchmark",
    "index",
    "rainfall amount",
    "temperature",
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
            "a forecast header is not a settlement, a yield, a price, a "
            "trade, or a completed harvest, and a rainfall amount, a "
            "temperature, or a figure is not stored"
        )
    if period is not None:
        raise ValueError("period is not replaced")
    if unit is not None:
        raise ValueError("unit is omitted")
    if administrative_area is not None:
        raise ValueError("administrative_area is not replaced")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != JMA_DAILY_URL:
        raise ValueError("citation_url is not the fetched page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "jma-daily.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
