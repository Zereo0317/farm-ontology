import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.modis_ndvi_sample import record_ndvi_sample
from farm_ontology.modis_vegetation import MODIS_URL, record_series_header
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = (
    ROOT / "tests" / "fixtures" / "modis-ndvi-sample.json"
).read_text(encoding="utf-8")


class ModisNdviSampleTests(unittest.TestCase):
    def test_header_still_rejects_a_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_series_header(
                    folder,
                    citation_url=MODIS_URL,
                    value="6067",
                )
            self.assertEqual(list(folder.iterdir()), [])

    def test_stores_the_printed_ndvi(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "modis-ndvi-sample.json"
            record_ndvi_sample(path, SAMPLE)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["value"], "6067")
        self.assertEqual(stored["band"], "NDVI")
        self.assertEqual(stored["image_id"], "MODIS/061/MOD13Q1/2026_10_16")
        self.assertEqual(stored["date"], "2026-10-16")
        self.assertEqual(stored["latitude"], "42.7018152")
        self.assertEqual(stored["longitude"], "142.4071291")
        self.assertEqual(stored["label"], "sample")
        self.assertEqual(stored["kind"], "sample")
        self.assertEqual(stored["citation_url"], MODIS_URL)
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertEqual(stored["ee_registration"], "noncommercial")
        self.assertNotIn("permits_financial_use_test", stored)
        text = json.dumps(stored)
        for leftover in ("0.6067", "tonnes", "yield", "trade", "harvest", "EVI"):
            self.assertNotIn(leftover, text)

    def test_no_ndvi_or_a_trade_label_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "modis-ndvi-sample.json"
            with self.assertRaises(ValueError):
                record_ndvi_sample(path, SAMPLE, refused=True)
            with self.assertRaises(ValueError):
                record_ndvi_sample(
                    path,
                    '{"image_id": "MODIS/061/MOD13Q1/2026_10_16", "date": "2026-10-16", "values": {}}',
                )
            for label in ("yield", "trade", "tonnes", "6067"):
                with self.assertRaises(ValueError):
                    record_ndvi_sample(path, SAMPLE, label=label)
            with self.assertRaises(ValueError):
                record_ndvi_sample(path, SAMPLE, permits_financial_use_test=True)
            self.assertFalse(path.exists())

    def test_module_does_not_start_an_export(self) -> None:
        text = (ROOT / "farm_ontology" / "modis_ndvi_sample.py").read_text(encoding="utf-8")
        self.assertNotIn("Export", text)
        self.assertNotIn("ee.batch", text)
        self.assertNotIn("ee.Initialize", text)
        self.assertNotIn("0.0001", text)

    def test_field_save_does_not_ingest_the_sample(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("modis_ndvi_sample", text)
            self.assertNotIn("modis_vegetation", text)
            self.assertNotIn("lpcloud-mod13q1", text)


if __name__ == "__main__":
    unittest.main()
