"""CME listed contracts and historical market data header.

One catalog from the historical distribution guideline that was already
opened. The stored record is the printed header. The citation stays on
https://www.cmegroup.com/market-data/distributor/files/cme-group-data-licensing-policy-guidelines-historical-information-distribution.pdf.
The FAQ that was opened is
https://www.cmegroup.com/market-data/license-data/files/january-2025-non-display-policy-faq.pdf.
The education-center page that was opened is
https://www.cmegroup.com/market-data/license-data/market-data-policy-education-center.html.
The opened guideline says historical information is information first
transmitted eight or more hours earlier. Distributing it requires a
Historical Distribution License for each designated contract market
even if the firm already pays for real-time or delayed distribution.
Delayed information is more than ten minutes and less than eight hours
old. The January 2025 non-display FAQ says non-display use of
historical information must be licensed, was not reportable, and
carried no fees at that time. Real-time and delayed non-display use is
licensed and reportable. The FAQ is not the contract. A public quote
page was not treated as that license. A sandbox wiki date of 1 January
1982 is not stored as confirmed. The catalog is not given a settlement
label, a price, or a trading right. It does not store a settlement or
a trade. This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

CME_MARKET_DATA_URL = (
    "https://www.cmegroup.com/market-data/distributor/files/"
    "cme-group-data-licensing-policy-guidelines-historical-information-distribution.pdf"
)

PUBLISHER = "CME Group"
PRODUCT = "listed contracts and historical market data"
PERIOD = (
    "trading-day settlements, plus delayed and real-time feeds under license; "
    "an official production page stating the first stored day was not opened; "
    "a CME client wiki in a space named EPICSANDBOX says DataMine end-of-day "
    "and time-and-sales history runs from 1 January 1982 or from contract "
    "inception if later; because that page is a sandbox wiki, the 1982 date "
    "is not treated as confirmed"
)
UNIT = (
    "the exchange publishes settlement and trade information for the contracts "
    "used to compare these markets, including NYMEX crude oil and CBOT grain "
    "and oilseed futures; this pass did not open a contract specification or "
    "copy a settlement; no settlement and no trade is stored"
)
ADMINISTRATIVE_AREA = (
    "the listed contracts named on the licensing pages; not a stored position"
)
KIND = "catalog"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "forecast",
    "observation",
    "completed harvest",
    "public domain",
    "benchmark",
})
CONFIRMED_1982_LABELS = frozenset({
    "1982",
    "1982 confirmed",
    "confirmed 1982",
    "1 january 1982",
    "january 1982",
})


def _rejects_confirmed_1982(label) -> bool:
    text = str(label).strip().lower()
    if text in CONFIRMED_1982_LABELS:
        return True
    return "1982" in text and "confirm" in text


def record_series_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and (
        str(label).strip().lower() in FORBIDDEN_LABELS or _rejects_confirmed_1982(label)
    ):
        raise ValueError(
            "a CME catalog figure is not a settlement, a yield, a trade, "
            "a forecast, an observation, a completed harvest, or a benchmark, "
            "and the 1982 date is not confirmed"
        )
    citation = str(citation_url).strip()
    if citation != CME_MARKET_DATA_URL:
        raise ValueError("citation_url is not the opened historical distribution guideline")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": UNIT,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "cme-market-data.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
