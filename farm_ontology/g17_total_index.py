"""One printed Federal Reserve G.17 industrial production index cell.

The page refetched on 17 Nov 2026 is:

https://www.federalreserve.gov/releases/g17/current/default.htm

The summary table prints the series Total index. Under Industrial
production, 2017=100, and the 2026 column Sept. [p], that row prints
104.0. The same row's percent-change cell for Sept. [p] prints .7. That
percent change is not the index. The index is not a price and not a trade.

permits_financial_use stays false. Class C stays closed. A missing
citation writes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

G17_URL = "https://www.federalreserve.gov/releases/g17/current/default.htm"

SERIES = "Total index"
MONTH = "Sept."
YEAR = "2026"
STATUS = "[p]"
VALUE = 104.0
UNIT = "2017=100"

FORBIDDEN_LABELS = frozenset(
    {
        "price",
        "trade",
        "settlement",
        "yield",
    }
)


def record_g17_total_index(
    path: Path,
    citation_url: str | None,
    *,
    series: str | None = None,
    month: str | None = None,
    value: object = None,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed index cell, or write nothing."""

    if citation_url is None or citation_url.strip() == "":
        raise ValueError("an index cell is not stored without a citation_url")
    if citation_url != G17_URL:
        raise ValueError("an index cell is not stored for a different citation")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("an index cell is not a price or a trade")
    if any(
        item is not None
        for item in (series, month, value, permits_financial_use, class_c_policy)
    ):
        raise ValueError("an index cell is not stored with a different value")
    header = {
        "series": SERIES,
        "month": MONTH,
        "year": YEAR,
        "status": STATUS,
        "value": VALUE,
        "unit": UNIT,
        "citation_url": G17_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
