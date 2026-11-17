"""Hokkaido soybean yield-anomaly check.

The stored survey year is 2024: 46,800 ha, 283 kg per 10 ares, and a
printed harvest of 132,400 t. The identity product is that area times
that yield, which is 132,444 t. It stays a check, not a forecast.

The estimator is leave-one-year-out ordinary least squares of the survey
yield anomaly on three growing-season features: MOD13Q1 mean NDVI,
ERA5-Land precipitation sum, and ERA5-Land 2 m temperature mean. The
anomaly is kg per 10 ares minus the mean of the stored survey years.
The growing season is June through September. A sample dated outside
that window is rejected and is not a feature. Soil water is not one of
the three features.

A coefficient may leave 0 only when at least 8 paired survey years have
all three features and a leave-one-year-out backtest is stored. With
fewer pairs the coefficient is 0, forecast kg per 10 ares is empty, and
forecast tonnes are empty. Tonnes are produced only when a forecast kg
per 10 ares exists and that year's planted area is a stored survey
figure. No coefficient, yield, or trade is invented.
permits_financial_use stays false. permits_financial_use_test is not
set. Class C stays closed. This module is not called from a field save.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

PLANTED_AREA_HA = 46_800
YIELD_KG_PER_10A = 283
HARVEST_T = 132_400
MINIMUM_PAIRED_YEARS = 8
GROWING_SEASON_MONTHS = (6, 7, 8, 9)
OUTSIDE_GROWING_SEASON = "outside June-September"
NOT_A_FEATURE = "not a growing-season feature"

STORED_SURVEYS = (
    {
        "year": 2024,
        "planted_area_ha": PLANTED_AREA_HA,
        "yield_kg_per_10a": YIELD_KG_PER_10A,
        "harvest_t": HARVEST_T,
    },
)

_KINDS = {
    "mod13q1_ndvi": "ndvi",
    "ndvi": "ndvi",
    "precipitation": "precipitation",
    "total_precipitation_sum": "precipitation",
    "temperature_2m": "temperature_2m",
    "soil_water": "soil_water",
    "volumetric_soil_water_layer_1": "soil_water",
}
_FEATURE_KINDS = ("ndvi", "precipitation", "temperature_2m")
_ZERO_COEFFICIENTS = {
    "intercept": 0,
    "mod13q1_mean_ndvi": 0,
    "era5_land_precipitation_sum": 0,
    "era5_land_temperature_2m_mean": 0,
}


def in_growing_season(value) -> bool:
    return _as_date(value).month in GROWING_SEASON_MONTHS


def solve_linear(matrix, vector):
    """Solve a square linear system. A singular system returns None."""

    width = len(vector)
    if width == 0 or any(len(row) != width for row in matrix):
        return None
    augmented = [
        [float(item) for item in row] + [float(vector[index])]
        for index, row in enumerate(matrix)
    ]
    for column in range(width):
        pivot = max(range(column, width), key=lambda row: abs(augmented[row][column]))
        if augmented[pivot][column] == 0.0:
            return None
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        scale = augmented[column][column]
        for index in range(column, width + 1):
            augmented[column][index] /= scale
        for row in range(width):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor == 0.0:
                continue
            for index in range(column, width + 1):
                augmented[row][index] -= factor * augmented[column][index]
    return [augmented[row][width] for row in range(width)]


def check_yield_anomaly(
    year: int,
    samples=(),
    path: Path | None = None,
    *,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> dict:
    """Return the yield-anomaly check for one year."""

    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    if permits_financial_use_test is not None:
        raise ValueError("permits_financial_use_test is not set")
    rejected, features_by_year = _split_samples(samples)
    complete = _complete_rows(features_by_year)
    backtest, coefficients = _gated_coefficients(complete)
    coefficient = 0 if all(value == 0 for value in coefficients.values()) else coefficients["intercept"]
    survey = next((item for item in STORED_SURVEYS if item["year"] == year), None)
    features = features_by_year.get(year)
    if backtest is None or features is None:
        forecast_kg = None
    else:
        forecast_kg = _forecast_kg(features, coefficients)
    if forecast_kg is None or survey is None:
        forecast_t = None
    else:
        forecast_t = forecast_kg * survey["planted_area_ha"] / 100
    stored = {
        "year": year,
        "crop": "soybean",
        "area": "北海道",
        "pair_count": len(STORED_SURVEYS),
        "stored_feature_year_count": len(features_by_year),
        "coefficient": coefficient,
        "coefficients": coefficients,
        "forecast_kg_per_10a": forecast_kg,
        "forecast_t": forecast_t,
        "leave_one_year_out_backtest": backtest,
        "growing_season_features": features,
        "rejected_samples": rejected,
        "label": "check",
        "not_a_forecast": True,
        "not_a_trade": True,
        "not_a_completed_harvest_for_the_biratori_field": True,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    if survey is not None:
        product = survey["planted_area_ha"] * survey["yield_kg_per_10a"] // 100
        stored["survey_planted_area_ha"] = survey["planted_area_ha"]
        stored["survey_yield_kg_per_10a"] = survey["yield_kg_per_10a"]
        stored["survey_harvest_t"] = survey["harvest_t"]
        stored["check_product_t"] = product
        stored["check_difference_t"] = product - survey["harvest_t"]
    if path is not None:
        path.write_text(
            json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return stored


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _split_samples(samples):
    rejected = []
    accepted = []
    for item in samples:
        if not isinstance(item, dict) or "date" not in item:
            raise ValueError("a sample needs a date")
        sample_date = _as_date(item["date"])
        supplied = str(item.get("name", ""))
        kind = _KINDS.get(supplied)
        record = {
            "date": sample_date.isoformat(),
            "name": supplied,
            "reason": OUTSIDE_GROWING_SEASON,
        }
        if not in_growing_season(sample_date):
            rejected.append(record)
            continue
        if kind not in _FEATURE_KINDS:
            record["reason"] = NOT_A_FEATURE
            rejected.append(record)
            continue
        value = _number(item.get("value"))
        if value is None:
            record["reason"] = NOT_A_FEATURE
            rejected.append(record)
            continue
        accepted.append({"year": sample_date.year, "kind": kind, "value": value})
    return rejected, _features_by_year(accepted)


def _features_by_year(accepted):
    buckets = {}
    for sample in accepted:
        bucket = buckets.setdefault(
            sample["year"],
            {"ndvi": [], "precipitation": [], "temperature_2m": []},
        )
        bucket[sample["kind"]].append(sample["value"])
    ready = {}
    for year, bucket in buckets.items():
        if not bucket["ndvi"] or not bucket["precipitation"] or not bucket["temperature_2m"]:
            continue
        ready[year] = {
            "mod13q1_mean_ndvi": sum(bucket["ndvi"]) / len(bucket["ndvi"]),
            "era5_land_precipitation_sum": sum(bucket["precipitation"]),
            "era5_land_temperature_2m_mean": (
                sum(bucket["temperature_2m"]) / len(bucket["temperature_2m"])
            ),
        }
    return ready


def _mean_yield():
    return sum(item["yield_kg_per_10a"] for item in STORED_SURVEYS) / len(STORED_SURVEYS)


def _complete_rows(features_by_year):
    rows = []
    mean_yield = _mean_yield()
    for survey in STORED_SURVEYS:
        features = features_by_year.get(survey["year"])
        if features is None:
            continue
        rows.append(
            {
                "year": survey["year"],
                "ndvi": features["mod13q1_mean_ndvi"],
                "precipitation": features["era5_land_precipitation_sum"],
                "temperature_2m": features["era5_land_temperature_2m_mean"],
                "anomaly": survey["yield_kg_per_10a"] - mean_yield,
            }
        )
    return rows


def _ols(rows):
    width = 4
    normal = [[0.0] * width for _ in range(width)]
    target = [0.0] * width
    for row in rows:
        values = (1.0, row["ndvi"], row["precipitation"], row["temperature_2m"])
        for left in range(width):
            target[left] += values[left] * row["anomaly"]
            for right in range(width):
                normal[left][right] += values[left] * values[right]
    solved = solve_linear(normal, target)
    if solved is None:
        return None
    return {
        "intercept": solved[0],
        "mod13q1_mean_ndvi": solved[1],
        "era5_land_precipitation_sum": solved[2],
        "era5_land_temperature_2m_mean": solved[3],
    }


def _leave_one_year_out(rows):
    if len(rows) < MINIMUM_PAIRED_YEARS:
        return None
    backtest = []
    for index, held in enumerate(rows):
        trained = _ols(rows[:index] + rows[index + 1 :])
        if trained is None:
            return None
        predicted = (
            trained["intercept"]
            + trained["mod13q1_mean_ndvi"] * held["ndvi"]
            + trained["era5_land_precipitation_sum"] * held["precipitation"]
            + trained["era5_land_temperature_2m_mean"] * held["temperature_2m"]
        )
        backtest.append(
            {
                "year": held["year"],
                "predicted_anomaly_kg_per_10a": predicted,
            }
        )
    return backtest


def _gated_coefficients(rows):
    if len(rows) < MINIMUM_PAIRED_YEARS:
        return None, dict(_ZERO_COEFFICIENTS)
    backtest = _leave_one_year_out(rows)
    if backtest is None:
        return None, dict(_ZERO_COEFFICIENTS)
    trained = _ols(rows)
    if trained is None:
        return None, dict(_ZERO_COEFFICIENTS)
    return backtest, trained


def _forecast_kg(features, coefficients):
    anomaly = (
        coefficients["intercept"]
        + coefficients["mod13q1_mean_ndvi"] * features["mod13q1_mean_ndvi"]
        + coefficients["era5_land_precipitation_sum"] * features["era5_land_precipitation_sum"]
        + coefficients["era5_land_temperature_2m_mean"] * features["era5_land_temperature_2m_mean"]
    )
    return _mean_yield() + anomaly
