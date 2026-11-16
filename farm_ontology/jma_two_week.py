"""JMA two-week temperature forecast header.

One page from the address that was fetched. The stored record is the
printed document-title segment. The publisher is Japan Meteorological
Agency. The product is Two-week Temperature Forecast. The citation
stays on
https://www.data.jma.go.jp/cpd/twoweek/en/.
https://www.jma.go.jp/ is not the citation.
https://www.data.jma.go.jp/ is not the citation.
https://www.data.jma.go.jp/cpd/twoweek/en is not the citation.
https://www.jma.go.jp/jma/indexe.html is not the citation.
https://www.jma.go.jp/jma/kokusai/multi.html is not the citation.
https://www.jma.go.jp/bosai/#lang=en&pattern=forecast is not the citation.
https://www.jma.go.jp/bosai/en_wdist/ is not the citation.
https://www.jma.go.jp/jma/en/copyright.html was not opened.
The page does not print a separate citation URL. The citation is the data-url the menu printed.
The document title is Japan Meteorological Agency | Two-week Temperature Forecast.
Two-week Temperature Forecast is the document-title segment. It is the product and the kind.
Forecast is not the kind.
Two-week Forecast is the breadcrumb, not a second kind.
The word Temperature in the title is the product name. A temperature number is not stored.
気象庁 is a printed name, not a second publisher.
The stored period is The Two-week Temperature Forecast is issued at 14:30 JST every day.; five-day average temperatures from eight days ahead.
Unit is omitted.
Administrative area is omitted.
The prefecture menu and the map region labels are not an administrative area.
Probability percentages are not stored.
Hidden list-view blocks were not stored.
Three-hourly Forecasts was not opened.
Local Information was not opened.
Daily Forecasts was not opened.
Seasonal Forecasts was not opened.
Do not store a rainfall amount.
Do not store a temperature number.
A forecast is not a completed harvest.
An index is not a quantity of goods.
The header is not marked public domain.
permits_financial_use stays false.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

JMA_TWO_WEEK_URL = "https://www.data.jma.go.jp/cpd/twoweek/en/"

PUBLISHER = "Japan Meteorological Agency"
PRODUCT = "Two-week Temperature Forecast"
PERIOD = (
    "The Two-week Temperature Forecast is issued at 14:30 JST every day.; "
    "five-day average temperatures from eight days ahead"
)
KIND = "Two-week Temperature Forecast"
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
    "forecast",
    "two-week forecast",
    "weather",
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
        raise ValueError("administrative_area is omitted")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != JMA_TWO_WEEK_URL:
        raise ValueError("citation_url is not the fetched page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "jma-two-week.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
