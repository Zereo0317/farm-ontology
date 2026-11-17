"""One USDA AMS cash bid for Northwest country-elevator soybeans.

The PDF opened on 17 Nov 2026 is:

https://www.ams.usda.gov/mnreports/ams_3225.pdf

The report prints "Grain Report for 11/16/2026 - Final". Under
"US #1  Soybeans  (Bulk)", Country Elevators - Conventional, the
Northwest row prints sale type Bid, delivery Current, price range
10.7900-11.3400, and average 11.1600. The price column prints $/Bu.
The block headed Closing Settlement Prices is not stored.
permits_financial_use stays false. Class C stays closed. A missing
citation writes nothing. The cash bid is not labeled a settlement
or a trade.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

AMS_URL = "https://www.ams.usda.gov/mnreports/ams_3225.pdf"

COMMODITY = "US #1  Soybeans  (Bulk)"
ELEVATORS = "Country Elevators - Conventional"
REGION = "Northwest"
SALE_TYPE = "Bid"
DELIVERY = "Current"
REPORT_DATE = "11/16/2026"
PRICE_RANGE = "10.7900-11.3400"
AVERAGE = "11.1600"
UNIT = "$/Bu"

FORBIDDEN_LABELS = frozenset(
    {
        "settlement",
        "closing settlement prices",
        "trade",
        "yield",
        "harvest",
        "completed harvest",
    }
)


def record_ams_soybean_bid(
    path: Path,
    citation_url: str | None,
    *,
    price_range: str | None = None,
    average: str | None = None,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed cash bid, or write nothing."""

    if citation_url is None or citation_url.strip() == "":
        raise ValueError("a cash bid is not stored without a citation_url")
    if citation_url != AMS_URL:
        raise ValueError("a cash bid is not stored for a different citation")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a cash bid is not stored as a settlement or a trade")
    if any(
        item is not None
        for item in (price_range, average, permits_financial_use, class_c_policy)
    ):
        raise ValueError("a cash bid is not stored with a different value")
    header = {
        "commodity": COMMODITY,
        "elevators": ELEVATORS,
        "region": REGION,
        "sale_type": SALE_TYPE,
        "delivery": DELIVERY,
        "report_date": REPORT_DATE,
        "price_range": PRICE_RANGE,
        "average": AVERAGE,
        "unit": UNIT,
        "citation_url": AMS_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
