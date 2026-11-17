"""Tokyo hourly relative humidity from the cited JMA page.

The refetch of

https://www.data.jma.go.jp/stats/etrn/view/hourly_s1.php?prec_no=44&block_no=47662&year=2026&month=11&day=17&view=

returned HTTP 200. The body prints that the 2026年11月17日 page was
shown, and that viewable days run through yesterday, 2026年11月16日.
It prints no humidity percent. Those printed facts are stored. No
humidity number is stored. A relative humidity is not calculated from temperature and dewpoint.
A request that fails writes nothing.
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
    "?prec_no=44&block_no=47662&year=2026&month=11&day=17&view="
)

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


def _reading(body: str) -> dict:
    parser = _Rows()
    parser.feed(body)
    hour_at = None
    humidity_at = None
    found: tuple[str, str] | None = None
    for row in parser.rows:
        if hour_at is None:
            for index, cell in enumerate(row):
                if cell == "時":
                    hour_at = index
                if "湿度" in cell:
                    humidity_at = index
            if hour_at is None or humidity_at is None:
                hour_at = None
                humidity_at = None
            continue
        if len(row) <= max(hour_at, humidity_at):
            continue
        hour = row[hour_at]
        percent = row[humidity_at]
        if re.fullmatch(r"\d{1,2}", hour) and re.fullmatch(r"\d{1,3}", percent):
            found = (hour, percent)
    if found is None:
        raise ValueError("the page has no humidity")
    hour, percent = found
    return {"hour": hour, "relative_humidity_percent": percent}


def _printed_facts(body: str) -> dict:
    shown = re.search(r"(\d{4}年\d{1,2}月\d{1,2}日)のページを表示しました", body)
    viewable = re.search(r"閲覧可能な日は、昨日(\d{4}年\d{1,2}月\d{1,2}日)までです", body)
    if shown is None or viewable is None:
        raise ValueError("the page does not print those facts")
    try:
        _reading(body)
    except ValueError:
        humidity_printed = False
    else:
        humidity_printed = True
    if humidity_printed:
        raise ValueError("a humidity number is not stored")
    return {
        "page_shown": shown.group(1),
        "viewable_through": viewable.group(1),
        "humidity_percent_printed": False,
    }


def record_jma_tokyo_printed_facts(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed page facts, with no humidity number."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("the printed facts are not stored without a response")
    if citation_url != TOKYO_HOURLY_URL:
        raise ValueError("the printed facts are not stored for a different citation")
    if body is None or body.strip() == "":
        raise ValueError("the page does not print those facts")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("the printed facts are not stored for a second station")
    if permits_financial_use not in (None, False) or class_c_policy not in (None, CLASS_C_POLICY):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    facts = _printed_facts(body)
    facts["citation_url"] = TOKYO_HOURLY_URL
    facts["permits_financial_use"] = False
    facts["class_c_policy"] = CLASS_C_POLICY
    path.write_text(
        json.dumps(facts, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def record_jma_tokyo_humidity(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write a printed Tokyo relative humidity, or write nothing."""

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
