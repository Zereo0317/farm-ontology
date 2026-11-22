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


def synthetic_irrigation_advisory(rows, **kwargs):
    """Adapt only synthetic test rows to the explicit v1 safety contract."""
    from datetime import date, timedelta
    from farm_ontology.agronomy.irrigation import IrrigationInitialState, SoilProfile, irrigation_advisory

    if not rows or kwargs.get("reading") is None:
        return irrigation_advisory(rows, **kwargs)
    at = kwargs["at"]
    prepared = [dict(row, source_kind="observation" if date.fromisoformat(row["date"]) < at.date() else "forecast",
                     availability_time=at.isoformat()) for row in rows]
    soil = kwargs.get("soil", SoilProfile())
    cfg = kwargs.get("cfg")
    root = cfg.initial_root_depletion_mm if cfg and cfg.initial_root_depletion_mm is not None else soil.raw_mm
    surface = cfg.initial_surface_depletion_mm if cfg and cfg.initial_surface_depletion_mm is not None else (cfg.tew_mm if cfg else 12.0)
    state = IrrigationInitialState((date.fromisoformat(prepared[0]["date"]) - timedelta(days=1)).isoformat(),
                                   0, root, surface, "synthetic test setup; not field evidence")
    return irrigation_advisory(prepared, initial_state=state, **kwargs)
