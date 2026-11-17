import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.era5_2022_season_sample import record_era5_2022_season_sample
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
RESPONSE = (ROOT / "tests" / "fixtures" / "era5-2022-season-sample.json").read_text(
    encoding="utf-8"
)
PRINTED = {
    "2022-06-10": (287.0479901631673, 0.0007978517302262844),
    "2022-06-26": (291.9650071461995, 0.007505419850247108),
    "2022-07-12": (294.39778391520184, 0.002423167228641887),
    "2022-07-28": (295.14350001017254, 0.00038104057301779903),
    "2022-08-13": (294.6106421152751, 0.0018546938895269705),
    "2022-08-29": (291.4259433746338, 0.0005768835544586182),
    "2022-09-14": (287.3880672454834, 1.2248753478161234e-06),
    "2022-09-30": (289.02060381571454, 7.569789886474609e-06),
}


class Era5Season2022SampleTests(unittest.TestCase):
    def test_stores_each_printed_date(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5-season.json"
            record_era5_2022_season_sample(path, RESPONSE)
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
            row for row in payload["returned"] if not str(row["image_id"]).endswith("20220930")
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5-season.json"
            record_era5_2022_season_sample(path, json.dumps(payload))
            stored = json.loads(path.read_text(encoding="utf-8"))
        samples = {sample["date"]: sample for sample in stored["samples"]}
        self.assertEqual(samples["2022-06-10"]["temperature_2m"], 287.0479901631673)
        self.assertNotIn("total_precipitation_sum", samples["2022-06-10"])
        self.assertNotIn("temperature_2m", samples["2022-09-30"])
        self.assertNotIn("total_precipitation_sum", samples["2022-09-30"])
        self.assertNotIn("tonnes", stored)

    def test_a_trade_switch_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5-season.json"
            with self.assertRaises(ValueError):
                record_era5_2022_season_sample(path, "")
            with self.assertRaises(ValueError):
                record_era5_2022_season_sample(path, RESPONSE, label="yield")
            with self.assertRaises(ValueError):
                record_era5_2022_season_sample(path, RESPONSE, permits_financial_use=True)
            with self.assertRaises(ValueError):
                record_era5_2022_season_sample(path, RESPONSE, permits_financial_use_test=True)
            with self.assertRaises(ValueError):
                record_era5_2022_season_sample(path, RESPONSE, class_c_policy="open")
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_sample(self) -> None:
        source = (ROOT / "farm_ontology" / "era5_2022_season_sample.py").read_text(encoding="utf-8")
        self.assertNotIn("planet-api-key", source)
        self.assertNotIn("Export", source)
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("era5_2022_season_sample", text)


if __name__ == "__main__":
    unittest.main()
