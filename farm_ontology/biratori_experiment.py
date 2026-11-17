"""Biratori experiment place.

The place is the plus code, the named town, and the map link that were
given. It is a non-commercial farm experiment with Hokkaido University.
No latitude, longitude, satellite value, weather value, soil value,
water value, yield, or demand figure is stored. permits_financial_use
stays false. permits_financial_use_test is not set. Class C stays
closed. The financial-mode print lists the place and is not a trade.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

PLUS_CODE = "PC24+PVC"
LOCALITY = "Biratori"
PREFECTURE = "Hokkaido"
COUNTRY = "Japan"
PLACE = "Biratori, Hokkaido, Japan"
MAP_URL = "https://maps.app.goo.gl/dKfj9uWuQm8U1aQi9"
PURPOSE = "non-commercial farm experiment with Hokkaido University"
UNSTORED_CLASSES = (
    "a satellite value is not stored",
    "a weather value is not stored",
    "a soil value is not stored",
    "a water value is not stored",
    "a yield is not stored",
    "a demand figure is not stored",
)


def financial_mode_print() -> str:
    """List the place for financial mode. The print is not a trade."""

    lines = [
        "Financial mode",
        f"plus code {PLUS_CODE}",
        PLACE,
        MAP_URL,
        PURPOSE,
    ]
    lines.extend(UNSTORED_CLASSES)
    lines.append("this print is not a trade")
    return "\n".join(lines) + "\n"


def record_experiment_point(
    path: Path,
    *,
    plus_code: str | None = None,
    place: str | None = None,
    map_url: str | None = None,
    purpose: str | None = None,
    latitude: object = None,
    longitude: object = None,
    satellite: object = None,
    weather: object = None,
    soil: object = None,
    water: object = None,
    yield_value: object = None,
    demand: object = None,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the given place, or write nothing."""

    if plus_code not in (None, PLUS_CODE):
        raise ValueError("the plus code is PC24+PVC")
    if place not in (None, PLACE):
        raise ValueError("the place is Biratori, Hokkaido, Japan")
    if map_url not in (None, MAP_URL):
        raise ValueError("the map link is the one that was given")
    if purpose not in (None, PURPOSE):
        raise ValueError("the purpose is the non-commercial farm experiment")
    invented = (
        latitude,
        longitude,
        satellite,
        weather,
        soil,
        water,
        yield_value,
        demand,
    )
    if any(value is not None for value in invented):
        raise ValueError(
            "latitude, longitude, satellite, weather, soil, water, yield, "
            "and demand are not stored"
        )
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    if permits_financial_use_test is not None:
        raise ValueError("permits_financial_use_test is not set")
    stored = {
        "plus_code": PLUS_CODE,
        "place": PLACE,
        "locality": LOCALITY,
        "prefecture": PREFECTURE,
        "country": COUNTRY,
        "map_url": MAP_URL,
        "purpose": PURPOSE,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
