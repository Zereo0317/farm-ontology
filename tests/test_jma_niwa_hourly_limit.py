import json
import tempfile
import unittest
import urllib.request
from pathlib import Path

from farm_ontology import jma_niwa_hourly_limit
from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.testing import online_gate


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AssertionError("the refetch does not follow another page")


class JmaNiwaHourlyLimitTest(unittest.TestCase):
    def _record(self, path: Path) -> None:
        jma_niwa_hourly_limit.record_jma_niwa_hourly_limit(
            path,
            jma_niwa_hourly_limit.NIWA_URL,
        )

    def test_stores_the_printed_limit_and_no_humidity_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "niwa-limit.json"
            self._record(path)
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            header,
            {
                "place": "新和",
                "publisher": "気象庁",
                "page": "１時間ごとの値",
                "requested_page": "2026年11月17日のページを表示しましたが、",
                "viewable_limit": "閲覧可能な日は、昨日2026年11月16日までです。",
                "citation_url": jma_niwa_hourly_limit.NIWA_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        self.assertEqual(list(header).count("place"), 1)
        text = json.dumps(header, ensure_ascii=False)
        self.assertNotIn("平取", text)
        self.assertNotIn("湿度", text)
        self.assertNotIn("％", text)
        self.assertNotIn("humidity", text)
        self.assertNotIn("hour", header)
        self.assertNotIn("Biratori", text)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "niwa-limit.json"
            with self.assertRaises(ValueError):
                jma_niwa_hourly_limit.record_jma_niwa_hourly_limit(path, None)
            with self.assertRaises(ValueError):
                jma_niwa_hourly_limit.record_jma_niwa_hourly_limit(path, "   ")
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "niwa-limit.json"
            with self.assertRaises(ValueError):
                jma_niwa_hourly_limit.record_jma_niwa_hourly_limit(
                    path,
                    jma_niwa_hourly_limit.NIWA_URL.replace("day=17", "day=16"),
                )
            self.assertFalse(path.exists())

    def test_rejected_labels_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "niwa-limit.json"
            for label in ("平取", "Biratori", "humidity", "湿度", "yield"):
                with self.assertRaises(ValueError):
                    jma_niwa_hourly_limit.record_jma_niwa_hourly_limit(
                        path,
                        jma_niwa_hourly_limit.NIWA_URL,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                jma_niwa_hourly_limit.record_jma_niwa_hourly_limit(
                    path,
                    jma_niwa_hourly_limit.NIWA_URL,
                    station="平取",
                )
            with self.assertRaises(ValueError):
                jma_niwa_hourly_limit.record_jma_niwa_hourly_limit(
                    path,
                    jma_niwa_hourly_limit.NIWA_URL,
                    humidity_percent=91,
                )
            with self.assertRaises(ValueError):
                jma_niwa_hourly_limit.record_jma_niwa_hourly_limit(
                    path,
                    jma_niwa_hourly_limit.NIWA_URL,
                    hour="1",
                )
            with self.assertRaises(ValueError):
                jma_niwa_hourly_limit.record_jma_niwa_hourly_limit(
                    path,
                    jma_niwa_hourly_limit.NIWA_URL,
                    permits_financial_use=True,
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_invent_a_humidity(self) -> None:
        source = (
            Path(jma_niwa_hourly_limit.__file__)
            .read_text(encoding="utf-8")
            .replace("\n", " ")
        )
        self.assertIn("station of this citation is 新和", source)
        self.assertIn("second station is not added", source)
        self.assertIn("does not print an hour", source)
        self.assertIn("No humidity number is stored", source)
        self.assertIn("Humidity is not calculated", source)
        self.assertNotIn("field_save", source)
        self.assertNotIn("91", source)

    @online_gate()
    def test_live_refetch_prints_the_viewable_limit_and_no_percent(self) -> None:
        request = urllib.request.Request(
            jma_niwa_hourly_limit.NIWA_URL,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(request, timeout=60) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.geturl(), jma_niwa_hourly_limit.NIWA_URL)
            body = response.read()
        text = body.decode("utf-8")
        # JMA legitimately serves TWO shapes for this URL depending on the
        # calendar day: (a) the viewable-limit banner (beyond-yesterday
        # requests), (b) the hourly data table itself (recent days). Accept
        # either; the dated banner text is pinned exactly in the offline
        # fixture test.
        banner_shape = (
            "のページを表示しましたが、" in text
            and "閲覧可能な日は、昨日" in text
        )
        data_shape = "１時間ごとの値" in text and "data_0_0" in text
        self.assertTrue(banner_shape or data_shape, "page is neither the banner nor the data table")
        self.assertIn(jma_niwa_hourly_limit.PAGE, text)
        if banner_shape:
            # In the banner shape the page shows no hourly columns at all.
            self.assertNotIn("湿度", text)
            self.assertNotIn("％", text)
            self.assertNotIn("平取", text)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "niwa-limit.json"
            self._record(path)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(stored.get("viewable_limit"))
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], "closed")
        self.assertNotIn("humidity_percent", stored)


if __name__ == "__main__":
    unittest.main()
