import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.biratori_bundle import record_bundle_observations

ROOT = Path(__file__).resolve().parents[1]

RECORDS = [
    {
        "dataset": "MODIS/061/MOD09GA",
        "image_id": "MODIS/061/MOD09GA/2026_11_14",
        "image_date": "2026-11-14",
        "band": "sur_refl_b01",
        "value": 1667,
    },
    {
        "dataset": "ECMWF/ERA5_LAND/DAILY_AGGR",
        "image_id": "ECMWF/ERA5_LAND/DAILY_AGGR/20261108",
        "image_date": "2026-11-08",
        "band": "temperature_2m",
        "value": 273.0963548024495,
    },
    {
        "dataset": "ECMWF/ERA5_LAND/DAILY_AGGR",
        "image_id": "ECMWF/ERA5_LAND/DAILY_AGGR/20261108",
        "image_date": "2026-11-08",
        "band": "u_component_of_wind_10m",
        "value": 2.654146194458008,
    },
    {
        "dataset": "ECMWF/ERA5_LAND/DAILY_AGGR",
        "image_id": "ECMWF/ERA5_LAND/DAILY_AGGR/20261108",
        "image_date": "2026-11-08",
        "band": "v_component_of_wind_10m",
        "value": -1.241633415222168,
    },
    {
        "dataset": "UCSB-CHG/CHIRPS/DAILY",
        "image_id": "UCSB-CHG/CHIRPS/DAILY/20260930",
        "image_date": "2026-09-30",
        "band": "precipitation",
        "value": 0,
    },
]


class BiratoriBundleTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_bundle_without_citation_url_writes_nothing(self):
        self.assertEqual(len(RECORDS), 5)
        for record in RECORDS:
            self.assertNotIn("citation_url", record)
        attempts = [
            RECORDS,
            [{**record, "citation_url": None} for record in RECORDS],
            [{**record, "citation_url": ""} for record in RECORDS],
            [{**record, "citation_url": "   "} for record in RECORDS],
        ]
        for records in attempts:
            with self.assertRaises(ValueError):
                record_bundle_observations(self.folder, records)
        self.assertEqual(list(self.folder.iterdir()), [])
        source = (ROOT / "farm_ontology" / "biratori_bundle.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("It has no citation_url on any record.", flat)
        self.assertIn("Do not invent a catalog URL.", flat)
        self.assertIn("permits_financial_use stays false.", flat)
        self.assertIn("No yield, price, or trade is stored.", flat)
        for number in (
            "1667",
            "273.0963548024495",
            "2.654146194458008",
            "-1.241633415222168",
        ):
            self.assertNotIn(number, source)
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("biratori_bundle", text)
            self.assertNotIn("1667", text)
            self.assertNotIn("273.0963548024495", text)


if __name__ == "__main__":
    unittest.main()
