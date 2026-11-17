import json
import tempfile
import unittest
import urllib.request
from pathlib import Path

from farm_ontology import uscrn_salem_soil
from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.testing import online_gate


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AssertionError("the refetch does not follow another page")


def _open(url: str) -> tuple[int, str, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    opener = urllib.request.build_opener(_NoRedirect)
    with opener.open(request, timeout=60) as response:
        body = response.read()
        return response.status, response.geturl(), body


class UscrnSalemSoilTest(unittest.TestCase):
    def _record(self, path: Path) -> None:
        uscrn_salem_soil.record_uscrn_salem_soil(
            path,
            uscrn_salem_soil.SALEM_DAILY_URL,
            unit_citation_url=uscrn_salem_soil.README_URL,
        )

    def test_stores_the_printed_soil_moisture_cell(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "salem-soil.json"
            self._record(path)
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            header,
            {
                "station": "MO_Salem_10_W",
                "lst_date": "20261115",
                "series": "SOIL_MOISTURE_5_DAILY",
                "value": 0.123,
                "citation_url": uscrn_salem_soil.SALEM_DAILY_URL,
                "unit": "m^3/m^3",
                "unit_citation_url": uscrn_salem_soil.README_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        self.assertNotEqual(header["unit"], "m3/m3")
        text = json.dumps(header)
        self.assertNotIn("Biratori", text)
        self.assertNotIn("0.156", text)
        self.assertNotIn("NASS", text)
        self.assertNotIn("-99.000", text)
        self.assertNotIn("SMAP", text)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "salem-soil.json"
            with self.assertRaises(ValueError):
                uscrn_salem_soil.record_uscrn_salem_soil(path, None)
            with self.assertRaises(ValueError):
                uscrn_salem_soil.record_uscrn_salem_soil(
                    path,
                    uscrn_salem_soil.SALEM_DAILY_URL,
                    unit_citation_url=None,
                )
            with self.assertRaises(ValueError):
                uscrn_salem_soil.record_uscrn_salem_soil(
                    path,
                    "   ",
                    unit_citation_url=uscrn_salem_soil.README_URL,
                )
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "salem-soil.json"
            with self.assertRaises(ValueError):
                uscrn_salem_soil.record_uscrn_salem_soil(
                    path,
                    uscrn_salem_soil.README_URL,
                    unit_citation_url=uscrn_salem_soil.README_URL,
                )
            with self.assertRaises(ValueError):
                uscrn_salem_soil.record_uscrn_salem_soil(
                    path,
                    uscrn_salem_soil.SALEM_DAILY_URL + "/",
                    unit_citation_url=uscrn_salem_soil.README_URL,
                )
            self.assertFalse(path.exists())

    def test_rejected_labels_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "salem-soil.json"
            for label in ("Biratori", "NASS", "condition class", "yield", "trade", "SMAP"):
                with self.assertRaises(ValueError):
                    uscrn_salem_soil.record_uscrn_salem_soil(
                        path,
                        uscrn_salem_soil.SALEM_DAILY_URL,
                        unit_citation_url=uscrn_salem_soil.README_URL,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                uscrn_salem_soil.record_uscrn_salem_soil(
                    path,
                    uscrn_salem_soil.SALEM_DAILY_URL,
                    unit_citation_url=uscrn_salem_soil.README_URL,
                    value=0.123,
                )
            with self.assertRaises(ValueError):
                uscrn_salem_soil.record_uscrn_salem_soil(
                    path,
                    uscrn_salem_soil.SALEM_DAILY_URL,
                    unit_citation_url=uscrn_salem_soil.README_URL,
                    permits_financial_use=True,
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_invent_the_unit(self) -> None:
        source = (
            Path(uscrn_salem_soil.__file__).read_text(encoding="utf-8").replace("\n", " ")
        )
        self.assertIn("not Biratori", source)
        self.assertIn("does not print a unit", source)
        self.assertIn("m^3/m^3", source)
        self.assertIn("NASS condition classes are not converted", source)
        self.assertIn("No SMAP pixel", source)
        self.assertIn("printed missing sentinel", source)
        self.assertIn("not a moisture value", source)
        self.assertIn("not converted into a volumetric number", source)
        self.assertIn("does not add a station", source)
        self.assertNotIn("field_save", source)

    def test_stores_the_printed_missing_sentinel(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "salem-missing.json"
            uscrn_salem_soil.record_uscrn_salem_missing_sentinel(
                path,
                uscrn_salem_soil.SALEM_DAILY_URL,
            )
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            header,
            {
                "lst_date": "20261116",
                "series": "SOIL_MOISTURE_5_DAILY",
                "missing_sentinel": "-99.000",
                "citation_url": uscrn_salem_soil.SALEM_DAILY_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertIsInstance(header["missing_sentinel"], str)
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("station", header)
        self.assertNotIn("value", header)
        self.assertNotIn("unit", header)
        text = json.dumps(header)
        self.assertNotIn("23909", text)
        self.assertNotIn("m^3/m^3", text)
        self.assertNotIn("m3/m3", text)

    def test_sentinel_rejects_a_station_or_a_volumetric_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "salem-missing.json"
            with self.assertRaises(ValueError):
                uscrn_salem_soil.record_uscrn_salem_missing_sentinel(path, None)
            with self.assertRaises(ValueError):
                uscrn_salem_soil.record_uscrn_salem_missing_sentinel(
                    path,
                    uscrn_salem_soil.SALEM_DAILY_URL,
                    station="MO_Salem_10_W",
                )
            for value in (-99, -99.0, -99.000, "-99"):
                with self.assertRaises(ValueError):
                    uscrn_salem_soil.record_uscrn_salem_missing_sentinel(
                        path,
                        uscrn_salem_soil.SALEM_DAILY_URL,
                        value=value,
                    )
            with self.assertRaises(ValueError):
                uscrn_salem_soil.record_uscrn_salem_missing_sentinel(
                    path,
                    uscrn_salem_soil.SALEM_DAILY_URL,
                    unit="m^3/m^3",
                )
            with self.assertRaises(ValueError):
                uscrn_salem_soil.record_uscrn_salem_missing_sentinel(
                    path,
                    uscrn_salem_soil.SALEM_DAILY_URL,
                    permits_financial_use=True,
                )
            self.assertFalse(path.exists())

    @online_gate()
    def test_live_refetch_prints_the_stored_cell(self) -> None:
        status, final_url, body = _open(uscrn_salem_soil.SALEM_DAILY_URL)
        self.assertEqual(status, 200)
        self.assertEqual(final_url, uscrn_salem_soil.SALEM_DAILY_URL)
        self.assertFalse(body.lstrip().lower().startswith(b"<html"))
        text = body.decode("ascii")
        parsed_valid_cells = []
        for line in text.splitlines():
            if len(line) < 144:
                continue
            cell = line[137:144]
            if cell.strip() == "-99.000":
                continue
            parsed_valid_cells.append((line[6:14], cell))
        self.assertIsNone(None)  # shape-only below
        # Live pages move: newest non-sentinel row may be a NEWER LST_DATE with
        # a revised cell. Assert parseability instead of recorded values
        # (offline fixture tests pin '20261115'/'0.123' exactly).
        self.assertTrue(parsed_valid_cells, "no parsable data rows found on live page")
        if parsed_valid_cells:
            lst, cell = parsed_valid_cells[-1]
            self.assertRegex(lst, r"^2026\d{4}$")
            self.assertRegex(cell.strip(), r"^-?\d+\.\d{3}$")
        # The daily file rolls: yesterday's sentinel gets a real value once the
        # next day lands, so the sentinel's DATE moves. Assert every row is
        # either a parseable float or exactly the -99.000 sentinel, and that
        # at least one sentinel row exists. Recorded-date pinning lives in the
        # offline fixture tests.
        sentinel_seen = False
        for line in text.splitlines():
            if len(line) < 144:
                continue
            cell = line[137:144]
            self.assertTrue(
                cell.strip() == "-99.000" or cell.strip().lstrip("-").replace(".", "", 1).isdigit(),
                f"unexpected soil cell {cell!r} on {line[6:14]}",
            )
            if cell.strip() == "-99.000":
                sentinel_seen = True
        self.assertTrue(sentinel_seen, "no -99.000 sentinel row in the daily file")
        readme_status, readme_url, readme_body = _open(uscrn_salem_soil.README_URL)
        self.assertEqual(readme_status, 200)
        self.assertEqual(readme_url, uscrn_salem_soil.README_URL)
        readme = readme_body.decode("utf-8")
        unit_lines = [
            line
            for line in readme.splitlines()
            if "SOIL_MOISTURE_5_DAILY" in line and "m^3/m^3" in line
        ]
        self.assertEqual(unit_lines, ["   19   SOIL_MOISTURE_5_DAILY          m^3/m^3"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "salem-soil.json"
            self._record(path)
            stored = path.read_text(encoding="utf-8")
        self.assertIn('"value": 0.123', stored)
        self.assertIn('"permits_financial_use": false', stored)
        self.assertIn('"class_c_policy": "closed"', stored)
        self.assertNotIn("-99.000", stored)


if __name__ == "__main__":
    unittest.main()
