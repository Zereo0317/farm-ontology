"""One printed WASDE forecast quantity.

The citation already stored for the landing page is

https://www.usda.gov/oce/commodity-markets/wasde

That page links the November 2026 WASDE Report text at

https://www.usda.gov/oce/commodity/wasde/wasde1126.txt

The text opened from that link prints World Wheat Output for
2026/27 (Proj.) Nov as 827.51 million metric tons. The row is marked
(Proj.). The stored record is that one cell, and its kind is
published_forecast. It is not a completed harvest. The Trade column on
the same line is not stored. A forecast is not a price or a trade.

permits_financial_use stays false. Class C stays closed. A missing
citation, a failed request, or a report that does not print this cell
writes nothing. This module is not called from a field save.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

REPORT_URL = "https://www.usda.gov/oce/commodity/wasde/wasde1126.txt"

SERIES = "Wheat"
AREA = "World"
ITEM = "Output"
PERIOD = "2026/27 (Proj.)"
MONTH = "Nov"
UNIT = "Million Metric Tons"
KIND = "published_forecast"

FORBIDDEN_LABELS = frozenset(
    {
        "price",
        "trade",
        "settlement",
        "yield",
        "harvest",
        "completed harvest",
        "observation",
    }
)


def _printed_forecast(body: str) -> dict:
    """Read the World Wheat Output cell, or refuse the report."""

    lines = body.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    start = None
    for index, line in enumerate(lines):
        if line.strip() != "Million Metric Tons":
            continue
        window = "\n".join(lines[index : index + 6])
        if "Output" in window and "Trade" in window:
            start = index
            break
    if start is None:
        raise ValueError("the report prints no quantity")
    world = None
    end = None
    header = None
    for index in range(start, len(lines)):
        stripped = lines[index].strip()
        if header is None and "Output" in lines[index] and "Trade" in lines[index]:
            header = lines[index]
        if stripped == "World" and world is None:
            world = index
        elif world is not None and stripped == "United States":
            end = index
            break
    if header is None or world is None or end is None:
        raise ValueError("the report prints no quantity")
    if header.find("Output") < 0 or header.find("Output") >= header.find("Trade"):
        raise ValueError("the report prints no quantity")
    block = lines[world:end]
    wheat = next((index for index, line in enumerate(block) if line.strip() == "Wheat"), None)
    if wheat is None:
        raise ValueError("the report prints no quantity")
    period = None
    for index in range(wheat + 1, len(block)):
        stripped = block[index].strip()
        if stripped == PERIOD:
            period = index
            break
        if (
            stripped
            and not stripped.startswith("202")
            and not stripped.startswith("Oct")
            and not stripped.startswith("Nov")
        ):
            break
    if period is None:
        raise ValueError("the report prints no quantity")
    token = None
    for index in range(period + 1, len(block)):
        stripped = block[index].strip()
        if stripped.startswith("Nov"):
            numbers = re.findall(r"\d+\.\d+", block[index])
            token = numbers[0] if numbers else None
            break
        if stripped and not stripped.startswith("Oct"):
            break
    if token is None:
        raise ValueError("the report prints no quantity")
    number = float(token)
    if json.dumps(number) != token:
        raise ValueError("the report prints no quantity")
    return {
        "series": SERIES,
        "area": AREA,
        "item": ITEM,
        "period": PERIOD,
        "month": MONTH,
        "value": number,
        "unit": UNIT,
        "kind": KIND,
    }


def record_wasde_forecast(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed forecast cell, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("a forecast is not stored without the report")
    if citation_url != REPORT_URL:
        raise ValueError("a forecast is not stored for a different citation")
    if body is None or body.strip() == "":
        raise ValueError("the report prints no quantity")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a forecast is not a price, a trade, or a completed harvest")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    stored = _printed_forecast(body)
    stored["citation_url"] = REPORT_URL
    stored["permits_financial_use"] = False
    stored["class_c_policy"] = CLASS_C_POLICY
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
