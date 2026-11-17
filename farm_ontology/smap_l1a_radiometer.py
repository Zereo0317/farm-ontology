"""One SMAP L1A radiometer time range from the printed ISO metadata.

The ISO XML opened on 17 Nov 2026 is:

https://data.nsidc.earthdatacloud.nasa.gov/nsidc-cumulus-prod-public/SMAP/SPL1AP/002/2026/11/16/SMAP_L1A_RADIOMETER_62995_D_20261116T215830_R19240_001.h5.iso.xml

That file prints the product series L1A_Radiometer. Its temporal extent
prints begin 2026-11-16T21:58:29.862Z and end 2026-11-16T22:51:51.299Z.
The swath polygon is not stored. Percent of Missing Data is not soil
moisture and is not a measurement of the ground. No brightness
temperature is invented.
permits_financial_use stays false. Class C stays closed. A missing
citation writes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

ISO_URL = (
    "https://data.nsidc.earthdatacloud.nasa.gov/nsidc-cumulus-prod-public/"
    "SMAP/SPL1AP/002/2026/11/16/"
    "SMAP_L1A_RADIOMETER_62995_D_20261116T215830_R19240_001.h5.iso.xml"
)

PRODUCT = "L1A_Radiometer"
BEGIN = "2026-11-16T21:58:29.862Z"
END = "2026-11-16T22:51:51.299Z"

FORBIDDEN_LABELS = frozenset(
    {
        "pixel",
        "soil moisture",
        "brightness temperature",
        "percent of missing data",
        "yield",
        "price",
        "trade",
        "settlement",
        "harvest",
        "completed harvest",
    }
)


def record_smap_l1a_time(
    path: Path,
    citation_url: str | None,
    *,
    product: str | None = None,
    begin: str | None = None,
    end: str | None = None,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed time range, or write nothing."""

    if citation_url is None or citation_url.strip() == "":
        raise ValueError("a time range is not stored without a citation_url")
    if citation_url != ISO_URL:
        raise ValueError("a time range is not stored for a different citation")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a time range is not a pixel or a ground measurement")
    if any(
        item is not None
        for item in (product, begin, end, permits_financial_use, class_c_policy)
    ):
        raise ValueError("a time range is not stored with a different value")
    header = {
        "product": PRODUCT,
        "begin": BEGIN,
        "end": END,
        "citation_url": ISO_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
