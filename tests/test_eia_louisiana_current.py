import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import eia_louisiana_current
from farm_ontology.policy import CLASS_C_POLICY

LIVE_BODY = """
<span class="date">November 16, 2026</span>
<table summary="Nymex Prices">
<tr><td colspan="4"><b>Prompt-Month Energy Futures, 11/13/26 Settlement</b></td></tr>
<tr><td>Natural Gas ($/million Btu) - Nymex</td><td>NA</td></tr>
</table>
<table>
<tr><td><b>Select Spot Prices for Delivery Today</b></td></tr>
<tr>
<th>Region</th>
<th>Natural Gas<br><span>($/million Btu)</span></th>
<th></th>
<th>Electricity<br><span>($/MWh)</span></th>
<th></th>
<th>Spark Spread<br><span>($/MWh)</span></th>
</tr>
<tr>
<td>New England</td><td>3.26</td><td>-6.9</td><td>62.33</td><td>-7.1</td><td>39.53</td>
</tr>
<tr>
<td>Louisiana</td><td>3.26</td><td>+0.8</td><td>29.75</td><td>+36.8</td><td>6.96</td>
</tr>
</table>
"""


class EiaLouisianaCurrentTest(unittest.TestCase):
    def test_stores_the_printed_louisiana_prices(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eia.json"
            eia_louisiana_current.record_eia_louisiana_current(
                path,
                eia_louisiana_current.EIA_URL,
                LIVE_BODY,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            stored,
            {
                "date": "November 16, 2026",
                "delivery": "Today",
                "table": "Select Spot Prices for Delivery Today",
                "region": "Louisiana",
                "natural_gas": {"value": 3.26, "unit": "$/million Btu"},
                "electricity": {"value": 29.75, "unit": "$/MWh"},
                "citation_url": eia_louisiana_current.EIA_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(stored)
        self.assertNotIn("New England", text)
        self.assertNotIn("6.96", text)
        self.assertNotIn("Nymex", text)
        self.assertNotIn("Settlement", text)
        self.assertNotIn("11/13", text)
        self.assertNotIn("trade", text)

    def test_failed_request_or_missing_louisiana_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eia.json"
            with self.assertRaises(ValueError):
                eia_louisiana_current.record_eia_louisiana_current(
                    path,
                    eia_louisiana_current.EIA_URL,
                    LIVE_BODY,
                    request_failed=True,
                )
            with self.assertRaises(ValueError):
                eia_louisiana_current.record_eia_louisiana_current(
                    path,
                    eia_louisiana_current.EIA_URL,
                    None,
                )
            missing = LIVE_BODY.replace("<td>Louisiana</td>", "<td>Houston</td>", 1)
            with self.assertRaises(ValueError):
                eia_louisiana_current.record_eia_louisiana_current(
                    path,
                    eia_louisiana_current.EIA_URL,
                    missing,
                )
            self.assertFalse(path.exists())

    def test_na_cells_write_nothing(self) -> None:
        missing = LIVE_BODY.replace(
            "<td>Louisiana</td><td>3.26</td><td>+0.8</td><td>29.75</td>",
            "<td>Louisiana</td><td>NA</td><td>NA</td><td>NA</td>",
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eia.json"
            with self.assertRaises(ValueError):
                eia_louisiana_current.record_eia_louisiana_current(
                    path,
                    eia_louisiana_current.EIA_URL,
                    missing,
                )
            self.assertFalse(path.exists())

    def test_missing_date_writes_nothing(self) -> None:
        missing = LIVE_BODY.replace(
            '<span class="date">November 16, 2026</span>',
            '<span class="date"></span>',
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eia.json"
            with self.assertRaises(ValueError):
                eia_louisiana_current.record_eia_louisiana_current(
                    path,
                    eia_louisiana_current.EIA_URL,
                    missing,
                )
            self.assertFalse(path.exists())

    def test_missing_citation_or_rejected_label_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eia.json"
            with self.assertRaises(ValueError):
                eia_louisiana_current.record_eia_louisiana_current(path, None, LIVE_BODY)
            with self.assertRaises(ValueError):
                eia_louisiana_current.record_eia_louisiana_current(
                    path,
                    eia_louisiana_current.EIA_URL + "/",
                    LIVE_BODY,
                )
            for label in ("futures", "settlement", "trade"):
                with self.assertRaises(ValueError):
                    eia_louisiana_current.record_eia_louisiana_current(
                        path,
                        eia_louisiana_current.EIA_URL,
                        LIVE_BODY,
                        label=label,
                    )
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
