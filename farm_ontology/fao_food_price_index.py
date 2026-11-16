"""FAO Food Price Index header.

One index from the release page that was already opened. The stored
record is the printed header. FAO website content is copyrighted.
Copying for private study, research, teaching, and non-commercial
products requires FAO to be named as source and copyright holder.
Commercial reuse goes to copyright@fao.org. The statistical-database
policy was not opened. The 1961 annual file is a spliced extension and
is not this index. Recent meat months mix projected and observed prices
and can be revised, so a recent month is not stored as finished. It
does not store an index level. This module is not called from a field
save.
"""

from __future__ import annotations

import json
from pathlib import Path

FAO_FOOD_PRICE_INDEX_URL = "https://www.fao.org/worldfoodsituation/foodpricesindex/en/"

PUBLISHER = "Food and Agriculture Organization of the United Nations"
PRODUCT = "Food Price Index"
PERIOD = (
    "monthly; the page opened was the 6 November 2026 release; "
    "the official monthly nominal index runs from 1990; "
    "the 1961 annual file is a spliced extension and is not the same "
    "object as the post-1990 price index"
)
UNIT = (
    "an index; five group indexes are cereals, vegetable oils, dairy, meat, "
    "and sugar, weighted by average export shares for 2014-2016; "
    "no index level is stored"
)
ADMINISTRATIVE_AREA = (
    "an international export-price basket; not a country, not a retail price, "
    "and not a farm"
)
KIND = "index"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "retail price",
    "futures settlement",
    "observation",
    "public domain",
    "completed harvest",
})


def record_series_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "an FAO Food Price Index figure is not a settlement, a yield, "
            "a trade, a retail price, a futures settlement, an observation, "
            "or a completed harvest"
        )
    citation = str(citation_url).strip()
    if citation != FAO_FOOD_PRICE_INDEX_URL:
        raise ValueError("citation_url is not the opened Food Price Index page")
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
    path = folder / "food-price-index.json"
    path.write_text(json.dumps(header, indent=2) + "\n", encoding="utf-8")
    return {"file": path.name, "header": header}
