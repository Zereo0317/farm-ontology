"""One printed WASDE soybean projection.

The opened text is

https://www.usda.gov/oce/commodity/wasde/wasde1126.txt

The stored cell is the November row of World Soybean Supply and Use,
column Domestic Total, for 2026/27 (Proj.). The printed number is kept
with crop soybean, area World, period 2026/27, and column Domestic
Total. The label is projection. No other cell is stored. The wheat
output cell is not stored again. A projection is not a completed
harvest, not the Biratori field, and not a trade.
permits_financial_use stays false. permits_financial_use_test is not
set. Class C stays closed. A report that does not print this cell
writes nothing. This module does not change the WASDE header. This
module is not called from a field save.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

REPORT_URL = "https://www.usda.gov/oce/commodity/wasde/wasde1126.txt"
_NUMBER = re.compile(r"\d+\.\d+")
FORBIDDEN_LABELS = frozenset(
    {
        "harvest",
        "completed harvest",
        "yield",
        "trade",
        "biratori",
        "biratori field",
        "wheat",
        "price",
        "settlement",
    }
)


def _domestic_total(body: str) -> str:
    """Read the November World Domestic Total cell, or refuse the report."""

    lines = body.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    start = next(
        (index for index, line in enumerate(lines) if "World Soybean Supply and Use" in line),
        None,
    )
    if start is None:
        raise ValueError("the report prints no soybean domestic-total cell")
    end = next(
        (
            index
            for index, line in enumerate(lines)
            if index > start and "World Soybean Meal" in line
        ),
        len(lines),
    )
    section = lines[start:end]
    header = "\n".join(section[:12])
    if "Million Metric Tons" not in header or "Domestic" not in header:
        raise ValueError("the report prints no soybean domestic-total cell")
    imports_at = header.find("Imports")
    crush_at = header.find("Crush")
    total_at = header.find("Total")
    if not (0 <= imports_at < crush_at < total_at):
        raise ValueError("the report prints no soybean domestic-total cell")
    projected = next(
        (index for index, line in enumerate(section) if line.strip() == "2026/27 Proj."),
        None,
    )
    if projected is None:
        raise ValueError("the report prints no soybean domestic-total cell")
    world = next(
        (
            index
            for index, line in enumerate(section)
            if index > projected
            and line.strip().startswith("World")
            and "Less" not in line
        ),
        None,
    )
    if world is None:
        raise ValueError("the report prints no soybean domestic-total cell")
    november = []
    for line in section[world + 1 :]:
        stripped = line.strip()
        if not stripped or stripped.startswith("Oct"):
            continue
        if stripped.startswith("Nov"):
            november.append(_NUMBER.findall(line))
            continue
        break
    if len(november) != 1 or len(november[0]) != 7:
        raise ValueError("the report prints no soybean domestic-total cell")
    return november[0][4]


def record_soybean_domestic_total(
    path: Path,
    body: str | None = None,
    *,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed Domestic Total cell, or write nothing."""

    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or any(character.isdigit() for character in label)
    ):
        raise ValueError("a projection is not a harvest and not a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    if permits_financial_use_test is not None:
        raise ValueError("permits_financial_use_test is not set")
    if body is None or not body.strip():
        raise ValueError("the report prints no soybean domestic-total cell")
    value = _domestic_total(body)
    stored = {
        "crop": "soybean",
        "area": "World",
        "period": "2026/27",
        "month": "Nov",
        "column": "Domestic Total",
        "value": value,
        "unit": "Million Metric Tons",
        "label": "projection",
        "kind": "projection",
        "not_a_completed_harvest": True,
        "not_the_biratori_field": True,
        "not_a_trade": True,
        "citation_url": REPORT_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
