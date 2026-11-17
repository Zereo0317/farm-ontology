"""Current Louisiana prices from the cited EIA daily prices page.

The refetch of

https://www.eia.gov/todayinenergy/prices.php

returned HTTP 200. The page date prints November 16, 2026. The table
"Select Spot Prices for Delivery Today" prints Louisiana natural gas
3.26 under ($/million Btu) and electricity 29.75 under ($/MWh). The
futures block is not stored. A cell that prints NA is not stored. The
spark spread is not stored. A request that fails, or a body with no
Louisiana price, writes nothing.
permits_financial_use stays false. Class C stays closed. These cells
are not a trade.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

EIA_URL = "https://www.eia.gov/todayinenergy/prices.php"
REGION = "Louisiana"
TABLE = "Select Spot Prices for Delivery Today"
GAS_UNIT = "$/million Btu"
ELECTRICITY_UNIT = "$/MWh"

FORBIDDEN_LABELS = frozenset(
    {
        "futures",
        "nymex",
        "settlement",
        "trade",
        "na",
        "yield",
        "harvest",
        "completed harvest",
    }
)


class _Rows(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell = ""
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._in_cell = True
            self._cell = ""

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self._in_cell and self._row is not None:
            self._row.append(" ".join(self._cell.split()))
            self._in_cell = False
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._in_cell:
            self._cell += data


def _printed_value(text: str):
    token = " ".join(text.split())
    if token == "" or token == "NA":
        return None
    if re.fullmatch(r"\d+\.\d+|\d+", token):
        number = float(token) if "." in token else int(token)
        if json.dumps(number) == token:
            return number
    return token


def _page_date(body: str) -> str:
    match = re.search(r'class="date">\s*([^<]+?)\s*<', body)
    if match is None:
        raise ValueError("the response body has no delivery date")
    printed = match.group(1).strip()
    if printed == "":
        raise ValueError("the response body has no delivery date")
    return printed


def _spot_table(body: str) -> str:
    start = body.find(TABLE)
    if start < 0 or "Delivery Today" not in body[start : start + len(TABLE)]:
        raise ValueError("the response body has no delivery date")
    end = body.find("</table>", start)
    if end < 0:
        raise ValueError("the response body has no Louisiana price")
    return body[start:end]


def _reading(body: str) -> dict:
    table = _spot_table(body)
    if f"({GAS_UNIT})" not in table or f"({ELECTRICITY_UNIT})" not in table:
        raise ValueError("the response body has no Louisiana price")
    if "Natural Gas" not in table or "Electricity" not in table:
        raise ValueError("the response body has no Louisiana price")
    parser = _Rows()
    parser.feed(table)
    for row in parser.rows:
        if not row or row[0] != REGION or len(row) < 5:
            continue
        natural_gas = _printed_value(row[1])
        electricity = _printed_value(row[3])
        cells = {}
        if natural_gas is not None:
            cells["natural_gas"] = {"value": natural_gas, "unit": GAS_UNIT}
        if electricity is not None:
            cells["electricity"] = {"value": electricity, "unit": ELECTRICITY_UNIT}
        if not cells:
            break
        return {
            "date": _page_date(body),
            "delivery": "Today",
            "table": TABLE,
            "region": REGION,
            **cells,
        }
    raise ValueError("the response body has no Louisiana price")


def record_eia_louisiana_current(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed Louisiana prices, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("a Louisiana price is not stored without a response")
    if citation_url != EIA_URL:
        raise ValueError("a Louisiana price is not stored for a different citation")
    if body is None or body.strip() == "":
        raise ValueError("the response body has no Louisiana price")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a Louisiana price is not stored for that label")
    if permits_financial_use not in (None, False) or class_c_policy not in (None, CLASS_C_POLICY):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    reading = _reading(body)
    reading["citation_url"] = EIA_URL
    reading["permits_financial_use"] = False
    reading["class_c_policy"] = CLASS_C_POLICY
    path.write_text(
        json.dumps(reading, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
