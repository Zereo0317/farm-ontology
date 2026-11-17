"""Printed 新和 relative humidity for 16 November 2026.

The hourly page refetched on 17 Nov 2026 is:

https://www.data.jma.go.jp/stats/etrn/view/hourly_a1.php?prec_no=22&block_no=0137&year=2026&month=11&day=16&view=

The heading prints 新和（日高地方) and 2026年11月16日. The row whose 時
cell is 1 prints 91 in the column 湿度(％). That percent is the printed
cell. Humidity is not calculated.

The station of this citation is 新和. The response does not print 平取,
and a second station is not added.

permits_financial_use stays false. Class C stays closed. A missing
citation writes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

NIWA_URL = (
    "https://www.data.jma.go.jp/stats/etrn/view/hourly_a1.php"
    "?prec_no=22&block_no=0137&year=2026&month=11&day=16&view="
)

PLACE = "新和"
HEADING = "新和（日高地方)\u30002026年11月16日（１時間ごとの値）"
DATE = "2026年11月16日"
HOUR_COLUMN = "時"
HOUR = "1"
HUMIDITY_COLUMN = "湿度(％)"
HUMIDITY_PERCENT = 91

FORBIDDEN_LABELS = frozenset(
    {
        "biratori",
        "平取",
        "calculated",
        "yield",
        "price",
        "trade",
        "harvest",
        "completed harvest",
    }
)


def record_jma_niwa_hour_humidity(
    path: Path,
    citation_url: str | None,
    *,
    station: str | None = None,
    place: str | None = None,
    hour: object = None,
    humidity_percent: object = None,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed humidity cell, or write nothing."""

    if citation_url is None or citation_url.strip() == "":
        raise ValueError("a humidity cell is not stored without a citation_url")
    if citation_url != NIWA_URL:
        raise ValueError("a humidity cell is not stored for a different citation")
    if station is not None:
        raise ValueError("a second station is not added")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a humidity cell is not a 平取 reading")
    if any(
        value is not None
        for value in (
            place,
            hour,
            humidity_percent,
            permits_financial_use,
            class_c_policy,
        )
    ):
        raise ValueError("a humidity cell is not stored with a different value")
    header = {
        "place": PLACE,
        "heading": HEADING,
        "date": DATE,
        "hour_column": HOUR_COLUMN,
        "hour": HOUR,
        "humidity_column": HUMIDITY_COLUMN,
        "humidity_percent": HUMIDITY_PERCENT,
        "citation_url": NIWA_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
