"""China NBS major farm products header.

One administrative statistical query from the reply that was already
opened. The stored record is the printed header. It is not a county
yield, not a farm yield, and not a production total. It does not store
a number. This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

PUBLISHER = "National Bureau of Statistics of China"
PRODUCT = "Output of major farm products"
PERIOD = "annual; a start year was not stated in the opened reply"
UNIT = "not printed in the opened reply"
ADMINISTRATIVE_AREA = (
    "national query; provincial yearbooks also publish sown area and output"
)
CITATION_URL = "https://www.stats.gov.cn/hd/lyzx/zxgk/202405/t20240524_1953659.html"
KIND = "observation"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "completed harvest",
})


def record_nbs_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "an NBS farm-products query is not a settlement, a yield, a trade, "
            "or a completed harvest"
        )
    citation = str(citation_url).strip()
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
    path = folder / "output-of-major-farm-products.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
