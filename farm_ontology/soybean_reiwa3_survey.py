"""Printed 令和３年産 Hokkaido soybean survey cells.

The workbook is f002-03-021.xls. It was opened from the e-Stat series
that already cites f002-06-021.xls, through the printed 令和３年産作物
統計 list and the linked 大豆 table. 令和３年産 is the 2021 crop. The
workbook prints 令和３年産, not the digits 2021.

北海道 is printed under 全国農業地域 and under 都道府県. The three
cells match, so each is stored once: 作付面積 42,000 ha, 10ａ当たり収量
251 kg, and 収穫量 105,400 ｔ. These are prefecture survey totals, not
the Biratori field and not a trade. A cell that is not printed is
omitted. No yield, area, or harvest is invented.
permits_financial_use stays false. permits_financial_use_test is not
set. Class C stays closed. This module does not change the yield-anomaly
coefficient. This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

CITATION_URL = (
    "https://www.e-stat.go.jp/stat-search/files?layout=dataset"
    "&toukei=00500215&tstat=000001013427&tclass1=000001032288"
    "&tclass2=000001032753&tclass3=000001162906&stat_infid=000032210655"
)
FILE_URL = (
    "https://www.e-stat.go.jp/stat-search/file-download"
    "?statInfId=000032210655&fileKind=0"
)
FILE_NAME = "f002-03-021.xls"
CROP = "大豆"
PERIOD = "令和３年産"
CROP_YEAR = 2021
AREA = "北海道"
GROUPINGS = ("全国農業地域", "都道府県")
SERIES = (
    ("作付面積", "ha"),
    ("10ａ当たり収量", "kg"),
    ("収穫量", "ｔ"),
)
ROW_LABEL = "prefecture survey total"
FORBIDDEN_LABELS = frozenset(
    {
        "yield",
        "trade",
        "biratori",
        "biratori field",
        "completed harvest",
        "forecast",
    }
)


def _table(file_text: str) -> list[list[str]]:
    rows = []
    for raw in file_text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not raw.strip():
            continue
        rows.append(raw.split("\t"))
    return rows


def _columns(rows: list[list[str]]) -> dict[str, tuple[int, str]]:
    header = next(
        (
            parts
            for parts in rows
            if all(name in parts for name, _unit in SERIES)
        ),
        None,
    )
    units = next(
        (
            parts
            for parts in rows
            if all(unit in parts for _name, unit in SERIES)
        ),
        None,
    )
    if header is None or units is None:
        raise ValueError("the file does not print the survey columns")
    columns = {}
    for name, unit in SERIES:
        index = header.index(name)
        printed_unit = units[index] if index < len(units) else ""
        if printed_unit != unit:
            continue
        columns[name] = (index, printed_unit)
    if not columns:
        raise ValueError("the file does not print the survey columns")
    return columns


def _rows(file_text: str) -> list[dict]:
    if CROP not in file_text or PERIOD not in file_text:
        raise ValueError("the file does not print 令和３年産 大豆")
    rows = _table(file_text)
    columns = _columns(rows)
    found: dict[str, dict[str, list[str]]] = {name: {} for name in GROUPINGS}
    section = None
    for parts in rows:
        marker = parts[0].strip()
        if marker in {f"({name})" for name in GROUPINGS}:
            section = marker[1:-1]
            continue
        if section is None or not parts or parts[0].strip() != AREA:
            continue
        for name, (index, _unit) in columns.items():
            if index >= len(parts):
                continue
            value = parts[index].strip()
            if value == "" or value == "x":
                continue
            found[section].setdefault(name, []).append(value)
    stored = []
    for name, unit in SERIES:
        if name not in columns:
            continue
        present = {
            grouping: found[grouping][name]
            for grouping in GROUPINGS
            if name in found[grouping]
        }
        if not present:
            continue
        flat = [value for values in present.values() for value in values]
        if any(len(values) != 1 for values in present.values()) or len(set(flat)) != 1:
            raise ValueError("the file does not print one Hokkaido survey cell")
        stored.append(
            {
                "series": name,
                "value": flat[0],
                "unit": unit,
                "printed_under": [grouping for grouping in GROUPINGS if grouping in present],
            }
        )
    if not stored:
        raise ValueError("the file prints no Hokkaido survey cell")
    return stored


def record_hokkaido_survey(
    path: Path,
    file_text: str | None = None,
    *,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed Hokkaido survey cells, or write nothing."""

    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or any(character.isdigit() for character in label)
    ):
        raise ValueError("a prefecture survey total is not the Biratori field and not a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    if permits_financial_use_test is not None:
        raise ValueError("permits_financial_use_test is not set")
    if not file_text or not file_text.strip():
        raise ValueError("the file prints no Hokkaido survey cell")
    mark = {
        "area": AREA,
        "label": ROW_LABEL,
        "not_the_biratori_field": True,
        "not_a_trade": True,
    }
    stored = {
        "crop": CROP,
        "period": PERIOD,
        "crop_year": CROP_YEAR,
        "area": AREA,
        "file_name": FILE_NAME,
        "citation_url": CITATION_URL,
        "file_url": FILE_URL,
        "rows": [{**row, **mark} for row in _rows(file_text)],
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
