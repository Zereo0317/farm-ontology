"""One printed MOD13Q1 NDVI sample.

The collection is MODIS/061/MOD13Q1, the V061 MOD13Q1 product named by
the catalog citation. The sample is at 42.7018152, 142.4071291 and uses
the existing noncommercial Earth Engine registration for seges-ai. No
export task is started. One printed NDVI is stored with the image id
and date. NDVI is not converted into tonnes. It is a sample, not a
yield and not a trade. No value is invented. A response with no NDVI
stores nothing. permits_financial_use stays false.
permits_financial_use_test is not set. Class C stays closed. This
module does not change a header function that rejects a number. This
module is not called from a field save.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from farm_ontology.modis_vegetation import MODIS_URL
from farm_ontology.policy import CLASS_C_POLICY

LATITUDE = "42.7018152"
LONGITUDE = "142.4071291"
_IMAGE = re.compile(r'"image_id"\s*:\s*"(MODIS/061/MOD13Q1/[^"]+)"')
_DATE = re.compile(r'"date"\s*:\s*"(\d{4}-\d{2}-\d{2})"')
_NDVI = re.compile(r'"NDVI"\s*:\s*(-?\d+(?:\.\d+)?)')
FORBIDDEN_LABELS = frozenset(
    {
        "yield",
        "trade",
        "completed harvest",
        "harvest",
        "tonnes",
        "evi",
    }
)


def record_ndvi_sample(
    path: Path,
    sample_response: str | None = None,
    *,
    refused: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write one printed NDVI, or write nothing."""

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
        raise ValueError("the response prints no NDVI")
    image = _IMAGE.search(sample_response)
    dated = _DATE.search(sample_response)
    values = _NDVI.findall(sample_response)
    if image is None or dated is None or len(values) != 1:
        raise ValueError("the response prints no NDVI")
    stored = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "image_id": image.group(1),
        "date": dated.group(1),
        "band": "NDVI",
        "value": values[0],
        "kind": "sample",
        "label": "sample",
        "citation_url": MODIS_URL,
        "ee_registration": "noncommercial",
        "gcp_project": "seges-ai",
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
