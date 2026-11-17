"""The EDB terms sentence that forbids reproduction.

The manufacturing page

https://www.edb.gov.sg/en/corporate-news/monthly-manufacturing-performance

still links Terms of use. Only

https://www.edb.gov.sg/en/terms

was opened. The stored sentence forbids reproduction without EDB's
prior written permission and keeps the personal-download exception.
No spreadsheet or bulk file was opened. No index value is stored. An
index is not a quantity of goods and not a trade. permits_financial_use
stays false. Class C stays closed. This module does not call the header
function that rejects an index value.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.edb_manufacturing import EDB_MANUFACTURING_URL

TERMS_URL = "https://www.edb.gov.sg/en/terms"
REPRODUCTION_SENTENCE = (
    "No material including without limitation, the website design, branding "
    "and layout, graphics, images and hyperlinks from this website may be "
    "imitated, modified, reproduced, republished, uploaded, posted, "
    "transmitted or distributed in any way, without the prior written "
    "permission of EDB, except that you may download one copy of the "
    "material on a single computer for your own personal domestic use only, "
    "provided you keep intact all accompanying copyright and other "
    "proprietary notices."
)
STATEMENT = "An index is not a quantity of goods and not a trade."
FORBIDDEN_LABELS = frozenset({
    "trade",
    "quantity of goods",
    "index value",
    "settlement",
    "yield",
})


def record_terms_sentence(
    path: Path,
    citation_url: str | None,
    *,
    label: str | None = None,
    value: object = None,
    permits_financial_use: bool | None = None,
) -> None:
    """Write the printed reproduction sentence, or write nothing."""

    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("a terms sentence is not stored without the manufacturing citation")
    if str(citation_url).strip() != EDB_MANUFACTURING_URL:
        raise ValueError("a terms sentence is not stored for a different citation")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("an index is not a trade or a quantity of goods")
    if value is not None or permits_financial_use not in (None, False):
        raise ValueError("an index value is not stored")
    stored = {
        "citation_url": EDB_MANUFACTURING_URL,
        "terms_url": TERMS_URL,
        "reproduction_sentence": REPRODUCTION_SENTENCE,
        "statement": STATEMENT,
        "permits_financial_use": False,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
