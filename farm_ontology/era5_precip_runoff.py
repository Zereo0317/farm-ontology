"""Precipitation and runoff from one printed ERA5-Land image.

The sample is ECMWF/ERA5_LAND/DAILY_AGGR/20261108 at the printed
coordinates 42.7018152, 142.4071291. It uses the existing noncommercial
Earth Engine registration for seges-ai. No export task is started.
Only printed total precipitation and printed runoff bands are stored.
A band absent from the response is omitted. No value is invented.
Each stored value is a sample, not a yield and not a trade.
permits_financial_use stays false. permits_financial_use_test is not
set. Class C stays closed. This module does not change a header
function that rejects a number. This module is not called from a
field save.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from farm_ontology.adapters.earth_engine import SERIES
from farm_ontology.policy import CLASS_C_POLICY

CITATION = SERIES["ERA5-Land"]["asset"]
IMAGE_ID = "ECMWF/ERA5_LAND/DAILY_AGGR/20261108"
LATITUDE = "42.7018152"
LONGITUDE = "142.4071291"
_IMAGE = re.compile(r'"image_id"\s*:\s*"([^"]+)"')
_VALUE = re.compile(
    r'"((?:total_precipitation|surface_runoff|sub_surface_runoff|runoff)_[A-Za-z0-9_]+)"'
    r"\s*:\s*(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"
)
FORBIDDEN_LABELS = frozenset(
    {
        "yield",
        "trade",
        "completed harvest",
        "harvest",
    }
)


def record_precip_runoff(
    path: Path,
    sample_response: str | None = None,
    *,
    refused: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed precipitation and runoff, or write nothing."""

    if refused:
        raise ValueError("the Earth Engine call was refused")
    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or any(character.isdigit() for character in label)
    ):
        raise ValueError("a sample is not a yield and not a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    if permits_financial_use_test is not None:
        raise ValueError("permits_financial_use_test is not set")
    if not sample_response or not sample_response.strip():
        raise ValueError("the response prints no precipitation or runoff")
    image = _IMAGE.search(sample_response)
    values = _VALUE.findall(sample_response)
    if image is None or image.group(1) != IMAGE_ID or not values:
        raise ValueError("the response prints no precipitation or runoff")
    rows = [
        {
            "band": band,
            "value": number,
            "kind": "sample",
            "label": "sample",
        }
        for band, number in values
    ]
    stored = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "image_id": IMAGE_ID,
        "citation": CITATION,
        "ee_registration": "noncommercial",
        "gcp_project": "seges-ai",
        "rows": rows,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
