import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.adapters.earth_engine import SERIES
from farm_ontology.era5_land import ERA5_LAND_URL, record_series_header
from farm_ontology.era5_point_sample import record_point_sample
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = (
    ROOT / "tests" / "fixtures" / "era5-biratori-sample.json"
).read_text(encoding="utf-8")
COORDINATES = (
    "https://www.google.com/maps/place/42.701815,142.407129/data=!4m6!3m5!1s0!7e2"
    "!8m2!3d42.7018152!4d142.4071291"
)
FIRST = (
    ("temperature_2m", "273.0963548024495"),
    ("volumetric_soil_water_layer_1", "0.385250727335612"),
)


class Era5PointSampleTests(unittest.TestCase):
    def test_header_still_rejects_a_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_series_header(
                    folder,
                    citation_url=ERA5_LAND_URL,
                    value="273.0963548024495",
                )
            self.assertEqual(list(folder.iterdir()), [])

    def test_stores_the_printed_temperature_and_soil_water(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5-point-sample.json"
            record_point_sample(
                path,
                coordinate_response=COORDINATES,
                sample_response=SAMPLE,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))
        rows = stored["rows"]
        self.assertEqual(rows[0]["band"], FIRST[0][0])
        self.assertEqual(rows[0]["value"], FIRST[0][1])
        self.assertEqual(rows[1]["band"], FIRST[1][0])
        self.assertEqual(rows[1]["value"], FIRST[1][1])
        self.assertEqual(len(rows), 13)
        self.assertTrue(all(row["label"] == "sample" for row in rows))
        self.assertTrue(all(row["kind"] == "sample" for row in rows))
        self.assertEqual(stored["latitude"], "42.7018152")
        self.assertEqual(stored["longitude"], "142.4071291")
        self.assertEqual(stored["image_id"], "ECMWF/ERA5_LAND/DAILY_AGGR/20261108")
        self.assertEqual(stored["citation"], SERIES["ERA5-Land"]["asset"])
        self.assertEqual(stored["plus_code"], "PC24+PVC")
        self.assertEqual(stored["place"], "Biratori, Hokkaido, Japan")
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertEqual(stored["ee_registration"], "noncommercial")
        self.assertNotIn("permits_financial_use_test", stored)
        text = json.dumps(stored)
        for leftover in ("yield", "trade", "harvest", "dewpoint", "Export"):
            self.assertNotIn(leftover, text)
        bands = [row["band"] for row in rows]
        self.assertNotIn("total_precipitation_sum", bands)
        self.assertTrue(all(band == "temperature_2m" or band.startswith("volumetric_soil_water") for band in bands))

    def test_refusal_or_missing_coordinates_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5-point-sample.json"
            with self.assertRaises(ValueError):
                record_point_sample(
                    path,
                    coordinate_response=COORDINATES,
                    sample_response=SAMPLE,
                    refused=True,
                )
            with self.assertRaises(ValueError):
                record_point_sample(
                    path,
                    coordinate_response="no coordinates printed",
                    sample_response=SAMPLE,
                )
            with self.assertRaises(ValueError):
                record_point_sample(
                    path,
                    coordinate_response=COORDINATES,
                    sample_response='{"error": "permission denied"}',
                )
            for label in ("yield", "trade", "273"):
                with self.assertRaises(ValueError):
                    record_point_sample(
                        path,
                        coordinate_response=COORDINATES,
                        sample_response=SAMPLE,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                record_point_sample(
                    path,
                    coordinate_response=COORDINATES,
                    sample_response=SAMPLE,
                    permits_financial_use_test=True,
                )
            self.assertFalse(path.exists())

    def test_module_does_not_start_an_export(self) -> None:
        text = (ROOT / "farm_ontology" / "era5_point_sample.py").read_text(encoding="utf-8")
        self.assertNotIn("Export", text)
        self.assertNotIn("ee.batch", text)
        self.assertNotIn("ee.Initialize", text)

    def test_field_save_does_not_ingest_the_sample(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("era5_point_sample", text)
            self.assertNotIn("era5_land", text)
            self.assertNotIn("reanalysis-era5-land", text)


if __name__ == "__main__":
    unittest.main()
