"""METI September 2026 production index level.

The results page prints 2026年9月分. The production row prints the
seasonally adjusted confirmed index 103.9, with the preliminary figure
104.1 in parentheses. The original index 107.7 is a second column and
is not stored. Month-on-month and year-on-year percents are not stored.
2020年＝100 is the printed base, not the level. The download file and
the terms page were not opened. An index is not a quantity of goods
and not a trade. permits_financial_use stays false.
permits_financial_use_test is not set. Class C stays closed. This
module does not change the header function that rejects a number. This
module is not called from a field save.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from farm_ontology.meti_iip import (
    ADMINISTRATIVE_AREA,
    METI_IIP_URL,
    PERIOD,
)
from farm_ontology.policy import CLASS_C_POLICY

BASE = "2020年＝100"
_LEVEL = re.compile(
    r"生産\s*\(速報値\)\s*(\d+\.\d+)\s*\(\d+\.\d+\)"
)
FORBIDDEN_LABELS = frozenset(
    {
        "trade",
        "completed harvest",
        "harvest",
        "quantity of goods",
        "trading right",
        "settlement",
        "settlement price",
        "price",
        "前月比",
        "前年同月比",
        "base",
    }
)


def _plain(body: str) -> str:
    text = re.sub(r"<[^>]+>", " ", body.replace("\xa0", " ").replace("&nbsp;", " "))
    return " ".join(text.split())


def _production_level(body: str) -> str:
    plain = _plain(body)
    if PERIOD not in plain or f"鉱工業指数、{BASE}" not in plain:
        raise ValueError("the page prints no production index level")
    found = _LEVEL.findall(plain)
    if len(found) != 1:
        raise ValueError("the page prints no single production index level")
    return found[0]


def record_production_level(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    source_url: str | None = None,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed production index level, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("a level is not stored without the results page")
    if citation_url != METI_IIP_URL:
        raise ValueError("a level is not stored for a different citation")
    if source_url not in (None, METI_IIP_URL):
        raise ValueError("the download file and the terms page are not opened")
    if body is None or body.strip() == "":
        raise ValueError("the page prints no production index level")
    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or label.strip() in FORBIDDEN_LABELS
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
    if permits_financial_use_test is not None:
        raise ValueError("permits_financial_use_test is not set")
    level = _production_level(body)
    stored = {
        "value": level,
        "series": "生産",
        "presentation": "季節調整済指数",
        "period": PERIOD,
        "base": BASE,
        "base_label": "base",
        "administrative_area": ADMINISTRATIVE_AREA,
        "kind": "level",
        "citation_url": METI_IIP_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
