"""BPS monthly manufacturing production index header.

One index from the statistics-table page that was already opened. The
stored record is the printed title. Period, unit, and administrative
area were not opened and are not filled. The page printed Hak Cipta
© 2023 Badan Pusat Statistik. A license sentence was not opened. A bulk
history file was not opened. The words Bulanan and (2010=100) stay
inside the product title and are not an index value. No province, start
month, or national label is invented. The index is not a quantity of
goods and is not a trading right. This module is not called from a
field save.
"""

from __future__ import annotations

import json
from pathlib import Path

BPS_MANUFACTURING_INDEX_URL = (
    "https://www.bps.go.id/id/statistics-table/2/MjA3NyMy/"
    "indeks-produksi-bulanan-industri-besar-dan-sedang-menurut-kbli-2-digit"
    "--kbli-2020---2010-100-.html"
)

PUBLISHER = "Badan Pusat Statistik"
PRODUCT = (
    "Indeks Produksi Bulanan Industri Besar dan Sedang Menurut KBLI 2 Digit "
    "[KBLI 2020] (2010=100)"
)
NOT_OPENED = "the field was not opened"
KIND = "index"
COPYRIGHT_NOTICE = "Hak Cipta © 2023 Badan Pusat Statistik"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "forecast",
    "observation",
    "completed harvest",
    "public domain",
    "benchmark",
    "province",
    "national",
    "nasional",
    "start month",
    "2010=100",
    "bulanan",
    "quantity of goods",
    "trading right",
})


def record_series_header(
    directory,
    *,
    citation_url=None,
    label=None,
    period=None,
    unit=None,
    administrative_area=None,
) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a BPS manufacturing index figure is not a settlement, a yield, "
            "a trade, a forecast, an observation, a completed harvest, or a "
            "benchmark"
        )
    if period is not None or unit is not None or administrative_area is not None:
        raise ValueError("period, unit, and administrative_area were not opened")
    citation = str(citation_url).strip()
    if citation != BPS_MANUFACTURING_INDEX_URL:
        raise ValueError("citation_url is not the opened statistics-table page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": NOT_OPENED,
        "unit": NOT_OPENED,
        "administrative_area": NOT_OPENED,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
        "copyright_notice": COPYRIGHT_NOTICE,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "bps-manufacturing-index.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
