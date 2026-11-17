"""JAXA G-Portal product catalog header.

The home page https://www.gportal.jaxa.jp/?lang=en was opened.
Its printed link /information/product was the product page that was opened.
The product page final URL is https://www.gportal.jaxa.jp/information/product?lang=en.
The printed canonical link is https://www.gportal.jaxa.jp/information/product.
https://www.gportal.jaxa.jp/ is not the citation.
https://www.gportal.jaxa.jp/?lang=en is not the citation.
https://www.gportal.jaxa.jp/information/product?lang=en is not the citation.
https://www.gportal.jaxa.jp/information/product/ is not the citation.
http://www.gportal.jaxa.jp/index.php is not the citation.
The citation is the printed canonical link.
The publisher is Japan Aerospace Exploration Agency.
G-Portal is the site name in the title, not a second publisher.
The product is Product Information / Operation.
The document title is G-PortalProduct Information / Operation.
Information about products and their operation is provided by spacecraft. That sentence is not a second product.
Spacecraft names in the menu are not a second product.
Period was not printed.
Unit was not printed.
Area was not printed.
Kind was not printed.
Licence was not printed. Terms of Use is a link, not a licence sentence.
Do not store a scene id.
Do not store a pixel.
Do not store a yield.
Do not store a price.
Do not store a rainfall amount.
Do not store a temperature.
Do not store a trade.
A catalog product is not a completed harvest.
Class C stays closed.
permits_financial_use stays false.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

JAXA_GPORTAL_URL = "https://www.gportal.jaxa.jp/information/product"

PUBLISHER = "Japan Aerospace Exploration Agency"
PRODUCT = "Product Information / Operation"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "price",
    "trade",
    "rainfall",
    "rainfall amount",
    "temperature",
    "scene",
    "scene id",
    "pixel",
    "completed harvest",
    "observation",
    "public domain",
    "benchmark",
    "index",
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
    kind=None,
    licence=None,
    value=None,
) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and (
        str(label).strip().lower() in FORBIDDEN_LABELS or _stores_figure(label)
    ):
        raise ValueError(
            "a catalog header is not a settlement, a yield, a price, a "
            "trade, or a completed harvest, and a scene id, a pixel, a "
            "rainfall amount, a temperature, or a figure is not stored"
        )
    if period is not None:
        raise ValueError("period was not printed")
    if unit is not None:
        raise ValueError("unit was not printed")
    if administrative_area is not None:
        raise ValueError("area was not printed")
    if kind is not None:
        raise ValueError("kind was not printed")
    if licence is not None:
        raise ValueError("licence was not printed")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != JAXA_GPORTAL_URL:
        raise ValueError("citation_url is not the fetched page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "citation_url": citation,
        "permits_financial_use": False,
        "class_c_policy": "closed",
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "gportal-product.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
