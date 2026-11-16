"""Philadelphia Fed manufacturing survey header.

One survey from the page that was already opened. The stored record is
the printed header. The Bank's privacy notice says some site content
may be copyrighted and needs the owner's permission. A separate
open-data grant for the CSV was not on the pages opened. The six-month
questions are what respondents expect. They are not a tested forecast
and are not stored as a forecast or as a finished observation. It does
not store an index value. This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

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
