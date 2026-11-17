"""One printed local quantity from the Singapore Food Statistics PDF.

The stored citation redirected. This record cites only the redirect
target:

https://www.sfa.gov.sg/api/assets/c1f675bd-351c-4ac1-bef9-b6b534b6e229/sgfs-2025-publication-060526-fa.pdf

Fig 2.2 prints Vegetables on the Production (Thousand Tonnes) axis.
Under 2025 that bar prints 16.6. The same column's Productivity
(Tonnes/ha) bar prints 253.3. That productivity figure is not stored.
Singapore is not a farm. It is not a trade. A soybean crop, a farm
yield, and an import share are not stored.

permits_financial_use stays false. Class C stays closed. A missing
citation writes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

SFA_URL = (
    "https://www.sfa.gov.sg/api/assets/"
    "c1f675bd-351c-4ac1-bef9-b6b534b6e229/"
    "sgfs-2025-publication-060526-fa.pdf"
)

SERIES = "Vegetables"
PERIOD = "2025"
VALUE = "16.6"
UNIT = "thousand tonnes"

FORBIDDEN_LABELS = frozenset(
    {
        "soybean crop",
        "yield",
        "trade",
        "import share",
        "farm",
    }
)


def record_sfa_local_quantity(
    path: Path,
    citation_url: str | None,
    *,
    series: str | None = None,
    period: str | None = None,
    value: object = None,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed local quantity, or write nothing."""

    if citation_url is None or citation_url.strip() == "":
        raise ValueError("a local quantity is not stored without a citation_url")
    if citation_url != SFA_URL:
        raise ValueError("a local quantity is not stored for a different citation")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a local quantity is not a soybean crop, a farm yield, or an import share"
        )
    if any(
        item is not None
        for item in (series, period, value, permits_financial_use, class_c_policy)
    ):
        raise ValueError("a local quantity is not stored with a different value")
    header = {
        "series": SERIES,
        "period": PERIOD,
        "value": VALUE,
        "unit": UNIT,
        "citation_url": SFA_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
