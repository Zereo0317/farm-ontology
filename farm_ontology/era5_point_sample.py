"""ERA5-Land daily sample at the printed Biratori point.

Coordinates are taken only from a response that prints them. The sample
uses the already-cited daily asset ECMWF/ERA5_LAND/DAILY_AGGR and the
existing noncommercial Earth Engine registration for seges-ai. No export
task is started. Only the printed 2 m temperature and the printed
volumetric soil water are stored, with the image id and the citation.
Each value is a sample, not a yield and not a trade. No band value is
invented. A refused call stores nothing. permits_financial_use stays
false. permits_financial_use_test is not set. Class C stays closed.
This module does not change a header function that rejects a number.
This module is not called from a field save.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from farm_ontology.adapters.earth_engine import SERIES
from farm_ontology.policy import CLASS_C_POLICY

CITATION = SERIES["ERA5-Land"]["asset"]
PLUS_CODE = "PC24+PVC"
PLACE = "Biratori, Hokkaido, Japan"
MAP_URL = "https://maps.app.goo.gl/dKfj9uWuQm8U1aQi9"
_COORDINATES = re.compile(r"3d(-?\d+\.\d+)!4d(-?\d+\.\d+)")
_IMAGE = re.compile(r'"image_id"\s*:\s*"([^"]+)"')
_VALUE = re.compile(
    r'"(temperature_2m|volumetric_soil_water_[A-Za-z0-9_]+)"\s*:\s*(-?\d+(?:\.\d+)?)'
)
FORBIDDEN_LABELS = frozenset(
    {
        "yield",
        "trade",
        "completed harvest",
        "harvest",
    }
)


def record_point_sample(
    path: Path,
    *,
    coordinate_response: str | None = None,
    sample_response: str | None = None,
    refused: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed sample, or write nothing."""

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
    if not coordinate_response or not sample_response:
        raise ValueError("a sample is not stored without a printed response")
    coordinates = _COORDINATES.search(coordinate_response)
    image = _IMAGE.search(sample_response)
    values = _VALUE.findall(sample_response)
    if coordinates is None or image is None or not values:
        raise ValueError("the response prints no sample")
    image_id = image.group(1)
    if not image_id.startswith(CITATION + "/"):
        raise ValueError("the image is not the cited daily product")
    rows = [
        {
            "band": band,
            "value": number,
            "kind": "sample",
            "label": "sample",
        }
        for band, number in values
        if band == "temperature_2m" or band.startswith("volumetric_soil_water")
    ]
    if not rows:
        raise ValueError("the response prints no sample")
    stored = {
        "plus_code": PLUS_CODE,
        "place": PLACE,
        "map_url": MAP_URL,
        "latitude": coordinates.group(1),
        "longitude": coordinates.group(2),
        "image_id": image_id,
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
