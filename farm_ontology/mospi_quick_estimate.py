"""All-India IIP quick estimate.

The September 2026 press release prints one all-India index. The
sentence is: The Quick Estimate of IIP stands at 124.3 against 116.5
in September 2025. The stored value is 124.3. 116.5 is September 2025
and is not stored. Sector indices and growth rates are not stored. The
citation is that press release. No reproduction sentence is required.
An index is not a quantity of goods, not a trade, and not a settlement
price. permits_financial_use stays false. permits_financial_use_test is
a non-commercial test switch on this record only. It is not an executed
trade. Class C stays closed. This module does not change the header
function that rejects an index number. This module is not called from
a field save.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from farm_ontology.mospi_iip import (
    ADMINISTRATIVE_AREA,
    MOSPI_IIP_URL,
    PERIOD,
    PRODUCT,
)
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
_LEVEL = re.compile(r"Quick Estimate of IIP stands at (\d+\.\d+)")
FORBIDDEN_LABELS = frozenset(
    {
        "trade",
        "completed harvest",
        "harvest",
        "quantity of goods",
        "settlement",
        "settlement price",
        "price",
        "growth",
        "growth rate",
        "sector",
    }
)


def _plain(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def _all_india_level(plain: str) -> str:
    found = _LEVEL.findall(plain)
    if len(found) != 1:
        raise ValueError("the release prints no single all-India index number")
    return found[0]


def record_quick_estimate(
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
    """Write the printed all-India quick estimate, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("an index number is not stored without the press release")
    if citation_url not in _RELEASE_URLS:
        raise ValueError("the citation is the September 2026 press release")
    if body is None or body.strip() == "":
        raise ValueError("the release prints no single all-India index number")
    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or "%" in label
        or any(character.isdigit() for character in label)
    ):
        raise ValueError("an index is not a trade and not a settlement price")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    if permits_financial_use_test not in (None, True):
        raise ValueError("the test switch is not an executed trade")
    level = _all_india_level(_plain(body))
    stored = {
        "value": level,
        "product": PRODUCT,
        "period": PERIOD,
        "administrative_area": ADMINISTRATIVE_AREA,
        "kind": "index",
        "citation_url": RELEASE_URL,
        "permits_financial_use": False,
        "permits_financial_use_test": True,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
