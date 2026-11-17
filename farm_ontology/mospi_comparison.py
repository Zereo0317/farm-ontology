"""September 2025 IIP comparison.

The September 2026 press release prints one sentence: The Quick
Estimate of IIP stands at 124.3 against 116.5 in September 2025. This
record stores 116.5, the printed September 2025 comparison. It does not
store 124.3. 116.5 is not the September 2026 index and not a settlement
price. The citation is that press release. No other number is invented.
permits_financial_use stays false. permits_financial_use_test is not set
on this record. Class C stays closed. This module does not change the
header function that rejects an index number. This module is not called
from a field save.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from farm_ontology.mospi_iip import ADMINISTRATIVE_AREA, MOSPI_IIP_URL, PRODUCT
from farm_ontology.policy import CLASS_C_POLICY

RELEASE_URL = (
    "https://www.mospi.gov.in/uploads/latestreleasesfiles/"
    "1793184301608-IIP Press Release September 2026.pdf"
)
_RELEASE_URLS = frozenset(
    {
        RELEASE_URL,
        "https://www.mospi.gov.in/uploads/latestreleasesfiles/"
        "1793184301608-IIP%20Press%20Release%20September%202026.pdf",
    }
)
LABEL = "printed September 2025 comparison"
PERIOD = "September 2025"
_COMPARISON = re.compile(r"against (\d+\.\d+) in September 2025")
FORBIDDEN_LABELS = frozenset(
    {
        "trade",
        "completed harvest",
        "harvest",
        "quantity of goods",
        "settlement",
        "settlement price",
        "price",
        "september 2026 index",
        "index",
    }
)


def _plain(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def _comparison(plain: str) -> str:
    found = _COMPARISON.findall(plain)
    if len(found) != 1:
        raise ValueError("the release prints no September 2025 comparison")
    return found[0]


def record_september_2025_comparison(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed September 2025 comparison, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("a comparison is not stored without the press release")
    if citation_url not in _RELEASE_URLS:
        raise ValueError("the citation is the September 2026 press release")
    if body is None or body.strip() == "":
        raise ValueError("the release prints no September 2025 comparison")
    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or any(character.isdigit() for character in label)
    ):
        raise ValueError("116.5 is not the September 2026 index and not a settlement price")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    if permits_financial_use_test is not None:
        raise ValueError("permits_financial_use_test is not set on this record")
    value = _comparison(_plain(body))
    stored = {
        "value": value,
        "label": LABEL,
        "product": PRODUCT,
        "period": PERIOD,
        "administrative_area": ADMINISTRATIVE_AREA,
        "kind": "comparison",
        "citation_url": RELEASE_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
