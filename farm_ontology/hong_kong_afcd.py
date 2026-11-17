"""Hong Kong local production and fresh-food header.

One official estimate from the pages that were already opened. The
stored record is the printed header. Soybean is not in the opened crop
list. It is not a farm yield and not a trade. It does not store a
farmed-area figure or a throughput number. This module is not called
from a field save.

Refetched on 17 Nov 2026, the stored citation prints land areas, dollar
values, a daily production line with no year, and consumption shares.
It does not print one local quantity for vegetables, flowers, fruit,
pigs, poultry, fish, eggs, or cattle with a year. No quantity is
stored. Hong Kong is not a farm. It is not a completed harvest and not
a trade.
"""

from __future__ import annotations

import json
from pathlib import Path

PUBLISHER = (
    "Agriculture, Fisheries and Conservation Department, "
    "and the Census and Statistics Department"
)
PRODUCT = "local agricultural production and fresh-food consumption"
PERIOD = "2025; the wholesale consumption table includes 2023–2025"
UNIT = (
    "not printed as one unit; the opened pages name vegetables, flowers, "
    "fruit, pigs, poultry, fish, eggs, and cattle"
)
ADMINISTRATIVE_AREA = "Hong Kong, the territory and named wholesale markets"
CITATION_URL = "https://www.afcd.gov.hk/english/agriculture/agr_hk/agr_hk.html"
KIND = "estimate"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "soybean crop",
    "completed harvest",
})


def record_afcd_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a Hong Kong food-supply figure is not a settlement, a yield, "
            "a trade, a soybean crop, or a completed harvest"
        )
    citation = str(citation_url).strip()
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
    path = folder / "local-agricultural-production.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}


def read_stored_record(path) -> dict:
    """Read the stored header. Reading writes no file and no trade."""

    source = Path(path)
    folder = source.parent
    before = sorted(item.name for item in folder.iterdir())
    record = json.loads(source.read_text(encoding="utf-8"))
    after = sorted(item.name for item in folder.iterdir())
    if after != before:
        raise ValueError("reading the stored record writes no trade")
    if record.get("permits_financial_use") is not False:
        raise ValueError("permits_financial_use stays false")
    if "trade" in record:
        raise ValueError("a Hong Kong record is not a trade")
    for value in record.values():
        if "trade" in str(value).lower():
            raise ValueError("a Hong Kong record is not a trade")
    return record
