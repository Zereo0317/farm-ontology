"""One Pink Sheet monthly price cell, copied from the live workbook.

The file opened on 17 Nov 2026 is:

https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx

The Monthly Prices sheet prints series "Crude oil, average" and unit
"($/bbl)". The latest printed cell on that series is period 2026M10,
value 108.5. The sheet subtitle "1960 to present" is the series span,
not this cell's period. This cell is not a settlement, not a yield, and
not a trade. permits_financial_use stays false. Class C stays closed.
A missing citation writes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

CMO_MONTHLY_URL = (
    "https://thedocs.worldbank.org/en/doc/"
    "74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/"
    "CMO-Historical-Data-Monthly.xlsx"
)

SERIES = "Crude oil, average"
PERIOD = "2026M10"
UNIT = "($/bbl)"
VALUE = 108.5

FORBIDDEN_LABELS = frozenset({"settlement", "yield", "trade"})


def record_cmo_monthly_price(
    path: Path,
    citation_url: str | None,
    *,
    series: str | None = None,
    period: str | None = None,
    unit: str | None = None,
    value: object = None,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed price cell, or write nothing."""

    if citation_url is None or citation_url.strip() == "":
        raise ValueError("a Pink Sheet price is not stored without a citation_url")
    if citation_url != CMO_MONTHLY_URL:
        raise ValueError("a Pink Sheet price is not stored for a different citation")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a Pink Sheet price is not a settlement, a yield, or a trade")
    if any(
        item is not None
        for item in (series, period, unit, value, permits_financial_use, class_c_policy)
    ):
        raise ValueError("a Pink Sheet price is not stored with a different value")
    header = {
        "series": SERIES,
        "period": PERIOD,
        "unit": UNIT,
        "value": VALUE,
        "citation_url": CMO_MONTHLY_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
