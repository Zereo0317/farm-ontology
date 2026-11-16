"""OPEC Annual Statistical Bulletin disclaimer header.

One disclaimer from the 2026 bulletin PDF that was already opened. The
stored record is the printed header. The publisher is OPEC Secretariat.
The product is OPEC Annual Statistical Bulletin (ASB). The period is
2026. The kind is Disclaimer. The citation stays on
https://publications.opec.org/ASSETS/assetdb/asb-2026.pdf.
https://asb.opec.org/ASB_Disclaimer.html loaded a foreword and is not the citation.
Unit and administrative area were not opened.
The bulletin is not a benchmark or input data to a benchmark.
Full reproduction needs the OPEC Secretariat's written permission.
The educational and non-commercial sentence is not a grant to store a balance, price, or production figure.
No balance, price, or production figure is stored.
The bulletin is not marked public domain.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

OPEC_ASB_URL = "https://publications.opec.org/ASSETS/assetdb/asb-2026.pdf"

PUBLISHER = "OPEC Secretariat"
PRODUCT = "OPEC Annual Statistical Bulletin (ASB)"
PERIOD = "2026"
NOT_OPENED = "the field was not opened"
KIND = "Disclaimer"
FOREWORD_URL = "https://asb.opec.org/ASB_Disclaimer.html"
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
    "balance",
    "production",
    "production figure",
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
            "a bulletin disclaimer is not a settlement, a yield, a trade, a "
            "forecast, an observation, a completed harvest, or a benchmark, "
            "and a balance, price, or production figure is not stored"
        )
    if unit is not None or administrative_area is not None:
        raise ValueError("unit and administrative_area were not opened")
    if period is not None or value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != OPEC_ASB_URL:
        raise ValueError("citation_url is not the opened bulletin PDF")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": NOT_OPENED,
        "administrative_area": NOT_OPENED,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "opec-asb.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
