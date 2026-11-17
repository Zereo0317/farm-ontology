import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.modis_season_sample import record_growing_season_samples

ROOT = Path(__file__).resolve().parents[1]
RESPONSE = (
    ROOT / "tests" / "fixtures" / "modis-2024-growing-season.json"
).read_text(encoding="utf-8")
PRINTED = (
    ("MODIS/061/MOD13Q1/2024_06_09", "2024-06-09", 7303),
    ("MODIS/061/MOD13Q1/2024_06_25", "2024-06-25", 7984),
    ("MODIS/061/MOD13Q1/2024_07_11", "2024-07-11", 8619),
    ("MODIS/061/MOD13Q1/2024_07_27", "2024-07-27", 8447),
    ("MODIS/061/MOD13Q1/2024_08_12", "2024-08-12", 8348),
    ("MODIS/061/MOD13Q1/2024_08_28", "2024-08-28", 8530),
    ("MODIS/061/MOD13Q1/2024_09_13", "2024-09-13", 7751),
    ("MODIS/061/MOD13Q1/2024_09_29", "2024-09-29", 8060),
)


class ModisSeasonSampleTests(unittest.TestCase):
    def test_stores_each_printed_raw_ndvi_and_their_mean(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "modis-2024-growing-season.json"
            record_growing_season_samples(path, RESPONSE)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            [(row["image_id"], row["date"], row["ndvi"]) for row in stored["samples"]],
            list(PRINTED),
        )
        values = [ndvi for _image, _date, ndvi in PRINTED]
        self.assertEqual(stored["sample_mean"]["count"], len(values))
        self.assertEqual(stored["sample_mean"]["value"], "8130.25")
        self.assertEqual(sum(values) / len(values), 8130.25)
        self.assertEqual(stored["sample_mean"]["label"], "sample mean")
        self.assertTrue(stored["sample_mean"]["not_a_yield"])
        self.assertTrue(stored["sample_mean"]["not_a_season_coefficient"])
        self.assertEqual(stored["label"], "sample")
        self.assertTrue(stored["not_the_biratori_field_harvest"])
        self.assertTrue(stored["not_a_trade"])
        self.assertEqual(stored["ee_registration"], "noncommercial")
        self.assertEqual(stored["gcp_project"], "seges-ai")
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("permits_financial_use_test", stored)
        for absent in ("tonnes", "product", "harvest", "yield", "coefficient"):
            self.assertNotIn(absent, stored)
        text = json.dumps(stored)
        self.assertNotIn("0.7303", text)
        self.assertNotIn("6067", text)

    def test_a_missing_value_is_left_out_of_the_mean(self) -> None:
        payload = json.loads(RESPONSE)
        payload["features"][0]["properties"]["NDVI"] = None
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "modis-2024-growing-season.json"
            record_growing_season_samples(path, json.dumps(payload))
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(stored["samples"]), 7)
        self.assertNotIn("2024_06_09", json.dumps(stored))
        kept = [row["ndvi"] for row in stored["samples"]]
        self.assertEqual(stored["sample_mean"]["count"], 7)
        self.assertEqual(sum(kept), sum(ndvi for _image, _date, ndvi in PRINTED[1:]))
        self.assertNotEqual(stored["sample_mean"]["value"], "8130.25")

    def test_a_trade_switch_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "modis-2024-growing-season.json"
            with self.assertRaises(ValueError):
                record_growing_season_samples(path, "")
            with self.assertRaises(ValueError):
                record_growing_season_samples(path, RESPONSE, label="yield")
            with self.assertRaises(ValueError):
                record_growing_season_samples(path, RESPONSE, permits_financial_use=True)
            with self.assertRaises(ValueError):
                record_growing_season_samples(path, RESPONSE, permits_financial_use_test=True)
            with self.assertRaises(ValueError):
                record_growing_season_samples(path, RESPONSE, class_c_policy="open")
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_sample(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            source = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("modis_season_sample", source)


if __name__ == "__main__":
    unittest.main()
