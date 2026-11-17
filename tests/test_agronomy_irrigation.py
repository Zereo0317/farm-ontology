"""Irrigation adviser tests (WS3.2): balance math + the honest-claims
ladder. Fixtures synthetic; offline."""

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from farm_ontology.agronomy.common import AgronomyGap, CONFIG_VERSION
from farm_ontology.agronomy.irrigation import (
    CoverageLevel,
    DEFAULT_IRRIGATION_CONFIG,
    SoilProfile,
    has_calibrated_coverage,
    irrigation_advisory,
)
from farm_ontology.agronomy.phenology import phenology_reading
from tests.agronomy_fixtures import (
    daily_season_rows,
    sensor_projection_rows,
)

PARCEL = "observation/boundary/demo-not-a-real-farm"
FOREIGN = "observation/boundary/someone-elses-field"
AT = datetime(2026, 8, 10, 4, 0, tzinfo=timezone.utc)
SOWING = datetime(2026, 5, 20, tzinfo=timezone.utc)

ROWS = daily_season_rows()


def _reading():
    return phenology_reading(ROWS, sowing=SOWING, emergence=None)


def _window_rows(last_days: int = 14):
    """A realistic irrigation horizon: the two weeks before AT."""
    cutoff = (AT - timedelta(days=last_days)).strftime("%Y-%m-%d")
    return [row for row in ROWS if row["date"] >= cutoff]


class BalanceMathTests(unittest.TestCase):
    def test_consecutive_dry_hot_days_build_deficit(self):
        reading = _reading()
        dry = [
            {"date": (AT - timedelta(days=n)).date().isoformat(),
             "t_mean_c": 24.0, "eto_mm": 5.0, "rain_mm": 0.0,
             "native_resolution_km": 5}
            for n in range(7, 0, -1)
        ]
        advice = irrigation_advisory(dry, reading=reading, at=AT)
        # Root depletion must exceed RAW after a bone-dry hot week.
        self.assertTrue(advice.recommend)
        self.assertGreater(advice.net_irrigation_requirement_mm, 0.0)
        self.assertGreater(advice.root_depletion_mm, advice.raw_mm)

    def test_generous_rain_suppresses_recommendation(self):
        reading = _reading()
        wet = [
            {"date": (AT - timedelta(days=n)).date().isoformat(),
             "t_mean_c": 20.0, "eto_mm": 3.0, "rain_mm": 40.0,
             "native_resolution_km": 5}
            for n in range(7, 0, -1)
        ]
        advice = irrigation_advisory(wet, reading=reading, at=AT)
        self.assertFalse(advice.recommend)
        self.assertEqual(advice.net_irrigation_requirement_mm, 0.0)

    def test_double_kc_coefficients_within_fao_bounds(self):
        reading = _reading()
        advice = irrigation_advisory(_window_rows(), reading=reading, at=AT)
        for step in advice.daily_trace:
            self.assertLessEqual(step["kc"], DEFAULT_IRRIGATION_CONFIG.kc_max)
            self.assertGreaterEqual(step["kcb"], DEFAULT_IRRIGATION_CONFIG.kcb_anchors[0][1])
            self.assertGreaterEqual(step["ke"], 0.0)

    def test_runoff_haircut_is_conservative_direction(self):
        reading = _reading()
        rainy = [
            {"date": (AT - timedelta(days=n)).date().isoformat(),
             "t_mean_c": 22.0, "eto_mm": 4.0, "rain_mm": 10.0,
             "native_resolution_km": 5}
            for n in range(5, 0, -1)
        ]
        less_rainy = [dict(row, rain_mm=5.0) for row in rainy]
        # MORE gross rain can only reduce (never raise) depletion: the
        # runoff haircut biases demand upward — water never vanishes in
        # the direction that hides need.
        wetter = irrigation_advisory(rainy, reading=reading, at=AT).root_depletion_mm
        drier = irrigation_advisory(less_rainy, reading=reading, at=AT).root_depletion_mm
        self.assertLess(wetter, drier)

    def test_raw_and_taw_from_declared_soil_profile(self):
        soil = SoilProfile(theta_fc_m3m3=0.35, theta_wp_m3m3=0.15, rooting_depth_m=0.6)
        self.assertAlmostEqual(soil.taw_mm, 120.0)
        self.assertAlmostEqual(soil.raw_mm, 60.0)

    def test_horizon_semantics_are_explicit_in_why(self):
        advice = irrigation_advisory(_window_rows(), reading=_reading(), at=AT)
        self.assertIn("RAW", advice.why)
        self.assertIn("horizon end", advice.why)

    def test_daily_trace_is_replayable_arithmetic(self):
        advice = irrigation_advisory(_window_rows(), reading=_reading(), at=AT)
        depleted = max(
            0.0,
            (DEFAULT_IRRIGATION_CONFIG.initial_root_depletion_mm
             if DEFAULT_IRRIGATION_CONFIG.initial_root_depletion_mm is not None
             else advice.raw_mm),
        )
        for step in advice.daily_trace:
            depleted = max(
                0.0,
                depleted - step["effective_rain_mm"] + step["etc_adj_mm"],
            )
        self.assertAlmostEqual(depleted, advice.root_depletion_mm, places=2)


