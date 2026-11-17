import json
import tempfile
import unittest
import urllib.request
from pathlib import Path

from farm_ontology import usdm_printed_class
from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.testing import online_gate

PRINTED = (
    "the introduction of moderate drought across "
    "Western New York State into far northeastern Ohio"
)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AssertionError("the refetch does not follow another page")


class UsdmPrintedClassTest(unittest.TestCase):
    def _record(self, path: Path) -> None:
        usdm_printed_class.record_usdm_printed_class(path, usdm_printed_class.USDM_URL)

    def test_stores_the_printed_class_and_area(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usdm-class.json"
            self._record(path)
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            header,
            {
                "drought_class": "moderate drought",
                "area": "Western New York State into far northeastern Ohio",
                "citation_url": "https://droughtmonitor.unl.edu/",
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(header)
        self.assertNotIn("trade", text)
        self.assertNotIn("yield", text)
        self.assertNotIn("soil", text)
        self.assertNotIn("moisture", text)
        self.assertNotIn("percent", text)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usdm-class.json"
            with self.assertRaises(ValueError):
                usdm_printed_class.record_usdm_printed_class(path, None)
            with self.assertRaises(ValueError):
                usdm_printed_class.record_usdm_printed_class(path, "   ")
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usdm-class.json"
            with self.assertRaises(ValueError):
                usdm_printed_class.record_usdm_printed_class(
                    path,
                    "https://droughtmonitor.unl.edu/CurrentMap.aspx",
                )
            self.assertFalse(path.exists())

    def test_forbidden_labels_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usdm-class.json"
            for label in ("soil moisture", "yield", "trade", "YIELD", "TRADE"):
                with self.assertRaises(ValueError):
                    usdm_printed_class.record_usdm_printed_class(
                        path,
                        usdm_printed_class.USDM_URL,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                usdm_printed_class.record_usdm_printed_class(
                    path,
                    usdm_printed_class.USDM_URL,
                    permits_financial_use=True,
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_call_the_class_moisture(self) -> None:
        source = (
            Path(usdm_printed_class.__file__).read_text(encoding="utf-8").replace("\n", " ")
        )
        self.assertIn("moderate drought", source)
        self.assertIn("Western New York State into far northeastern Ohio", source)
        self.assertIn("not soil moisture, a yield, or a trade", source)
        self.assertNotIn("field_save", source)

    @online_gate()
    def test_live_refetch_prints_the_class_and_area(self) -> None:
        request = urllib.request.Request(
            usdm_printed_class.USDM_URL,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(request, timeout=60) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.geturl(), usdm_printed_class.USDM_URL)
            page = response.read().decode("utf-8")
        self.assertIn(PRINTED, page)
        self.assertEqual(usdm_printed_class.DROUGHT_CLASS, "moderate drought")
        self.assertEqual(
            usdm_printed_class.AREA,
            "Western New York State into far northeastern Ohio",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usdm-class.json"
            self._record(path)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["drought_class"], "moderate drought")
        self.assertEqual(
            stored["area"],
            "Western New York State into far northeastern Ohio",
        )
        self.assertEqual(stored["citation_url"], usdm_printed_class.USDM_URL)
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], "closed")

    def test_reading_the_record_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "usdm-class.json"
            self._record(path)
            before = path.read_text(encoding="utf-8")
            names_before = sorted(item.name for item in folder.iterdir())
            header = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names_after = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names_after, names_before)
        self.assertEqual(names_after, ["usdm-class.json"])
        self.assertEqual(header["drought_class"], "moderate drought")
        self.assertEqual(
            header["area"],
            "Western New York State into far northeastern Ohio",
        )
        self.assertFalse(header["permits_financial_use"])
        self.assertNotIn("trade", header)
        self.assertNotIn("yield", header)
        self.assertNotIn("trade", after)
        self.assertNotIn("yield", after)
        self.assertNotIn("moisture", after)


if __name__ == "__main__":
    unittest.main()
