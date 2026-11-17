"""MoSPI September 2026 IIP release.

The product page links one September 2026 press release. That release
prints the Quick Estimate of IIP for September 2026 as 124.3. It does
not print a sentence that permits reproduction with attribution. Sector
indices, growth rates, and the bulk history file are not stored. An
index number is stored only when the release also prints one
reproduction sentence, and that sentence stays with the figure. An
index is not a quantity of goods and not a trade. permits_financial_use
stays false. Class C stays closed. This module does not change the
header function that rejects an index number. This module is not called
from a field save.
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
        "trading right",
        "growth",
        "growth rate",
        "sector",
    }
)


def _plain(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def _reproduction_sentence(plain: str) -> str:
    found = []
    for sentence in re.split(r"(?<=\.)\s+", plain):
        lowered = sentence.lower()
        if "reproduc" in lowered and ("attribut" in lowered or "acknowledg" in lowered):
            found.append(sentence.strip())
    if len(found) != 1:
        raise ValueError("the release prints no reproduction sentence")
    return found[0]


def _all_india_level(plain: str) -> str:
    found = _LEVEL.findall(plain)
    if len(found) != 1:
        raise ValueError("the release prints no single all-India index number")
    return found[0]


def record_release_level(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    release_url: str | None = None,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write one all-India level with its reproduction sentence, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("an index number is not stored without the product page")
    if citation_url != MOSPI_IIP_URL:
        raise ValueError("an index number is not stored for a different citation")
    if release_url not in _RELEASE_URLS:
        raise ValueError("only the September 2026 press release is opened")
    if body is None or body.strip() == "":
        raise ValueError("the release prints no all-India index number")
    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or "%" in label
        or any(character.isdigit() for character in label)
    ):
        raise ValueError("an index is not a quantity of goods and not a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    plain = _plain(body)
    sentence = _reproduction_sentence(plain)
    level = _all_india_level(plain)
    stored = {
        "sentence": sentence,
        "value": level,
        "product": PRODUCT,
        "period": PERIOD,
        "administrative_area": ADMINISTRATIVE_AREA,
        "kind": "index",
        "citation_url": MOSPI_IIP_URL,
        "release_page": RELEASE_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
