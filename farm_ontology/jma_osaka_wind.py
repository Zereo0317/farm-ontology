"""Osaka wind cells from the live JMA daily table, marks kept.

The page opened on 17 Nov 2026 is:

https://www.data.jma.go.jp/stats/data/mdrr/synopday/data1s.html

The heading prints 2026年11月17日　10時現在. For 大阪, the 最大 wind group
prints 風速 3.7], 風向 北], and 起時 08:33]. The unit table prints m/s for
風速. The legend prints 値] as 資料不足値 *2. The bracket stays with each
value. These are not a complete observation. The place is 大阪, not 平取
and not Biratori. Humidity is not calculated.

permits_financial_use stays false. Class C stays closed. A missing citation
writes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

JMA_SYNOPDAY_URL = "https://www.data.jma.go.jp/stats/data/mdrr/synopday/data1s.html"

PLACE = "大阪"
HEADING = "2026年11月17日\u300010時現在"
MARK = "値]"
MARK_MEANING = "資料不足値 *2"
WIND_GROUP = "最大"
WIND_SPEED = "3.7]"
WIND_SPEED_UNIT = "m/s"
WIND_DIRECTION = "北]"
WIND_TIME = "08:33]"

FORBIDDEN_LABELS = frozenset(
    {
        "biratori",
        "平取",
        "humidity",
        "complete observation",
        "yield",
        "price",
        "trade",
        "settlement",
        "harvest",
        "completed harvest",
    }
)


def record_jma_osaka_wind(
    path: Path,
    citation_url: str | None,
    *,
    place: str | None = None,
    wind_speed: object = None,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed Osaka wind cells, or write nothing."""

    if citation_url is None or citation_url.strip() == "":
        raise ValueError("an Osaka wind cell is not stored without a citation_url")
    if citation_url != JMA_SYNOPDAY_URL:
        raise ValueError("an Osaka wind cell is not stored for a different citation")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("an Osaka wind cell is not a complete observation")
    if any(
        value is not None
        for value in (place, wind_speed, permits_financial_use, class_c_policy)
    ):
        raise ValueError("an Osaka wind cell is not stored with a different value")
    header = {
        "place": PLACE,
        "heading": HEADING,
        "mark": MARK,
        "mark_meaning": MARK_MEANING,
        "wind": [
            {
                "group": WIND_GROUP,
                "column": "風速",
                "value": WIND_SPEED,
                "unit": WIND_SPEED_UNIT,
            },
            {"group": WIND_GROUP, "column": "風向", "value": WIND_DIRECTION},
            {"group": WIND_GROUP, "column": "起時", "value": WIND_TIME},
        ],
        "citation_url": JMA_SYNOPDAY_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
