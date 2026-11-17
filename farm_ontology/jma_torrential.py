"""JMA localized torrential rain forecast header.

One page from the address that was fetched. The publisher is Japan Meteorological Agency.
The product is Localized Torrential Rain Forecast Map.
The kind is Forecast.
The citation stays on
https://www.jma.go.jp/bosai/en_kaikotan/.
https://www.jma.go.jp/ is not the citation.
https://www.jma.go.jp/bosai/ is not the citation.
https://www.jma.go.jp/bosai/en_kaikotan is not the citation.
https://www.jma.go.jp/bosai/en_kaikotan/#elements:sjfcstmap is not the citation.
en_kaikotan/#elements:sjfcstmap is not the citation.
https://www.jma.go.jp/bosai/#lang=en&pattern=forecast is not the citation.
The citation is the printed canonical link.
The map-view hash is omitted.
The document title is Japan Meteorological Agency | Localized Torrential Rain Forecast Map.
Localized Torrential Rain Forecast Map is the product. Forecast is the kind. Forecast is not the product.
Local Information is the menu document title, not the product.
Information on Disaster Mitigation is the group heading, not a stored field.
The stored period is 08:50 JST, 17 November 2026; 20:50; 23:50; 02:50; 05:50; 08:50; next 3 h; every 10 minutes; up to 6 hours ahead; from 7 to 15 hours ahead; every hour.
The stored unit is 300 km; 1 km; 5 km.
A kilometre scale is not a rainfall amount.
Administrative area is omitted.
The legend image was not stored.
2020 is the copyright year on the page. It is not stored.
Do not store a rainfall amount.
Do not store a temperature.
A forecast is not a completed harvest.
An index is not a quantity of goods.
The header is not marked public domain.
permits_financial_use stays false.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

JMA_TORRENTIAL_URL = "https://www.jma.go.jp/bosai/en_kaikotan/"

PUBLISHER = "Japan Meteorological Agency"
PRODUCT = "Localized Torrential Rain Forecast Map"
PERIOD = (
    "08:50 JST, 17 November 2026; "
    "20:50; "
    "23:50; "
    "02:50; "
    "05:50; "
    "08:50; "
    "next 3 h; "
    "every 10 minutes; "
    "up to 6 hours ahead; "
    "from 7 to 15 hours ahead; "
    "every hour"
)
UNIT = "300 km; 1 km; 5 km"
KIND = "Forecast"
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
    "position",
    "local information",
    "disaster mitigation",
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
        raise ValueError("unit is not replaced")
    if administrative_area is not None:
        raise ValueError("administrative_area is omitted")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != JMA_TORRENTIAL_URL:
        raise ValueError("citation_url is not the fetched page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": UNIT,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "jma-torrential.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
