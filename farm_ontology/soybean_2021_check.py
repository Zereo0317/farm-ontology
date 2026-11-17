"""Check the printed 2021 Hokkaido soybean figures.

The printed planted area is 42,000 ha. The printed yield rate is 251 kg
per 10 ares. The printed harvest is 105,400 t. The figures are from
f002-03-021.xls, 令和３年産, 北海道, each stored once. One hectare is
ten times 10 ares, and one tonne is 1,000 kg, so the product in tonnes
is

    planted hectares * kg per 10 ares * 10 / 1000

The product is the check. It is compared with the printed harvest, and
the difference is rounding, not a new official harvest. It is a
prefecture survey check, not a completed harvest for the Biratori field
and not a forecast. No planted area is stored for 2025 or 2026, so
those years return no tonnes. No area, yield, or harvest is invented.
The yield-anomaly coefficient is not changed. permits_financial_use
stays false. permits_financial_use_test is not set. Class C stays
closed. This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

PLANTED_AREA_HA = 42_000
YIELD_KG_PER_10A = 251
HARVEST_T = 105_400


def _tonnes(planted_area_ha: int, yield_kg_per_10a: int) -> int:
    return planted_area_ha * yield_kg_per_10a * 10 // 1000


def check_2021_hokkaido_survey(
    year: int,
    path: Path | None = None,
    *,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> dict:
    """Return the 2021 prefecture survey check, or no tonnes."""

    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    if permits_financial_use_test is not None:
        raise ValueError("permits_financial_use_test is not set")
    if year == 2021:
        product = _tonnes(PLANTED_AREA_HA, YIELD_KG_PER_10A)
        stored = {
            "year": 2021,
            "period": "令和３年産",
            "crop": "soybean",
            "area": "北海道",
            "planted_area": "42,000",
            "planted_area_unit": "ha",
            "yield_rate": "251",
            "yield_rate_unit": "kg per 10 ares",
            "harvest": "105,400",
            "harvest_unit": "t",
            "product": product,
            "product_unit": "t",
            "difference": product - HARVEST_T,
            "difference_unit": "t",
            "difference_is": "rounding",
            "not_a_new_official_harvest": True,
            "label": "prefecture survey check",
            "not_a_completed_harvest_for_the_biratori_field": True,
            "not_a_forecast": True,
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
