"""Check the stored 2024 Hokkaido soybean figures.

The stored planted area is 46,800 ha. The stored yield rate is 283 kg
per 10 ares. The stored harvest is 132,400 t. One hectare is ten times
10 ares, and one tonne is 1,000 kg, so the product in tonnes is

    planted_hectares * yield_kg_per_10a / 100

The product is compared with the stored harvest. The difference is
rounding, not a new official harvest. The product is a check of the
printed figures, not a completed harvest for the Biratori field and
not a trade. No planted area is stored for 2025 or 2026, so those
years return no tonnes. No area, yield rate, or harvest is invented.
permits_financial_use stays false. permits_financial_use_test is not
set. Class C stays closed. This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

PLANTED_AREA_HA = 46_800
YIELD_KG_PER_10A = 283
HARVEST_T = 132_400
# 1 ha = 10 x 10 ares, and 1 t = 1,000 kg.
TONNES_PER_HECTARE_FACTOR = 100


def _tonnes(planted_area_ha: int, yield_kg_per_10a: int) -> int:
    return planted_area_ha * yield_kg_per_10a // TONNES_PER_HECTARE_FACTOR


def check_printed_hokkaido_harvest(
    year: int,
    path: Path | None = None,
    *,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> dict:
    """Return the 2024 check, or no tonnes when no planted area is stored."""

    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    if permits_financial_use_test is not None:
        raise ValueError("permits_financial_use_test is not set")
    if year == 2024:
        product = _tonnes(PLANTED_AREA_HA, YIELD_KG_PER_10A)
        difference = product - HARVEST_T
        stored = {
            "year": 2024,
            "period": "令和６年産",
            "crop": "soybean",
            "area": "北海道",
            "planted_area": "46,800",
            "planted_area_unit": "ha",
            "yield_rate": "283",
            "yield_rate_unit": "kg per 10 ares",
            "harvest": "132,400",
            "harvest_unit": "t",
            "product": product,
            "product_unit": "t",
            "difference": difference,
            "difference_unit": "t",
            "difference_is": "rounding",
            "not_a_new_official_harvest": True,
            "label": "check of printed figures",
            "not_a_completed_harvest_for_the_biratori_field": True,
            "not_a_trade": True,
            "permits_financial_use": False,
            "class_c_policy": CLASS_C_POLICY,
        }
    else:
        stored = {
            "year": year,
            "crop": "soybean",
            "area": "北海道",
            "planted_area_stored": False,
            "permits_financial_use": False,
            "class_c_policy": CLASS_C_POLICY,
        }
    if path is not None:
        path.write_text(
            json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return stored