class HonestClaimsLadderTests(unittest.TestCase):
    """grid → probe-footprint → parcel; climbing needs evidence."""

    def test_grid_support_always_present_even_sensor_less(self):
        advice = irrigation_advisory(ROWS, reading=_reading(), parcel=PARCEL, at=AT)
        self.assertTrue(advice.support.base.startswith("grid-support (native 5 km)"))
        self.assertEqual(advice.coverage.level, CoverageLevel.NONE)

    def test_mixed_grid_resolutions_refused_support_never_blended(self):
        rows = _window_rows() + [dict(_window_rows()[-1], native_resolution_km=9)]
        with self.assertRaises(AgronomyGap) as ctx:
            irrigation_advisory(rows, reading=_reading(), at=AT)
        self.assertEqual(ctx.exception.gap, "grid-resolution-mixed")

    def test_probe_footprint_claim_never_states_hectares(self):
        rows = [
            dict(row)
            for row in sensor_projection_rows()
            if "scan-array" not in row["sensor_iri"]
        ]
        cov = has_calibrated_coverage(rows, PARCEL, AT)
        self.assertEqual(cov.level, CoverageLevel.PROBE_FOOTPRINT)
        for text in cov.footprint_texts:
            self.assertIn("probe footprint", text)
            # The probe texts never express an AREA claim.
            self.assertRegex(text, r"radius|unspecified")
            self.assertNotRegex(text, r"\b\d+(\.\d+)?\s*ha\b")
        self.assertEqual(cov.area_ha_claims, ())

    def test_parcel_claim_requires_the_sensor_itself_to_declare_area(self):
        cov = has_calibrated_coverage(sensor_projection_rows(), PARCEL, AT)
        self.assertEqual(cov.level, CoverageLevel.PARCEL_REPORTED)
        self.assertEqual(cov.area_ha_claims, (0.4,))
        for text in cov.footprint_texts:
            if "parcel-support" in text:
                self.assertIn("sensor-reported", text)

    def test_uncalibrated_sensor_never_earns_any_claim(self):
        rows = sensor_projection_rows()
        uncertified = [r for r in rows if "uncertified" in r["sensor_iri"]]
        cov = has_calibrated_coverage(uncertified, PARCEL, AT)
        self.assertEqual(cov.level, CoverageLevel.NONE)
        self.assertEqual(cov.excluded[0]["reason"], "no-calibration-activity")

    def test_expired_certificate_excluded_with_named_reason(self):
        rows = sensor_projection_rows()
        expired = [r for r in rows if "expired" in r["sensor_iri"]]
        cov = has_calibrated_coverage(expired, PARCEL, AT)
        self.assertEqual(cov.level, CoverageLevel.NONE)
        self.assertEqual(cov.excluded[0]["reason"], "calibration-expired")

    def test_foreign_parcel_link_excluded_and_self_consistent(self):
        rows = sensor_projection_rows()
        foreign = [r for r in rows if "other-parcel" in r["sensor_iri"]]
        cov_home = has_calibrated_coverage(foreign, PARCEL, AT)
        self.assertEqual(cov_home.level, CoverageLevel.NONE)
        self.assertEqual(cov_home.excluded[0]["reason"], "no-parcel-link")
        # The SAME row honestly earns its claims for ITS OWN parcel.
        cov_there = has_calibrated_coverage(foreign, FOREIGN, AT)
        self.assertEqual(cov_there.level, CoverageLevel.PROBE_FOOTPRINT)

    def test_advice_support_carries_earned_rungs_and_exclusion_trail(self):
        advice = irrigation_advisory(
            ROWS, reading=_reading(), sensor_rows=sensor_projection_rows(),
            parcel=PARCEL, at=AT,
        )
        text = advice.support.render()
        self.assertIn("grid-support (native 5 km)", text)
        self.assertIn("parcel-support", text)
        self.assertIn("sensor-reported 0.4 ha", text)
        self.assertIn("no-parcel-link", text)  # the trail is published
        self.assertIn("calibration-expired", text)

    def test_no_parcel_argument_means_no_sensor_claims_possible(self):
        advice = irrigation_advisory(
            ROWS, reading=_reading(), sensor_rows=sensor_projection_rows(), at=AT
        )
        self.assertEqual(advice.coverage.level, CoverageLevel.NONE)
        # The HECTARE word never appears in a no-sensor-story output.
        self.assertNotIn("ha coverage", advice.support.render())


