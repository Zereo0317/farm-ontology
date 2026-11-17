"""Printed soybean survey yield rates from the opened e-Stat file.

The file is f002-06-021.xls, already opened. The stored rows are the
printed 10ａ当たり収量 for 大豆, 令和６年産: 全国 and 北海道. Each value
is stored once with its printed unit. 北海道 is printed under both
全国農業地域 and 都道府県; it is stored once when those cells print the
same value, and both groupings are recorded. 収穫量 is not stored
again. No other prefecture is stored. Each row is the survey yield
rate, not the Biratori field and not a yield for PC24+PVC. The figures
are not a trade. A cell that is not printed is omitted. No number is
invented. permits_financial_use stays false.
permits_financial_use_test is not set. Class C stays closed. This
module does not change the header that stores no figure. This module
is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

FILE_URL = (
    "https://www.e-stat.go.jp/stat-search/file-download"
    "?statInfId=000040286486&fileKind=0"
)
CROP = "大豆"
PERIOD = "令和６年産"
SERIES = "10ａ当たり収量"
UNIT = "kg"
ROW_LABEL = "survey yield rate"
FORBIDDEN_LABELS = frozenset(
    {
        "yield",
        "trade",
        "biratori",
        "biratori field",
        "pc24+pvc",
        "completed harvest",
        "harvest",
    }
)


def _rows(file_text: str) -> list[dict]:
    if CROP not in file_text or PERIOD not in file_text or SERIES not in file_text:
        raise ValueError("the file prints no survey yield rate")
    active = False
    national: list[str] = []
    hokkaido: dict[str, list[str]] = {"全国農業地域": [], "都道府県": []}
    for raw in file_text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.strip()
        if not line:
            continue
        parts = line.split("\t")
        if parts[0] == SERIES and len(parts) == 2 and parts[1] == UNIT:
            active = True
            continue
        if len(parts) == 2 and parts[0] != "全国":
            active = False
            continue
        if not active:
            continue
        if len(parts) == 3 and parts[0] == "全国" and parts[2] == UNIT:
            national.append(parts[1])
            continue
        if (
            len(parts) == 4
            and parts[0] in hokkaido
            and parts[1] == "北海道"
            and parts[3] == UNIT
        ):
            hokkaido[parts[0]].append(parts[2])
    rows = []
    if len(national) == 1:
        rows.append({"area": "全国", "value": national[0], "unit": UNIT})
    elif national:
        raise ValueError("the file prints no single national survey yield rate")
    present = {name: values for name, values in hokkaido.items() if values}
    if present:
        flat = [value for values in present.values() for value in values]
        if any(len(values) != 1 for values in present.values()) or len(set(flat)) != 1:
            raise ValueError("the file prints no single Hokkaido survey yield rate")
        rows.append(
            {
                "area": "北海道",
                "value": flat[0],
                "unit": UNIT,
                "printed_under": [name for name in ("全国農業地域", "都道府県") if name in present],
            }
        )
    if not rows:
        raise ValueError("the file prints no survey yield rate")
    return rows


def record_yield_rates(
    path: Path,
    file_text: str | None = None,
    *,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed survey yield rates, or write nothing."""

    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or any(character.isdigit() for character in label)
    ):
        raise ValueError("a survey yield rate is not the field yield and not a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    if permits_financial_use_test is not None:
        raise ValueError("permits_financial_use_test is not set")
    if not file_text or not file_text.strip():
        raise ValueError("the file prints no survey yield rate")
    mark = {
        "label": ROW_LABEL,
        "not_the_biratori_field": True,
        "not_a_yield_for": "PC24+PVC",
        "not_a_trade": True,
    }
    stored = {
        "crop": CROP,
        "period": PERIOD,
        "series": SERIES,
        "citation_url": FILE_URL,
        "rows": [{**row, **mark} for row in _rows(file_text)],
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
