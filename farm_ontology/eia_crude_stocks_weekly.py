"""Latest weekly U.S. crude-oil stocks from the cited EIA page.

The refetch of

https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=WCESTUS1&f=W

returned HTTP 200. The title prints Weekly U.S. Ending Stocks excluding
SPR of Crude Oil (Thousand Barrels). The latest filled end date is
11/06 in the 2026-Nov row, and that value prints 414,417. The series
is the weekly history the page prints. It is not labeled a 5-minute
or hourly feed. A request that fails, or a page with no value, writes
nothing. A stock level is not invented.
permits_financial_use stays false. Class C stays closed.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

EIA_STOCKS_URL = (
    "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=WCESTUS1&f=W"
)

FORBIDDEN_LABELS = frozenset(
    {
        "5-minute",
        "5-min",
        "hourly",
        "trade",
        "settlement",
        "yield",
        "harvest",
        "completed harvest",
    }
)


class _Rows(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell = ""
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._in_cell = True
            self._cell = ""

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self._in_cell and self._row is not None:
            self._row.append(" ".join(self._cell.split()))
            self._in_cell = False
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._in_cell:
            self._cell += data


def _series(body: str) -> tuple[str, str]:
    match = re.search(r"<title>\s*([^<]+?)\s*</title>", body)
    if match is None:
        raise ValueError("the page has no value")
    title = " ".join(match.group(1).split())
    unit = re.search(r"\(([^)]+)\)\s*$", title)
    if unit is None or "Crude Oil" not in title:
        raise ValueError("the page has no value")
    return title, unit.group(1)


def _latest(body: str) -> tuple[str, str, str]:
    parser = _Rows()
    parser.feed(body)
    found: tuple[str, str, str] | None = None
    for row in parser.rows:
        if not row or not re.fullmatch(r"\d{4}-[A-Z][a-z]{2}", row[0]):
            continue
        cells = row[1:]
        for index in range(0, len(cells) - 1, 2):
            week = cells[index]
            value = cells[index + 1]
            if re.fullmatch(r"\d{2}/\d{2}", week) and re.fullmatch(r"\d{1,3}(?:,\d{3})+", value):
                found = (row[0], week, value)
    if found is None:
        raise ValueError("the page has no value")
    return found


def record_eia_crude_stocks_weekly(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the latest printed crude-oil stocks week, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("a stocks value is not stored without a response")
    if citation_url != EIA_STOCKS_URL:
        raise ValueError("a stocks value is not stored for a different citation")
    if body is None or body.strip() == "":
        raise ValueError("the page has no value")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("this series is not labeled with that feed")
    if permits_financial_use not in (None, False) or class_c_policy not in (None, CLASS_C_POLICY):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    series, unit = _series(body)
    year_month, week, value = _latest(body)
    stored = {
        "series": series,
        "year_month": year_month,
        "week": week,
        "value": value,
        "unit": unit,
        "citation_url": EIA_STOCKS_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
