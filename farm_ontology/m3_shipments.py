"""One printed Census M3 shipments figure.

The page refetched on 17 Nov 2026 is:

https://www.census.gov/manufacturing/m3/current/index.html

The lead paragraph prints "New orders for manufactured goods in
September" and then "Shipments, up eleven of the last twelve months,
increased $8.8 billion or 1.3 percent to $668.5 billion." August is
named only as the prior increase. The shipments figure is the printed
level $668.5 billion. The $8.8 billion change is not the figure. The
figure is not a price and not a trade.

permits_financial_use stays false. Class C stays closed. A missing
citation writes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

M3_URL = "https://www.census.gov/manufacturing/m3/current/index.html"

SERIES = "Shipments"
MONTH = "September"
VALUE = "$668.5 billion"

FORBIDDEN_LABELS = frozenset(
    {
        "price",
        "trade",
        "settlement",
        "yield",
    }
)


def record_m3_shipments(
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
    """Write the printed shipments figure, or write nothing."""

    if citation_url is None or citation_url.strip() == "":
        raise ValueError("a shipments figure is not stored without a citation_url")
    if citation_url != M3_URL:
        raise ValueError("a shipments figure is not stored for a different citation")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a shipments figure is not a price or a trade")
    if any(
        item is not None
        for item in (series, month, value, permits_financial_use, class_c_policy)
    ):
        raise ValueError("a shipments figure is not stored with a different value")
    header = {
        "series": SERIES,
        "month": MONTH,
        "value": VALUE,
        "citation_url": M3_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
