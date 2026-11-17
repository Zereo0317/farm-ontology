"""TAMSAT rainfall terms sentence.

The stored citation is

https://ourresearch.reading.ac.uk/tamsat/rainfall/.

That page prints: TAMSAT data are free to use and are released for
operational, research and commercial use under the terms of the Creative
Commons Attribution 4.0 International license (CC BY 4.0). The stored
record is that sentence. The deed page
https://creativecommons.org/licenses/by/4.0/ was not opened. No rainfall
amount is stored. A rainfall estimate is not a completed harvest and not
a trade. A commercial-use sentence does not set permits_financial_use to
true. Class C stays closed. This module does not change the header
function that rejects a figure. This module is not called from a field
save.
"""

from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.tamsat_rainfall import TAMSAT_RAINFALL_URL

USE_SENTENCE = (
    "TAMSAT data are free to use and are released for operational, research "
    "and commercial use under the terms of the Creative Commons Attribution "
    "4.0 International license (CC BY 4.0)."
)
_COMMERCIAL = "released for operational, research and commercial use"
_CC_BY = re.compile(r"\bcc by 4\.0\b", re.IGNORECASE)
_ATTRIBUTION = "creative commons attribution 4.0"
_RAINFALL_AMOUNT = re.compile(r"\d+(?:\.\d+)?\s*mm\b", re.IGNORECASE)
FORBIDDEN_LABELS = frozenset(
    {
        "trade",
        "completed harvest",
        "harvest",
        "rainfall",
        "rainfall amount",
        "rainfall estimate",
        "figure",
        "settlement",
        "yield",
    }
)


def _plain(body: str) -> str:
    text = unescape(body).replace("\xa0", " ")
    text = re.sub(r"<[^>]+>", " ", text)
    text = " ".join(text.split())
    return re.sub(r"\s+([.,;:])", r"\1", text)


def _matches(sentence: str) -> bool:
    lowered = sentence.lower()
    return (
        _COMMERCIAL in lowered
        or _CC_BY.search(sentence) is not None
        or _ATTRIBUTION in lowered
    )


def _printed_sentence(body: str) -> str:
    plain = _plain(body)
    if USE_SENTENCE in plain:
        return USE_SENTENCE
    found: list[str] = []
    for piece in re.split(r"(?<!\d)\.\s+", plain.strip()):
        piece = piece.strip()
        if not piece:
            continue
        sentence = piece if piece.endswith(".") else piece + "."
        if len(sentence) > 400 or not _matches(sentence):
            continue
        if _RAINFALL_AMOUNT.search(sentence):
            raise ValueError("a rainfall amount is not stored")
        if sentence not in found:
            found.append(sentence)
    if len(found) != 1:
        raise ValueError("the page prints no such sentence")
    return found[0]


def record_use_sentence(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    source_url: str | None = None,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the terms sentence the rainfall page prints, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("a terms sentence is not stored without the rainfall page")
    if citation_url != TAMSAT_RAINFALL_URL:
        raise ValueError("a terms sentence is not stored for a different citation")
    if source_url not in (None, TAMSAT_RAINFALL_URL):
        raise ValueError("only the rainfall page is opened")
    if body is None or body.strip() == "":
        raise ValueError("the page prints no such sentence")
    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or any(character.isdigit() for character in label)
    ):
        raise ValueError("a rainfall estimate is not a completed harvest and not a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    sentence = _printed_sentence(body)
    if _RAINFALL_AMOUNT.search(sentence):
        raise ValueError("a rainfall amount is not stored")
    stored = {
        "sentence": sentence,
        "citation_url": TAMSAT_RAINFALL_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
