"""JODI-Oil World Database header.

One revised compilation from the overview page that was already opened.
The stored record is the printed header. JODI does not adjust or fill
gaps, so a missing month stays missing. This file is not a copy of the
site on a past date. The opened terms page is a website terms-of-use.
It does not store a quantity. This module is not called from a field
save.
"""

from __future__ import annotations

import json
from pathlib import Path

JODI_OIL_OVERVIEW_URL = "https://www.jodidata.org/oil/database/overview.aspx"

PUBLISHER = "Joint Organisations Data Initiative"
PRODUCT = "JODI-Oil World Database"
PERIOD = (
    "monthly; the full CSV runs from January 2002 through data about one "
    "month old; the extended Beyond 20/20 file starts in January 2009; "
    "the database is updated on or around the 20th of each month"
)
UNIT = (
    "barrels, tonnes, and litres are the units named for the database; "
    "no quantity is stored"
)
ADMINISTRATIVE_AREA = (
    "participating country; more than 90 countries submit; "
    "this is not a world balance"
)
KIND = "compilation"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "observation",
    "forecast",
    "vintage",
    "world balance",
    "completed harvest",
})


def record_series_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a JODI-Oil figure is not a settlement, a yield, a trade, "
            "an observation, a forecast, a vintage, a world balance, "
            "or a completed harvest"
        )
    citation = str(citation_url).strip()
    if citation != JODI_OIL_OVERVIEW_URL:
        raise ValueError("citation_url is not the opened JODI-Oil overview")
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
    path = folder / "jodi-oil-world-database.json"
    path.write_text(json.dumps(header, indent=2) + "\n", encoding="utf-8")
    return {"file": path.name, "header": header}
