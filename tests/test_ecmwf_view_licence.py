import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import ecmwf_view_licence
from farm_ontology.ecmwf_open_data import ECMWF_OPEN_DATA_URL
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]

OVERVIEW = (
    "<p>A subset of ECMWF real-time forecast data from the IFS and AIFS "
    "models is made available to the public free of charge. Their use is "
    "governed by the Creative Commons CC-BY-4.0 licence and the ECMWF "
    "Terms of Use. This means that the data may be redistributed and used "
    "commercially, subject to&nbsp;<a "
    'href="https://apps.ecmwf.int/datasets/licences/general/">'
    "appropriate attribution</a>.</p>"
    "<p>forecast value 12.4</p>"
    '<a href="https://data.ecmwf.int/forecasts/">Browse the data files</a>'
)
LICENCE = (
    "<h1>Use of data accessed via this service</h1>"
    "<p>applied in addition to the Creative Commons CC-4.0-BY licence.</p>"
    "<p>This data product is published under a Creative Commons Attribution "
    "4.0 International (CC BY 4.0). To view a copy of this licence, visit "
    "https://creativecommons.org/licenses/by/4.0/</p>"
    "<p>forecast value 827.51</p>"
    '<a href="https://www.ecmwf.int/sites/default/files/2026-01/'
    'ecmwf-service-agreement.pdf">service agreement</a>'
)
DIFFERENT_OVERVIEW = (
    "Files may be redistributed and used commercially, subject to "
    "named attribution."
)
DIFFERENT_LICENCE = "This product is published under a Example Licence."


class EcmwfViewLicenceTests(unittest.TestCase):
    def test_stores_the_printed_sentence_and_licence_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ecmwf-view-licence.json"
            ecmwf_view_licence.record_view_licence(
                path,
                ECMWF_OPEN_DATA_URL,
                OVERVIEW,
                LICENCE,
                licence_url=ecmwf_view_licence.VIEW_LICENCE_URL,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            stored,
            {
                "sentence": (
                    "This means that the data may be redistributed and used "
                    "commercially, subject to appropriate attribution."
                ),
                "licence_name": (
                    "Creative Commons Attribution 4.0 International (CC BY 4.0)"
                ),
                "citation_url": ECMWF_OPEN_DATA_URL,
                "licence_page": ecmwf_view_licence.VIEW_LICENCE_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(stored)
        self.assertNotIn("12.4", text)
        self.assertNotIn("827.51", text)
        self.assertNotIn("forecast", stored["sentence"])
        self.assertNotIn("forecast", stored["licence_name"])
        self.assertNotIn("trade", text)
        self.assertNotIn("harvest", text)
        self.assertNotIn("creativecommons.org", text)
        self.assertNotIn("service-agreement", text)
        self.assertNotIn("grib", text.lower())
        self.assertNotIn("value", stored)
        self.assertNotIn("CC-BY-4.0", stored["sentence"])

    def test_different_wording_stores_what_the_pages_print(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ecmwf-view-licence.json"
            ecmwf_view_licence.record_view_licence(
                path,
                ECMWF_OPEN_DATA_URL,
                DIFFERENT_OVERVIEW,
                DIFFERENT_LICENCE,
                licence_url="https://apps.ecmwf.int:443/datasets/licences/general/",
            )
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            stored["sentence"],
            "Files may be redistributed and used commercially, subject to named attribution.",
        )
        self.assertEqual(stored["licence_name"], "Example Licence")
        self.assertEqual(stored["licence_page"], ecmwf_view_licence.VIEW_LICENCE_URL)
        self.assertFalse(stored["permits_financial_use"])

    def test_reading_the_stored_record_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "ecmwf-view-licence.json"
            ecmwf_view_licence.record_view_licence(
                path,
                ECMWF_OPEN_DATA_URL,
                OVERVIEW,
                LICENCE,
                licence_url=ecmwf_view_licence.VIEW_LICENCE_URL,
            )
            before = path.read_text(encoding="utf-8")
            stored = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names, ["ecmwf-view-licence.json"])
        self.assertFalse((folder / "trade.json").exists())
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], "closed")
        self.assertNotIn("trade", stored)
        self.assertNotIn("trade", after)

    def test_other_pages_write_nothing(self) -> None:
        others = (
            "https://confluence.ecmwf.int/display/DAC/Service+Charges%3A+From+01+July+2024",
            "https://www.ecmwf.int/en/forecasts/accessing-forecasts/licences-available",
            "https://data.ecmwf.int/forecasts/",
            "https://data.ecmwf.int/forecasts/example.grib",
            "https://creativecommons.org/licenses/by/4.0/",
            "https://doi.org/10.21957/open-data",
            "https://api.open-meteo.com/v1/forecast",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ecmwf-view-licence.json"
            for licence_url in others:
                with self.assertRaises(ValueError):
                    ecmwf_view_licence.record_view_licence(
                        path,
                        ECMWF_OPEN_DATA_URL,
                        OVERVIEW,
                        LICENCE,
                        licence_url=licence_url,
                    )
            for citation in (None, "", "   ", "https://www.ecmwf.int/"):
                with self.assertRaises(ValueError):
                    ecmwf_view_licence.record_view_licence(
                        path,
                        citation,
                        OVERVIEW,
                        LICENCE,
                        licence_url=ecmwf_view_licence.VIEW_LICENCE_URL,
                    )
            with self.assertRaises(ValueError):
                ecmwf_view_licence.record_view_licence(
                    path,
                    ECMWF_OPEN_DATA_URL,
                    "No redistribution sentence is printed.",
                    LICENCE,
                    licence_url=ecmwf_view_licence.VIEW_LICENCE_URL,
                )
            with self.assertRaises(ValueError):
                ecmwf_view_licence.record_view_licence(
                    path,
                    ECMWF_OPEN_DATA_URL,
                    OVERVIEW,
                    "<p>No licence name is printed.</p>",
                    licence_url=ecmwf_view_licence.VIEW_LICENCE_URL,
                )
            self.assertFalse(path.exists())

    def test_forecast_trade_or_open_class_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ecmwf-view-licence.json"
            for label in (
                "trade",
                "completed harvest",
                "forecast",
                "forecast value",
                "12.4",
            ):
                with self.assertRaises(ValueError):
                    ecmwf_view_licence.record_view_licence(
                        path,
                        ECMWF_OPEN_DATA_URL,
                        OVERVIEW,
                        LICENCE,
                        licence_url=ecmwf_view_licence.VIEW_LICENCE_URL,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                ecmwf_view_licence.record_view_licence(
                    path,
                    ECMWF_OPEN_DATA_URL,
                    OVERVIEW,
                    LICENCE,
                    licence_url=ecmwf_view_licence.VIEW_LICENCE_URL,
                    permits_financial_use=True,
                )
            with self.assertRaises(ValueError):
                ecmwf_view_licence.record_view_licence(
                    path,
                    ECMWF_OPEN_DATA_URL,
                    OVERVIEW,
                    LICENCE,
                    licence_url=ecmwf_view_licence.VIEW_LICENCE_URL,
                    class_c_policy="open",
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_view_licence(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("ecmwf_view_licence", text)
            self.assertNotIn("datasets/licences/general", text)


if __name__ == "__main__":
    unittest.main()
