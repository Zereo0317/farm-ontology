"""Printed MOD13Q1 NDVI samples for one point.

The collection is MODIS/061/MOD13Q1. The point is 42.7018152,
142.4071291. Composite start dates run from 2022-06-01 through
2022-09-30. The project is seges-ai, noncommercial Contributor use
only. No export task is started. NDVI is the raw sample value, the
same scale as the stored 2026-10-16 sample. A sample with no NDVI is
not given a number. The mean uses only values that were stored. It is
a sample mean, not a yield and not a season coefficient. No year is
given tonnes. The point sample is not the Biratori field harvest and
not a trade. The yield-anomaly coefficient is not changed.
permits_financial_use stays false. permits_financial_use_test is not
set. Class C stays closed. This module is not called from a field save.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from farm_ontology.modis_vegetation import MODIS_URL
from farm_ontology.policy import CLASS_C_POLICY

LATITUDE = "42.7018152"
LONGITUDE = "142.4071291"
COLLECTION = "MODIS/061/MOD13Q1"
WINDOW_START = date(2022, 6, 1)
WINDOW_END = date(2022, 9, 30)
FORBIDDEN_LABELS = frozenset(
    {
        "yield",
        "trade",
        "completed harvest",
        "harvest",
        "tonnes",
        "coefficient",
        "forecast",
    }
)


def _samples(sample_response: str) -> list[dict]:
    try:
        payload = json.loads(sample_response)
    except json.JSONDecodeError as exc:
        raise ValueError("the response prints no NDVI") from exc
    features = payload.get("features") if isinstance(payload, dict) else None
    if not isinstance(features, list):
        raise ValueError("the response prints no NDVI")
    stored = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties")
        if not isinstance(props, dict):
            continue
        image_id = props.get("image_id")
        raw_date = props.get("date")
        value = props.get("NDVI")
        if not isinstance(image_id, str) or not image_id.startswith(COLLECTION + "/"):
            continue
        if not isinstance(raw_date, str):
            continue
        try:
            sample_date = date.fromisoformat(raw_date)
        except ValueError:
            continue
        if sample_date < WINDOW_START or sample_date > WINDOW_END:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        stored.append(
            {
                "image_id": image_id,
                "date": raw_date,
                "ndvi": value,
            }
        )
    if not stored:
        raise ValueError("the response prints no NDVI")
    return stored


def _mean(samples: list[dict]) -> str:
    total = sum(sample["ndvi"] for sample in samples)
    return format(Decimal(total) / Decimal(len(samples)), "f")


def record_2022_growing_season_samples(
    path: Path,
    sample_response: str | None = None,
    *,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed point samples, or write nothing."""

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
    samples = _samples(sample_response)
    stored = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "collection": COLLECTION,
        "window_start": WINDOW_START.isoformat(),
        "window_end": WINDOW_END.isoformat(),
        "samples": samples,
        "sample_mean": {
            "value": _mean(samples),
            "count": len(samples),
            "label": "sample mean",
            "not_a_yield": True,
            "not_a_season_coefficient": True,
        },
        "kind": "sample",
        "label": "sample",
        "not_the_biratori_field_harvest": True,
        "not_a_trade": True,
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
