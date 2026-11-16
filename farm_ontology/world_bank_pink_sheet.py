"""World Bank Pink Sheet header.

One compilation from the commodity-markets page that was already opened.
The stored record is the printed header plus the dataset terms. Those
terms are not permission to trade. The file is not given a
public-domain label. A separate Commodity Markets Outlook carries
price forecasts; the October 2026 forecast PDF was not read and is not
scored. These are compiled averages and assessments, including some
nearby futures, not a settlement of the underlying contracts. It does
not store a price or an index level. This module is not called from a
field save.
"""

from __future__ import annotations

import json
from pathlib import Path

WORLD_BANK_PINK_SHEET_URL = "https://www.worldbank.org/en/research/commodity-markets"

PUBLISHER = "World Bank, Prospects Group"
PRODUCT = "Pink Sheet"
PERIOD = (
    "monthly file; the commodity-markets page says the next update after the "
    "3 November 2026 publication is 2 December 2026; the monthly workbook's "
    "own title line says nominal U.S. dollars, 1960 to present, and the period "
    "column runs 1960M01 through 2026M10 (802 months); the annual workbook, "
    "updated 2 September 2026, says annual prices from 1960 to present in "
    "nominal and real dollars; the monthly and annual workbooks were updated "
    "on different days"
)
UNIT = (
    "monthly nominal prices and nominal indexes, and annual nominal and real "
    "prices and indexes, for energy, agriculture, food, beverages, raw "
    "materials, fertilizers, and metals; the monthly price sheet has 71 series; "
    "indexes on the monthly file are 2010=100; monthly series are available "
    "only in nominal dollars; real means constant prices deflated by the "
    "Manufacturers Unit Value index; no price and no index level is stored"
)
ADMINISTRATIVE_AREA = (
    "the published commodity series, not a country balance; the Manufacturers "
    "Unit Value index is the U.S.-dollar unit-value index of manufactures "
    "exported from fifteen countries listed in the workbook: Brazil, Canada, "
    "China, Germany, France, India, Italy, Japan, Mexico, the Republic of "
    "Korea, South Africa, Spain, the United Kingdom, and the United States, "
    "plus one name spelled Pailand in the file"
)
KIND = "compilation"
COPYRIGHT_STATEMENT = (
    "World Bank dataset terms, last updated 23 March 2018, say datasets are "
    "CC BY 4.0 unless labeled otherwise, with attribution in the form "
    '"The World Bank: Dataset name: Data source (if known)," '
    "and with a mediation and arbitration clause. Some third-party indicators "
    "may not be redistributed. The Pink Sheet description sheet shows that "
    "individual series change source and specification."
)
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
            "a Pink Sheet figure is not a settlement, a yield, a trade, "
            "a forecast, an observation, a completed harvest, or a benchmark"
        )
    citation = str(citation_url).strip()
    if citation != WORLD_BANK_PINK_SHEET_URL:
        raise ValueError("citation_url is not the opened commodity-markets page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": UNIT,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
        "copyright_statement": COPYRIGHT_STATEMENT,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "pink-sheet.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
