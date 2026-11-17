"""Philadelphia Fed manufacturing survey header.

One survey from the page that was already opened. The stored header is
the printed header and does not store an index value. The Bank's
privacy notice says some site content may be copyrighted and needs the
owner's permission. A separate open-data grant for the CSV was not on
the pages opened, and no CSV is downloaded.

The same page prints one current diffusion index in the chart sentence
"The current general business activity diffusion index declined to 20.9
in October from 37.8 in September." The stored figure is 20.9 for
October. That sentence prints no year. 37.8 is the prior month and is
not stored. The future index in the next sentence is an expectation
six months ahead and is not stored. The page is not national supply
and not a trade.

The six-month questions are what respondents expect. They are not a
tested forecast and are not stored as a forecast or as a finished
observation. This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

PHILADELPHIA_FED_MBOS_URL = (
    "https://www.philadelphiafed.org/surveys-and-data/"
    "regional-economic-analysis/manufacturing-business-outlook-survey"
)

PUBLISHER = "Federal Reserve Bank of Philadelphia"
PRODUCT = "Manufacturing Business Outlook Survey"
PERIOD = (
    "monthly; the survey page lists a 19 November 2026 release at 8:30 a.m.; "
    "the readme dated 7 March 2025 says historical monthly data run from "
    "May 1968 to the most current month; the user guide says the files are "
    "revised annually for seasonal factors"
)
UNIT = (
    "a diffusion index, the share reporting an increase minus the share "
    "reporting a decrease; current conditions and expectations six months "
    "ahead are named; no index value is stored"
)
ADMINISTRATIVE_AREA = (
    "manufacturing firms in the Third District; not national manufacturing supply"
)
KIND = "survey"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "forecast",
    "observation",
    "completed harvest",
    "public domain",
    "national supply",
})
PRINTED_SERIES = "current general business activity diffusion index"
PRINTED_MONTH = "October"
PRINTED_VALUE = "20.9"
INDEX_FORBIDDEN_LABELS = FORBIDDEN_LABELS | frozenset({"price"})


def record_series_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a Manufacturing Business Outlook Survey figure is not a settlement, "
            "a yield, a trade, a forecast, an observation, a completed harvest, "
            "or national supply"
        )
    citation = str(citation_url).strip()
    if citation != PHILADELPHIA_FED_MBOS_URL:
        raise ValueError("citation_url is not the opened Manufacturing Business Outlook Survey page")
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
    path = folder / "manufacturing-business-outlook-survey.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}


def record_printed_index(
    directory,
    *,
    citation_url=None,
    label=None,
    series=None,
    month=None,
    value=None,
    permits_financial_use=None,
    class_c_policy=None,
) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in INDEX_FORBIDDEN_LABELS:
        raise ValueError(
            "a Manufacturing Business Outlook Survey diffusion index is not a "
            "price, a trade, or national supply"
        )
    if any(
        item is not None
        for item in (series, month, value, permits_financial_use, class_c_policy)
    ):
        raise ValueError("the printed diffusion index is not stored with a different value")
    citation = str(citation_url).strip()
    if citation != PHILADELPHIA_FED_MBOS_URL:
        raise ValueError("citation_url is not the Manufacturing Business Outlook Survey page")
    record = {
        "series": PRINTED_SERIES,
        "month": PRINTED_MONTH,
        "value": PRINTED_VALUE,
        "citation_url": citation,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "current-general-business-activity.json"
    path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "record": record}
