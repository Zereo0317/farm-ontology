"""The C&SD subject page prints no terms link.

The refetch of

https://www.censtatd.gov.hk/en/scode310.html

returned HTTP 200 and stayed on that URL. The page links no terms or
copyright page. No terms page was opened. The web table was not opened.
The parenthetical figure was not stored. An index is not a quantity of
goods and not a trade. permits_financial_use stays false. Class C stays
closed.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.csd_industrial import CSD_INDUSTRIAL_URL

TERMS_LINK = "the subject page prints no terms link"
FORBIDDEN_LABELS = frozenset({
    "trade",
    "quantity of goods",
    "settlement",
    "yield",
    "figure",
})


def record_terms_link(
    path: Path,
    citation_url: str | None,
    *,
    label: str | None = None,
    value: object = None,
    permits_financial_use: bool | None = None,
) -> None:
    """Write that the subject page prints no terms link, or write nothing."""

    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("a terms note is not stored without the subject citation")
    if str(citation_url).strip() != CSD_INDUSTRIAL_URL:
        raise ValueError("a terms note is not stored for a different citation")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("an index is not a trade or a quantity of goods")
    if value is not None or permits_financial_use not in (None, False):
        raise ValueError("the parenthetical figure is not stored")
    stored = {
        "citation_url": CSD_INDUSTRIAL_URL,
        "terms_link": TERMS_LINK,
        "permits_financial_use": False,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
