"""China Meteorological Administration CLDAS header.

One catalog header from the page that was already opened. The stored
record is that header. The publisher is 国家气象信息中心(中国气象局气象数据中心).
The product is 中国气象局陆面数据同化系统（CLDAS-V2.0）实时产品数据集. The citation stays on
https://data.cma.cn/data/detail/dataCode/NAFP_CLDAS2.0_RT.html.
https://data.cma.cn/ is not the citation.
The page calls the product a 等经纬度网格融合分析产品.
The real-time product is updated with a lag of one hour: 实时产品实时更新发布,滞后1小时.
An analysis is not a completed harvest.
Do not relabel it as a forecast, a yield, or a trade.
Unit was not opened.
The quality paragraph prints precipitation error figures. Those figures are not copied and no unit is taken from them.
中国区域陆面产品 is a breadcrumb, not the administrative area.
地址：北京海淀区中关村南大街46号 邮编：100081 is the centre's address, not the product area.
datacenter@cma.gov.cn is not stored.
数据资源登记编号 was printed and is not stored.
Sharing level 普通注册用户访问 is not a redistribution grant.
Copyright 2005-2017 国家气象信息中心(中国气象局气象数据中心) is a copyright line, not public domain.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

CMA_WEATHER_URL = "https://data.cma.cn/data/detail/dataCode/NAFP_CLDAS2.0_RT.html"

PUBLISHER = "国家气象信息中心(中国气象局气象数据中心)"
PRODUCT = "中国气象局陆面数据同化系统（CLDAS-V2.0）实时产品数据集"
PERIOD = (
    "数据起始时间 2017年1月19日; 数据终止时间 目前; "
    "制作时间 实时; 更新频率 1小时，1天"
)
NOT_OPENED = "the field was not opened"
ADMINISTRATIVE_AREA = "亚洲区域（0-65°N，60-160°E）"
KIND = "融合分析产品"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "forecast",
    "observation",
    "completed harvest",
    "public domain",
    "benchmark",
    "index",
    "figure",
})


def _stores_figure(label) -> bool:
    return any(character.isdigit() for character in str(label))


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
        str(label).strip().lower() in FORBIDDEN_LABELS or _stores_figure(label)
    ):
        raise ValueError(
            "a CLDAS header is not a settlement, a yield, a trade, a "
            "forecast, an observation, a completed harvest, a benchmark, "
            "or an index, and a figure is not stored"
        )
    if unit is not None:
        raise ValueError("unit was not opened")
    if period is not None or administrative_area is not None:
        raise ValueError("period and administrative_area are not replaced")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != CMA_WEATHER_URL:
        raise ValueError("citation_url is not the opened catalog page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": NOT_OPENED,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "cma-weather.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
