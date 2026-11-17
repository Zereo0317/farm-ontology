"""Live refetch of the merged SMAP header.

The citation is the one already stored on origin/main.
The refetch reads that page and checks the stored product title.
It does not store a soil-moisture value, a yield, a price, or a trade.
An index is not a quantity of goods.
permits_financial_use stays false. Class C stays closed.
"""

import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.testing import online_gate
from farm_ontology.smap_soil_moisture import (
    PRODUCT,
    SMAP_SOIL_MOISTURE_URL,
    record_series_header,
)

ROOT = Path(__file__).resolve().parents[1]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AssertionError("the refetch does not follow another page")


class SmapSoilMoistureRefetchTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    @online_gate()
    def test_live_refetch_still_prints_the_stored_product_title(self):
        saved = record_series_header(self.folder, citation_url=SMAP_SOIL_MOISTURE_URL)
        header = saved["header"]
        self.assertEqual(header["product"], "SMAP | Soil Moisture Active Passive")
        self.assertEqual(header["product"], PRODUCT)
        self.assertEqual(header["citation_url"], "https://smap.jpl.nasa.gov/")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(CLASS_C_POLICY, "closed")
        before = (self.folder / saved["file"]).read_text(encoding="utf-8")
        request = urllib.request.Request(
            SMAP_SOIL_MOISTURE_URL,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(request, timeout=45) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.geturl(), SMAP_SOIL_MOISTURE_URL)
            body = response.read()
        self.assertIn(PRODUCT.encode("utf-8"), body)
        after = (self.folder / saved["file"]).read_text(encoding="utf-8")
        self.assertEqual(after, before)
        stored = __import__("json").loads(after)
        self.assertFalse(stored["permits_financial_use"])
        for key in ("value", "soil_moisture", "yield", "price", "trade"):
            self.assertNotIn(key, stored)
        source = (ROOT / "farm_ontology" / "smap_soil_moisture.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("Do not store a soil-moisture value.", flat)
        self.assertIn("An index is not a quantity of goods.", Path(__file__).read_text(encoding="utf-8"))
        self.assertEqual(len(list(self.folder.iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
