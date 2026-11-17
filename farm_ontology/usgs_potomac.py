"""One USGS instantaneous Potomac observation.

The JSON opened on 17 Nov 2026 is:

https://waterservices.usgs.gov/nwis/iv/?format=json&sites=01646500&parameterCd=00060,00065&siteStatus=all

It prints site POTOMAC RIVER NEAR WASH, DC LITTLE FALLS PUMP STA,
streamflow 1600 ft3/s and gage height 2.73 ft at
2026-11-16T19:50:00.000-05:00, qualifier P. This is not the 2015 annual withdrawal.
permits_financial_use stays false. Class C stays closed. A missing
citation writes nothing. The observation is not a settlement and not
a trade.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

USGS_URL = (
    "https://waterservices.usgs.gov/nwis/iv/?format=json&sites=01646500"
    "&parameterCd=00060,00065&siteStatus=all"
)

SITE = "POTOMAC RIVER NEAR WASH, DC LITTLE FALLS PUMP STA"
OBSERVED_AT = "2026-11-16T19:50:00.000-05:00"
QUALIFIER = "P"
STREAMFLOW = 1600
STREAMFLOW_UNIT = "ft3/s"
GAGE_HEIGHT = 2.73
GAGE_HEIGHT_UNIT = "ft"

FORBIDDEN_LABELS = frozenset(
    {
        "annual withdrawal",
        "2015",
        "settlement",
        "trade",
        "yield",
        "price",
        "harvest",
        "completed harvest",
    }
)


def record_usgs_potomac(
    path: Path,
    citation_url: str | None,
    *,
    streamflow: object = None,
    gage_height: object = None,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed instantaneous values, or write nothing."""

    if citation_url is None or citation_url.strip() == "":
        raise ValueError("an observation is not stored without a citation_url")
    if citation_url != USGS_URL:
        raise ValueError("an observation is not stored for a different citation")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("an observation is not an annual withdrawal, settlement, or trade")
    if any(
        item is not None
        for item in (streamflow, gage_height, permits_financial_use, class_c_policy)
    ):
        raise ValueError("an observation is not stored with a different value")
    header = {
        "site": SITE,
        "observed_at": OBSERVED_AT,
        "qualifier": QUALIFIER,
        "streamflow": {"value": STREAMFLOW, "unit": STREAMFLOW_UNIT},
        "gage_height": {"value": GAGE_HEIGHT, "unit": GAGE_HEIGHT_UNIT},
        "citation_url": USGS_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
