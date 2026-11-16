"""NBS industrial value-added header.

One report from the release page that was already opened. The stored
record is the printed header plus the copyright line. The growth figure
in the title was not copied. Unit and administrative area were not
opened and are not filled. The source line prints 来源：国家统计局. The
release date printed beside the title is 2026/11/16 10:00. The scope
sentence prints 规模以上工业的统计范围为年主营业务收入2000万元及以上的工业企业。
The 2000万元 figure is the scope threshold in that sentence. It is not
an output value. The method sentence prints
规模以上工业企业工业生产报表按月进行全面调查（1月份数据免报）。
The service-terms page was not opened. A bulk history file was not
opened. No growth rate is stored. The report is not a quantity of goods
and is not a trading right. This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

NBS_INDUSTRIAL_URL = "https://www.stats.gov.cn/sj/zxfb/202611/t20261116_1965842.html"

PUBLISHER = "国家统计局"
PRODUCT = "规模以上工业增加值"
PERIOD = "2026年10月份"
NOT_OPENED = "the field was not opened"
KIND = "report"
COPYRIGHT_NOTICE = "版权所有: 国家统计局"
SOURCE_LINE = "来源：国家统计局"
RELEASE_TIME_NOT_A_RATE = "2026/11/16 10:00"
SCOPE_SENTENCE = "规模以上工业的统计范围为年主营业务收入2000万元及以上的工业企业。"
METHOD_SENTENCE = "规模以上工业企业工业生产报表按月进行全面调查（1月份数据免报）。"
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
    "growth rate",
    "growth",
    "增长",
    "增长率",
    "同比",
    "环比",
})


def _stores_growth_rate(label) -> bool:
    text = str(label).strip()
    if any(mark in text for mark in ("%", "％", ":", "/", "增长", "同比", "环比", "2000")):
        return True
    compact = text.replace(".", "", 1).replace("-", "", 1).replace("+", "", 1)
    return compact.isdigit()


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
        str(label).strip().lower() in FORBIDDEN_LABELS or _stores_growth_rate(label)
    ):
        raise ValueError(
            "an NBS industrial figure is not a settlement, a yield, a trade, "
            "a forecast, an observation, a completed harvest, or a benchmark, "
            "and a growth rate is not stored"
        )
    if unit is not None or administrative_area is not None:
        raise ValueError("unit and administrative_area were not opened")
    if period is not None or value is not None:
        raise ValueError("a growth rate is not stored")
    citation = str(citation_url).strip()
    if citation != NBS_INDUSTRIAL_URL:
        raise ValueError("citation_url is not the opened NBS release")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": NOT_OPENED,
        "administrative_area": NOT_OPENED,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
        "copyright_notice": COPYRIGHT_NOTICE,
        "source_line": SOURCE_LINE,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "nbs-industrial.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
