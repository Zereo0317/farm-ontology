"""BPS monthly manufacturing production level.

The citation is the statistics-table page. A refetch returned
Cloudflare's challenge page, titled Just a moment. That response prints
no production index level. (2010=100) in the product title is the base,
not a level. A level is stored only when the page prints exactly one
level together with a period and a label. No province, national label,
or start month is invented. A bulk file was not opened. An index is not
a quantity of goods and not a trade. permits_financial_use stays false.
permits_financial_use_test is not set. Class C stays closed. This
module does not change the header function that rejects a number. This
module is not called from a field save.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from farm_ontology.bps_manufacturing_index import BPS_MANUFACTURING_INDEX_URL
from farm_ontology.policy import CLASS_C_POLICY

BASE = "2010=100"
_MONTHS = (
    "Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|"
    "September|Oktober|November|Desember"
)
_LEVEL = re.compile(
    rf"\b(?P<label>[A-Z][^0-9]{{2,40}}?)\s+"
    rf"(?P<period>(?:{_MONTHS})\s+\d{{4}})\s+"
    rf"(?P<value>\d{{1,3}}(?:[.,]\d+)?)\b"
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
        "province",
        "national",
        "nasional",
        "start month",
        "2010=100",
    }
)


def _plain(body: str) -> str:
    text = re.sub(r"<[^>]+>", " ", body.replace("\xa0", " "))
    return " ".join(text.split())


def _printed_level(body: str) -> tuple[str, str, str, bool]:
    plain = _plain(body)
    found = _LEVEL.findall(plain)
    if len(found) != 1:
        raise ValueError("the page prints no production index level")
    label, period, value = found[0]
    label = " ".join(label.split())
    if label.lower() in FORBIDDEN_LABELS or BASE in label:
        raise ValueError("the page prints no production index level")
    return value, period, label, BASE in plain


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
    """Write one printed production level, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("a level is not stored without the statistics-table page")
    if citation_url != BPS_MANUFACTURING_INDEX_URL:
        raise ValueError("a level is not stored for a different citation")
    if source_url not in (None, BPS_MANUFACTURING_INDEX_URL):
        raise ValueError("a bulk file is not opened")
    if body is None or body.strip() == "":
        raise ValueError("the page prints no production index level")
    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or any(character.isdigit() for character in label)
    ):
        raise ValueError("an index is not a quantity of goods and not a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    if permits_financial_use_test is not None:
        raise ValueError("permits_financial_use_test is not set")
    value, period, printed_label, has_base = _printed_level(body)
    stored = {
        "value": value,
        "period": period,
        "label": printed_label,
        "citation_url": BPS_MANUFACTURING_INDEX_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    if has_base:
        stored["base"] = BASE
        stored["base_label"] = "base"
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
