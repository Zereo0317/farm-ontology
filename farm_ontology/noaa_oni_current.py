"""Latest NOAA Oceanic Niño Index from the cited page.

The citation already stored in the tests is

https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v5/

The refetch of that URL returned HTTP 200 and stayed on that URL.
The page prints the Oceanic Niño Index (ONI). The latest printed
season is AMJ 2026 and the printed anomaly is 1.0. The same page
states that ONI values may change up to two months after the initial
real-time posting. The header record stores no anomaly. This record
is not labeled finished, a forecast, or a trade. A request that fails,
a missing citation, or a page with no anomaly number writes nothing.
An anomaly is not invented.
permits_financial_use stays false. Class C stays closed.
"""

from __future__ import annotations

import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

from farm_ontology.noaa_oni import NOAA_ONI_URL
from farm_ontology.policy import CLASS_C_POLICY

FORBIDDEN_LABELS = frozenset(
    {
        "price",
        "trade",
        "finished",
        "forecast",
        "settlement",
        "yield",
        "harvest",
        "completed harvest",
    }
)
_SERIES = "Oceanic Niño Index (ONI)"
_STATEMENT = (
    "Because of the high frequency filter applied to the ERSSTv5 data "
    "(Huang et al. 2017, J.Climate), ONI values may change up to two months "
    'after the initial "real time" value is posted. Therefore, the most recent '
    "ONI values should be considered an estimate."
)
_NUMBER = re.compile(r"-?\d+\.\d+")


class _Rows(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "tr":
            self._row = []
        elif tag == "td" and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if any(self._row):
                self.rows.append(self._row)
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


def _plain(body: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", body))
    return " ".join(text.split())


def _reading(body: str) -> dict:
    text = _plain(body)
    if _SERIES not in text:
        raise ValueError("the page has no series")
    if _STATEMENT not in text:
        raise ValueError("the page does not state that the latest values can change")
    parser = _Rows()
    parser.feed(body)
    header: list[str] | None = None
    latest: tuple[str, str, str] | None = None
    for row in parser.rows:
        if row and row[0] == "Year" and "DJF" in row:
            header = row
            continue
        if header is None or not re.fullmatch(r"\d{4}", row[0] if row else ""):
            continue
        for index, cell in enumerate(row[1:], start=1):
            if index >= len(header) or not _NUMBER.fullmatch(cell):
                continue
            latest = (header[index], row[0], cell)
    if latest is None:
        raise ValueError("the page has no value")
    season, year, token = latest
    number = float(token)
    if json.dumps(number) != token:
        number = token
    return {
        "series": _SERIES,
        "season": f"{season} {year}",
        "value": number,
        "statement": _STATEMENT,
        "kind": "index",
    }


def record_noaa_oni_current(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed index, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("an index is not stored without a response")
    if citation_url != NOAA_ONI_URL:
        raise ValueError("an index is not stored for a different citation")
    if body is None or body.strip() == "":
        raise ValueError("the page has no value")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("an index is not finished, a forecast, or a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (None, CLASS_C_POLICY):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    stored = _reading(body)
    stored["citation_url"] = NOAA_ONI_URL
    stored["permits_financial_use"] = False
    stored["class_c_policy"] = CLASS_C_POLICY
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
