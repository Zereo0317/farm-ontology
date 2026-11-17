import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.adapters.earth_engine import SERIES
from farm_ontology.era5_land import ERA5_LAND_URL, record_series_header
from farm_ontology.era5_precip_runoff import record_precip_runoff
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = (
    ROOT / "tests" / "fixtures" / "era5-precip-runoff.json"
).read_text(encoding="utf-8")
PRINTED = (
    ("runoff_max", "3.8951635360717773e-05"),
    ("runoff_min", "3.580283373594284e-05"),
    ("runoff_sum", "0.0008704811334609985"),
    ("sub_surface_runoff_max", "3.662705421447754e-05"),
    ("sub_surface_runoff_min", "3.565195947885513e-05"),
    ("sub_surface_runoff_sum", "0.0008672624826431274"),
    ("surface_runoff_max", "2.339482307434082e-06"),
    ("surface_runoff_min", "0"),
    ("surface_runoff_sum", "3.2186508178710938e-06"),
    ("total_precipitation_max", "3.4749507904052734e-05"),
    ("total_precipitation_min", "2.115964889526367e-06"),
    ("total_precipitation_sum", "0.00030462741841574825"),
)


class Era5PrecipRunoffTests(unittest.TestCase):
    def test_header_still_rejects_a_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_series_header(
                    folder,
                    citation_url=ERA5_LAND_URL,
                    value="0.00030462741841574825",
                )
            self.assertEqual(list(folder.iterdir()), [])

    def test_stores_the_printed_precipitation_and_runoff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5-precip-runoff.json"
            record_precip_runoff(path, SAMPLE)
            stored = json.loads(path.read_text(encoding="utf-8"))
        rows = stored["rows"]
        self.assertEqual([(row["band"], row["value"]) for row in rows], list(PRINTED))
        self.assertTrue(all(row["label"] == "sample" for row in rows))
        self.assertTrue(all(row["kind"] == "sample" for row in rows))
        self.assertEqual(stored["latitude"], "42.7018152")
        self.assertEqual(stored["longitude"], "142.4071291")
        self.assertEqual(stored["image_id"], "ECMWF/ERA5_LAND/DAILY_AGGR/20261108")
        self.assertEqual(stored["citation"], SERIES["ERA5-Land"]["asset"])
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertEqual(stored["ee_registration"], "noncommercial")
        self.assertNotIn("permits_financial_use_test", stored)
        text = json.dumps(stored)
        for leftover in ("yield", "trade", "harvest", "temperature_2m", "volumetric_soil_water"):
            self.assertNotIn(leftover, text)

    def test_an_absent_band_is_omitted(self) -> None:
        body = """
        {"image_id": "ECMWF/ERA5_LAND/DAILY_AGGR/20261108",
         "values": {"total_precipitation_sum": 0.00030462741841574825}}
        """
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5-precip-runoff.json"
            record_precip_runoff(path, body)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(stored["rows"]), 1)
        self.assertEqual(stored["rows"][0]["band"], "total_precipitation_sum")
        self.assertNotIn("runoff_sum", json.dumps(stored))

    def test_refusal_or_a_trade_label_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5-precip-runoff.json"
            with self.assertRaises(ValueError):
                record_precip_runoff(path, SAMPLE, refused=True)
            with self.assertRaises(ValueError):
                record_precip_runoff(path, '{"image_id": "ECMWF/ERA5_LAND/DAILY_AGGR/20261108"}')
            for label in ("yield", "trade", "0.0003"):
                with self.assertRaises(ValueError):
                    record_precip_runoff(path, SAMPLE, label=label)
            with self.assertRaises(ValueError):
                record_precip_runoff(path, SAMPLE, permits_financial_use_test=True)
            with self.assertRaises(ValueError):
                record_precip_runoff(path, SAMPLE, class_c_policy="open")
            self.assertFalse(path.exists())

    def test_module_does_not_start_an_export(self) -> None:
        text = (ROOT / "farm_ontology" / "era5_precip_runoff.py").read_text(encoding="utf-8")
        self.assertNotIn("Export", text)
        self.assertNotIn("ee.batch", text)
        self.assertNotIn("ee.Initialize", text)

    def test_field_save_does_not_ingest_the_sample(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("era5_precip_runoff", text)
            self.assertNotIn("era5_land", text)
            self.assertNotIn("reanalysis-era5-land", text)


if __name__ == "__main__":
    unittest.main()
