"""Offline tests for the WS2.3 Sandbox NDVI weekly baseline.

The Statistical API call is MOCKED here (recorded-fixture transport);
the real call stays guarded behind the env seam and is proven to refuse
loudly when unarmed. The 10 m support isolation is asserted on the
stored row.
"""

import json
import sys
import tempfile
import unittest
import unittest.mock
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import ingest_core
from farm_ontology.ingest_ndvi import (
    BASE_URL_ENV,
    CLIENT_SECRET_NAME_ENV,
    NDVI_JOB,
    NDVI_SUPPORT,
    cell_geometry,
    run_ndvi_job,
    statistical_request,
)

NOW = datetime(2026, 11, 16, 6, 0, tzinfo=timezone.utc)  # a Monday
LAT, LON = 42.7018152, 142.4071291

#: Recorded-shape Statistical API answer (aggregation.intervalBins of
#: the documented response): one weekly bin, NDVI stats inside.
STATS_FIXTURE = {
    "type": "GetDataStatisticsResultsCollection",
    "aggregation": {
        "interval": [
            {
                "from": "2026-11-09T06:00:00Z",
                "to": "2026-11-16T06:00:00Z",
                "bins": {
                    "ndvi B0 [0.0 - 0.5)": {
                        "count": 41,
                        "coverage": 100.0,
                        "min": 0.284,
                        "max": 0.467,
                        "mean": 0.381,
                        "stDev": 0.041,
                    }
                },
            }
        ]
    },
}


def new_backend():
    root = Path(tempfile.mkdtemp(prefix="ws2-ndvi-"))
    return root, ingest_core.local_pipe_backend(root)


def transport(stats=STATS_FIXTURE):
    calls = []

    def _transport(request_body, *, now):
        calls.append({"body": request_body, "now": now})
        return json.loads(json.dumps(stats))

    _transport.calls = calls
    return _transport


class GeometryTests(unittest.TestCase):
    def test_cell_geometry_is_a_closed_ten_metre_square(self):
        geometry = cell_geometry(LAT, LON)
        ring = geometry["coordinates"][0]
        self.assertEqual(ring[0], ring[-1])
        self.assertAlmostEqual(abs(ring[1][0] - ring[0][0]), 0.0001, places=8)
        xs = [point[0] for point in ring]
        ys = [point[1] for point in ring]
        self.assertAlmostEqual(max(xs) - min(xs), 0.0001, places=8)
        self.assertAlmostEqual(max(ys) - min(ys), 0.0001, places=8)


class RequestTests(unittest.TestCase):
    def test_request_names_sentinel2_the_window_and_10m_resolution(self):
        body = statistical_request(cell_geometry(LAT, LON), from_=NOW - timedelta(days=7), to=NOW)
        data = body["input"]["data"][0]
        self.assertEqual(data["type"], "sentinel-2-l2a")
        self.assertEqual(data["dataFilter"]["timeRange"]["to"], NOW.isoformat().replace("+00:00", "+00:00"))
        self.assertEqual(body["aggregation"]["resolution"], "10m")
        self.assertEqual(body["aggregation"]["aggregationInterval"]["of"], "P7D")
        self.assertIn("(B08 - B04)", body["calculations"]["ndvi"]["indices"]["ndvi"])


class WeeklyRunTests(unittest.TestCase):
    def setUp(self):
        self.root, self.backend = new_backend()

    def test_injected_transport_stores_one_10m_row(self):
        fake = transport()
        result = run_ndvi_job(self.backend, now=NOW, latitude=LAT, longitude=LON, transport=fake)
        self.assertTrue(result["ok"])
        self.assertEqual(result["row_count"], 1)
        self.assertEqual(len(fake.calls), 1)
        rows = ingest_core.job_rows(self.backend, "ndvi", "ndvi-")
        row = rows[0]
        self.assertEqual(row["support"], NDVI_SUPPORT)
        self.assertEqual(row["native_resolution_m"], 10)
        self.assertFalse(row["mixed_into_coarse_support"])
        self.assertFalse(row["permits_financial_use"])
        self.assertEqual(row["statistics"], STATS_FIXTURE)
        self.assertIn("never mixed", row["support_note"])

    def test_window_looks_back_seven_days(self):
        fake = transport()
        run_ndvi_job(self.backend, now=NOW, latitude=LAT, longitude=LON, transport=fake)
        body = fake.calls[0]["body"]
        self.assertEqual(
            body["input"]["data"][0]["dataFilter"]["timeRange"]["from"],
            (NOW - timedelta(days=7)).isoformat(),
        )

    def test_repeat_week_same_transport_writes_a_new_dated_row(self):
        fake = transport()
        run_ndvi_job(self.backend, now=NOW, latitude=LAT, longitude=LON, transport=fake)
        next_monday = run_ndvi_job(
            self.backend, now=NOW + timedelta(days=7),
            latitude=LAT, longitude=LON, transport=fake,
        )
        self.assertEqual(next_monday["row_count"], 1)
        self.assertEqual(len(ingest_core.job_rows(self.backend, "ndvi", "ndvi-")), 2)

    def test_unarmed_real_call_is_a_loud_failure_and_a_run_row(self):
        result = run_ndvi_job(self.backend, now=NOW, latitude=LAT, longitude=LON, transport=None)
        self.assertFalse(result["ok"])
        self.assertIn("not armed", result["error"])
        self.assertIn(BASE_URL_ENV, result["error"])
        self.assertIn(CLIENT_SECRET_NAME_ENV, result["error"])
        rows = ingest_core.run_rows(self.backend, NDVI_JOB)
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["ok"])

    def test_armed_but_unmounted_secret_refuses_before_any_network(self):
        env = {BASE_URL_ENV: "https://services.sentinel-hub.com/api/v1", CLIENT_SECRET_NAME_ENV: "FARM_TEST_SECRET"}
        with unittest.mock.patch.dict("os.environ", env, clear=False):
            import os
            os.environ.pop("FARM_TEST_SECRET", None)
            result = run_ndvi_job(self.backend, now=NOW, latitude=LAT, longitude=LON, transport=None)
        self.assertFalse(result["ok"])
        self.assertIn("not mounted", result["error"])

    def test_three_unarmed_weeks_trip_the_generic_alert(self):
        for offset in range(3):
            run_ndvi_job(
                self.backend, now=NOW + timedelta(weeks=offset),
                latitude=LAT, longitude=LON, transport=None,
            )
        standing = ingest_core.standing_alerts(self.backend, NDVI_JOB)
        self.assertEqual(len(standing), 1)
        self.assertIn("ALERT.json", standing[0])


if __name__ == "__main__":
    unittest.main()
