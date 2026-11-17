import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.era5_season_sample import record_era5_season_sample
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
RESPONSE = (ROOT / "tests" / "fixtures" / "era5-2024-season-sample.json").read_text(encoding="utf-8")
PRINTED = {
    "2024-06-09": (288.9521077473958, 0.014481455087661743),
    "2024-06-25": (288.5377833048503, 0.0023400604724770346),
    "2024-07-11": (292.8079662322998, 0.0015412449835707775),
    "2024-07-27": (292.32324409484863, 0.02605074644088745),
    "2024-08-12": (297.82244364420575, 0.00029669106006124935),
    "2024-08-28": (294.45959726969403, 0.00046935081481436214),
    "2024-09-13": (289.6643708546956, 0.0013131201266673997),
    "2024-09-29": (287.72180493672687, 4.199445237418331e-05),
}


class Era5SeasonSampleTests(unittest.TestCase):
    def test_stores_each_printed_date(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5-season.json"
            record_era5_season_sample(path, RESPONSE)
            stored = json.loads(path.read_text(encoding="utf-8"))
        samples = {sample["date"]: sample for sample in stored["samples"]}
        self.assertEqual(list(samples), list(PRINTED))
        temperatures = []
        precipitation = []
        for sample_date, (temperature, rain) in PRINTED.items():
            self.assertEqual(samples[sample_date]["temperature_2m"], temperature)
            self.assertEqual(samples[sample_date]["total_precipitation_sum"], rain)
            temperatures.append(Decimal(str(temperature)))
            precipitation.append(Decimal(str(rain)))
        self.assertEqual(
            stored["temperature_2m_sample_mean"],
            format(sum(temperatures) / Decimal(len(temperatures)), "f"),
        )
        self.assertEqual(
            stored["total_precipitation_sample_sum"],
            format(sum(precipitation), "f"),
        )
        self.assertEqual(stored["latitude"], "42.7018152")
        self.assertEqual(stored["longitude"], "142.4071291")
        self.assertEqual(stored["ee_registration"], "noncommercial")
        self.assertEqual(stored["gcp_project"], "seges-ai")
        self.assertTrue(stored["not_a_yield"])
        self.assertTrue(stored["not_a_coefficient"])
        self.assertTrue(stored["not_a_trade"])
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("permits_financial_use_test", stored)
        self.assertNotIn("tonnes", stored)
        self.assertNotIn("coefficient", stored)

    def test_a_missing_value_is_omitted(self) -> None:
        payload = json.loads(RESPONSE)
        payload["returned"][0]["total_precipitation_sum"] = None
        payload["returned"] = [
            row for row in payload["returned"] if not str(row["image_id"]).endswith("20240929")
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5-season.json"
            record_era5_season_sample(path, json.dumps(payload))
            stored = json.loads(path.read_text(encoding="utf-8"))
        samples = {sample["date"]: sample for sample in stored["samples"]}
        self.assertEqual(samples["2024-06-09"]["temperature_2m"], 288.9521077473958)
        self.assertNotIn("total_precipitation_sum", samples["2024-06-09"])
        self.assertNotIn("temperature_2m", samples["2024-09-29"])
        self.assertNotIn("total_precipitation_sum", samples["2024-09-29"])
        self.assertNotIn("tonnes", stored)

    def test_a_trade_switch_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5-season.json"
            with self.assertRaises(ValueError):
                record_era5_season_sample(path, "")
            with self.assertRaises(ValueError):
                record_era5_season_sample(path, RESPONSE, label="yield")
            with self.assertRaises(ValueError):
                record_era5_season_sample(path, RESPONSE, permits_financial_use=True)
            with self.assertRaises(ValueError):
                record_era5_season_sample(path, RESPONSE, permits_financial_use_test=True)
            with self.assertRaises(ValueError):
                record_era5_season_sample(path, RESPONSE, class_c_policy="open")
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_sample(self) -> None:
        source = (ROOT / "farm_ontology" / "era5_season_sample.py").read_text(encoding="utf-8")
        self.assertNotIn("planet-api-key", source)
        self.assertNotIn("Export", source)
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("era5_season_sample", text)


if __name__ == "__main__":
    unittest.main()
