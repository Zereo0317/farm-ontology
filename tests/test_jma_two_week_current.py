import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import jma_two_week_current
from farm_ontology.policy import CLASS_C_POLICY

LIVE_BODY = """
<title>Japan Meteorological Agency | Two-week Temperature Forecast</title>
<h1>Two-week Temperature Forecast</h1>
<div class="fuken zenpan">
The Two-week Temperature Forecast is issued at 14:30 JST every day.
This page shows time-series representations of observed temperatures for the past week
and forecasts for the next two weeks. Forecasts for the second week ahead are averaged
over the five-day periods marked in parentheses.
Appearance ratios for high/very high, normal and low/very low temperatures are 33%
in the relevant climatology. The terms very high and very low refer to temperatures
with climatology appearance ratios of 10%.
This image shows categorized five-day average temperatures from eight days ahead,
at probabilities of 30% or more.
</div>
"""


class JmaTwoWeekCurrentTest(unittest.TestCase):
    def test_stores_the_printed_title_and_no_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "two-week.json"
            jma_two_week_current.record_jma_two_week_current(
                path,
                jma_two_week_current.JMA_TWO_WEEK_URL,
                LIVE_BODY,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            stored,
            {
                "title": "Japan Meteorological Agency | Two-week Temperature Forecast",
                "citation_url": jma_two_week_current.JMA_TWO_WEEK_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(stored, ensure_ascii=False)
        self.assertFalse(any(character.isdigit() for character in text))
        self.assertNotIn("14:30", text)
        self.assertNotIn("33", text)
        self.assertNotIn("value", stored)

    def test_failed_request_or_empty_body_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "two-week.json"
            with self.assertRaises(ValueError):
                jma_two_week_current.record_jma_two_week_current(
                    path,
                    jma_two_week_current.JMA_TWO_WEEK_URL,
                    LIVE_BODY,
                    request_failed=True,
                )
            with self.assertRaises(ValueError):
                jma_two_week_current.record_jma_two_week_current(
                    path,
                    jma_two_week_current.JMA_TWO_WEEK_URL,
                    None,
                )
            self.assertFalse(path.exists())

    def test_missing_title_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "two-week.json"
            with self.assertRaises(ValueError):
                jma_two_week_current.record_jma_two_week_current(
                    path,
                    jma_two_week_current.JMA_TWO_WEEK_URL,
                    "<div>five-day periods 14:30 33%</div>",
                )
            self.assertFalse(path.exists())

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "two-week.json"
            with self.assertRaises(ValueError):
                jma_two_week_current.record_jma_two_week_current(path, None, LIVE_BODY)
            with self.assertRaises(ValueError):
                jma_two_week_current.record_jma_two_week_current(
                    path,
                    jma_two_week_current.JMA_TWO_WEEK_URL.rstrip("/"),
                    LIVE_BODY,
                )
            self.assertFalse(path.exists())

    def test_injected_temperature_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "two-week.json"
            with self.assertRaises(ValueError):
                jma_two_week_current.record_jma_two_week_current(
                    path,
                    jma_two_week_current.JMA_TWO_WEEK_URL,
                    LIVE_BODY,
                    value=12,
                )
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
