"""Hong Kong vegetable land figure.

The stored citation prints: "By the end of 2025, the land used for
vegetable, flower, field crop, and orchard are 342 ha, 116 ha, 4 ha,
and 250 ha respectively." The stored record is only the vegetable
figure: 342 ha at the end of 2025. The other land figures in that
sentence are not stored. Dollar values and the daily production line
are not stored. Hong Kong is not a farm. It is not a yield and not a
trade. This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

PUBLISHER = (
    "Agriculture, Fisheries and Conservation Department, "
    "and the Census and Statistics Department"
)
PRODUCT = "local agricultural production and fresh-food consumption"
SERIES = "land used for vegetable"
PERIOD = "the end of 2025"
VALUE = "342 ha"
UNIT = "ha"
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


def record_afcd_header(
    directory,
    *,
    citation_url=None,
    label=None,
    series=None,
    period=None,
    value=None,
) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if str(citation_url).strip() != CITATION_URL:
        raise ValueError("citation_url is the stored agriculture page")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a Hong Kong food-supply figure is not a settlement, a yield, "
            "a trade, a soybean crop, or a completed harvest"
        )
    if any(item is not None for item in (series, period, value)):
        raise ValueError("only the printed vegetable land figure is stored")
    if ADMINISTRATIVE_AREA.strip().lower() == "farm":
        raise ValueError("Hong Kong is not a farm")
    citation = str(citation_url).strip()
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "series": SERIES,
        "period": PERIOD,
        "value": VALUE,
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
