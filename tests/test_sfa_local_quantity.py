import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from farm_ontology import sfa_local_quantity
from farm_ontology.policy import CLASS_C_POLICY


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class SfaLocalQuantityTest(unittest.TestCase):
    def test_exact_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "sfa-local.json"
            with self.assertRaises(ValueError):
                sfa_local_quantity.record_sfa_local_quantity(
                    path,
                    sfa_local_quantity.SFA_URL,
                )
            self.assertEqual(list(folder.iterdir()), [])

    def test_labels_and_overrides_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "sfa-local.json"
            for label in ("soybean crop", "yield", "trade", "import share"):
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
                    value="1",
                    permits_financial_use=True,
                )
            self.assertEqual(list(folder.iterdir()), [])

    def test_source_does_not_invent_a_quantity(self) -> None:
        source = (
            Path(sfa_local_quantity.__file__).read_text(encoding="utf-8").replace("\n", " ")
        )
        self.assertIn("printed no local quantity", source)
        self.assertIn("Singapore is not a farm", source)
        self.assertIn("It is not a trade", source)
        self.assertIn("not opened", source)
        self.assertNotIn("field_save", source)
        self.assertNotIn("tonnes", source)

    def test_live_refetch_is_not_a_pdf(self) -> None:
        request = urllib.request.Request(
            sfa_local_quantity.SFA_URL,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        opener = urllib.request.build_opener(_NoRedirect)
        with self.assertRaises(urllib.error.HTTPError) as caught:
            opener.open(request, timeout=60)
        response = caught.exception
        body = response.read()
        self.assertEqual(response.code, 301)
        self.assertEqual(response.geturl(), sfa_local_quantity.SFA_URL)
        self.assertFalse(body.startswith(b"%PDF"))
        self.assertNotIn(b"vegetable", body.lower())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sfa-local.json"
            with self.assertRaises(ValueError):
                sfa_local_quantity.record_sfa_local_quantity(
                    path,
                    sfa_local_quantity.SFA_URL,
                )
            self.assertFalse(path.exists())

    def test_reading_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "sfa-local.json"
            names_before = sorted(item.name for item in folder.iterdir())
            with self.assertRaises(ValueError):
                sfa_local_quantity.record_sfa_local_quantity(
                    path,
                    sfa_local_quantity.SFA_URL,
                    permits_financial_use=False,
                )
            self.assertFalse(path.exists())
            names_after = sorted(item.name for item in folder.iterdir())
        self.assertEqual(names_after, names_before)
        self.assertEqual(names_after, [])
        self.assertEqual(CLASS_C_POLICY, "closed")
        self.assertNotIn("trade", names_after)


if __name__ == "__main__":
    unittest.main()
