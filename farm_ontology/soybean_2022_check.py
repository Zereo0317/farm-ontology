"""Check the printed 2022 Hokkaido soybean figures.

The printed planted area is 43,200 ha. The printed yield rate is 252 kg
per 10 ares. The printed harvest is 108,900 t. The figures are from
f002-04-021.xls, 令和４年産, 北海道, each stored once. One hectare is
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

PLANTED_AREA_HA = 43_200
YIELD_KG_PER_10A = 252
HARVEST_T = 108_900


def _tonnes(planted_area_ha: int, yield_kg_per_10a: int) -> int:
    return planted_area_ha * yield_kg_per_10a * 10 // 1000


def check_2022_hokkaido_survey(
    year: int,
    path: Path | None = None,
    *,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> dict:
    """Return the 2022 prefecture survey check, or no tonnes."""

    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    if permits_financial_use_test is not None:
        raise ValueError("permits_financial_use_test is not set")
    if year == 2022:
        product = _tonnes(PLANTED_AREA_HA, YIELD_KG_PER_10A)
        stored = {
            "year": 2022,
            "period": "令和４年産",
            "crop": "soybean",
            "area": "北海道",
            "planted_area": "43,200",
            "planted_area_unit": "ha",
            "yield_rate": "252",
            "yield_rate_unit": "kg per 10 ares",
            "harvest": "108,900",
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
