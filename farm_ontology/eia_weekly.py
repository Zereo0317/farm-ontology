"""EIA weekly U.S. crude stocks header.

One named series from the weekly file the survey opened: WCESTUS1.
The stored record is the printed header: publisher, product, period,
and unit. It does not store a stock level, a price, or a world oil
balance. Class C stays closed. This module is not called from a field
save.
"""

from __future__ import annotations

import json
import ssl
import urllib.request
from pathlib import Path

EIA_WEEKLY_CRUDE_STOCKS_URL = (
    "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=WCESTUS1&f=W"
)

PUBLISHER = "U.S. Energy Information Administration"
PRODUCT_VERSION = "Weekly Petroleum Status Report"
SERIES = "Weekly U.S. Ending Stocks excluding SPR of Crude Oil"
PERIOD = "Weekly"
UNIT = "Thousand Barrels"
KIND = "observation"
FORBIDDEN_LABELS = frozenset({"settlement", "yield", "trade"})


def fetch_weekly_series(citation_url: str) -> bytes:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_default_certs()
    request = urllib.request.Request(
        citation_url,
        headers={"User-Agent": "farm-ontology eia-weekly ingest"},
    )
    with urllib.request.urlopen(request, timeout=60, context=context) as response:
        body = response.read()
    if SERIES.encode("utf-8") not in body or UNIT.encode("utf-8") not in body:
        raise ValueError("citation did not return the weekly crude stocks series")
    return body


def record_series_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("an EIA crude stocks value is not a settlement, a yield, or a trade")
    citation = str(citation_url).strip()
    if citation != EIA_WEEKLY_CRUDE_STOCKS_URL:
        raise ValueError("citation_url is not the opened weekly crude stocks series")
    fetch_weekly_series(citation)
    header = {
        "publisher": PUBLISHER,
        "product_version": PRODUCT_VERSION,
        "series": SERIES,
        "period": PERIOD,
        "unit": UNIT,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
        "class_c_policy": "closed",
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "weekly-us-ending-stocks-excluding-spr.json"
    path.write_text(json.dumps(header, indent=2) + "\n", encoding="utf-8")
    return {"file": path.name, "header": header}
