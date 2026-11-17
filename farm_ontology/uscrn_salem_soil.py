"""One USCRN daily soil-moisture cell for MO Salem 10 W.

The data file opened on 17 Nov 2026 is:

https://www.ncei.noaa.gov/pub/data/uscrn/products/daily01/2026/CRND0103-2026-MO_Salem_10_W.txt

That file prints LST_DATE 20261115 and, in the SOIL_MOISTURE_5_DAILY
column, 0.123. The station in the file name is MO_Salem_10_W. This is
Missouri, not Biratori. The data row does not print a unit. The product
README prints the unit for SOIL_MOISTURE_5_DAILY as m^3/m^3:

https://www.ncei.noaa.gov/pub/data/uscrn/products/daily01/README.txt

NASS condition classes are not converted into this value.
permits_financial_use stays false. Class C stays closed. A missing
citation writes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

SALEM_DAILY_URL = (
    "https://www.ncei.noaa.gov/pub/data/uscrn/products/daily01/2026/"
    "CRND0103-2026-MO_Salem_10_W.txt"
)
README_URL = (
    "https://www.ncei.noaa.gov/pub/data/uscrn/products/daily01/README.txt"
)

STATION = "MO_Salem_10_W"
LST_DATE = "20261115"
SERIES = "SOIL_MOISTURE_5_DAILY"
VALUE = 0.123
UNIT = "m^3/m^3"

FORBIDDEN_LABELS = frozenset(
    {
        "biratori",
        "nass",
        "condition class",
        "yield",
        "price",
        "trade",
        "settlement",
        "harvest",
        "completed harvest",
    }
)


def record_uscrn_salem_soil(
    path: Path,
    citation_url: str | None,
    *,
    unit_citation_url: str | None = None,
    station: str | None = None,
    lst_date: str | None = None,
    series: str | None = None,
    value: object = None,
    unit: str | None = None,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed soil-moisture cell, or write nothing."""

    if citation_url is None or citation_url.strip() == "":
        raise ValueError("a soil-moisture cell is not stored without a citation_url")
    if unit_citation_url is None or unit_citation_url.strip() == "":
        raise ValueError("a soil-moisture unit is not stored without a citation_url")
    if citation_url != SALEM_DAILY_URL or unit_citation_url != README_URL:
        raise ValueError("a soil-moisture cell is not stored for a different citation")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a soil-moisture cell is not a NASS condition class")
    if any(
        item is not None
        for item in (
            station,
            lst_date,
            series,
            value,
            unit,
            permits_financial_use,
            class_c_policy,
        )
    ):
        raise ValueError("a soil-moisture cell is not stored with a different value")
    header = {
        "station": STATION,
        "lst_date": LST_DATE,
        "series": SERIES,
        "value": VALUE,
        "citation_url": SALEM_DAILY_URL,
        "unit": UNIT,
        "unit_citation_url": README_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
