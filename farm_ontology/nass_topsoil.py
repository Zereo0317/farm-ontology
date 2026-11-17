"""NASS topsoil moisture condition shares, copied from the live PDF.

The file opened on 17 Nov 2026 is the Crop Progress report:

https://release.nass.usda.gov/reports/prog4526.pdf

The topsoil table prints "Topsoil Moisture Condition - Selected States: Week
Ending November 8, 2026". The publisher line on that page is "USDA, National
Agricultural Statistics Service". The table note prints "[National topsoil
moisture conditions for selected States are weighted based on cropland
acreage]". The columns are Very short, Short, Adequate, and Surplus, and each
column is labeled "(percent)".

The 48 States row prints very short 11, short 23, adequate 58, surplus 8.
The Texas row prints very short 10, short 31, adequate 52, surplus 7 for the
same week. These percent columns are shares of cropland in each condition
class. They are not volumetric water content, they are not m3/m3, and they
are not a SMAP sample. They are not a completed harvest.

permits_financial_use stays false. Class C stays closed. A missing citation
writes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

NASS_TOPSOIL_URL = "https://release.nass.usda.gov/reports/prog4526.pdf"

PUBLISHER = "USDA, National Agricultural Statistics Service"
TABLE = "Topsoil Moisture Condition - Selected States: Week Ending November 8, 2026"
PERIOD = "Week Ending November 8, 2026"
WEIGHTING = (
    "[National topsoil moisture conditions for selected States are weighted "
    "based on cropland acreage]"
)
UNIT = "percent"

ROWS = (
    {
        "state": "48 States",
        "Very short": 11,
        "Short": 23,
        "Adequate": 58,
        "Surplus": 8,
        "unit": UNIT,
    },
    {
        "state": "Texas",
        "Very short": 10,
        "Short": 31,
        "Adequate": 52,
        "Surplus": 7,
        "unit": UNIT,
    },
)

FORBIDDEN_LABELS = frozenset(
    {
        "volumetric water content",
        "m3/m3",
        "smap",
        "yield",
        "price",
        "trade",
        "harvest",
        "completed harvest",
    }
)


def record_nass_topsoil(
    path: Path,
    citation_url: str | None,
    *,
    publisher: str | None = None,
    table: str | None = None,
    period: str | None = None,
    weighting: str | None = None,
    rows: object = None,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed topsoil rows, or write nothing."""

    if citation_url is None or citation_url.strip() == "":
        raise ValueError("a topsoil condition share is not stored without a citation_url")
    if citation_url != NASS_TOPSOIL_URL:
        raise ValueError("a topsoil condition share is not stored for a different citation")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a topsoil condition share is not volumetric water content")
    if any(
        value is not None
        for value in (
            publisher,
            table,
            period,
            weighting,
            rows,
            permits_financial_use,
            class_c_policy,
        )
    ):
        raise ValueError("a topsoil condition share is not stored with a different value")
    header = {
        "publisher": PUBLISHER,
        "table": TABLE,
        "period": PERIOD,
        "weighting": WEIGHTING,
        "rows": [dict(row) for row in ROWS],
        "citation_url": NASS_TOPSOIL_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
