"""data.gov.tw dataset 58977 header.

The page https://data.gov.tw/dataset/58977 was fetched.
The final URL is https://data.gov.tw/dataset/58977.
The citation is the URL that was fetched.
https://data.gov.tw/ is not the citation.
https://data.gov.tw/dataset/58977/ is not the citation.
https://data.gov.tw/licenses is not the citation.
https://opendata.cwa.gov.tw/index is not the citation.
The publisher is 交通部中央氣象署.
數位發展部 is the platform operator, not the dataset publisher.
政府資料開放平臺 is the site name, not the publisher.
The product is 數值預報模式-區域預報模式(WRF).
The document title appends 政府資料開放平臺.
The description prints 數值預報資料. That phrase is the kind.
The kind is not a second product.
The period is 第0小時至第84小時.
每6時 is the update frequency, not the period.
2017-11-01 is the shelf date, not the period.
2026-01-08 11:59 is the metadata update time, not the period.
15公里及3公里 is a resolution, not a unit.
Grib2格式 is a format, not a unit.
Unit was not printed.
生活安全及品質 is a service category, not an area.
Area was not printed.
The licence is 政府資料開放授權條款-第1版.
Resource names are not a second product.
The resource links leave data.gov.tw and were not opened.
Do not store a rainfall amount.
Do not store a temperature.
Do not store a yield.
Do not store a price.
Do not store a trade.
A forecast is not a completed harvest.
permits_financial_use stays false.
Class C stays closed.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

DATA_GOV_TW_58977_URL = "https://data.gov.tw/dataset/58977"

PUBLISHER = "交通部中央氣象署"
PRODUCT = "數值預報模式-區域預報模式(WRF)"
PERIOD = "第0小時至第84小時"
KIND = "數值預報資料"
LICENCE = "政府資料開放授權條款-第1版"
FORBIDDEN_LABELS = frozenset({
    "yield",
    "price",
    "trade",
    "rainfall",
    "rainfall amount",
    "temperature",
    "completed harvest",
    "settlement",
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
    kind=None,
    licence=None,
    value=None,
    permits_financial_use=None,
    class_c_policy=None,
) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and (
        str(label).strip().lower() in FORBIDDEN_LABELS or _stores_figure(label)
    ):
        raise ValueError(
            "a forecast header is not a yield, a price, a trade, a "
            "rainfall amount, or a temperature, and a figure is not stored"
        )
    if period is not None:
        raise ValueError("period is not replaced")
    if unit is not None:
        raise ValueError("unit was not printed")
    if administrative_area is not None:
        raise ValueError("area was not printed")
    if kind is not None:
        raise ValueError("kind is not replaced")
    if licence is not None:
        raise ValueError("licence is not replaced")
    if value is not None:
        raise ValueError("a figure is not stored")
    if permits_financial_use is not None:
        raise ValueError("permits_financial_use stays false")
    if class_c_policy is not None:
        raise ValueError("class C stays closed")
    citation = str(citation_url).strip()
    if citation != DATA_GOV_TW_58977_URL:
        raise ValueError("citation_url is not the fetched page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "citation_url": citation,
        "kind": KIND,
        "licence": LICENCE,
        "permits_financial_use": False,
        "class_c_policy": "closed",
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "data-gov-tw-58977.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
