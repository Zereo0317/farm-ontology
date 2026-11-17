"""Tokyo relative humidity for 16 November 2026 from the cited JMA page.

The refetch of

https://www.data.jma.go.jp/stats/etrn/view/hourly_s1.php?prec_no=44&block_no=47662&year=2026&month=11&day=16&view=

returned HTTP 200. The heading prints 東京（東京都)　2026年11月16日.
The humidity column prints ％. Hour 6 prints 88. The last hour that
prints a percent is 24, and that percent is 55. The stored percent is
55. A relative humidity is not calculated from temperature and dewpoint.
A request that fails, or a page with no humidity, writes nothing.
No second station is added.
permits_financial_use stays false. Class C stays closed.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

TOKYO_HOURLY_URL = (
    "https://www.data.jma.go.jp/stats/etrn/view/hourly_s1.php"
    "?prec_no=44&block_no=47662&year=2026&month=11&day=16&view="
)
HUMIDITY_AT = 7

FORBIDDEN_LABELS = frozenset(
    {
        "osaka",
        "大阪",
        "biratori",
        "平取",
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


def _heading(body: str) -> tuple[str, str]:
    match = re.search(
        r"(東京（東京都\))\u3000(\d{4}年\d{1,2}月\d{1,2}日)",
        body,
    )
    if match is None:
        raise ValueError("the page has no humidity")
    return match.group(1), match.group(2)


def _reading(body: str) -> dict:
    if "湿度" not in body or "％" not in body:
        raise ValueError("the page has no humidity")
    place, observed_on = _heading(body)
    parser = _Rows()
    parser.feed(body)
    found: tuple[str, str] | None = None
    for row in parser.rows:
        if len(row) <= HUMIDITY_AT or not re.fullmatch(r"\d{1,2}", row[0]):
            continue
        percent = row[HUMIDITY_AT]
        if re.fullmatch(r"\d{1,3}", percent):
            found = (row[0], percent)
    if found is None:
        raise ValueError("the page has no humidity")
    hour, percent = found
    return {
        "place": place,
        "date": observed_on,
        "hour": int(hour),
        "relative_humidity_percent": int(percent),
        "unit": "％",
    }


def record_jma_tokyo_humidity_1116(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the last printed Tokyo humidity, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("a relative humidity is not stored without a response")
    if citation_url != TOKYO_HOURLY_URL:
        raise ValueError("a relative humidity is not stored for a different citation")
    if body is None or body.strip() == "":
        raise ValueError("the page has no humidity")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a relative humidity is not stored for a second station")
    if permits_financial_use not in (None, False) or class_c_policy not in (None, CLASS_C_POLICY):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    reading = _reading(body)
    reading["citation_url"] = TOKYO_HOURLY_URL
    reading["permits_financial_use"] = False
    reading["class_c_policy"] = CLASS_C_POLICY
    path.write_text(
        json.dumps(reading, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
