import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import ecmwf_realtime_catalogue
from farm_ontology.ecmwf_open_data import ECMWF_OPEN_DATA_URL
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE_URL = ecmwf_realtime_catalogue.CATALOGUE_URL
SENTENCE = ecmwf_realtime_catalogue.ATTRIBUTION_SENTENCE

OVERVIEW = (
    "<p>This means that the data may be redistributed and used "
    "commercially, subject to appropriate attribution.</p>"
)
CATALOGUE = (
    "<p>The Catalogue outlines the real-time meteorological and "
    "oceanographic products available from the ECMWF forecasting system. "
    "These products are published under a Creative Commons permissive "
    "CC-BY-4.0 licence and the ECMWF Terms Of Use also apply.</p>"
    "<p>Set VI: IFS Sub-seasonal Forecast comprises ensembles of "
    "individual forecasts up to 46 days.</p>"
    "<p>Products are available up to 7 months ahead. Products are "
    "available for month 8-13 ahead each quarter.</p>"
    "<p>Deterministic AIFS forecast provides up to 15 days of forecast.</p>"
    "<p>CAMS Global Atmospheric Composition Forecast provides up to 5 "
    "days of forecast.</p>"
    "<p>ERA5T (ERA5 Initial Release Data, 5 days behind real-time).</p>"
    '<a href="https://www.ecmwf.int/en/forecasts/datasets/set-i">'
    "Set I: IFS Medium-range Control</a>"
    '<a href="https://www.ecmwf.int/en/forecasts/datasets/set-ix">'
    "Set IX: AIFS Single Forecast</a>"
)
FILE_LINKS = (
    '<a href="https://data.ecmwf.int/forecasts/example.grib">example.grib</a>'
    '<a href="https://data.ecmwf.int/forecasts/">Browse the data files</a>'
)
PRINTED = (
    "The 2 m temperature at 12:00 UTC on 17 November 2026 for Europe "
    "is 8.2 °C."
)
LATLON = (
    "The 2 m temperature at 12:00 UTC on 17 November 2026 at 43.2 N "
    "141.3 E is 8.2 °C."
)
TWO = (
    "The 2 m temperature at 12:00 UTC on 17 November 2026 for Europe "
    "is 8.2 °C. The wind at 18:00 UTC on 17 November 2026 for Europe "
    "is 3.0 m/s."
)


class EcmwfRealtimeCatalogueTests(unittest.TestCase):
    def _record(self, path: Path, catalogue: str, **kwargs) -> None:
        ecmwf_realtime_catalogue.record_catalogue_forecast(
            path,
            kwargs.get("citation_url", ECMWF_OPEN_DATA_URL),
            kwargs.get("overview", OVERVIEW),
            catalogue,
            catalogue_url=kwargs.get("catalogue_url", CATALOGUE_URL),
            label=kwargs.get("label"),
            permits_financial_use=kwargs.get("permits_financial_use"),
            class_c_policy=kwargs.get("class_c_policy"),
        )

    def test_catalogue_page_prints_no_forecast_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ecmwf-catalogue.json"
            with self.assertRaises(ValueError) as caught:
                self._record(path, CATALOGUE)
            self.assertIn("no forecast value", str(caught.exception))
            self.assertFalse(path.exists())
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_file_links_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ecmwf-catalogue.json"
            with self.assertRaises(ValueError):
                self._record(path, FILE_LINKS)
            self.assertFalse(path.exists())

    def test_latitude_or_longitude_is_not_chosen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ecmwf-catalogue.json"
            with self.assertRaises(ValueError):
                self._record(path, LATLON)
            self.assertFalse(path.exists())

    def test_two_printed_figures_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ecmwf-catalogue.json"
            with self.assertRaises(ValueError):
                self._record(path, TWO)
            self.assertFalse(path.exists())

    def test_keeps_the_attribution_sentence_with_one_printed_figure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ecmwf-catalogue.json"
            self._record(path, PRINTED)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            stored,
            {
                "sentence": SENTENCE,
                "parameter": "2 m temperature",
                "time": "12:00 UTC on 17 November 2026",
                "area": "Europe",
                "value": "8.2 °C",
                "kind": "published_forecast",
                "citation_url": ECMWF_OPEN_DATA_URL,
                "catalogue_page": CATALOGUE_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertNotEqual(stored["kind"], "completed harvest")
        self.assertNotIn("trade", stored)
        self.assertNotIn("harvest", stored)
        self.assertNotIn("trade", json.dumps(stored))

    def test_missing_sentence_or_other_pages_write_nothing(self) -> None:
        others = (
            "https://data.ecmwf.int/forecasts/",
            "https://data.ecmwf.int/forecasts/example.grib",
            "https://www.ecmwf.int/en/forecasts/datasets/set-i",
            "https://www.ecmwf.int/en/forecasts/datasets/set-ix",
            "https://creativecommons.org/licenses/by/4.0/",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ecmwf-catalogue.json"
            for catalogue_url in others:
                with self.assertRaises(ValueError):
                    self._record(path, PRINTED, catalogue_url=catalogue_url)
            for citation in (None, "", "   ", "https://www.ecmwf.int/"):
                with self.assertRaises(ValueError):
                    self._record(path, PRINTED, citation_url=citation)
            with self.assertRaises(ValueError):
                self._record(path, PRINTED, overview="<p>No attribution sentence.</p>")
            self.assertFalse(path.exists())

    def test_trade_or_open_class_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ecmwf-catalogue.json"
            for label in ("trade", "completed harvest", "8.2"):
                with self.assertRaises(ValueError):
                    self._record(path, PRINTED, label=label)
            with self.assertRaises(ValueError):
                self._record(path, PRINTED, permits_financial_use=True)
            with self.assertRaises(ValueError):
                self._record(path, PRINTED, class_c_policy="open")
            self.assertFalse(path.exists())

    def test_reading_a_stored_figure_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "ecmwf-catalogue.json"
            self._record(path, PRINTED)
            before = path.read_text(encoding="utf-8")
            stored = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names, ["ecmwf-catalogue.json"])
        self.assertFalse((folder / "trade.json").exists())
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], "closed")
        self.assertNotIn("trade", after)

    def test_field_save_does_not_ingest_the_catalogue(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("ecmwf_realtime_catalogue", text)
            self.assertNotIn("catalogue-ecmwf-real-time-products", text)


if __name__ == "__main__":
    unittest.main()
