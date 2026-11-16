import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.jma_daily import JMA_DAILY_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = JMA_DAILY_URL
PERIOD = (
    "Daily weather forecasts for the week ahead in map form; "
    "Issued at 22 JST, 16 Nov. 2026"
)


class JmaDailyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Japan Meteorological Agency")
        self.assertEqual(header["product"], "Daily Forecasts")
        self.assertEqual(header["period"], PERIOD)
        self.assertIn(
            "Daily weather forecasts for the week ahead in map form",
            header["period"],
        )
        self.assertIn("Issued at 22 JST, 16 Nov. 2026", header["period"])
        self.assertNotIn("unit", header)
        self.assertEqual(header["administrative_area"], "Japan (list)")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Daily Forecasts")
        self.assertEqual(header["kind"], header["product"])
        self.assertNotEqual(header["kind"], "forecast")
        self.assertNotEqual(header["kind"], "Local Information")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(
            set(header),
            {
                "publisher",
                "product",
                "period",
                "administrative_area",
                "citation_url",
                "kind",
                "permits_financial_use",
            },
        )
        for key in ("value", "price", "temperature", "rainfall", "trade", "figure", "unit"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "気象庁",
            "統合地図",
            "5:00",
            "11:00",
            "17:00",
            "as necessary",
            "16(Mon)",
            "17(Tue)",
            "18(Wed)",
            "19(Thu)",
            "20(Fri)",
            "21(Sat)",
            "22(Sun)",
            "23(Mon)",
            "16 Nov., Weather",
            "Tokyo",
            "Ogasawara",
            "Niigata",
            "Osaka",
            "Fukuoka",
            "Kagoshima",
            "Naha",
            "Ishigakijima",
            "Asahikawa",
            "Sapporo",
            "Sendai",
            "Three-hourly",
            "Two-week",
            "Seasonal",
            "Local Information",
            "Nationwide",
            "settlement",
            "yield",
            "price",
            "trade",
            "completed harvest",
            "rainfall",
            "temperature",
            "pattern=forecast",
            "copyright.html",
            "indexe",
            "kokusai",
            "the field was not opened",
            "unit",
            "licence",
            "license",
        ):
            self.assertNotIn(word, text, word)
        source = (ROOT / "farm_ontology" / "jma_daily.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://www.jma.go.jp/ is not the citation.", flat)
        self.assertIn("https://www.jma.go.jp/jma/indexe.html is not the citation.", flat)
        self.assertIn("https://www.jma.go.jp/jma/kokusai/multi.html is not the citation.", flat)
        self.assertIn(
            "https://www.jma.go.jp/bosai/#lang=en&pattern=forecast is not the citation.",
            flat,
        )
        self.assertIn("https://www.jma.go.jp/bosai/map.html is not the citation.", flat)
        self.assertIn("https://www.jma.go.jp/jma/en/copyright.html was not opened.", flat)
        self.assertIn("The page did not print a separate canonical URL.", flat)
        self.assertIn("The response title is 気象庁｜統合地図ページ.", flat)
        self.assertIn(
            "The document title is Japan Meteorological Agency｜Daily Forecasts.",
            flat,
        )
        self.assertIn("Daily Forecasts is the document-title segment.", flat)
        self.assertIn("気象庁 is a printed name, not a second publisher.", flat)
        self.assertIn(
            "The stored period is Daily weather forecasts for the week ahead in map form; Issued at 22 JST, 16 Nov. 2026.",
            flat,
        )
        self.assertIn(
            "That update schedule is not the period and is not a separate series.",
            flat,
        )
        self.assertIn("16 Nov., Weather is not the period.", flat)
        self.assertIn(
            "16(Mon), 17(Tue), 18(Wed), 19(Thu), 20(Fri), 21(Sat), 22(Sun), and 23(Mon) are slider labels. They are not the period.",
            flat,
        )
        self.assertIn("Unit is omitted.", flat)
        self.assertIn("The stored administrative area is Japan (list).", flat)
        self.assertIn(
            "Tokyo, Ogasawara Islands, Niigata, Osaka, Fukuoka, Kagoshima, Naha, Ishigakijima Island, Asahikawa, Sapporo, and Sendai are map panel titles. They are not the administrative area.",
            flat,
        )
        self.assertIn("Do not store a rainfall amount.", flat)
        self.assertIn("Do not store a temperature.", flat)
        self.assertIn("A forecast is not a completed harvest.", flat)
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
            "https://www.jma.go.jp/jma/indexe.html",
            "https://www.jma.go.jp/jma/kokusai/multi.html",
            "https://www.jma.go.jp/bosai/#lang=en&pattern=forecast",
            "https://www.jma.go.jp/bosai/map.html",
            "https://www.jma.go.jp/bosai/map.html#contents=forecast",
            "https://www.jma.go.jp/bosai/map.html#contents=forecast&lang=en/",
            "http://www.jma.go.jp/bosai/map.html#contents=forecast&lang=en",
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
            "16(Mon)",
            "22",
            "5:00",
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
            {"period": "Daily weather forecasts for the week ahead in map form"},
            {"period": "Issued at 22 JST, 16 Nov. 2026"},
            {
                "period": (
                    "Daily forecasts are updated at 5:00, 11:00 and 17:00 JST "
                    "every day and at other times as necessary."
                )
            },
            {"period": "16(Mon)"},
            {"period": "16 Nov., Weather"},
            {"period": "the field was not opened"},
            {"unit": "the field was not opened"},
            {"unit": "temperature"},
            {"unit": "rainfall"},
            {"administrative_area": "Japan (list)"},
            {"administrative_area": "Tokyo"},
            {"administrative_area": "Ogasawara Islands"},
            {"administrative_area": "Sendai"},
            {"value": 12.5},
            {"value": "rainfall"},
            {"value": "temperature"},
            {"value": "22"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_jma_daily(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("jma_daily", text)
            self.assertNotIn("bosai/map.html#contents=forecast", text)


if __name__ == "__main__":
    unittest.main()
