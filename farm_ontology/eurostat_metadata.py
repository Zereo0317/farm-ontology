"""Eurostat STS metadata licence.

The stored citation is the navigation response. This module does not
open a product page, a data download, or a bulk file. It records only
the metadata page named in eurostat_industrial:

https://ec.europa.eu/eurostat/cache/metadata/en/sts_esms.htm

That page was opened. It prints no licence or copyright sentence.
The stored record says so and nothing more. No index value and no
growth rate is stored. An index is not a quantity of goods and not a
trade. permits_financial_use stays false. Class C stays closed.
This module is not called from a field save.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from farm_ontology.eurostat_industrial import EUROSTAT_INDUSTRIAL_URL, METADATA_PAGE
from farm_ontology.policy import CLASS_C_POLICY

NO_LICENCE_STATEMENT = (
    "the metadata page was opened and no licence sentence was printed"
)
_MARKERS = ("licence", "license", "copyright", "©", "all rights reserved")
FORBIDDEN_LABELS = frozenset(
    {
        "trade",
        "quantity of goods",
        "index",
        "index value",
        "growth",
        "growth rate",
        "percent",
    }
)


def _plain(body: str) -> str:
    text = re.sub(r"<[^>]+>", " ", body)
    return " ".join(text.split())


def _licence_sentence(body: str) -> str | None:
    text = _plain(body)
    parts = re.split(r"(?<=[。．.])\s*", text)
    for part in parts:
        lowered = part.lower()
        if not any(marker in lowered for marker in _MARKERS):
            continue
        sentence = part.strip()
        if sentence:
            return sentence
    return None


def record_metadata_licence(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    metadata_url: str | None = None,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed licence sentence, or the no-sentence statement."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("a metadata note is not stored without the citation")
    if citation_url != EUROSTAT_INDUSTRIAL_URL:
        raise ValueError("a metadata note is not stored for a different citation")
    if metadata_url not in (None, METADATA_PAGE):
        raise ValueError("a metadata note is not stored for a different page")
    if body is None or body.strip() == "":
        raise ValueError("the metadata page was not opened")
    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or any(character.isdigit() for character in label)
        or "%" in label
        or "％" in label
    ):
        raise ValueError("an index is not a quantity of goods and not a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    sentence = _licence_sentence(body)
    if sentence is None:
        stored = {
            "citation_url": EUROSTAT_INDUSTRIAL_URL,
            "metadata_page": METADATA_PAGE,
            "statement": NO_LICENCE_STATEMENT,
            "permits_financial_use": False,
            "class_c_policy": CLASS_C_POLICY,
        }
    else:
        stored = {
            "citation_url": EUROSTAT_INDUSTRIAL_URL,
            "metadata_page": METADATA_PAGE,
            "sentence": sentence,
            "permits_financial_use": False,
            "class_c_policy": CLASS_C_POLICY,
        }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
