"""One BPA balancing-authority reading from the printed 5-minute file.

The file opened on 17 Nov 2026 is:

https://transmission.bpa.gov/Business/Operations/Wind/baltwg.txt

Its last filled row prints 11/16/2026 17:50, Load 8154, VER 128,
Hydro 9147, Fossil/Biomass 1172, and Nuclear 1155. The file prints
"Based on 5-min MW readings". Load is demand. VER, Hydro,
Fossil/Biomass, and Nuclear are generation. This is not a forecast.
Empty later rows are not stored.
permits_financial_use stays false. Class C stays closed. A missing
citation writes nothing. The row is not a settlement and not a trade.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

BPA_URL = "https://transmission.bpa.gov/Business/Operations/Wind/baltwg.txt"

TIMESTAMP = "11/16/2026 17:50"
BASIS = "Based on 5-min MW readings"
UNIT = "MW"
LOAD = 8154
GENERATION = {
    "VER": 128,
    "Hydro": 9147,
    "Fossil/Biomass": 1172,
    "Nuclear": 1155,
}

FORBIDDEN_LABELS = frozenset(
    {
        "forecast",
        "settlement",
        "trade",
        "yield",
        "price",
        "harvest",
        "completed harvest",
    }
)


def record_bpa_balancing(
    path: Path,
    citation_url: str | None,
    *,
    timestamp: str | None = None,
    load: object = None,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the last filled reading, or write nothing."""

    if citation_url is None or citation_url.strip() == "":
        raise ValueError("a balancing reading is not stored without a citation_url")
    if citation_url != BPA_URL:
        raise ValueError("a balancing reading is not stored for a different citation")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a balancing reading is not a forecast, settlement, or trade")
    if any(item is not None for item in (timestamp, load, permits_financial_use, class_c_policy)):
        raise ValueError("a balancing reading is not stored with a different value")
    header = {
        "timestamp": TIMESTAMP,
        "basis": BASIS,
        "unit": UNIT,
        "load": {"role": "demand", "value": LOAD},
        "generation": dict(GENERATION),
        "citation_url": BPA_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
