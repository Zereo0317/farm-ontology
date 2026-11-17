"""Current BPA balancing-authority reading from the cited 5-minute file.

The refetch of

https://transmission.bpa.gov/Business/Operations/Wind/baltwg.txt

returned HTTP 200. The last filled row prints 11/16/2026 18:05, Load
8137, VER 126, Hydro 9049, Fossil/Biomass 1172, and Nuclear 1154. The
file prints "Based on 5-min MW readings". Where a printed value differs
from an earlier row, the stored reading is the later printed value.
A request that fails, or a body with no value, unit, or time, writes
nothing. No second balancing authority is added.
permits_financial_use stays false. Class C stays closed.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

BPA_URL = "https://transmission.bpa.gov/Business/Operations/Wind/baltwg.txt"
UNIT_LINE = "Based on 5-min MW readings"
COLUMNS = ("Load", "VER", "Hydro", "Fossil/Biomass", "Nuclear")

FORBIDDEN_LABELS = frozenset(
    {
        "settlement",
        "trade",
        "yield",
        "price",
        "harvest",
        "completed harvest",
    }
)


def _filled_row(line: str) -> dict | None:
    parts = [part.strip() for part in line.split("\t")]
    if len(parts) < 6 or not parts[0][:1].isdigit():
        return None
    if any(part == "" or not part.isdigit() for part in parts[1:6]):
        return None
    reading = {"timestamp": parts[0], "unit": "MW"}
    for name, part in zip(COLUMNS, parts[1:6]):
        reading[name] = int(part)
    return reading


def _current_reading(body: str) -> dict:
    if "BPA Balancing Authority" not in body or UNIT_LINE not in body:
        raise ValueError("the response body has no reading")
    current = None
    for line in body.splitlines():
        row = _filled_row(line)
        if row is not None:
            current = row
    if current is None:
        raise ValueError("the response body has no reading")
    return current


def record_bpa_current(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed current reading, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("a reading is not stored without a response")
    if citation_url != BPA_URL:
        raise ValueError("a reading is not stored for a different citation")
    if body is None or body.strip() == "":
        raise ValueError("the response body has no reading")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a balancing reading is not a settlement or a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (None, CLASS_C_POLICY):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    reading = _current_reading(body)
    reading["basis"] = UNIT_LINE
    reading["citation_url"] = BPA_URL
    reading["permits_financial_use"] = False
    reading["class_c_policy"] = CLASS_C_POLICY
    path.write_text(
        json.dumps(reading, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
