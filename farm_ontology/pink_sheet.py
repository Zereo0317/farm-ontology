"""World Bank Pink Sheet monthly header.

One named series from the monthly workbook. The stored record is the
header that was printed: series, period, and unit. It does not store a
price level. Class C stays closed. This module is not called from a
field save.
"""

from __future__ import annotations

import json
import ssl
import urllib.request
from pathlib import Path

PINK_SHEET_MONTHLY_URL = (
    "https://thedocs.worldbank.org/en/doc/"
    "74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/"
    "CMO-Historical-Data-Monthly.xlsx"
)

PUBLISHER = "World Bank"
PRODUCT_VERSION = "CMO Historical Data Monthly"
SERIES = "Crude oil, average"
PERIOD = "1960 to present"
UNIT = "($/bbl)"
KIND = "observation"
FORBIDDEN_LABELS = frozenset({"settlement", "yield", "trade"})


def fetch_monthly_workbook(citation_url: str) -> bytes:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_default_certs()
    request = urllib.request.Request(
        citation_url,
        headers={"User-Agent": "farm-ontology pink-sheet ingest"},
    )
    with urllib.request.urlopen(request, timeout=60, context=context) as response:
        body = response.read()
    if not body.startswith(b"PK"):
        raise ValueError("citation did not return the monthly workbook")
    return body


def record_series_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a Pink Sheet value is not a settlement, a yield, or a trade")
    citation = str(citation_url).strip()
    fetch_monthly_workbook(citation)
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
    path = folder / "crude-oil-average.json"
    path.write_text(json.dumps(header, indent=2) + "\n", encoding="utf-8")
    return {"file": path.name, "header": header}
