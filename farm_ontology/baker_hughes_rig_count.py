"""Baker Hughes rig count header.

One survey from the overview page that was already opened. The stored
record is the printed header. Baker Hughes terms forbid copying,
reproducing, republishing, redistributing, or making derivative works
from site content without prior written consent, apart from a limited
personal license to use the site as presented. The international
methodology PDF opened is marked copyright 2022, all rights reserved.
A rig is not a barrel. This survey is not oil supply, a forecast, a
settlement, or a completed harvest. It does not store a rig count.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

BAKER_HUGHES_RIG_COUNT_URL = "https://rigcount.bakerhughes.com/rig-count-overview/"

PUBLISHER = "Baker Hughes Company"
PRODUCT = "rig count"
PERIOD = (
    "North America is a weekly census released Friday at noon Central, "
    "described as the last workday of the week; the international count is a "
    "monthly average of weekly counts, and since February 2020 it is released "
    "on the last working day of the first week of the month; the overview says "
    "counts have been issued since 1944, when weekly U.S. and Canadian counts "
    "began, and that the monthly international count began in 1975; a "
    "historical-file page lists annual archives that include 1968 through 1999; "
    "this pass did not confirm a file for every year back to 1944"
)
UNIT = (
    "a census of active drilling rigs; this is drilling activity, not oil "
    "supply; no rig count is stored"
)
ADMINISTRATIVE_AREA = (
    "North America covers rigs exploring for or developing oil, natural gas, "
    "or geothermal energy in the United States and Canada; the international "
    "count is outside North America; the FAQ says it does not include rigs "
    "drilling in Russia, the Caspian region, Iran, Sudan, Cuba, North Korea, "
    "or onshore China; Iraq was excluded from September 1990 to May 2012; "
    "Syria has been excluded since February 2012; Saudi Arabia reports "
    "operating rigs rather than the active-rig definition used elsewhere"
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
    "benchmark",
    "oil supply",
})


def record_series_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a Baker Hughes rig-count figure is not a settlement, a yield, "
            "a trade, a forecast, an observation, a completed harvest, "
            "a benchmark, or oil supply"
        )
    citation = str(citation_url).strip()
    if citation != BAKER_HUGHES_RIG_COUNT_URL:
        raise ValueError("citation_url is not the opened rig count overview")
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
    path = folder / "rig-count.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
