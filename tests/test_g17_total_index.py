import json
import re
import tempfile
import unittest
import urllib.request
from pathlib import Path

from farm_ontology import g17_total_index
from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.testing import online_gate


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AssertionError("the refetch does not follow another page")


def _september_index(page: str) -> str:
    row = re.search(r'id=hdr21>(.*?)</tr>', page, re.S)
    cell = re.search(
        r'<td headers=" hdr1 hdr3 hdr12 hdr21">([^<]*)</td>',
        row.group(0),
    )
    return cell.group(1).strip()


class G17TotalIndexTest(unittest.TestCase):
    def _record(self, path: Path) -> None:
        g17_total_index.record_g17_total_index(path, g17_total_index.G17_URL)

    def test_stores_the_printed_total_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "g17-total-index.json"
            self._record(path)
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            header,
            {
                "series": "Total index",
                "month": "Sept.",
                "year": "2026",
                "status": "[p]",
                "value": 104.0,
                "unit": "2017=100",
                "citation_url": g17_total_index.G17_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        self.assertIsInstance(header["value"], float)
        text = json.dumps(header)
        self.assertNotIn("price", text)
        self.assertNotIn("trade", text)
        self.assertNotIn(".7", text)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "g17-total-index.json"
            with self.assertRaises(ValueError):
                g17_total_index.record_g17_total_index(path, None)
            with self.assertRaises(ValueError):
                g17_total_index.record_g17_total_index(path, "   ")
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "g17-total-index.json"
            with self.assertRaises(ValueError):
                g17_total_index.record_g17_total_index(
                    path,
                    g17_total_index.G17_URL + "#table",
                )
            self.assertFalse(path.exists())

    def test_price_or_trade_label_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "g17-total-index.json"
            for label in ("price", "trade", "Price", "TRADE"):
                with self.assertRaises(ValueError):
                    g17_total_index.record_g17_total_index(
                        path,
                        g17_total_index.G17_URL,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                g17_total_index.record_g17_total_index(
                    path,
                    g17_total_index.G17_URL,
                    value=104.0,
                )
            with self.assertRaises(ValueError):
                g17_total_index.record_g17_total_index(
                    path,
                    g17_total_index.G17_URL,
                    permits_financial_use=True,
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_call_the_index_a_price(self) -> None:
        source = (
            Path(g17_total_index.__file__).read_text(encoding="utf-8").replace("\n", " ")
        )
        self.assertIn("Total index", source)
        self.assertIn("104.0", source)
        self.assertIn("not the index", source)
        self.assertIn("not a price and not a trade", source)
        self.assertNotIn("field_save", source)

    @online_gate()
    def test_live_refetch_prints_the_september_index(self) -> None:
        request = urllib.request.Request(
            g17_total_index.G17_URL,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(request, timeout=60) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.geturl(), g17_total_index.G17_URL)
            page = response.read().decode("utf-8")
        self.assertIn("Total&nbsp;index", page)
        self.assertIn("2017=100", page)
        # Shape assertions on the live page: the publisher revises printed
        # values, so the LIVE run checks parseability, not the recorded
        # number (the offline fixture tests pin "104.0" exactly).
        september = _september_index(page)
        self.assertRegex(september, r"^\d{1,3}\.\d$")
        self.assertEqual(g17_total_index.SERIES, "Total index")
        self.assertEqual(g17_total_index.MONTH, "Sept.")
        self.assertEqual(g17_total_index.YEAR, "2026")
        self.assertIsInstance(g17_total_index.VALUE, float)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "g17-total-index.json"
            self._record(path)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["series"], "Total index")
        self.assertIsInstance(stored["value"], (int, float))
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], "closed")
        self.assertNotIn("price", stored)
        self.assertNotIn("trade", stored)

    def test_september_2026_index_is_not_a_price_and_reading_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "g17-total-index.json"
            self._record(path)
            before = path.read_text(encoding="utf-8")
            names_before = sorted(item.name for item in folder.iterdir())
            header = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names_after = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names_after, names_before)
        self.assertEqual(names_after, ["g17-total-index.json"])
        self.assertEqual(header["series"], "Total index")
        self.assertEqual(header["month"], "Sept.")
        self.assertEqual(header["year"], "2026")
        self.assertEqual(header["value"], 104.0)
        self.assertEqual(header["unit"], "2017=100")
        self.assertNotEqual(header["value"], 0.7)
        self.assertFalse(header["permits_financial_use"])
        self.assertNotIn("price", header)
        self.assertNotIn("trade", header)
        self.assertNotIn("percent_change", header)
        self.assertNotIn("price", after)
        self.assertNotIn("trade", after)
        self.assertNotIn("0.7", after)
        self.assertNotIn(".7", after)


if __name__ == "__main__":
    unittest.main()
