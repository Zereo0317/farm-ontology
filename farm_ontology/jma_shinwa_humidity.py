"""Shinwa hourly humidity, and the printed Hiratori station-list facts.

The hourly page opened on 17 Nov 2026 is:

https://www.data.jma.go.jp/stats/etrn/view/hourly_a1.php?prec_no=22&block_no=0137&year=2026&month=11&day=16&view=

Its heading prints 新和（日高地方) and 2026年11月16日. The row 時 = 1 prints
91 in the column 湿度(％). The same row prints 3.8 in 気温(℃) and 2.5 in
露点温度(℃). Those two cells stay under their own column labels. Humidity
is not calculated from them. The place label is 新和. This is not a 平取
reading and not a Biratori farm reading.

The station list the 平取 page links prints block 1594, humidity flag 0,
and the observation end 2004年10月11日まで観測:

https://www.data.jma.go.jp/stats/etrn/select/prefecture.php?prec_no=22&block_no=1594&year=&month=&day=&view=

The 平取 station page has no hourly humidity table and no humidity percent:

https://www.data.jma.go.jp/stats/etrn/index.php?prec_no=22&block_no=1594&year=&month=&day=&view=

permits_financial_use stays false. Class C stays closed. A missing citation
writes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

SHINWA_URL = (
    "https://www.data.jma.go.jp/stats/etrn/view/hourly_a1.php"
    "?prec_no=22&block_no=0137&year=2026&month=11&day=16&view="
)
STATION_LIST_URL = (
    "https://www.data.jma.go.jp/stats/etrn/select/prefecture.php"
    "?prec_no=22&block_no=1594&year=&month=&day=&view="
)
STATION_PAGE_URL = (
    "https://www.data.jma.go.jp/stats/etrn/index.php"
    "?prec_no=22&block_no=1594&year=&month=&day=&view="
)

PLACE = "新和"
HEADING = "新和（日高地方)"
DATE = "2026年11月16日"
HOUR_COLUMN = "時"
HOUR = "1"
HUMIDITY_COLUMN = "湿度(％)"
HUMIDITY_PERCENT = 91
TEMPERATURE_COLUMN = "気温(℃)"
TEMPERATURE = 3.8
DEWPOINT_COLUMN = "露点温度(℃)"
DEWPOINT = 2.5
STATION = "平取"
BLOCK = "1594"
HUMIDITY_FLAG = "0"
OBSERVATION_END = "2004年10月11日まで観測"

FORBIDDEN_LABELS = frozenset(
    {
        "biratori",
        "平取",
        "farm reading",
        "biratori farm reading",
        "yield",
        "price",
        "trade",
        "harvest",
        "completed harvest",
    }
)


def record_jma_shinwa_humidity(
    path: Path,
    citation_url: str | None,
    *,
    station_list_citation_url: str | None = None,
    station_page_citation_url: str | None = None,
    place: str | None = None,
    humidity_percent: object = None,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed cells, or write nothing."""

    citations = (
        citation_url,
        station_list_citation_url,
        station_page_citation_url,
    )
    if any(value is None or str(value).strip() == "" for value in citations):
        raise ValueError("a humidity cell is not stored without a citation_url")
    if (
        citation_url != SHINWA_URL
        or station_list_citation_url != STATION_LIST_URL
        or station_page_citation_url != STATION_PAGE_URL
    ):
        raise ValueError("a humidity cell is not stored for a different citation")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("91 is not a Biratori farm reading")
    if any(
        value is not None
        for value in (place, humidity_percent, permits_financial_use, class_c_policy)
    ):
        raise ValueError("a humidity cell is not stored with a different value")
    header = {
        "place": PLACE,
        "heading": HEADING,
        "date": DATE,
        "hour_column": HOUR_COLUMN,
        "hour": HOUR,
        "cells": [
            {"column": HUMIDITY_COLUMN, "value": HUMIDITY_PERCENT},
            {"column": TEMPERATURE_COLUMN, "value": TEMPERATURE},
            {"column": DEWPOINT_COLUMN, "value": DEWPOINT},
        ],
        "citation_url": SHINWA_URL,
        "hiratori_station_list": {
            "station": STATION,
            "block": BLOCK,
            "humidity_flag": HUMIDITY_FLAG,
            "observation_end": OBSERVATION_END,
            "citation_url": STATION_LIST_URL,
        },
        "hiratori_station_page": {
            "station": STATION,
            "hourly_humidity_table": False,
            "citation_url": STATION_PAGE_URL,
        },
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
