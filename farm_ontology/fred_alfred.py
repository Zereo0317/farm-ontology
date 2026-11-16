"""FRED and ALFRED header.

One reprint from the FRED terms page that was already opened. The stored
record is the printed header. The citation stays on
https://fred.stlouisfed.org/legal/terms. The ALFRED help page that was
opened is https://alfred.stlouisfed.org/help. The API terms page that
was opened is https://fred.stlouisfed.org/docs/api/terms_of_use.html.
FRED terms say third-party copyright survives. Three labels are used:
copyrighted and pre-approval required, copyrighted and citation
required, and series that may be used without permission if no
prohibited use applies. The Bank cannot license a third-party series.
API terms repeat that. Personal use of FRED is free. Anything beyond
personal use of a copyrighted series needs the owner. FRED is not given
a public-domain label. ALFRED's help text hopes users will build
forecasting models. That hope is not stored as a forecast, and the
reprint is not a trading right. It does not store a value. This module
is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

FRED_ALFRED_URL = "https://fred.stlouisfed.org/legal/terms"

PUBLISHER = "Federal Reserve Bank of St. Louis, reprinting other publishers"
PRODUCT = "FRED and ALFRED"
PERIOD = (
    "follows the source series; ALFRED's help page says many sources do not "
    "keep their own previously published estimates, and that some vintages "
    "are then checked against third-party data services; coverage is "
    "whatever vintages ALFRED holds, not every series"
)
UNIT = (
    "not a new measurement; FRED redistributes many of the government series "
    "already recorded; ALFRED stores vintage versions so a reader can see a "
    "series as it was published on a past date; no value is stored"
)
ADMINISTRATIVE_AREA = (
    "the reprinted series; this record is not a new geographic measurement"
)
KIND = "reprint"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "forecast",
    "observation",
    "completed harvest",
    "public domain",
    "benchmark",
    "new measurement",
})


def record_series_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a FRED and ALFRED figure is not a settlement, a yield, a trade, "
            "a forecast, an observation, a completed harvest, a benchmark, "
            "or a new measurement"
        )
    citation = str(citation_url).strip()
    if citation != FRED_ALFRED_URL:
        raise ValueError("citation_url is not the opened FRED terms page")
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
    path = folder / "fred-alfred.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
