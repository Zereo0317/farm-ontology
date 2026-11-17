"""Second layer of the stored 2024 Hokkaido soybean check.

The first product is 46,800 ha times 283 kg per 10 ares, which is
132,444 t. The adjustment coefficient for NDVI and weather is 0. It is
not estimated. Passing an NDVI, a 2 m temperature, soil water, or
precipitation does not change 132,444 t and does not create tonnes for
2025 or 2026. No area or harvest is invented. The result is a check,
not a completed harvest for the Biratori field and not a trade.
permits_financial_use stays false. permits_financial_use_test is not
set. Class C stays closed. This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

PLANTED_AREA_HA = 46_800
YIELD_KG_PER_10A = 283
ADJUSTMENT_COEFFICIENT = 0


def _base_product_t(year: int) -> int | None:
    if year != 2024:
        return None
    return PLANTED_AREA_HA * YIELD_KG_PER_10A // 100


def _adjustment_t(
    ndvi: float | None,
    temperature_2m: float | None,
    soil_water: float | None,
    precipitation: float | None,
) -> int:
    observed = 0.0
    for value in (ndvi, temperature_2m, soil_water, precipitation):
        if value is not None:
            observed += float(value)
    return int(ADJUSTMENT_COEFFICIENT * observed)


def check_with_observations(
    year: int,
    path: Path | None = None,
    *,
    ndvi: float | None = None,
    temperature_2m: float | None = None,
    soil_water: float | None = None,
    precipitation: float | None = None,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> dict:
    """Return the 2024 check unchanged by observations, or no tonnes."""

    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    if permits_financial_use_test is not None:
        raise ValueError("permits_financial_use_test is not set")
    if ADJUSTMENT_COEFFICIENT != 0:
        raise ValueError("the adjustment coefficient is 0 and is not estimated")
    base = _base_product_t(year)
    if base is None:
        stored = {
            "year": year,
            "crop": "soybean",
            "area": "北海道",
            "planted_area_stored": False,
            "adjustment_coefficient": ADJUSTMENT_COEFFICIENT,
            "label": "check",
            "not_a_completed_harvest_for_the_biratori_field": True,
            "not_a_trade": True,
            "permits_financial_use": False,
            "class_c_policy": CLASS_C_POLICY,
        }
    else:
        stored = {
            "year": 2024,
            "period": "令和６年産",
            "crop": "soybean",
            "area": "北海道",
            "product": base + _adjustment_t(ndvi, temperature_2m, soil_water, precipitation),
            "product_unit": "t",
            "adjustment_coefficient": ADJUSTMENT_COEFFICIENT,
            "label": "check",
            "not_a_completed_harvest_for_the_biratori_field": True,
            "not_a_trade": True,
            "permits_financial_use": False,
            "class_c_policy": CLASS_C_POLICY,
        }
    if path is not None:
        path.write_text(
            json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return stored
