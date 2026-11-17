"""Live refetch of the merged JMA two-week header.

The citation is the one already stored on origin/main.
The refetch reads that page and checks the stored product title.
It does not store a new rainfall amount, a temperature, a yield, a
price, or a trade. A forecast is not a completed harvest.
permits_financial_use stays false. Class C stays closed.
"""

import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.jma_two_week import JMA_TWO_WEEK_URL, PRODUCT, record_series_header
from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.testing import online_gate

ROOT = Path(__file__).resolve().parents[1]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AssertionError("the refetch does not follow another page")


class JmaTwoWeekRefetchTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    @online_gate()
    def test_live_refetch_still_prints_the_stored_product_title(self):
        saved = record_series_header(self.folder, citation_url=JMA_TWO_WEEK_URL)
        header = saved["header"]
        self.assertEqual(header["product"], "Two-week Temperature Forecast")
        self.assertEqual(header["product"], PRODUCT)
        self.assertEqual(header["citation_url"], "https://www.data.jma.go.jp/cpd/twoweek/en/")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(CLASS_C_POLICY, "closed")
        before = (self.folder / saved["file"]).read_text(encoding="utf-8")
        request = urllib.request.Request(
            JMA_TWO_WEEK_URL,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(request, timeout=45) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.geturl(), JMA_TWO_WEEK_URL)
            body = response.read()
        self.assertIn(PRODUCT.encode("utf-8"), body)
        after = (self.folder / saved["file"]).read_text(encoding="utf-8")
        self.assertEqual(after, before)
        stored = __import__("json").loads(after)
        self.assertFalse(stored["permits_financial_use"])
        for key in ("value", "rainfall", "temperature", "yield", "price", "trade"):
            self.assertNotIn(key, stored)
        source = (ROOT / "farm_ontology" / "jma_two_week.py").read_text(encoding="utf-8")
        self.assertIn("A forecast is not a completed harvest.", source.replace("\n", " "))
        self.assertEqual(len(list(self.folder.iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
