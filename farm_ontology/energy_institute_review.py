"""Energy Institute Statistical Review header.

One compilation from the pages that were already opened. The stored
record is the printed header. The Institute says the review is free to
access and calls it a global public good. No workbook licence was on
the pages opened. Ember's website licence was not a licence for the
Institute's workbook. The PDF says statistics are taken from government
sources and published data and that no confidential information is
used. This compilation is not a forecast, a settlement, or a direct
observation. It does not store a quantity or a price. This module is
not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

ENERGY_INSTITUTE_REVIEW_URL = "https://www.energyinst.org/statistical-review"

PUBLISHER = (
    "Energy Institute, with Ember as co-author of the current edition. "
    "Previously published by bp. The Institute has been custodian since 2023."
)
PRODUCT = "Statistical Review of World Energy"
PERIOD = (
    "annual, covering the prior year; the Institute's site says the review "
    "has been published since 1952; the tables on display cover 2015-2025; "
    "the site says downloadable Excel goes back to 1965 for many sectors; "
    "the PDF opened is the 74th edition; the Excel workbook was not opened, "
    "so 1965 is the site's claim, not a span counted in the workbook"
)
UNIT = (
    "annual production, consumption, trade, refining, and prices for oil, "
    "oil products, gas, coal, nuclear, hydro, and renewables, plus total "
    "energy and carbon dioxide emissions; the edition page says more than "
    "50 countries and 12 regions; no quantity and no price is stored"
)
ADMINISTRATIVE_AREA = (
    "the review's published country and region tables; the PDF's reserves "
    "note says proved-reserve figures are a compilation, not a single SEC "
    "definition, and that countries use different methods"
)
KIND = "compilation"
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


def record_series_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a Statistical Review figure is not a settlement, a yield, a trade, "
            "a forecast, an observation, a completed harvest, or a benchmark"
        )
    citation = str(citation_url).strip()
    if citation != ENERGY_INSTITUTE_REVIEW_URL:
        raise ValueError("citation_url is not the opened Statistical Review page")
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
    path = folder / "statistical-review-of-world-energy.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
