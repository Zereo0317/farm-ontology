"""GEOGLAM Crop Monitor for AMIS header.

One consensus condition assessment from the page that was already
opened. The stored header is the printed header. It is not a pixel
yield, not a harvest measurement, and not a supply number. The header
does not store a condition class for any place, a percent, or a tonne.

The same page prints the rice section date "Crop condition information
is based on information as of October 28th, 2026." and then "In China,
harvesting continues for single-season rice (largest season) and late
double-crop rice (medium season) under favourable conditions." The
stored class is that one printed class: rice, China, October 28th,
2026, favourable. A class is not a yield, not tonnes, and not a trade.
No other URL was opened.

This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

PUBLISHER = "GEOGLAM Crop Monitor"
PRODUCT = "Crop Monitor for AMIS condition classes"
PERIOD = "eleven reports a year, first Thursday of the month, every month except January"
UNIT = (
    "condition class; the opened rules name exceptional, favourable, "
    "watch, poor, out-of-season, and no data"
)
ADMINISTRATIVE_AREA = "main growing areas, national and subnational units"
CITATION_URL = "https://www.cropmonitor.org/crop-monitor-for-amis"
KIND = "assessment"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "tonne",
    "observation",
    "completed harvest",
})
PRINTED_CROP = "rice"
PRINTED_PLACE = "China"
PRINTED_MONTH = "October 28th, 2026"
PRINTED_CLASS = "favourable"
CLASS_FORBIDDEN_LABELS = FORBIDDEN_LABELS | frozenset({"tonnes"})


def record_crop_monitor_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a Crop Monitor class is not a settlement, a yield, a trade, "
            "a tonne, an observation, or a completed harvest"
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
    path = folder / "crop-monitor-for-amis.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}


def record_printed_class(
    directory,
    *,
    citation_url=None,
    label=None,
    crop=None,
    place=None,
    month=None,
    condition_class=None,
    permits_financial_use=None,
    class_c_policy=None,
) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in CLASS_FORBIDDEN_LABELS:
        raise ValueError(
            "a Crop Monitor class is not a yield, not tonnes, and not a trade"
        )
    if any(
        item is not None
        for item in (
            crop,
            place,
            month,
            condition_class,
            permits_financial_use,
            class_c_policy,
        )
    ):
        raise ValueError("the printed condition class is not stored with a different value")
    citation = str(citation_url).strip()
    if citation != CITATION_URL:
        raise ValueError("citation_url is not the Crop Monitor for AMIS page that printed the class")
    record = {
        "crop": PRINTED_CROP,
        "place": PRINTED_PLACE,
        "month": PRINTED_MONTH,
        "condition_class": PRINTED_CLASS,
        "citation_url": citation,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "china-rice-condition.json"
    path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "record": record}
