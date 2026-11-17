"""JMA Niwa hourly page for 17 November 2026, the printed viewable-day limit.

The page refetched on 17 Nov 2026 is:

https://www.data.jma.go.jp/stats/etrn/view/hourly_a1.php?prec_no=22&block_no=0137&year=2026&month=11&day=17&view=

It prints 「2026年11月17日のページを表示しましたが、」 and 「閲覧可能な日は、昨日2026年11月16日までです。」
The heading prints １時間ごとの値. The title prints 気象庁｜過去の気象データ検索.
The response does not print an hour, the column 湿度, or a percent. No humidity
number is stored. Humidity is not calculated.

The station of this citation is 新和. The response does not print 平取, and a
second station is not added.

permits_financial_use stays false. Class C stays closed. A missing citation
writes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

NIWA_URL = (
    "https://www.data.jma.go.jp/stats/etrn/view/hourly_a1.php"
    "?prec_no=22&block_no=0137&year=2026&month=11&day=17&view="
)

PLACE = "新和"
PUBLISHER = "気象庁"
PAGE = "１時間ごとの値"
REQUESTED_PAGE = "2026年11月17日のページを表示しましたが、"
VIEWABLE_LIMIT = "閲覧可能な日は、昨日2026年11月16日までです。"

FORBIDDEN_LABELS = frozenset(
    {
        "biratori",
        "平取",
        "humidity",
        "湿度",
        "percent",
        "yield",
        "price",
        "trade",
        "harvest",
        "completed harvest",
    }
)


def record_jma_niwa_hourly_limit(
    path: Path,
    citation_url: str | None,
    *,
    station: str | None = None,
    place: str | None = None,
    humidity_percent: object = None,
    hour: object = None,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed viewable-day limit, or write nothing."""

    if citation_url is None or citation_url.strip() == "":
        raise ValueError("a viewable-day limit is not stored without a citation_url")
    if citation_url != NIWA_URL:
        raise ValueError("a viewable-day limit is not stored for a different citation")
    if station is not None:
        raise ValueError("a second station is not added")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a viewable-day limit is not a humidity number")
    if any(
        value is not None
        for value in (
            place,
            humidity_percent,
            hour,
            permits_financial_use,
            class_c_policy,
        )
    ):
        raise ValueError("a humidity number is not stored")
    header = {
        "place": PLACE,
        "publisher": PUBLISHER,
        "page": PAGE,
        "requested_page": REQUESTED_PAGE,
        "viewable_limit": VIEWABLE_LIMIT,
        "citation_url": NIWA_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
