"""One printed Stats SA manufacturing production index.

The PDF refetched on 17 Nov 2026 is:

https://www.statssa.gov.za/publications/P30412/P30412September2026.pdf

Table 1, Index of the volume of manufacturing production
(Base: 2019=100), prints September 2026 as 95,1. September 2025 in
the same row is 98,5. The release text says manufacturing production
decreased by 3,5% in September 2026 compared with September 2025.
That percentage is the change, not the index. The seasonally adjusted
September 2026 index 89,5 is not this figure. The sales estimate
310 284 is not this figure. The October 2026 PDF was not opened.

An index is not a quantity of goods. The stored copyright sentence
is the acknowledgment already stored with the header: users may apply
the information if they acknowledge Stats SA as the source. The header
function that rejects a value is unchanged.

permits_financial_use stays false. Class C stays closed. A missing
citation writes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.stats_sa_manufacturing import (
    COPYRIGHT_NOTICE,
    STATS_SA_MANUFACTURING_URL,
)

SERIES = "Index of the volume of manufacturing production"
PERIOD = "September 2026"
UNIT = "Base: 2019=100"
VALUE = "95,1"

FORBIDDEN_LABELS = frozenset(
    {
        "settlement",
        "trade",
        "yield",
        "quantity of goods",
        "tonne",
        "tonnes",
    }
)


def record_printed_index(
    directory,
    *,
    citation_url=None,
    label=None,
    series=None,
    period=None,
    unit=None,
    value=None,
    permits_financial_use=None,
    class_c_policy=None,
) -> dict:
    """Write the printed September 2026 production index, or write nothing."""

    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a manufacturing production index is not a quantity of goods, "
            "a settlement, or a trade"
        )
    if any(
        item is not None
        for item in (
            series,
            period,
            unit,
            value,
            permits_financial_use,
            class_c_policy,
        )
    ):
        raise ValueError("the printed production index is not stored with a different value")
    citation = str(citation_url).strip()
    if citation != STATS_SA_MANUFACTURING_URL:
        raise ValueError("citation_url is not the September 2026 manufacturing release")
    record = {
        "series": SERIES,
        "period": PERIOD,
        "unit": UNIT,
        "value": VALUE,
        "citation_url": citation,
        "copyright_notice": COPYRIGHT_NOTICE,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "manufacturing-production-index.json"
    path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "record": record}
