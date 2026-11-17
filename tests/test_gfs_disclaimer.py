import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import gfs_disclaimer
from farm_ontology.gfs_forecast import GFS_FORECAST_URL, record_series_header
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
SENTENCE = gfs_disclaimer.DISCLAIMER_SENTENCE
PAGE = (
    "<h2>Use of NOAA/NWS Data and Products</h2><p>"
    + SENTENCE
    + " You also cannot present information of your own in a way that "
    "makes it appear to be official government information.</p>"
    "<p>Google Maps and Google Earth map information and photographic "
    "imagery are used under license by Google.</p>"
    "<p>The information on National Weather Service Web servers and Web "
    "sites is in the public domain, unless specifically annotated "
    "otherwise, and may be used freely by the public.</p>"
    "<p>2 m temperature 12.4 wind 3.0 m/s rainfall 8 mm grid 13 km</p>"
)
DIFFERENT = "This notice places the pages in the public domain."
NONE = "<p>The disclaimer page was opened and prints no licence sentence.</p>"
TWO = (
    "One product is in the public domain. "
    "Another product is used under license by a vendor."
)


class GfsDisclaimerTests(unittest.TestCase):
    def test_header_still_rejects_a_figure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_series_header(folder, citation_url=GFS_FORECAST_URL, value=13)
            self.assertEqual(list(folder.iterdir()), [])

    def test_stores_the_printed_public_domain_sentence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gfs-disclaimer.json"
            gfs_disclaimer.record_disclaimer_sentence(
                path,
                GFS_FORECAST_URL,
                PAGE,
                disclaimer_url=gfs_disclaimer.DISCLAIMER_URL,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            stored,
            {
                "sentence": SENTENCE,
                "citation_url": GFS_FORECAST_URL,
                "disclaimer_page": gfs_disclaimer.DISCLAIMER_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(stored)
        self.assertNotIn("12.4", text)
        self.assertNotIn("temperature", text)
        self.assertNotIn("wind", text)
        self.assertNotIn("rainfall", text)
        self.assertNotIn("13 km", text)
        self.assertNotIn("Google", text)
        self.assertNotIn("freely by the public", text)
        self.assertNotIn("trade", text)
        self.assertNotIn("harvest", text)
        self.assertNotIn("value", stored)

    def test_different_wording_stores_the_printed_sentence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gfs-disclaimer.json"
            gfs_disclaimer.record_disclaimer_sentence(
                path,
                GFS_FORECAST_URL,
                DIFFERENT,
                disclaimer_url=gfs_disclaimer.DISCLAIMER_URL,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["sentence"], DIFFERENT)
        self.assertNotEqual(stored["sentence"], SENTENCE)
        self.assertFalse(stored["permits_financial_use"])

    def test_no_sentence_or_two_sentences_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gfs-disclaimer.json"
            for body in (NONE, TWO, None, "   "):
                with self.assertRaises(ValueError):
                    gfs_disclaimer.record_disclaimer_sentence(
                        path,
                        GFS_FORECAST_URL,
                        body,
                        disclaimer_url=gfs_disclaimer.DISCLAIMER_URL,
                    )
            self.assertFalse(path.exists())

    def test_other_pages_write_nothing(self) -> None:
        others = (
            "https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast-system",
            "https://www.emc.ncep.noaa.gov/emc/pages/disclaimer/disclaimer_small.png",
            "https://www.weather.gov/disclaimer/",
            "https://example.com/forecast.grib",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gfs-disclaimer.json"
            for disclaimer_url in others:
                with self.assertRaises(ValueError):
                    gfs_disclaimer.record_disclaimer_sentence(
                        path,
                        GFS_FORECAST_URL,
                        PAGE,
                        disclaimer_url=disclaimer_url,
                    )
            for citation in (None, "", "   ", "https://www.emc.ncep.noaa.gov/"):
                with self.assertRaises(ValueError):
                    gfs_disclaimer.record_disclaimer_sentence(
                        path,
                        citation,
                        PAGE,
                        disclaimer_url=gfs_disclaimer.DISCLAIMER_URL,
                    )
            self.assertFalse(path.exists())

    def test_reading_the_stored_record_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "gfs-disclaimer.json"
            gfs_disclaimer.record_disclaimer_sentence(
                path,
                GFS_FORECAST_URL,
                PAGE,
                disclaimer_url=gfs_disclaimer.DISCLAIMER_URL,
            )
            before = path.read_text(encoding="utf-8")
            stored = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names, ["gfs-disclaimer.json"])
        self.assertFalse((folder / "trade.json").exists())
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], "closed")
        self.assertNotIn("trade", after)

    def test_forecast_or_open_class_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gfs-disclaimer.json"
            for label in (
                "trade",
                "completed harvest",
                "forecast value",
                "temperature",
                "12.4",
            ):
                with self.assertRaises(ValueError):
                    gfs_disclaimer.record_disclaimer_sentence(
                        path,
                        GFS_FORECAST_URL,
                        PAGE,
                        disclaimer_url=gfs_disclaimer.DISCLAIMER_URL,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                gfs_disclaimer.record_disclaimer_sentence(
                    path,
                    GFS_FORECAST_URL,
                    PAGE,
                    disclaimer_url=gfs_disclaimer.DISCLAIMER_URL,
                    permits_financial_use=True,
                )
            with self.assertRaises(ValueError):
                gfs_disclaimer.record_disclaimer_sentence(
                    path,
                    GFS_FORECAST_URL,
                    PAGE,
                    disclaimer_url=gfs_disclaimer.DISCLAIMER_URL,
                    class_c_policy="open",
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_disclaimer(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("gfs_disclaimer", text)
            self.assertNotIn("weather.gov/disclaimer", text)


if __name__ == "__main__":
    unittest.main()
