"""FAA air-traffic figures.

The page https://www.faa.gov/air_traffic/by_the_numbers was fetched.
The final URL is that address.
The citation is the URL that was fetched.
The product is Air Traffic By The Numbers.
The publisher is Federal Aviation Administration.
The page prints more than 44,000 flights.
The page prints more than 3 million airline passengers.
Those figures are based on FY24.
more than 29 million square miles is airspace, not a flight figure.
The linked PDF was not opened.
Do not store a yield.
Do not store a price.
Do not store a trade.
permits_financial_use stays false.
Class C stays closed.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

FAA_BY_THE_NUMBERS_URL = "https://www.faa.gov/air_traffic/by_the_numbers"

PUBLISHER = "Federal Aviation Administration"
PRODUCT = "Air Traffic By The Numbers"
PERIOD = "FY24"
FLIGHTS = "more than 44,000"
PASSENGERS = "more than 3 million"
FORBIDDEN_LABELS = frozenset({
    "yield",
    "price",
    "trade",
    "harvest",
    "completed harvest",
})


def record_flights(
    directory,
    *,
    citation_url=None,
    label=None,
    flights=None,
    passengers=None,
    permits_financial_use=None,
    class_c_policy=None,
) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a flight figure is not a yield or a trade")
    if flights is not None or passengers is not None:
        raise ValueError("the printed figures are not replaced")
    if permits_financial_use is not None:
        raise ValueError("permits_financial_use stays false")
    if class_c_policy is not None:
        raise ValueError("class C stays closed")
    citation = str(citation_url).strip()
    if citation != FAA_BY_THE_NUMBERS_URL:
        raise ValueError("citation_url is not the fetched page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "flights": FLIGHTS,
        "passengers": PASSENGERS,
        "citation_url": citation,
        "permits_financial_use": False,
        "class_c_policy": "closed",
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "faa-flights.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
