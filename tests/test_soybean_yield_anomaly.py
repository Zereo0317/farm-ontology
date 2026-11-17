import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.soybean_yield_anomaly import (
    MINIMUM_PAIRED_YEARS,
    STORED_SURVEYS,
    check_yield_anomaly,
    in_growing_season,
    solve_linear,
)

ROOT = Path(__file__).resolve().parents[1]
NDVI = 0.6067
TEMPERATURE_2M = 273.0963548024495
SOIL_WATER = 0.385250727335612
PRECIPITATION = 0.00030462741841574825
SAMPLES = (
    {"date": "2026-10-16", "name": "mod13q1_ndvi", "value": NDVI},
    {"date": "2026-11-08", "name": "temperature_2m", "value": TEMPERATURE_2M},
    {"date": "2026-11-08", "name": "soil_water", "value": SOIL_WATER},
    {"date": "2026-11-08", "name": "precipitation", "value": PRECIPITATION},
)


class SoybeanYieldAnomalyTests(unittest.TestCase):
    def test_one_stored_survey_keeps_the_coefficient_at_zero(self) -> None:
        self.assertEqual(len(STORED_SURVEYS), 1)
        self.assertEqual(STORED_SURVEYS[0]["year"], 2024)
        self.assertEqual(MINIMUM_PAIRED_YEARS, 8)
        plain = check_yield_anomaly(2024)
        self.assertEqual(plain["pair_count"], 1)
        self.assertEqual(plain["coefficient"], 0)
        self.assertEqual(plain["check_product_t"], 46_800 * 283 // 100)
        self.assertEqual(plain["check_product_t"], 132_444)
        self.assertEqual(plain["survey_harvest_t"], 132_400)
        self.assertEqual(plain["survey_planted_area_ha"], 46_800)
        self.assertEqual(plain["survey_yield_kg_per_10a"], 283)
        self.assertEqual(plain["check_difference_t"], 44)
        self.assertEqual(plain["label"], "check")
        self.assertTrue(plain["not_a_forecast"])
        self.assertTrue(plain["not_a_trade"])
        self.assertTrue(plain["not_a_completed_harvest_for_the_biratori_field"])
        self.assertIsNone(plain["forecast_kg_per_10a"])
        self.assertIsNone(plain["forecast_t"])
        self.assertIsNone(plain["leave_one_year_out_backtest"])
        self.assertIsNone(plain["growing_season_features"])
        self.assertEqual(plain["stored_feature_year_count"], 0)
        self.assertFalse(plain["permits_financial_use"])
        self.assertEqual(plain["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("permits_financial_use_test", plain)
        for name, value in plain["coefficients"].items():
            self.assertEqual(value, 0, name)

        stored = check_yield_anomaly(2024, SAMPLES)
        self.assertEqual(stored["pair_count"], 1)
        self.assertEqual(stored["coefficient"], 0)
        self.assertEqual(stored["check_product_t"], plain["check_product_t"])
        self.assertIsNone(stored["forecast_kg_per_10a"])
        self.assertIsNone(stored["forecast_t"])
        self.assertIsNone(stored["leave_one_year_out_backtest"])
        self.assertIsNone(stored["growing_season_features"])
        self.assertEqual(stored["stored_feature_year_count"], 0)
        self.assertEqual(stored["label"], "check")
        self.assertEqual(len(stored["rejected_samples"]), 4)
        for sample in SAMPLES:
            alone = check_yield_anomaly(2024, (sample,))
            self.assertEqual(alone["pair_count"], 1)
            self.assertEqual(alone["coefficient"], 0)
            self.assertEqual(alone["check_product_t"], 132_444)
            self.assertIsNone(alone["forecast_kg_per_10a"])
            self.assertIsNone(alone["forecast_t"])
            self.assertIsNone(alone["growing_season_features"])
            self.assertEqual(alone["rejected_samples"][0]["date"], sample["date"])
            self.assertEqual(alone["rejected_samples"][0]["reason"], "outside June-September")

    def test_rejected_samples_create_no_tonnes_for_2025_or_2026(self) -> None:
        for year in (2025, 2026):
            stored = check_yield_anomaly(year, SAMPLES)
            self.assertEqual(stored["pair_count"], 1)
            self.assertEqual(stored["coefficient"], 0)
            self.assertIsNone(stored["forecast_kg_per_10a"])
            self.assertIsNone(stored["forecast_t"])
            self.assertIsNone(stored["growing_season_features"])
            self.assertNotIn("check_product_t", stored)
            self.assertNotIn("survey_harvest_t", stored)
            self.assertNotIn("survey_planted_area_ha", stored)
            self.assertNotIn("survey_yield_kg_per_10a", stored)
            text = json.dumps(stored)
            for invented in ("132444", "132400", "46800", "283", "132,444", "46,800"):
                self.assertNotIn(invented, text)

    def test_dates_outside_june_through_september_are_not_features(self) -> None:
        self.assertTrue(in_growing_season(date(2024, 6, 1)))
        self.assertTrue(in_growing_season(date(2024, 9, 30)))
        self.assertFalse(in_growing_season(date(2026, 5, 31)))
        self.assertFalse(in_growing_season(date(2026, 10, 1)))
        self.assertFalse(in_growing_season("2026-10-16"))
        self.assertFalse(in_growing_season("2026-11-08"))
        stored = check_yield_anomaly(2024, SAMPLES)
        self.assertEqual(
            [item["date"] for item in stored["rejected_samples"]],
            ["2026-10-16", "2026-11-08", "2026-11-08", "2026-11-08"],
        )
        self.assertEqual(
            [item["name"] for item in stored["rejected_samples"]],
            ["mod13q1_ndvi", "temperature_2m", "soil_water", "precipitation"],
        )
        text = json.dumps(stored["growing_season_features"])
        for value in ("0.6067", "273.0963548024495", "0.385250727335612"):
            self.assertNotIn(value, text)

    def test_a_trade_switch_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "soybean-yield-anomaly.json"
            with self.assertRaises(ValueError):
                check_yield_anomaly(2024, SAMPLES, path, permits_financial_use=True)
            with self.assertRaises(ValueError):
                check_yield_anomaly(2024, SAMPLES, path, permits_financial_use_test=True)
            with self.assertRaises(ValueError):
                check_yield_anomaly(2026, SAMPLES, path, class_c_policy="open")
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_model(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            source = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("soybean_yield_anomaly", source)

    def test_solver_does_not_invent_a_singular_solution(self) -> None:
        self.assertEqual(solve_linear([[2.0, 0.0], [0.0, 4.0]], [2.0, 8.0]), [1.0, 2.0])
        self.assertIsNone(solve_linear([[0.0, 0.0], [0.0, 0.0]], [1.0, 0.0]))


if __name__ == "__main__":
    unittest.main()
