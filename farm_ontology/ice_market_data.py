"""ICE Futures Europe market data policy header.

One policy from the PDF that was already opened. The stored record is
the printed header. The publisher is ICE Futures Europe. The product
and kind are Market Data Policy. The citation stays on
https://www.ice.com/publicdocs/futures/ICE_Futures_Europe_Market_Data_Policy.pdf.
https://www.ice.com/ is not the citation. Version 4 January 2026 is the policy version date, not a data period.
Period, unit, and administrative area were not opened.
The commodities list names Brent under ICE Futures Europe (Commodities).
No settlement, price, quote, or trade is stored.
The printed restriction is: This material may not be reproduced or redistributed in whole or in part without the express, prior written consent of Intercontinental Exchange, Inc.
The copyright line is © Copyright Intercontinental Exchange, Inc. 2025. All Rights Reserved.
The policy is not marked public domain.
The Exchange offers End of Day ongoing and historical data subscriptions for clients looking to receive an automated end of day report of information published on the ICE website. These are available free of charge on ICE's website, see links below.
That free end-of-day sentence is not a redistribution grant.
A quote page was not opened. No settlement file was downloaded.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

ICE_MARKET_DATA_URL = (
    "https://www.ice.com/publicdocs/futures/ICE_Futures_Europe_Market_Data_Policy.pdf"
)

PUBLISHER = "ICE Futures Europe"
PRODUCT = "Market Data Policy"
NOT_OPENED = "the field was not opened"
KIND = "Market Data Policy"
POLICY_VERSION = "Version 4"
POLICY_VERSION_DATE = "January 2026"
RESTRICTION = "This material may not be reproduced or redistributed in whole or in part without the express, prior written consent of Intercontinental Exchange, Inc."
COPYRIGHT_LINE = "© Copyright Intercontinental Exchange, Inc. 2025. All Rights Reserved."
COMMODITIES_NAME = "Brent"
FREE_END_OF_DAY = "The Exchange offers End of Day ongoing and historical data subscriptions for clients looking to receive an automated end of day report of information published on the ICE website. These are available free of charge on ICE's website, see links below."
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "forecast",
    "observation",
    "completed harvest",
    "public domain",
    "benchmark",
    "price",
    "quote",
    "brent",
    "redistribution grant",
    "figure",
})


def _stores_figure(label) -> bool:
    return any(character.isdigit() for character in str(label))


def record_series_header(
    directory,
    *,
    citation_url=None,
    label=None,
    period=None,
    unit=None,
    administrative_area=None,
    value=None,
) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and (
        str(label).strip().lower() in FORBIDDEN_LABELS or _stores_figure(label)
    ):
        raise ValueError(
            "a market data policy is not a settlement, a yield, a trade, a "
            "forecast, an observation, a completed harvest, or a benchmark, "
            "and a settlement, price, quote, trade, or figure is not stored"
        )
    if period is not None or unit is not None or administrative_area is not None:
        raise ValueError("period, unit, and administrative_area were not opened")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != ICE_MARKET_DATA_URL:
        raise ValueError("citation_url is not the opened market data policy")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": NOT_OPENED,
        "unit": NOT_OPENED,
        "administrative_area": NOT_OPENED,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "ice-market-data.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
