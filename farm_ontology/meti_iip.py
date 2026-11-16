"""METI Indices of Industrial Production header.

One report from the Japanese results page that was already opened. The
stored record is the printed header plus the footer copyright. The
citation stays on
https://www.meti.go.jp/statistics/tyo/iip/result-1.html.
The English URL
https://www.meti.go.jp/english/statistics/tyo/iip/index.html
returned the ministry page-not-found document and was not used. The
product name includes 製造工業生産予測指数. That name is not a stored
forecast. The index page says the survey grasps the production plan for the next two months.
That sentence is not a forecast value. Kind stays
report. No index value and no percent change is stored. The 利用規約
page was not opened. A bulk history file was not opened. The results
page links to 時系列データ等ダウンロード and to booklets, and those
files were not opened. The report is not a quantity of goods and is not
a trading right. This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

METI_IIP_URL = "https://www.meti.go.jp/statistics/tyo/iip/result-1.html"
ENGLISH_PAGE_NOT_USED = (
    "https://www.meti.go.jp/english/statistics/tyo/iip/index.html"
)

PUBLISHER = "経済産業省"
PRODUCT = "鉱工業指数(生産・出荷・在庫、生産能力・稼働率)、製造工業生産予測指数"
PERIOD = "2026年9月分"
UNIT = "2020年＝100"
ADMINISTRATIVE_AREA = "日本"
KIND = "report"
COPYRIGHT_NOTICE = (
    "Copyright Ministry of Economy, Trade and Industry. All Rights Reserved."
)
PAGE_SUMMARY = "結果の概要【2026年9月分】"
ANNOUNCEMENT = "（2026年11月16日発表）"
PAGE_HEAD = "鉱工業指数概況【2026年9月分確報】"
SUBTITLE = "製造業の動きから見る日本の景気"
PRINTED_BASES = (
    "鉱工業指数、2020年＝100",
    "製造工業生産能力指数、2020年＝100",
    "製造工業稼働率指数、2020年＝100",
)
PERCENT_COLUMNS = ("前月比（％）", "前年同月比（％）")
DOWNLOAD_LINK = "時系列データ等ダウンロード"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "forecast",
    "observation",
    "completed harvest",
    "public domain",
    "benchmark",
    "quantity of goods",
    "trading right",
    "予測",
    "前月比",
    "前年同月比",
})


def _stores_number(label) -> bool:
    text = str(label)
    if any(character.isdigit() for character in text):
        return True
    return any(mark in text for mark in ("=", "＝", "%", "％"))


def record_series_header(
    directory,
    *,
    citation_url=None,
    label=None,
    period=None,
    unit=None,
    administrative_area=None,
    value=None,
) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and (
        str(label).strip().lower() in FORBIDDEN_LABELS or _stores_number(label)
    ):
        raise ValueError(
            "a METI industrial-index figure is not a settlement, a yield, "
            "a trade, a forecast, an observation, a completed harvest, or a "
            "benchmark, and a number is not stored"
        )
    if (
        period is not None
        or unit is not None
        or administrative_area is not None
        or value is not None
    ):
        raise ValueError("a number is not stored")
    citation = str(citation_url).strip()
    if citation != METI_IIP_URL:
        raise ValueError("citation_url is not the opened METI results page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": UNIT,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
        "copyright_notice": COPYRIGHT_NOTICE,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "meti-iip.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
