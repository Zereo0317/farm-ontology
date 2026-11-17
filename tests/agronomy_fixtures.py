"""Fixture loaders for the WS3 agronomy engine tests.

Follows tests/support.py conventions; fixtures are the synthetic set
under fixtures/agronomy/ (see that directory's README for provenance).
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "agronomy"
SENSORS = ROOT / "fixtures" / "sensors"


def load_agronomy(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def daily_season_rows() -> list[dict]:
    return load_agronomy("daily-eto-rain-season.json")["rows"]


def hourly_rows() -> list[dict]:
    return load_agronomy("hourly-weather-48h.json")["hours"]


def soil_rows(full: bool = True) -> list[dict]:
    name = "soil-chemistry.json" if full else "soil-chemistry-short.json"
    return load_agronomy(name)["rows"]


def sensor_projection_rows() -> list[dict]:
    return load_agronomy("sensor-coverage-rows.json")["rows"]
