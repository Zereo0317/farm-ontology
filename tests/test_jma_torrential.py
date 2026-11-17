import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.jma_torrential import (
    JMA_TORRENTIAL_URL,
    PERIOD,
    UNIT,
    record_series_header,
)

ROOT = Path(__file__).resolve().parents[1]
URL = JMA_TORRENTIAL_URL


class JmaTorrentialTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Japan Meteorological Agency")
        self.assertEqual(header["product"], "Localized Torrential Rain Forecast Map")
        self.assertEqual(header["period"], PERIOD)
        self.assertIn("08:50 JST, 17 November 2026", header["period"])
        self.assertIn("20:50", header["period"])
        self.assertIn("23:50", header["period"])
        self.assertIn("02:50", header["period"])
        self.assertIn("05:50", header["period"])
        self.assertIn("08:50", header["period"])
        self.assertIn("next 3 h", header["period"])
        self.assertIn("every 10 minutes", header["period"])
        self.assertIn("up to 6 hours ahead", header["period"])
        self.assertIn("from 7 to 15 hours ahead", header["period"])
        self.assertIn("every hour", header["period"])
        self.assertEqual(header["unit"], UNIT)
        self.assertEqual(header["unit"], "300 km; 1 km; 5 km")
        self.assertNotIn("administrative_area", header)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Forecast")
        self.assertNotEqual(header["kind"], header["product"])
        self.assertNotEqual(header["kind"], "Localized Torrential Rain Forecast Map")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(
            set(header),
            {
                "publisher",
                "product",
                "period",
                "unit",
                "citation_url",
                "kind",
                "permits_financial_use",
            },
        )
        for key in (
            "value",
            "price",
            "temperature",
            "rainfall",
            "trade",
            "figure",
            "administrative_area",
        ):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "elements:sjfcstmap",
            "sjfcstmap",
            "pattern=forecast",
            "lang=en",
            "Local Information",
            "Disaster Mitigation",
            "legend_en_riskmap",
            "spatial resolution",
            "rainfall",
            "temperature",
            "yield",
            "price",
            "trade",
            "settlement",
            "completed harvest",
            "administrative",
            "position",
            "2020",
            "licence",
            "license",
            "index",
            "mm",
        ):
            self.assertNotIn(word, text, word)
        source = (ROOT / "farm_ontology" / "jma_torrential.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://www.jma.go.jp/ is not the citation.", flat)
        self.assertIn("https://www.jma.go.jp/bosai/ is not the citation.", flat)
        self.assertIn("https://www.jma.go.jp/bosai/en_kaikotan is not the citation.", flat)
        self.assertIn(
            "https://www.jma.go.jp/bosai/en_kaikotan/#elements:sjfcstmap is not the citation.",
            flat,
        )
        self.assertIn("en_kaikotan/#elements:sjfcstmap is not the citation.", flat)
        self.assertIn(
            "https://www.jma.go.jp/bosai/#lang=en&pattern=forecast is not the citation.",
            flat,
        )
        self.assertIn("The citation is the printed canonical link.", flat)
        self.assertIn("The map-view hash is omitted.", flat)
        self.assertIn(
            "The document title is Japan Meteorological Agency | Localized Torrential Rain Forecast Map.",
            flat,
        )
        self.assertIn(
            "Localized Torrential Rain Forecast Map is the product. Forecast is the kind. Forecast is not the product.",
            flat,
        )
        self.assertIn("Local Information is the menu document title, not the product.", flat)
        self.assertIn(
            "Information on Disaster Mitigation is the group heading, not a stored field.",
            flat,
        )
        self.assertIn(
            "The stored period is 08:50 JST, 17 November 2026; 20:50; 23:50; 02:50; 05:50; 08:50; next 3 h; every 10 minutes; up to 6 hours ahead; from 7 to 15 hours ahead; every hour.",
            flat,
        )
        self.assertIn("The stored unit is 300 km; 1 km; 5 km.", flat)
        self.assertIn("A kilometre scale is not a rainfall amount.", flat)
        self.assertIn("Administrative area is omitted.", flat)
        self.assertIn("The legend image was not stored.", flat)
        self.assertIn("2020 is the copyright year on the page. It is not stored.", flat)
        self.assertIn("Do not store a rainfall amount.", flat)
        self.assertIn("Do not store a temperature.", flat)
        self.assertIn("A forecast is not a completed harvest.", flat)
        self.assertIn("An index is not a quantity of goods.", flat)
        self.assertIn("The header is not marked public domain.", flat)
        self.assertIn("permits_financial_use stays false.", flat)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.jma.go.jp/",
            "https://www.jma.go.jp/bosai/",
            "https://www.jma.go.jp/bosai/en_kaikotan",
            "https://www.jma.go.jp/bosai/en_kaikotan/#elements:sjfcstmap",
            "en_kaikotan/#elements:sjfcstmap",
            "https://www.jma.go.jp/bosai/#lang=en&pattern=forecast",
            "http://www.jma.go.jp/bosai/en_kaikotan/",
            "https://www.jma.go.jp/jma/en/copyright.html",
            "https://example.com/jma.html",
        ):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "price",
            "trade",
            "completed harvest",
            "rainfall amount",
            "temperature",
            "position",
            "300 km",
            "1 km",
            "5 km",
            "08:50",
            "2026",
            "Settlement",
            "YIELD",
            "Price",
            "PRICE",
            "Trade",
            "Completed Harvest",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_filled_fields_and_figures_write_nothing(self):
        attempts = (
            {"period": PERIOD},
            {"period": "08:50 JST, 17 November 2026"},
            {"period": "next 3 h"},
            {"unit": UNIT},
            {"unit": "300 km"},
            {"unit": "mm"},
            {"administrative_area": "Japan"},
            {"administrative_area": "Hokkaido"},
            {"value": 12.5},
            {"value": "rainfall"},
            {"value": "300 km"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_jma_torrential(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("jma_torrential", text)
            self.assertNotIn("en_kaikotan", text)


if __name__ == "__main__":
    unittest.main()
