"""Current Osaka wind reading from the cited JMA national daily table.

The refetch of

https://www.data.jma.go.jp/stats/data/mdrr/synopday/data1s.html

returned HTTP 200. The heading prints 2026年11月17日　10時現在. For 大阪,
the 最大 wind group prints 風速 3.7], 風向 北], and 起時 08:33]. The unit
table prints m/s for 風速. The legend prints 値] as 資料不足値 *2. The
bracket stays on the printed cells. A request that fails, or a body
with no place, speed, direction, or time, writes nothing. No second
station is added.
permits_financial_use stays false. Class C stays closed.
"""

from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

JMA_SYNOPDAY_URL = "https://www.data.jma.go.jp/stats/data/mdrr/synopday/data1s.html"
PLACE = "大阪"
SPEED_AT = 15
DIRECTION_AT = 16
TIME_AT = 17

FORBIDDEN_LABELS = frozenset(
    {
        "biratori",
        "平取",
        "trade",
        "settlement",
        "yield",
        "price",
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
        elif tag == "td" and self._row is not None:
            self._in_cell = True
            self._cell = ""

    def handle_endtag(self, tag):
        if tag == "td" and self._in_cell and self._row is not None:
            self._row.append(" ".join(self._cell.split()))
            self._in_cell = False
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._in_cell:
            self._cell += data


def _heading(body: str) -> str:
    marker = "日別値詳細版:"
    start = body.find(marker)
    if start < 0:
        raise ValueError("the response body has no wind time")
    stop = body.find("）", start)
    if stop < 0:
        raise ValueError("the response body has no wind time")
    heading = body[start + len(marker) : stop].strip()
    if "時現在" not in heading:
        raise ValueError("the response body has no wind time")
    return heading


def _reading(body: str) -> dict:
    if "風速" not in body or "m/s" not in body:
        raise ValueError("the response body has no wind value")
    if "値]" not in body or "資料不足値 *2" not in body:
        raise ValueError("the response body has no wind value")
    parser = _Rows()
    parser.feed(body)
    for row in parser.rows:
        if not row or row[0] != PLACE:
            continue
        if len(row) <= TIME_AT:
            break
        speed = row[SPEED_AT]
        direction = row[DIRECTION_AT]
        wind_time = row[TIME_AT]
        if not speed or not direction or not wind_time:
            break
        return {
            "place": PLACE,
            "heading": _heading(body),
            "group": "最大",
            "speed": speed,
            "unit": "m/s",
            "direction": direction,
            "time": wind_time,
            "mark": "値]",
            "mark_meaning": "資料不足値 *2",
        }
    raise ValueError("the response body has no wind value")


def record_jma_osaka_wind_current(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed Osaka wind reading, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("a wind reading is not stored without a response")
    if citation_url != JMA_SYNOPDAY_URL:
        raise ValueError("a wind reading is not stored for a different citation")
    if body is None or body.strip() == "":
        raise ValueError("the response body has no wind value")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a wind reading is not stored for a second station")
    if permits_financial_use not in (None, False) or class_c_policy not in (None, CLASS_C_POLICY):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    reading = _reading(body)
    reading["citation_url"] = JMA_SYNOPDAY_URL
    reading["permits_financial_use"] = False
    reading["class_c_policy"] = CLASS_C_POLICY
    path.write_text(
        json.dumps(reading, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
