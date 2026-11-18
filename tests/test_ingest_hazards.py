"""Offline tests for the WS2.4 hazard watcher (pipelines/hazards).

Nothing here touches a network: the default (force=False) seam replays
the recorded in-repo fixture headers verbatim; the force path is probed
with an injected fetcher and the enabled environment flag.
"""

import sys
import tempfile
import unittest
import unittest.mock
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import ingest_core
from farm_ontology import jma_marine, jma_snow, jma_torrential, us_drought_monitor
from farm_ontology.pipelines.hazards import (
    FETCH_ENABLED_ENV,
    HAZARD_JOB,
    SEEN_WARNINGS_REL,
    HAZARD_SOURCES,
    fetch_hazard,
    hazard_signature,
    load_seen,
    run_hazard_job,
    source_ids,
)

NOW = datetime(2026, 11, 18, 7, 30, tzinfo=timezone.utc)


def day(offset: int) -> datetime:
    return NOW + timedelta(days=offset)


def new_backend():
    root = Path(tempfile.mkdtemp(prefix="ws2-hz-"))
    return root, ingest_core.local_pipe_backend(root)


class SeamTests(unittest.TestCase):
    def test_replay_carries_the_recorded_headers_verbatim(self):
        torrential = fetch_hazard("jma-torrential")
        self.assertTrue(torrential["fixture"])
        self.assertEqual(torrential["headers"]["publisher"], jma_torrential.PUBLISHER)
        self.assertEqual(torrential["headers"]["product"], jma_torrential.PRODUCT)
        self.assertEqual(torrential["headers"]["period"], jma_torrential.PERIOD)
        self.assertEqual(torrential["headers"]["citation_url"], jma_torrential.JMA_TORRENTIAL_URL)
        self.assertFalse(torrential["headers"]["permits_financial_use"])

    def test_usdm_headers_match_the_recorded_module(self):
        usdm = fetch_hazard("us-drought-monitor")
        self.assertEqual(usdm["headers"]["publisher"], us_drought_monitor.PUBLISHER)
        self.assertEqual(usdm["headers"]["administrative_area"], us_drought_monitor.ADMINISTRATIVE_AREA)
        self.assertEqual(usdm["headers"]["kind"], us_drought_monitor.KIND)

    def test_marine_header_has_no_unit_because_the_module_stores_none(self):
        marine = fetch_hazard("jma-marine")
        self.assertNotIn("unit", marine["headers"])
        self.assertIn("administrative_area", marine["headers"])

    def test_unknown_source_is_a_loud_refusal(self):
        with self.assertRaises(ValueError):
            fetch_hazard("bosnian-wind-gusts")

    def test_source_ids_cover_the_recorded_feeds(self):
        self.assertEqual(
            source_ids(),
            ("jma-torrential", "jma-snow", "jma-marine", "us-drought-monitor"),
        )

    def test_force_requires_the_environment_flag(self):
        with unittest.mock.patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop(FETCH_ENABLED_ENV, None)
            with self.assertRaises(ValueError) as caught:
                fetch_hazard("jma-snow", force=True, fetcher=lambda url: "x")
        self.assertIn(FETCH_ENABLED_ENV, str(caught.exception))

    def test_force_with_a_flag_and_fetcher_probes_but_fabricates_nothing(self):
        payload = "<html>JMA snow page contents</html>"
        seen_urls = []

        def fetcher(url: str) -> str:
            seen_urls.append(url)
            return payload

        with unittest.mock.patch.dict("os.environ", {FETCH_ENABLED_ENV: "1"}):
            result = fetch_hazard("jma-snow", force=True, fetcher=fetcher)
        self.assertEqual(seen_urls, [jma_snow.JMA_SNOW_URL])
        self.assertEqual(result["live_probe"]["bytes"], len(payload.encode("utf-8")))
        self.assertEqual(result["headers"]["product"], jma_snow.PRODUCT)

    def test_force_with_an_empty_fetch_raises(self):
        with unittest.mock.patch.dict("os.environ", {FETCH_ENABLED_ENV: "1"}):
            with self.assertRaises(ValueError):
                fetch_hazard("jma-snow", force=True, fetcher=lambda url: "  ")


class WatcherTests(unittest.TestCase):
    def setUp(self):
        self.root, self.backend = new_backend()

    def test_first_run_baselines_four_rows_and_four_warning_flags(self):
        first = run_hazard_job(self.backend, now=NOW)
        self.assertTrue(first["ok"])
        self.assertEqual(first["row_count"], 4)
        self.assertEqual(len(first["new_warnings"]), 4)
        rows = ingest_core.job_rows(self.backend, "hazards", "hazard-")
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertTrue(row["fixture"])
            self.assertFalse(row["permits_financial_use"])
        seen = load_seen(self.backend)
        self.assertEqual(len(seen["signatures"]), 4)
        warnings = [n for n in ingest_core.standing_alerts(self.backend, HAZARD_JOB) if "warnings" in n]
        self.assertEqual(len(warnings), 4)

    def test_second_identical_run_writes_no_new_warning_and_identical_rows(self):
        run_hazard_job(self.backend, now=NOW)
        import hashlib
        before = {
            p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (self.root / "pipelines" / "hazards").rglob("*.json")
        }
        second = run_hazard_job(self.backend, now=NOW)
        after = {
            p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (self.root / "pipelines" / "hazards").rglob("*.json")
        }
        self.assertEqual(before, after)
        self.assertEqual(second["row_count"], 4)
        self.assertEqual(second["new_warnings"], [])

    def test_changed_signature_fires_a_new_warning_for_that_source(self):
        run_hazard_job(self.backend, now=NOW)
        tomorrow = run_hazard_job(self.backend, now=day(1))
        self.assertEqual(tomorrow["new_warnings"], [])
        seen = load_seen(self.backend)
        self.assertEqual(len(seen["signatures"]), 4)
        # The recorded torrential period changing means the signature moved.
        template = dict(next(s for s in HAZARD_SOURCES if s["source_id"] == "jma-torrential"))
        changed = dict(template)
        changed["headers"] = dict(fetch_hazard("jma-torrential")["headers"], period="08:50 JST, 19 November 2026")
        signature = "|".join(hazard_signature(changed["headers"]))
        self.assertNotIn(signature, seen["signatures"])

    def test_failure_run_strikes_accumulate_into_the_generic_alert(self):
        # A forced run without the enabled flag refuses loudly -> three
        # failed days trip the standard 3-strike artefact.
        import unittest.mock as mock

        for offset in range(3):
            with mock.patch.dict("os.environ", {}, clear=False):
                import os
                os.environ.pop(FETCH_ENABLED_ENV, None)
                outcome = run_hazard_job(self.backend, now=day(offset), force=True)
        self.assertFalse(outcome["ok"])
        self.assertEqual(outcome["consecutive_failures"], 3)
        self.assertIsNotNone(outcome["alert"])
        self.assertIn("ALERT.json", outcome["alert"])
        alert = ingest_core.read_json(self.backend, outcome["alert"])
        self.assertEqual(len(alert["evidence"]), 3)


if __name__ == "__main__":
    unittest.main()
