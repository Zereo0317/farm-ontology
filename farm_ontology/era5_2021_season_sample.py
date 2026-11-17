"""Printed ERA5-Land daily samples for one point.

The asset is ECMWF/ERA5_LAND/DAILY_AGGR. The point is 42.7018152,
142.4071291. The dates are 2021-06-10, 2021-06-26, 2021-07-12,
2021-07-28, 2021-08-13, 2021-08-29, 2021-09-14, and 2021-09-30. The
project is seges-ai, noncommercial Contributor use only. No export
task is started. A date stores 2 m temperature and total precipitation
sum only when that image returns them. A mean or sum uses only stored
values. It is a sample, not a yield and not a coefficient. No tonnes
are produced. The yield-anomaly coefficient is not changed.
permits_financial_use stays false. permits_financial_use_test is not
set. Class C stays closed. This module is not called from a field save.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

LATITUDE = "42.7018152"
LONGITUDE = "142.4071291"
ASSET = "ECMWF/ERA5_LAND/DAILY_AGGR"
DATES = (
    "2021-06-10",
    "2021-06-26",
    "2021-07-12",
    "2021-07-28",
    "2021-08-13",
    "2021-08-29",
    "2021-09-14",
    "2021-09-30",
)
FIELDS = ("temperature_2m", "total_precipitation_sum")
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


def _number(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float))


def _samples(sample_response: str) -> list[dict]:
    try:
        payload = json.loads(sample_response)
    except json.JSONDecodeError as exc:
        raise ValueError("the response prints no sample") from exc
    returned = payload.get("returned") if isinstance(payload, dict) else None
    if not isinstance(returned, list):
        raise ValueError("the response prints no sample")
    by_date = {}
    for row in returned:
        if not isinstance(row, dict):
            continue
        image_id = row.get("image_id")
        if not isinstance(image_id, str) or not image_id.startswith(ASSET + "/"):
            continue
        suffix = image_id.rsplit("/", 1)[-1]
        if len(suffix) != 8 or not suffix.isdigit():
            continue
        sample_date = f"{suffix[0:4]}-{suffix[4:6]}-{suffix[6:8]}"
        if sample_date not in DATES:
            continue
        stored = {"date": sample_date, "image_id": image_id}
        for field in FIELDS:
            if _number(row.get(field)):
                stored[field] = row[field]
        by_date[sample_date] = stored
    samples = []
    for sample_date in DATES:
        samples.append(by_date.get(sample_date, {"date": sample_date}))
    if not any(field in sample for sample in samples for field in FIELDS):
        raise ValueError("the response prints no sample")
    return samples


def _decimal(value: int | float) -> Decimal:
    return Decimal(str(value))


def record_era5_2021_season_sample(
    path: Path,
    sample_response: str | None = None,
    *,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed daily samples, or write nothing."""

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
        raise ValueError("the response prints no sample")
    samples = _samples(sample_response)
    temperatures = [sample["temperature_2m"] for sample in samples if "temperature_2m" in sample]
    precipitation = [
        sample["total_precipitation_sum"]
        for sample in samples
        if "total_precipitation_sum" in sample
    ]
    stored = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "asset": ASSET,
        "ee_registration": "noncommercial",
        "gcp_project": "seges-ai",
        "samples": samples,
        "not_a_yield": True,
        "not_a_coefficient": True,
        "not_a_trade": True,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    if temperatures:
        stored["temperature_2m_sample_mean"] = format(
            sum(_decimal(value) for value in temperatures) / Decimal(len(temperatures)),
            "f",
        )
    if precipitation:
        stored["total_precipitation_sample_sum"] = format(
            sum(_decimal(value) for value in precipitation),
            "f",
        )
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
