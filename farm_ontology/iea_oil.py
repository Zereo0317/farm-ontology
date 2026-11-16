"""IEA oil-licence header.

One terms record from the Non-CC page that was already opened. The
stored record is the printed header. The publisher is International
Energy Agency ("IEA"). The product is Terms of Use for Non-CC Material.
The kind is Terms. The citation stays on
https://www.iea.org/terms/terms-of-use-for-non-cc-material.
https://www.iea.org/ is not the citation. Oil Market Report - November 2026 is a report title on another page, not a period.
Period, unit, and administrative area were not opened.
Oil Market Report (OMR) and Monthly Oil Data Service (MODS) Full Service are purchase-licence product names.
No supply, demand, stock, price, refinery figure, or world oil balance is stored.
The current Oil Market Report is not CC BY 4.0.
For an example of this report, see here (reports are made publicly available three months after their release.)
That sentence is not a grant to store the current balance.
Derived material are not used for the purposes of (i) providing financial services or advice or (ii) informing investment, corporate or financial decisions.
Disseminating the Non-CC Material in its entirety is not permitted, and sharing the file in full is not permitted.
The terms are not marked public domain.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

IEA_OIL_URL = "https://www.iea.org/terms/terms-of-use-for-non-cc-material"

PUBLISHER = 'International Energy Agency ("IEA")'
PRODUCT = "Terms of Use for Non-CC Material"
NOT_OPENED = "the field was not opened"
KIND = "Terms"
REPORT_TITLE = "Oil Market Report - November 2026"
PURCHASE_PRODUCTS = (
    "Oil Market Report (OMR) and Monthly Oil Data Service (MODS) Full Service"
)
PUBLIC_EXAMPLE = (
    "For an example of this report, see here (reports are made publicly "
    "available three months after their release.)"
)
DERIVED_USE = (
    "are not used for the purposes of (i) providing financial services or "
    "advice or (ii) informing investment, corporate or financial decisions"
)
NOT_SHARED_IN_FULL = "disseminating the Non-CC Material in its entirety"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "forecast",
    "observation",
    "completed harvest",
    "public domain",
    "benchmark",
    "supply",
    "demand",
    "stock",
    "price",
    "refinery",
    "refinery figure",
    "world oil balance",
    "oil market report",
    "mods",
    "cc by",
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
            "an IEA terms record is not a settlement, a yield, a trade, a "
            "forecast, an observation, a completed harvest, or a benchmark, "
            "and a supply, demand, stock, price, refinery figure, or world "
            "oil balance is not stored"
        )
    if period is not None or unit is not None or administrative_area is not None:
        raise ValueError("period, unit, and administrative_area were not opened")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != IEA_OIL_URL:
        raise ValueError("citation_url is not the opened Non-CC terms page")
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
    path = folder / "iea-oil.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
