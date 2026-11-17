import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.era5_2021_season_sample import record_era5_2021_season_sample
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
RESPONSE = (ROOT / "tests" / "fixtures" / "era5-2021-season-sample.json").read_text(
    encoding="utf-8"
)
PRINTED = {
    "2021-06-10": (292.7834866841634, 0),
    "2021-06-26": (291.74411964416504, 0),
    "2021-07-12": (292.6551456451416, 0.0011990875004812551),
    "2021-07-28": (297.25955963134766, 0.0009007215498968435),
    "2021-08-13": (288.5721035003662, 0.00011883080005503643),
    "2021-08-29": (293.73630968729657, 0.0026297595522919437),
    "2021-09-14": (286.72557004292804, 0.0004095464943816296),
    "2021-09-30": (289.72219785054523, 0.022035348415272438),
}


class Era5Season2021SampleTests(unittest.TestCase):
    def test_stores_each_printed_date(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5-season.json"
            record_era5_2021_season_sample(path, RESPONSE)
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
            row for row in payload["returned"] if not str(row["image_id"]).endswith("20210930")
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5-season.json"
            record_era5_2021_season_sample(path, json.dumps(payload))
            stored = json.loads(path.read_text(encoding="utf-8"))
        samples = {sample["date"]: sample for sample in stored["samples"]}
        self.assertEqual(samples["2021-06-10"]["temperature_2m"], 292.7834866841634)
        self.assertNotIn("total_precipitation_sum", samples["2021-06-10"])
        self.assertNotIn("temperature_2m", samples["2021-09-30"])
        self.assertNotIn("total_precipitation_sum", samples["2021-09-30"])
        self.assertNotIn("tonnes", stored)

    def test_a_trade_switch_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5-season.json"
            with self.assertRaises(ValueError):
                record_era5_2021_season_sample(path, "")
            with self.assertRaises(ValueError):
                record_era5_2021_season_sample(path, RESPONSE, label="yield")
            with self.assertRaises(ValueError):
                record_era5_2021_season_sample(path, RESPONSE, permits_financial_use=True)
            with self.assertRaises(ValueError):
                record_era5_2021_season_sample(path, RESPONSE, permits_financial_use_test=True)
            with self.assertRaises(ValueError):
                record_era5_2021_season_sample(path, RESPONSE, class_c_policy="open")
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_sample(self) -> None:
        source = (ROOT / "farm_ontology" / "era5_2021_season_sample.py").read_text(encoding="utf-8")
        self.assertNotIn("planet-api-key", source)
        self.assertNotIn("Export", source)
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("era5_2021_season_sample", text)


if __name__ == "__main__":
    unittest.main()
