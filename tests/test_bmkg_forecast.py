import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.bmkg_forecast import CITATION_URL, record_forecast_header

ROOT = Path(__file__).resolve().parents[1]
URL = CITATION_URL


class BmkgForecastTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_the_printed_header_without_a_reading(self):
        saved = record_forecast_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(
            header["publisher"],
            "Badan Meteorologi, Klimatologi, dan Geofisika",
        )
        self.assertEqual(header["product"], "public weather forecast")
        self.assertEqual(
            header["period"],
            "3 days, eight steps per day, updated twice a day; "
            "page updated 3 September 2025",
        )
        self.assertEqual(
            header["unit"],
            "not one stored reading; the page names air temperature, humidity, "
            "weather description, wind speed and direction, cloud cover, and visibility",
        )
        self.assertEqual(
            header["administrative_area"],
            "kelurahan or desa, requested by the level-IV administrative code",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "forecast")
        self.assertFalse(header["permits_financial_use"])
        for key in (
            "value",
            "temperature",
            "humidity",
            "wind_speed",
            "wind",
            "visibility",
            "cloud_cover",
            "supply",
        ):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in ("settlement", "yield", "trade", "observation", "completed harvest"):
            self.assertNotIn(word, text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_forecast_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "observation",
            "completed harvest",
            "Settlement",
            "YIELD",
            "Observation",
            "Completed Harvest",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_forecast_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_forecast(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("bmkg_forecast", text)
            self.assertNotIn("prakiraan-cuaca", text)
