"""Current Northwest soybean cash-bid average from the cited AMS PDF.

The refetch of

https://www.ams.usda.gov/mnreports/ams_3225.pdf

returned HTTP 200. The PDF prints "Grain Report for 11/16/2026 - Final".
Under "US #1  Soybeans  (Bulk)", Country Elevators - Conventional, the
Northwest Bid row prints average 11.1600. The column header prints
Price($/Bu). The block headed Closing Settlement Prices is not stored.
The price range is not stored. A request that fails, or a PDF with no
average, writes nothing.
permits_financial_use stays false. Class C stays closed. The average
is not stored as an executed trade.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

AMS_URL = "https://www.ams.usda.gov/mnreports/ams_3225.pdf"
COMMODITY = "US #1  Soybeans  (Bulk)"
ELEVATORS = "Country Elevators - Conventional"

FORBIDDEN_LABELS = frozenset(
    {
        "settlement",
        "closing settlement prices",
        "trade",
        "executed trade",
        "yield",
        "harvest",
        "completed harvest",
    }
)


def _report_date(text: str) -> str:
    match = re.search(r"Grain Report for (\d{2}/\d{2}/\d{4})", text)
    if match is None:
        raise ValueError("the PDF has no average")
    return match.group(1)


def _soybean_section(text: str) -> str:
    start = text.find(COMMODITY)
    if start < 0:
        raise ValueError("the PDF has no average")
    rest = text[start:]
    end = len(rest)
    for marker in ("US #1 Hard", "Closing Settlement Prices"):
        found = rest.find(marker, len(COMMODITY))
        if found >= 0:
            end = min(end, found)
    return rest[:end]


def _average(section: str) -> str:
    if ELEVATORS not in section or "Price($/Bu)" not in section:
        raise ValueError("the PDF has no average")
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if line != "Northwest" or index + 9 >= len(lines) or lines[index + 1] != "Bid":
            continue
        printed = lines[index + 6]
        if (
            re.fullmatch(r"\d+\.\d+", printed)
            and lines[index + 8] == "DLVD-T"
            and lines[index + 9] == "Current"
        ):
            return printed
        break
    raise ValueError("the PDF has no average")


def _reading(text: str) -> dict:
    section = _soybean_section(text)
    return {
        "commodity": COMMODITY,
        "elevators": ELEVATORS,
        "region": "Northwest",
        "sale_type": "Bid",
        "delivery": "Current",
        "report_date": _report_date(text),
        "average": _average(section),
        "unit": "$/Bu",
    }


def record_ams_soybean_average_current(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed soybean average, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("an average is not stored without a response")
    if citation_url != AMS_URL:
        raise ValueError("an average is not stored for a different citation")
    if body is None or body.strip() == "":
        raise ValueError("the PDF has no average")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("an average is not stored for that label")
    if permits_financial_use not in (None, False) or class_c_policy not in (None, CLASS_C_POLICY):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    reading = _reading(body)
    reading["citation_url"] = AMS_URL
    reading["permits_financial_use"] = False
    reading["class_c_policy"] = CLASS_C_POLICY
    path.write_text(
        json.dumps(reading, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