class ProbeVsGridDivergenceTests(unittest.TestCase):
    def test_fresh_probe_rides_along_without_touching_the_grid_number(self):
        advice = irrigation_advisory(
            ROWS, reading=_reading(), sensor_rows=sensor_projection_rows(),
            parcel=PARCEL, at=AT,
        )
        grid_alone = irrigation_advisory(ROWS, reading=_reading(), at=AT)
        self.assertIsNotNone(advice.probe_divergence)
        self.assertAlmostEqual(
            advice.net_irrigation_requirement_mm,
            grid_alone.net_irrigation_requirement_mm,
        )  # v0: the probe is evidence, never a rewriter of the number
        self.assertIn("footprint is the probe, not the parcel",
                      advice.probe_divergence["assumption"])
        # and the reconciliation duty is stamped onto the support notes
        self.assertTrue(
            any("reconciled by the human signatory" in note
                for note in advice.support.notes)
        )


class GapPathsTests(unittest.TestCase):
    def test_no_rows_gap(self):
        with self.assertRaises(AgronomyGap) as ctx:
            irrigation_advisory([], reading=_reading(), at=AT)
        self.assertEqual(ctx.exception.gap, "no-usable-rows")

    def test_missing_stage_gap_suggests_the_producer(self):
        with self.assertRaises(AgronomyGap) as ctx:
            irrigation_advisory(_window_rows(), reading=None, at=AT)
        self.assertEqual(ctx.exception.gap, "missing-stage")
        self.assertIn("phenology_reading", ctx.exception.remediation)

    def test_missing_numeric_field_names_row_and_field(self):
        broken = [dict(row) for row in _window_rows()]
        broken[0] = {**broken[0], "eto_mm": None}
        with self.assertRaises(AgronomyGap) as ctx:
            irrigation_advisory(broken, reading=_reading(), at=AT)
        self.assertEqual(ctx.exception.gap, "malformed-row")
        self.assertTrue(any("eto_mm" in m for m in ctx.exception.missing))

    def test_naive_at_refused(self):
        with self.assertRaises(ValueError):
            irrigation_advisory(_window_rows(), reading=_reading(),
                                at=datetime(2026, 8, 10, 4, 0))


class StampTests(unittest.TestCase):
    def test_stamped_with_config_source_and_use_class(self):
        advice = irrigation_advisory(
            ROWS, reading=_reading(), sensor_rows=sensor_projection_rows(),
            parcel=PARCEL, at=AT,
        )
        payload = advice.to_payload()
        self.assertEqual(payload["use_class"], "field-ops")
        self.assertEqual(payload["config_version"], CONFIG_VERSION)
        self.assertIn("VERIFY [FAO-56]", payload["source_note"])
        self.assertIn("VERIFY [FAO-56]", advice.support.render())

    def test_freshness_window_is_declared(self):
        from farm_ontology.agronomy.irrigation import SENSOR_FRESHNESS

        self.assertEqual(SENSOR_FRESHNESS, timedelta(hours=72))


if __name__ == "__main__":
    unittest.main()
