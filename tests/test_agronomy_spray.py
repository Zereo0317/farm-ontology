"""Spray-window adviser tests (WS3.3). Fixture series exercises every
rule branch; offline and deterministic."""

import unittest
from datetime import datetime, timedelta, timezone

from farm_ontology.agronomy.common import AgronomyGap, CONFIG_VERSION
from farm_ontology.agronomy.spray_windows import (
    MIN_RUN_HOURS,
    RAINFAST_HOURS,
    SPRAY_CONFIG,
    SPRAY_SOURCE_NOTE,
    Verdict,
    scan_spray_windows,
)
from tests.agronomy_fixtures import hourly_rows

AT = datetime(2026, 8, 10, 4, 0, tzinfo=timezone.utc)
HOURS = hourly_rows()


class InvalidWeatherRegressionTests(unittest.TestCase):
    def test_nonfinite_and_negative_values_never_create_a_go(self):
        for key, value in (("precip_mm", float("nan")), ("precip_mm", float("inf")),
                           ("precip_mm", -1), ("wind_ms", -1),
                           ("wind_ms", float("nan")), ("temp_c", float("inf"))):
            with self.subTest(key=key, value=value):
                rows = [dict(row) for row in HOURS]
                rows[0][key] = value
                with self.assertRaises(AgronomyGap) as ctx:
                    scan_spray_windows(rows, at=AT)
                self.assertEqual(ctx.exception.gap, "invalid-hour-field")


class ScanBehaviourTests(unittest.TestCase):
    def test_fixture_series_produces_ordered_verdict_windows(self):
        windows, summary = scan_spray_windows(HOURS, at=AT)
        self.assertTrue(windows)
        starts = [window.start for window in windows]
        self.assertEqual(starts, sorted(starts))
        for window in windows:
            self.assertIn(window.verdict,
                          (Verdict.GO, Verdict.CAUTION, Verdict.NO_GO,
                           f"{Verdict.GO} (conservative)"))

    def test_wind_rule_caps_and_conservative_tag(self):
        windows, _ = scan_spray_windows(HOURS, at=AT)
        verdicts = [window.verdict for window in windows]
        # The calm run in the fixture must be conservative-tagged GO or a
        # verdict justified by an evidence rule; the tagging is the claim
        # under test: a conservative tag exists iff worst wind ≤ 2 m/s.
        for window in windows:
            wind_ev = next(e for e in window.evidence if e["rule"] == "wind<=max")
            if window.verdict.startswith(Verdict.GO) and "conservative" in window.verdict:
                self.assertLessEqual(wind_ev["worst_observed_ms"], 2.0)
                self.assertTrue(wind_ev["conservative_eligible"])
        self.assertTrue(verdicts)  # something was scored

    def test_rain_inside_run_or_tail_downgrades_with_evidence(self):
        windows, _ = scan_spray_windows(HOURS, at=AT)
        rules_seen = {e["rule"] for window in windows for e in window.evidence}
        self.assertIn("wind<=max", rules_seen)
        # The fixture's post-rain calm stretch must carry the wet-tail rule.
        self.assertIn("rainfast-tail-wet", rules_seen)

    def test_every_window_carries_its_evidence_lines(self):
        windows, _ = scan_spray_windows(HOURS, at=AT)
        for window in windows:
            self.assertTrue(window.evidence)
            self.assertTrue(
                all(isinstance(e.get("rule"), str) for e in window.evidence)
            )
            fired = [e for e in window.evidence if e.get("fired")]
            # A GO window fires only the wind-pass line; anything stricter
            # (temp/wet) firing must downgrade.
            if window.verdict == Verdict.GO:
                self.assertFalse(
                    any("temp" in e["rule"] or "rainfast" in e["rule"]
                        for e in fired)
                )

    def test_summary_reports_unusable_spans_with_their_rule(self):
        windows, summary = scan_spray_windows(HOURS, at=AT)
        self.assertEqual(summary["config_version"], CONFIG_VERSION)
        self.assertIn("VERIFY [SPRAY-WINDOW]", summary["source_note"])
        self.assertGreater(summary["hours_scanned"], 0)
        for span in summary["unusable_spans"]:
            self.assertTrue(span["failed"])

    def test_scan_context_present_in_summary(self):
        _, summary = scan_spray_windows(HOURS, at=AT)
        self.assertEqual(summary["scan_context"], AT.astimezone(timezone.utc).isoformat())


