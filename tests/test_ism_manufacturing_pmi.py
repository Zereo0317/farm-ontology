import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.ism_manufacturing_pmi import (
    ISM_MANUFACTURING_PMI_URL,
    record_series_header,
)

ROOT = Path(__file__).resolve().parents[1]
URL = ISM_MANUFACTURING_PMI_URL


class IsmManufacturingPmiTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_an_index_value(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Institute for Supply Management")
        self.assertEqual(header["product"], "Manufacturing PMI")
        self.assertEqual(
            header["period"],
            "monthly; a February 2014 announcement said a paid historical "
            "subscription would include Report on Business information dating as far "
            "back as 1948 and stated an expected annual price of $2,500; that price "
            "was not re-checked; a January 2022 seasonal-factor release still points "
            "readers to a historical-data subscription; the 1948 span is not an open "
            "file",
        )
        self.assertEqual(
            header["unit"],
            "monthly diffusion index from a survey of U.S. purchasing and supply "
            "executives; the September 2025 branding note says the "
            "expansion/contraction baseline of 50.0 is unchanged and that "
            "seasonal-adjustment practice is unchanged; no index value is stored; a "
            "diffusion index is not a quantity of manufactured goods",
        )
        self.assertEqual(
            header["administrative_area"],
            "the United States survey of purchasing and supply executives; not a "
            "stored quantity of goods",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "survey")
        self.assertFalse(header["permits_financial_use"])
        self.assertIn("forbids copying", header["release_license_2022"])
        self.assertIn("ismworld.org/ism-pmi", header["branding_access_2025"])
        self.assertNotEqual(
            header["release_license_2022"],
            header["branding_access_2025"],
        )
        self.assertNotIn("public access", header["release_license_2022"])
        self.assertNotIn("forbids copying", header["branding_access_2025"])
        self.assertEqual(header["terms_of_use"], TERMS_SENTENCE)
        self.assertNotEqual(header["terms_of_use"], header["release_license_2022"])
        self.assertNotEqual(header["terms_of_use"], header["branding_access_2025"])
        self.assertNotIn("permission", header)
        self.assertIn("not an open file", header["period"])
        self.assertIn("not a quantity of manufactured goods", header["unit"])
        for key in (
            "value",
            "price",
            "index_level",
            "index_value",
            "quantity",
            "forecast",
            "observation",
            "settlement",
            "trade",
        ):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "yield",
            "trade",
            "forecast",
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "trading right",
            "redistributable",
        ):
            self.assertNotIn(word, text)
        self.assertNotIn("245203881.html", text)
        self.assertNotIn("301464999.html", text)
        self.assertNotIn("branding-ism-pmi-reports", text)
        source = (ROOT / "farm_ontology" / "ism_manufacturing_pmi.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "https://www.ismworld.org/supply-management-news-and-reports/news-publications/releases/2025/institute-for-supply-management-updates-monthly-economic-indicators-branding-ism-pmi-reports/",
            source,
        )
        self.assertIn(
            "https://www.prnewswire.com/news-releases/institute-for-supply-management-to-offer-subscription-access-to-historical-and-recent-ism-manufacturing-and-non-manufacturing-report-on-business-starting-march-1-245203881.html",
            source,
        )
        self.assertIn(
            "https://www.prnewswire.com/news-releases/ism-makes-annual-adjustments-to-seasonal-factors-for-manufacturing-pmi-services-pmi-and-diffusion-indexes-301464999.html",
            source,
        )
        self.assertEqual(len(list(self.folder.iterdir())), 1)


TERMS_SENTENCE = (
    "The general terms PDF says ISM products and data may be used for "
    "personal, non-commercial use only, and reproduction needs express "
    "written permission."
)


class IsmManufacturingPmiRejectionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.ismworld.org/supply-management-news-and-reports/news-publications/releases/2025/institute-for-supply-management-updates-monthly-economic-indicators-branding-ism-pmi-reports/",
            "https://www.prnewswire.com/news-releases/institute-for-supply-management-to-offer-subscription-access-to-historical-and-recent-ism-manufacturing-and-non-manufacturing-report-on-business-starting-march-1-245203881.html",
            "https://www.prnewswire.com/news-releases/ism-makes-annual-adjustments-to-seasonal-factors-for-manufacturing-pmi-services-pmi-and-diffusion-indexes-301464999.html",
            "https://example.com/ism.xlsx",
        ):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "forecast",
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "1948",
            "1948 history",
            "redistributable history",
            "1948 redistributable",
            "Settlement",
            "YIELD",
            "Trade",
            "Forecast",
            "Observation",
            "Completed Harvest",
            "Public Domain",
            "Benchmark",
            "1948 Redistributable",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_pmi(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("ism_manufacturing_pmi", text)
            self.assertNotIn("738-terms-and-conditions", text)
