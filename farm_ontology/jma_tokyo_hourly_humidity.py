"""Tokyo hourly relative humidity, copied from the live JMA page.

The page opened on 17 Nov 2026 is the hourly observation for 16 Nov 2026:

https://www.data.jma.go.jp/stats/etrn/view/hourly_s1.php?prec_no=44&block_no=47662&year=2026&month=11&day=16&view=

The heading prints 東京（東京都) and 2026年11月16日. The row 時 = 6 prints 88
in the column 湿度(％). This is a Tokyo observation, not a Biratori
observation, and not a value calculated from 露点温度 or 気温. Those other
cells are not stored as humidity.

permits_financial_use stays false. Class C stays closed. A missing citation
writes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

JMA_TOKYO_HOURLY_URL = (
    "https://www.data.jma.go.jp/stats/etrn/view/hourly_s1.php"
    "?prec_no=44&block_no=47662&year=2026&month=11&day=16&view="
)

PLACE = "東京（東京都)"
DATE = "2026年11月16日"
HOUR_COLUMN = "時"
HOUR = "6"
HUMIDITY_COLUMN = "湿度(％)"
HUMIDITY_PERCENT = 88

FORBIDDEN_LABELS = frozenset(
    {
        "biratori",
        "露点温度",
        "気温",
        "yield",
        "price",
        "trade",
        "farm humidity",
        "harvest",
        "completed harvest",
    }
)


def record_jma_tokyo_humidity(
    path: Path,
    citation_url: str | None,
    *,
    place: str | None = None,
    date: str | None = None,
    hour: str | None = None,
    humidity_percent: object = None,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed Tokyo humidity percent, or write nothing."""

    if citation_url is None or citation_url.strip() == "":
        raise ValueError("a Tokyo humidity percent is not stored without a citation_url")
    if citation_url != JMA_TOKYO_HOURLY_URL:
        raise ValueError("a Tokyo humidity percent is not stored for a different citation")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a Tokyo humidity percent is not calculated from 露点温度 or 気温")
    if any(
        value is not None
        for value in (
            place,
            date,
            hour,
            humidity_percent,
            permits_financial_use,
            class_c_policy,
        )
    ):
        raise ValueError("a Tokyo humidity percent is not stored with a different value")
    header = {
        "place": PLACE,
        "date": DATE,
        "hour_column": HOUR_COLUMN,
        "hour": HOUR,
        "column": HUMIDITY_COLUMN,
        "percent": HUMIDITY_PERCENT,
        "citation_url": JMA_TOKYO_HOURLY_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
