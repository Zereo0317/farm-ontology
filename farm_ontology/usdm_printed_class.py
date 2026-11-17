"""One printed U.S. Drought Monitor class.

The citation already stored in the tests is:

https://droughtmonitor.unl.edu/

That page's weekly summary prints "the introduction of moderate drought
across Western New York State into far northeastern Ohio." The class is
moderate drought. The area is Western New York State into far
northeastern Ohio. Rainfall percents on the same page are not this
class. A drought class is not soil moisture, a yield, or a trade.

permits_financial_use stays false. Class C stays closed. A missing
citation writes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

USDM_URL = "https://droughtmonitor.unl.edu/"

DROUGHT_CLASS = "moderate drought"
AREA = "Western New York State into far northeastern Ohio"

FORBIDDEN_LABELS = frozenset(
    {
        "soil moisture",
        "yield",
        "trade",
        "settlement",
    }
)


def record_usdm_printed_class(
    path: Path,
    citation_url: str | None,
    *,
    drought_class: str | None = None,
    area: str | None = None,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed class and area, or write nothing."""

    if citation_url is None or citation_url.strip() == "":
        raise ValueError("a drought class is not stored without a citation_url")
    if citation_url != USDM_URL:
        raise ValueError("a drought class is not stored for a different citation")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a drought class is not soil moisture, a yield, or a trade")
    if any(
        item is not None
        for item in (drought_class, area, permits_financial_use, class_c_policy)
    ):
        raise ValueError("a drought class is not stored with a different value")
    header = {
        "drought_class": DROUGHT_CLASS,
        "area": AREA,
        "citation_url": USDM_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