class GapPathsTests(unittest.TestCase):
    def test_empty_rows_gap(self):
        with self.assertRaises(AgronomyGap) as ctx:
            scan_spray_windows([], at=AT)
        self.assertEqual(ctx.exception.gap, "no-usable-rows")

    def test_sequence_hole_is_a_named_gap(self):
        rows = [dict(row) for row in HOURS]
        rows.insert(7, {**rows[6], "time": (datetime.fromisoformat(rows[6]["time"])
                                             + timedelta(minutes=37)).isoformat()})
        with self.assertRaises(AgronomyGap) as ctx:
            scan_spray_windows(rows, at=AT)
        self.assertEqual(ctx.exception.gap, "hour-sequence-hole")

    def test_missing_field_names_row_and_field(self):
        rows = [dict(row) for row in HOURS]
        del rows[3]["temp_c"]
        with self.assertRaises(AgronomyGap) as ctx:
            scan_spray_windows(rows, at=AT)
        self.assertEqual(ctx.exception.gap, "missing-hour-field")
        self.assertIn("temp_c", ctx.exception.missing[0])

    def test_non_numeric_field_value_refused(self):
        rows = [dict(row) for row in HOURS]
        rows[5] = {**rows[5], "wind_ms": "breezy"}
        with self.assertRaises(AgronomyGap) as ctx:
            scan_spray_windows(rows, at=AT)
        self.assertEqual(ctx.exception.gap, "missing-hour-field")

    def test_naive_timestamp_refused(self):
        rows = [dict(row) for row in HOURS]
        rows[2] = {**rows[2], "time": "2026-08-10T02:00:00"}
        with self.assertRaises(AgronomyGap):
            scan_spray_windows(rows, at=AT)

    def test_series_ending_before_now_refused(self):
        rows = [row for row in HOURS if row["time"] < "2026-08-10T04:00:00+00:00"]
        with self.assertRaises(AgronomyGap) as ctx:
            scan_spray_windows(rows, at=AT)
        self.assertEqual(ctx.exception.gap, "stale-hours")

    def test_series_beginning_far_past_refused(self):
        shifted = [
            dict(row, time=(datetime.fromisoformat(row["time"])
                            - timedelta(hours=48)).isoformat())
            for row in HOURS
        ]
        with self.assertRaises(AgronomyGap) as ctx:
            scan_spray_windows(shifted, at=AT)
        self.assertEqual(ctx.exception.gap, "stale-hours")

    def test_future_only_series_refused(self):
        shifted = [
            dict(row, time=(datetime.fromisoformat(row["time"])
                            + timedelta(hours=72)).isoformat())
            for row in HOURS
        ]
        with self.assertRaises(AgronomyGap) as ctx:
            scan_spray_windows(shifted, at=AT)
        self.assertEqual(ctx.exception.gap, "series-misses-now")

    def test_missing_native_resolution_refused(self):
        rows = [dict(row) for row in HOURS]
        del rows[0]["native_resolution_km"]
        with self.assertRaises(AgronomyGap) as ctx:
            scan_spray_windows(rows, at=AT)
        self.assertEqual(ctx.exception.gap, "missing-native-resolution")


class RuleConstantsTests(unittest.TestCase):
    def test_rule_table_values_match_the_documented_norms(self):
        self.assertEqual(SPRAY_CONFIG["wind_max_ms"], 3.0)
        self.assertEqual(SPRAY_CONFIG["wind_conservative_ms"], 2.0)
        self.assertEqual(SPRAY_CONFIG["temp_go_min_c"], 10.0)
        self.assertEqual(SPRAY_CONFIG["temp_go_max_c"], 25.0)
        self.assertGreaterEqual(RAINFAST_HOURS, 6)
        self.assertEqual(MIN_RUN_HOURS, 2)
        self.assertIn("VERIFY [SPRAY-WINDOW]", SPRAY_SOURCE_NOTE)

    def test_minimum_run_at_series_end_is_caution_with_published_doubt(self):
        # Two perfect hours at the end of the data: the run qualifies by
        # MIN_RUN_HOURS but its rainfast tail cannot be checked — the
        # window is CAUTION with evidence, never a hopeful GO.
        rows = [
            {"time": "2026-08-10T04:00:00+00:00", "wind_ms": 1.5,
             "precip_mm": 0.0, "temp_c": 22.0, "native_resolution_km": 5},
            {"time": "2026-08-10T05:00:00+00:00", "wind_ms": 1.5,
             "precip_mm": 0.0, "temp_c": 22.0, "native_resolution_km": 5},
        ]
        windows, summary = scan_spray_windows(rows, at=AT)
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0].hours, MIN_RUN_HOURS)
        self.assertTrue(windows[0].verdict.startswith(Verdict.CAUTION))
        self.assertIn(
            "rainfast-window-unverifiable",
            [e["rule"] for e in windows[0].evidence],
        )
        # An empty set with a published summary is a legitimate outcome
        # of a hostile series — never a fabricated window.
        self.assertEqual(summary["hours_scanned"], 2)


if __name__ == "__main__":
    unittest.main()
