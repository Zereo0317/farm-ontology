import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import eccc_toronto_humidity
from farm_ontology.policy import CLASS_C_POLICY


def _months(percents: tuple[float, ...]) -> list[dict[str, object]]:
    return [
        {"month": month, "percent": percent}
        for month, percent in zip(eccc_toronto_humidity.MONTHS, percents, strict=True)
    ]


class EcccTorontoHumidityTest(unittest.TestCase):
    def test_stores_printed_humidity_percents(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "toronto-humidity.json"
            eccc_toronto_humidity.record_eccc_toronto_humidity(
                path,
                eccc_toronto_humidity.ECCC_TORONTO_HUMIDITY_URL,
            )
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            header,
            {
                "station": "TORONTO (CITY)",
                "province": "ONTARIO",
                "product": "1991 to 2020 Canadian Climate Normals Data",
                "period": "1991 to 2020",
                "rows": [
                    {
                        "label": "Average Relative Humidity - 0600LST (%)",
                        "code": "D",
                        "code_legend": "D = At least 15 years",
                        "months": _months(eccc_toronto_humidity.PERCENTS_0600),
                    },
                    {
                        "label": "Average Relative Humidity - 1500LST (%)",
                        "code": "D",
                        "code_legend": "D = At least 15 years",
                        "months": _months(eccc_toronto_humidity.PERCENTS_1500),
                    },
                ],
                "citation_url": eccc_toronto_humidity.ECCC_TORONTO_HUMIDITY_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        january = header["rows"][0]["months"][0]
        self.assertEqual(january, {"month": "Jan", "percent": 77.5})
        text = json.dumps(header)
        self.assertIn("77.5", text)
        self.assertNotIn("Biratori", text)
        self.assertNotIn("Year", text)
        self.assertNotIn("Vapour", text)
        self.assertNotIn("kPa", text)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "toronto-humidity.json"
            with self.assertRaises(ValueError):
                eccc_toronto_humidity.record_eccc_toronto_humidity(path, None)
            with self.assertRaises(ValueError):
                eccc_toronto_humidity.record_eccc_toronto_humidity(path, "   ")
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        citation = eccc_toronto_humidity.ECCC_TORONTO_HUMIDITY_URL
        swapped = citation.replace(
            "climate_id=6158350&dispBack=0",
            "dispBack=0&climate_id=6158350",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "toronto-humidity.json"
            for other in (
                citation + "/",
                swapped,
                "https://climate.weather.gc.ca/climate_normals/results_1991_2020_e.html",
                citation.replace("results_1991_2020_e.html", "results_1991_2020_f.html"),
            ):
                with self.assertRaises(ValueError):
                    eccc_toronto_humidity.record_eccc_toronto_humidity(path, other)
            self.assertFalse(path.exists())

    def test_rejected_labels_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "toronto-humidity.json"
            for label in (
                "farm humidity",
                "Biratori",
                "current reading",
                "dewpoint",
                "temperature",
                "yield",
                "trade",
                "completed harvest",
            ):
                with self.assertRaises(ValueError):
                    eccc_toronto_humidity.record_eccc_toronto_humidity(
                        path,
                        eccc_toronto_humidity.ECCC_TORONTO_HUMIDITY_URL,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                eccc_toronto_humidity.record_eccc_toronto_humidity(
                    path,
                    eccc_toronto_humidity.ECCC_TORONTO_HUMIDITY_URL,
                    rows=[{"month": "Jan", "percent": None}],
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_normal(self) -> None:
        source = (
            Path(eccc_toronto_humidity.__file__)
            .read_text(encoding="utf-8")
            .replace("\n", " ")
        )
        self.assertIn("climate normal", source)
        self.assertIn("not a Biratori observation", source)
        self.assertIn("not a current reading", source)
        self.assertIn("not calculated from temperature or dewpoint", source)
        self.assertIn("not farm humidity", source)
        self.assertIn("At least 15 years", source)
        self.assertIn("not a completed harvest", source)
        self.assertNotIn("field_save", source)


if __name__ == "__main__":
    unittest.main()
