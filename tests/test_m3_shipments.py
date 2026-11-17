import json
import re
import tempfile
import unittest
import urllib.request
from pathlib import Path

from farm_ontology import m3_shipments
from farm_ontology.policy import CLASS_C_POLICY


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AssertionError("the refetch does not follow another page")


def _shipments_level(page: str) -> str:
    match = re.search(
        r"Shipments, up eleven of the last twelve months, "
        r"increased \$8\.8 billion or 1\.3 percent to (\$668\.5 billion)\.",
        page,
    )
    return match.group(1)


class M3ShipmentsTest(unittest.TestCase):
    def _record(self, path: Path) -> None:
        m3_shipments.record_m3_shipments(path, m3_shipments.M3_URL)

    def test_stores_the_printed_shipments_figure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "m3-shipments.json"
            self._record(path)
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            header,
            {
                "series": "Shipments",
                "month": "September",
                "value": "$668.5 billion",
                "citation_url": m3_shipments.M3_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(header)
        self.assertNotIn("price", text)
        self.assertNotIn("trade", text)
        self.assertNotIn("8.8", text)
        self.assertNotIn("1.3", text)
        self.assertNotIn("677.2", text)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "m3-shipments.json"
            with self.assertRaises(ValueError):
                m3_shipments.record_m3_shipments(path, None)
            with self.assertRaises(ValueError):
                m3_shipments.record_m3_shipments(path, "   ")
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "m3-shipments.json"
            with self.assertRaises(ValueError):
                m3_shipments.record_m3_shipments(
                    path,
                    "https://www.census.gov/manufacturing/m3/index.html",
                )
            self.assertFalse(path.exists())

    def test_price_or_trade_label_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "m3-shipments.json"
            for label in ("price", "trade", "Price", "TRADE"):
                with self.assertRaises(ValueError):
                    m3_shipments.record_m3_shipments(
                        path,
                        m3_shipments.M3_URL,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                m3_shipments.record_m3_shipments(
                    path,
                    m3_shipments.M3_URL,
                    value="$8.8 billion",
                )
            with self.assertRaises(ValueError):
                m3_shipments.record_m3_shipments(
                    path,
                    m3_shipments.M3_URL,
                    permits_financial_use=True,
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_call_the_figure_a_price(self) -> None:
        source = (
            Path(m3_shipments.__file__).read_text(encoding="utf-8").replace("\n", " ")
        )
        self.assertIn("Shipments", source)
        self.assertIn("$668.5 billion", source)
        self.assertIn("September", source)
        self.assertIn("not the figure", source)
        self.assertIn("not a price and not a trade", source)
        self.assertNotIn("field_save", source)

    def test_live_refetch_prints_the_september_shipments(self) -> None:
        request = urllib.request.Request(
            m3_shipments.M3_URL,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(request, timeout=60) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.geturl(), m3_shipments.M3_URL)
            page = response.read().decode("utf-8")
        self.assertIn("manufactured goods in September", page)
        self.assertEqual(_shipments_level(page), "$668.5 billion")
        self.assertEqual(m3_shipments.SERIES, "Shipments")
        self.assertEqual(m3_shipments.MONTH, "September")
        self.assertEqual(m3_shipments.VALUE, "$668.5 billion")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "m3-shipments.json"
            self._record(path)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["series"], "Shipments")
        self.assertEqual(stored["month"], "September")
        self.assertEqual(stored["value"], "$668.5 billion")
        self.assertNotEqual(stored["value"], "$8.8 billion")
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], "closed")
        self.assertNotIn("price", stored)
        self.assertNotIn("trade", stored)


if __name__ == "__main__":
    unittest.main()
