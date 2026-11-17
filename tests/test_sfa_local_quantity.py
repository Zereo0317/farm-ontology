import json
import tempfile
import unittest
import urllib.request
from pathlib import Path

from farm_ontology import sfa_local_quantity
from farm_ontology.policy import CLASS_C_POLICY


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AssertionError("the refetch does not follow another page")


class SfaLocalQuantityTest(unittest.TestCase):
    def _record(self, path: Path) -> None:
        sfa_local_quantity.record_sfa_local_quantity(path, sfa_local_quantity.SFA_URL)

    def test_stores_the_printed_2025_vegetable_quantity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sfa-local.json"
            self._record(path)
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            header,
            {
                "series": "Vegetables",
                "period": "2025",
                "value": "16.6",
                "unit": "thousand tonnes",
                "citation_url": sfa_local_quantity.SFA_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(header)
        self.assertNotIn("trade", text)
        self.assertNotIn("yield", text)
        self.assertNotIn("soybean", text)
        self.assertNotIn("import", text)
        self.assertNotIn("farm", text)
        self.assertNotIn("253.3", text)
        self.assertNotIn("582,200", text)

    def test_missing_or_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "sfa-local.json"
            for citation in (
                None,
                "   ",
                "https://www.sfa.gov.sg/docs/default-source/publication/"
                "sg-food-statistics/sgfs-2025-publication_060526-fa.pdf",
            ):
                with self.assertRaises(ValueError):
                    sfa_local_quantity.record_sfa_local_quantity(path, citation)
            self.assertEqual(list(folder.iterdir()), [])

    def test_forbidden_labels_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sfa-local.json"
            for label in ("soybean crop", "yield", "trade", "import share", "farm"):
                with self.assertRaises(ValueError):
                    sfa_local_quantity.record_sfa_local_quantity(
                        path,
                        sfa_local_quantity.SFA_URL,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                sfa_local_quantity.record_sfa_local_quantity(
                    path,
                    sfa_local_quantity.SFA_URL,
                    value="253.3",
                    permits_financial_use=True,
                )
            self.assertFalse(path.exists())

    def test_source_keeps_the_yield_out_of_the_quantity(self) -> None:
        source = (
            Path(sfa_local_quantity.__file__).read_text(encoding="utf-8").replace("\n", " ")
        )
        self.assertIn("16.6", source)
        self.assertIn("Vegetables", source)
        self.assertIn("253.3", source)
        self.assertIn("not stored", source)
        self.assertIn("Singapore is not a farm", source)
        self.assertIn("It is not a trade", source)
        self.assertNotIn("field_save", source)

    def test_live_refetch_is_the_redirect_target_pdf(self) -> None:
        request = urllib.request.Request(
            sfa_local_quantity.SFA_URL,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(request, timeout=90) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.geturl(), sfa_local_quantity.SFA_URL)
            body = response.read()
        self.assertTrue(body.startswith(b"%PDF"))
        self.assertIn(b"16.6", body)
        self.assertIn(b"2025", body)
        self.assertEqual(sfa_local_quantity.SERIES, "Vegetables")
        self.assertEqual(sfa_local_quantity.PERIOD, "2025")
        self.assertEqual(sfa_local_quantity.VALUE, "16.6")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sfa-local.json"
            self._record(path)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["value"], "16.6")
        self.assertNotEqual(stored["value"], "253.3")
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], "closed")

    def test_reading_the_record_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "sfa-local.json"
            self._record(path)
            before = path.read_text(encoding="utf-8")
            names_before = sorted(item.name for item in folder.iterdir())
            header = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names_after = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names_after, names_before)
        self.assertEqual(names_after, ["sfa-local.json"])
        self.assertEqual(header["series"], "Vegetables")
        self.assertEqual(header["period"], "2025")
        self.assertEqual(header["value"], "16.6")
        self.assertEqual(header["unit"], "thousand tonnes")
        self.assertFalse(header["permits_financial_use"])
        self.assertNotIn("trade", header)
        self.assertNotIn("yield", header)
        self.assertNotIn("farm", header)
        self.assertNotIn("trade", after)
        self.assertNotIn("yield", after)


if __name__ == "__main__":
    unittest.main()
