"""Platts trial subscription terms header.

One terms record from the trial page that was already opened. The stored
record is the printed header. The publisher is S&P Global Commodity
Insights. The product is Trial Subscription Terms and Conditions. The
kind is Terms. The citation stays on
https://www.spglobal.com/commodityinsights/en/support/delivery-platforms/platts-trial-subscription-terms-and-conditions.
The methodology PDF is not the citation. May 2024 is that guide's update line, not a period, and that guide prints no licence sentence.
https://www.spglobal.com/content/dam/spglobal/ci/en/documents/platts/en/our-methodology/methodology-specifications/Platts-Assessments-Methodology-Guide.pdf
Period, unit, and administrative area were not opened.
The grant is only an internal evaluation licence.
The information is not financial or investment advice.
No user should rely on a price assessment in an investment decision.
Publishing, reproducing, or distributing the information needs an additional licence.
The master subscription agreement was not opened.
No price, assessment, spread, or trade is stored.
The terms are not marked public domain.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

PLATTS_TERMS_URL = (
    "https://www.spglobal.com/commodityinsights/en/support/delivery-platforms/"
    "platts-trial-subscription-terms-and-conditions"
)
METHODOLOGY_PDF = (
    "https://www.spglobal.com/content/dam/spglobal/ci/en/documents/platts/en/"
    "our-methodology/methodology-specifications/"
    "Platts-Assessments-Methodology-Guide.pdf"
)

PUBLISHER = "S&P Global Commodity Insights"
PRODUCT = "Trial Subscription Terms and Conditions"
NOT_OPENED = "the field was not opened"
KIND = "Terms"
GUIDE_UPDATE = "May 2024"
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
    "assessment",
    "spread",
    "price assessment",
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
            "trial terms are not a settlement, a yield, a trade, a forecast, "
            "an observation, a completed harvest, or a benchmark, and a "
            "price, assessment, spread, or figure is not stored"
        )
    if period is not None or unit is not None or administrative_area is not None:
        raise ValueError("period, unit, and administrative_area were not opened")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != PLATTS_TERMS_URL:
        raise ValueError("citation_url is not the opened trial terms page")
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
    path = folder / "platts-terms.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
