import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.modis_2023_season_sample import record_2023_growing_season_samples

ROOT = Path(__file__).resolve().parents[1]
RESPONSE = (
    ROOT / "tests" / "fixtures" / "modis-2023-growing-season.json"
).read_text(encoding="utf-8")
PRINTED = (
    ("MODIS/061/MOD13Q1/2023_06_10", "2023-06-10", 6997),
    ("MODIS/061/MOD13Q1/2023_06_26", "2023-06-26", 8519),
    ("MODIS/061/MOD13Q1/2023_07_12", "2023-07-12", 8365),
    ("MODIS/061/MOD13Q1/2023_07_28", "2023-07-28", 7266),
    ("MODIS/061/MOD13Q1/2023_08_13", "2023-08-13", 7224),
    ("MODIS/061/MOD13Q1/2023_08_29", "2023-08-29", 8037),
    ("MODIS/061/MOD13Q1/2023_09_14", "2023-09-14", 7779),
    ("MODIS/061/MOD13Q1/2023_09_30", "2023-09-30", 7433),
)


class Modis2023SeasonSampleTests(unittest.TestCase):
    def test_stores_each_printed_raw_ndvi_and_their_mean(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "modis-2023-growing-season.json"
            record_2023_growing_season_samples(path, RESPONSE)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            [(row["image_id"], row["date"], row["ndvi"]) for row in stored["samples"]],
            list(PRINTED),
        )
        values = [ndvi for _image, _date, ndvi in PRINTED]
        self.assertEqual(stored["sample_mean"]["count"], len(values))
        self.assertEqual(stored["sample_mean"]["value"], "7702.5")
        self.assertEqual(sum(values) / len(values), 7702.5)
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
        self.assertNotIn("0.6997", text)
        self.assertNotIn("6067", text)

    def test_a_missing_value_is_left_out_of_the_mean(self) -> None:
        payload = json.loads(RESPONSE)
        payload["features"][0]["properties"]["NDVI"] = None
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "modis-2023-growing-season.json"
            record_2023_growing_season_samples(path, json.dumps(payload))
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(stored["samples"]), 7)
        self.assertNotIn("2023_06_10", json.dumps(stored))
        kept = [row["ndvi"] for row in stored["samples"]]
        self.assertEqual(stored["sample_mean"]["count"], 7)
        self.assertEqual(sum(kept), sum(ndvi for _image, _date, ndvi in PRINTED[1:]))
        self.assertNotEqual(stored["sample_mean"]["value"], "7702.5")

    def test_a_trade_switch_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "modis-2023-growing-season.json"
            with self.assertRaises(ValueError):
                record_2023_growing_season_samples(path, "")
            with self.assertRaises(ValueError):
                record_2023_growing_season_samples(path, RESPONSE, label="yield")
            with self.assertRaises(ValueError):
                record_2023_growing_season_samples(path, RESPONSE, permits_financial_use=True)
            with self.assertRaises(ValueError):
                record_2023_growing_season_samples(
                    path, RESPONSE, permits_financial_use_test=True
                )
            with self.assertRaises(ValueError):
                record_2023_growing_season_samples(path, RESPONSE, class_c_policy="open")
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_sample(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            source = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("modis_2023_season_sample", source)
        source = (
            ROOT / "farm_ontology" / "modis_2023_season_sample.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("Export", source)
        self.assertNotIn("planet-api-key", source)


if __name__ == "__main__":
    unittest.main()
