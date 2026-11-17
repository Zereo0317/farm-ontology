"""Printed soybean harvest totals from the opened e-Stat file.

The file is f002-06-021.xls, already opened. Two harvest rows are stored:
全国 252,400 t and 北海道 132,400 t, for 大豆, 令和６年産, 収穫量.
北海道 is printed twice, under 全国農業地域 and 都道府県, and is stored
once. No other prefecture is stored. Each row is a national or prefecture
total, not the Biratori field and not a yield for PC24+PVC. The figures
are not a trade. permits_financial_use stays false.
permits_financial_use_test is not set. Class C stays closed. This module
does not change the header that stores no figure. This module is not
called from a field save.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

FILE_URL = (
    "https://www.e-stat.go.jp/stat-search/file-download"
    "?statInfId=000040286486&fileKind=0"
)
CROP = "大豆"
PERIOD = "令和６年産"
SERIES = "収穫量"
ROW_LABEL = "national or prefecture total"
_LINE = re.compile(
    r"^(全国|全国農業地域|都道府県)\t([^\t]+)\t([0-9,]+)\s*$",
    re.M,
)
FORBIDDEN_LABELS = frozenset(
    {
        "yield",
        "trade",
        "biratori",
        "biratori field",
        "pc24+pvc",
        "completed harvest",
        "harvest yield",
    }
)


def record_harvest_totals(
    path: Path,
    file_text: str | None = None,
    *,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the two printed harvest rows, or write nothing."""

    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or any(character.isdigit() for character in label)
    ):
        raise ValueError("a national or prefecture total is not a yield and not a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    if permits_financial_use_test is not None:
        raise ValueError("permits_financial_use_test is not set")
    if not file_text or not file_text.strip():
        raise ValueError("the file prints no harvest row")
    if CROP not in file_text or PERIOD not in file_text or SERIES not in file_text:
        raise ValueError("the file prints no harvest row")
    national = []
    hokkaido: dict[str, list[str]] = {"全国農業地域": [], "都道府県": []}
    for heading, area, value in _LINE.findall(file_text):
        if heading == "全国" and area == SERIES:
            national.append(value)
            continue
        if area == "北海道" and heading in hokkaido:
            hokkaido[heading].append(value)
    hokkaido_values = hokkaido["全国農業地域"] + hokkaido["都道府県"]
    if (
        len(national) != 1
        or hokkaido["全国農業地域"] != ["132,400"]
        or hokkaido["都道府県"] != ["132,400"]
        or len(set(hokkaido_values)) != 1
    ):
        raise ValueError("the file prints no single pair of harvest rows")
    if national[0] != "252,400":
        raise ValueError("the file prints no single pair of harvest rows")
    row = {
        "label": ROW_LABEL,
        "not_the_biratori_field": True,
        "not_a_yield_for": "PC24+PVC",
        "not_a_trade": True,
    }
    stored = {
        "crop": CROP,
        "period": PERIOD,
        "series": SERIES,
        "unit": "t",
        "citation_url": FILE_URL,
        "rows": [
            {"area": "全国", "value": national[0], **row},
            {
                "area": "北海道",
                "value": hokkaido_values[0],
                "printed_under": ["全国農業地域", "都道府県"],
                **row,
            },
        ],
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
