import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import noaa_oni_current
from farm_ontology.noaa_oni import NOAA_ONI_URL
from farm_ontology.policy import CLASS_C_POLICY

STATEMENT = (
    "Because of the high frequency filter applied to the ERSSTv5 data "
    "(Huang et al. 2017, J.Climate), ONI values may change up to two months "
    'after the initial "real time" value is posted. Therefore, the most recent '
    "ONI values should be considered an estimate."
)

LIVE_BODY = f"""
<h2>Oceanic Niño Index (ONI): Historical El Niño / La Niña episodes (1950–Present)</h2>
<p>threshold of +/- 0.5<sup>o</sup>C for the Oceanic Niño Index (ONI)</p>
<p>{STATEMENT}</p>
<table>
<tr><td>Year</td><td>DJF</td><td>JFM</td><td>FMA</td><td>MAM</td><td>AMJ</td><td>MJJ</td></tr>
<tr><td>2025</td><td>-0.4</td><td>-0.2</td><td>-0.1</td><td>0.0</td><td>0.0</td><td>-0.5</td></tr>
<tr><td>2026</td><td>-0.4</td><td>-0.1</td><td>0.1</td><td>0.5</td><td>1.0</td></tr>
</table>
"""


class NoaaOniCurrentTest(unittest.TestCase):
    def test_stores_the_printed_amj_2026_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oni.json"
            noaa_oni_current.record_noaa_oni_current(path, NOAA_ONI_URL, LIVE_BODY)
            stored = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(NOAA_ONI_URL, noaa_oni_current.NOAA_ONI_URL)
        self.assertEqual(
            stored,
            {
                "series": "Oceanic Niño Index (ONI)",
                "season": "AMJ 2026",
                "value": 1.0,
                "statement": STATEMENT,
                "kind": "index",
                "citation_url": NOAA_ONI_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(stored)
        self.assertNotIn("-0.5", text)
        self.assertNotIn("MAM", text)
        self.assertNotIn("finished", text)
        self.assertNotIn("forecast", text)
        self.assertNotIn("price", text)
        self.assertNotIn("trade", text)

    def test_failed_request_or_empty_body_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oni.json"
            with self.assertRaises(ValueError):
                noaa_oni_current.record_noaa_oni_current(
                    path,
                    NOAA_ONI_URL,
                    LIVE_BODY,
                    request_failed=True,
                )
            with self.assertRaises(ValueError):
                noaa_oni_current.record_noaa_oni_current(path, NOAA_ONI_URL, None)
            self.assertFalse(path.exists())

    def test_missing_series_or_value_writes_nothing(self) -> None:
        no_series = LIVE_BODY.replace("Oceanic Niño Index (ONI)", "seasonal table")
        no_statement = LIVE_BODY.replace(STATEMENT, "")
        no_value = """
        <h2>Oceanic Niño Index (ONI)</h2>
        <table>
        <tr><td>Year</td><td>DJF</td><td>JFM</td><td>FMA</td><td>MAM</td><td>AMJ</td></tr>
        <tr><td>2026</td><td></td><td></td><td></td><td></td><td></td></tr>
        </table>
        """
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oni.json"
            for body in (no_series, no_value, no_statement):
                with self.assertRaises(ValueError):
                    noaa_oni_current.record_noaa_oni_current(path, NOAA_ONI_URL, body)
            self.assertFalse(path.exists())

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oni.json"
            with self.assertRaises(ValueError):
                noaa_oni_current.record_noaa_oni_current(path, None, LIVE_BODY)
            with self.assertRaises(ValueError):
                noaa_oni_current.record_noaa_oni_current(
                    path,
                    NOAA_ONI_URL.rstrip("/"),
                    LIVE_BODY,
                )
            self.assertFalse(path.exists())

    def test_reading_the_stored_record_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "oni.json"
            noaa_oni_current.record_noaa_oni_current(path, NOAA_ONI_URL, LIVE_BODY)
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(stored["series"], "Oceanic Niño Index (ONI)")
            self.assertEqual(stored["season"], "AMJ 2026")
            self.assertEqual(stored["value"], 1.0)
            self.assertEqual(stored["statement"], STATEMENT)
            self.assertEqual(stored["kind"], "index")
            self.assertNotIn("price", stored)
            self.assertNotIn("trade", stored)
            self.assertNotIn("finished", stored)
            self.assertNotIn("forecast", stored)
            self.assertFalse(stored["permits_financial_use"])
            self.assertFalse((folder / "trade.json").exists())
            self.assertEqual([item.name for item in folder.iterdir()], ["oni.json"])
            for label in ("price", "trade", "finished", "forecast"):
                rejected = folder / "rejected.json"
                with self.assertRaises(ValueError):
                    noaa_oni_current.record_noaa_oni_current(
                        rejected,
                        NOAA_ONI_URL,
                        LIVE_BODY,
                        label=label,
                    )
                self.assertFalse(rejected.exists())


if __name__ == "__main__":
    unittest.main()
