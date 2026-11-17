"""Other printed METI September 2026 figures.

The results page prints the seasonally adjusted production index 103.9.
That level is not stored again. The same production row prints the
original index 107.7, the preliminary 104.1, the month-on-month percent
2.0, and the year-on-year percent 1.7. Each stored figure keeps the
label printed next to it. 2020年＝100 is the base, not a level. The
download file and the terms page were not opened. An index is not a
quantity of goods and not a trade. permits_financial_use stays false.
permits_financial_use_test is not set. Class C stays closed. This
module does not change the header function that rejects a number. This
module is not called from a field save.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from farm_ontology.meti_iip import METI_IIP_URL, PERIOD
from farm_ontology.policy import CLASS_C_POLICY

BASE = "2020年＝100"
_ROW = re.compile(
    r"生産\s*\(速報値\)\s*"
    r"\d+\.\d+\s*\((\d+\.\d+)\)\s*"
    r"(\d+\.\d+)\s*"
    r"(\d+\.\d+)\s*\(\d+\.\d+\)\s*"
    r"(\d+\.\d+)"
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
    }
)


def _plain(body: str) -> str:
    text = re.sub(r"<[^>]+>", " ", body.replace("\xa0", " ").replace("&nbsp;", " "))
    return " ".join(text.split())


def _printed_figures(body: str) -> list[dict[str, str]]:
    plain = _plain(body)
    if PERIOD not in plain or f"鉱工業指数、{BASE}" not in plain:
        raise ValueError("the page prints no labeled production figures")
    found = _ROW.findall(plain)
    if len(found) != 1:
        raise ValueError("the page prints no single production row")
    preliminary, month_on_month, original, year_on_year = found[0]
    return [
        {"value": original, "label": "原指数"},
        {"value": preliminary, "label": "速報値"},
        {"value": month_on_month, "label": "前月比（％）"},
        {"value": year_on_year, "label": "前年同月比（％）"},
    ]


def record_printed_figures(
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
    """Write the other printed production figures, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("a figure is not stored without the results page")
    if citation_url != METI_IIP_URL:
        raise ValueError("a figure is not stored for a different citation")
    if source_url not in (None, METI_IIP_URL):
        raise ValueError("the download file and the terms page are not opened")
    if body is None or body.strip() == "":
        raise ValueError("the page prints no labeled production figures")
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
    if permits_financial_use_test is not None:
        raise ValueError("permits_financial_use_test is not set")
    stored = {
        "period": PERIOD,
        "series": "生産",
        "base": BASE,
        "base_label": "base",
        "figures": _printed_figures(body),
        "citation_url": METI_IIP_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
