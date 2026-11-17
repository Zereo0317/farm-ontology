"""METI terms sentence.

The stored results page is

https://www.meti.go.jp/statistics/tyo/iip/result-1.html

That page was refetched. Its HTML has no 利用規約 anchor. It loads
https://www.meti.go.jp/js_2017/footer.js, and that footer prints

利用規約 -> https://www.meti.go.jp/main/rules.html

Only that linked terms page was opened. It does not print a sentence
about copying or reproduction, so nothing is stored. The time-series
download and the booklets were not opened. No production index and no
percent change is stored. An index is not a quantity of goods and not
a trade. permits_financial_use stays false. Class C stays closed.
This module is not called from a field save.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

RESULTS_URL = "https://www.meti.go.jp/statistics/tyo/iip/result-1.html"
TERMS_URL = "https://www.meti.go.jp/main/rules.html"

_TERMS_LINK = re.compile(
    r'<a[^>]+href="https://www\.meti\.go\.jp/main/rules\.html"[^>]*>\s*利用規約\s*</a>'
)
_MARKERS = ("複製", "転載", "copying", "reproduction")
_INDEX_MARKS = ("%", "％", "＝", "=", "前月比", "前年同月比")
FORBIDDEN_LABELS = frozenset(
    {
        "trade",
        "quantity of goods",
        "index",
        "percent",
        "price",
        "settlement",
        "前月比",
        "前年同月比",
    }
)


def _plain(body: str) -> str:
    text = re.sub(r"<[^>]+>", " ", body)
    return " ".join(text.split())


def _copying_sentence(terms_body: str) -> str:
    text = _plain(terms_body)
    parts = re.split(r"(?<=[。．.])\s*", text)
    for part in parts:
        lowered = part.lower()
        if not any(marker.lower() in lowered for marker in _MARKERS):
            continue
        sentence = part.strip()
        if any(mark in sentence for mark in _INDEX_MARKS):
            raise ValueError("an index is not stored")
        if sentence:
            return sentence
    raise ValueError("the terms page prints no copying or reproduction sentence")


def record_copying_sentence(
    path: Path,
    citation_url: str | None,
    page_body: str | None = None,
    terms_body: str | None = None,
    *,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed copying sentence, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("a terms sentence is not stored without the results page")
    if citation_url != RESULTS_URL:
        raise ValueError("a terms sentence is not stored for a different citation")
    if page_body is None or _TERMS_LINK.search(page_body) is None:
        raise ValueError("the page links no terms page")
    if terms_body is None or terms_body.strip() == "":
        raise ValueError("the terms page prints no copying or reproduction sentence")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("an index is not a quantity of goods and not a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    sentence = _copying_sentence(terms_body)
    stored = {
        "sentence": sentence,
        "citation_url": TERMS_URL,
        "kind": "terms",
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
