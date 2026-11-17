"""The growth rate printed in the NBS industrial release title.

The printed title is 2026年10月份规模以上工业增加值增长4.8%.
The stored figure is that 4.8% growth rate. It is a growth rate, not a
quantity of goods, and not a trade. The attribution sentence stays with
the figure. No other number is stored. permits_financial_use stays
false. This module does not call the header function that rejects a
growth rate.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.nbs_industrial import (
    NBS_INDUSTRIAL_URL,
    REPRODUCTION_SENTENCE,
)

PRINTED_TITLE = "2026年10月份规模以上工业增加值增长4.8%"
PUBLISHER = "国家统计局"
VALUE = 4.8
UNIT = "%"
KIND = "growth rate"
STATEMENT = "This is a growth rate, not a quantity of goods."
FORBIDDEN_LABELS = frozenset({
    "trade",
    "quantity of goods",
    "settlement",
    "yield",
})


def record_title_growth_rate(
    path: Path,
    citation_url: str | None,
    *,
    label: str | None = None,
    value: object = None,
    permits_financial_use: bool | None = None,
) -> None:
    """Write the printed title growth rate, or write nothing."""

    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("a growth rate is not stored without the release citation")
    if str(citation_url).strip() != NBS_INDUSTRIAL_URL:
        raise ValueError("a growth rate is not stored for a different citation")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("the title growth rate is not a trade or a quantity of goods")
    if value is not None or permits_financial_use not in (None, False):
        raise ValueError("the stored growth rate is the printed title rate")
    stored = {
        "publisher": PUBLISHER,
        "title": PRINTED_TITLE,
        "value": VALUE,
        "unit": UNIT,
        "kind": KIND,
        "statement": STATEMENT,
        "citation_url": NBS_INDUSTRIAL_URL,
        "reproduction_sentence": REPRODUCTION_SENTENCE,
        "permits_financial_use": False,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
