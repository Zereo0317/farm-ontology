"""WS3 acceptance tests: gap-or-refuse EVERYWHERE, refusal honesty, and
the fixture-driven end-to-end advisory that matches the roadmap table."""

import unittest
from datetime import datetime, timedelta, timezone

from farm_ontology.agronomy.common import AgronomyGap, AgronomyRefusal
from farm_ontology.agronomy.fertility import soil_fertility_note
from farm_ontology.agronomy.irrigation import (
    CoverageLevel,
    irrigation_advisory,
)
from farm_ontology.agronomy.phenology import phenology_reading
from farm_ontology.agronomy.recommendation import (
    InputRef,
    draft_recommendation,
    RationaleStep,
)
from farm_ontology.agronomy.spray_windows import scan_spray_windows
from tests.agronomy_fixtures import (
    daily_season_rows,
    hourly_rows,
    sensor_projection_rows,
    soil_rows,
)

PARCEL = "observation/boundary/demo-not-a-real-farm"
AT_IRRIGATION = datetime(2026, 8, 10, 4, 0, tzinfo=timezone.utc)
AT_SPRAY = datetime(2026, 8, 10, 4, 0, tzinfo=timezone.utc)
AT_FERTILITY = datetime(2026, 11, 18, 4, 0, tzinfo=timezone.utc)
SOWING = datetime(2026, 5, 20, tzinfo=timezone.utc)


def _grid_input() -> InputRef:
    return InputRef(
        iri="observation/fixture-jma-msm-step",
        native_support="grid-cell",
        observed_property="farm-precipitation-amount",
        availability_iso="2026-08-10T00:00:00+00:00",
        is_forecast=False,
        licence_instrument="grant not recorded",
        licence_permits_financial_use=False,
        licence_permits_redistribution=False,
        licence_expiry="none stated",
    )


class MissingInputNeverSilentTests(unittest.TestCase):
    """Roadmap WS3 acceptance: missing-input paths return explicit gaps."""

    def test_phenology_without_anchor_publishes_a_gap_object(self):
        with self.assertRaises(AgronomyGap) as ctx:
            phenology_reading(daily_season_rows(), sowing=None, emergence=None)
        gap = ctx.exception.as_gap()
        payload = gap.to_payload()
        self.assertEqual(payload["gap"], "missing-sowing-anchor")
        self.assertIn("sowing", payload["missing"])

    def test_irrigation_without_stage_never_guesses_kcb(self):
        with self.assertRaises(AgronomyGap) as ctx:
            irrigation_advisory(daily_season_rows()[:30], reading=None,
                                at=AT_IRRIGATION)
        self.assertEqual(ctx.exception.gap, "missing-stage")

    def test_irrigation_without_rows_publishes_gap_object(self):
        reading = phenology_reading(
            daily_season_rows(), sowing=SOWING, emergence=None
        )
        with self.assertRaises(AgronomyGap) as ctx:
            irrigation_advisory([], reading=reading, at=AT_IRRIGATION)
        self.assertEqual(ctx.exception.as_gap().to_payload()["gap"], "no-usable-rows")

    def test_fertility_without_chemistry_enumerates_the_lab_work(self):
        with self.assertRaises(AgronomyGap) as ctx:
            soil_fertility_note([], at=AT_FERTILITY)
        payload = ctx.exception.as_gap().to_payload()
        self.assertEqual(payload["gap"], "needs-soil-chemistry")
        self.assertEqual(len(payload["missing"]), 6)

    def test_spray_without_recent_data_refuses_rather_than_time_travels(self):
        stale = [row for row in hourly_rows() if row["time"] < "2026-08-10T04:00:00+00:00"]
        with self.assertRaises(AgronomyGap) as ctx:
            scan_spray_windows(stale, at=AT_SPRAY)
        self.assertEqual(ctx.exception.gap, "stale-hours")

    def test_unsupported_sensor_story_never_shows_as_parcel_claim(self):
        rows = [row for row in sensor_projection_rows() if "scan-array" not in row["sensor_iri"]]
        cov = irrigation_advisory(
            daily_season_rows(),
            reading=phenology_reading(daily_season_rows(), sowing=SOWING, emergence=None),
            sensor_rows=[
                row for row in rows if "uncertified" in row["sensor_iri"]
            ],
            parcel=PARCEL,
            at=AT_IRRIGATION,
        ).coverage
        self.assertEqual(cov.level, CoverageLevel.NONE)


class RefusedUsesRemainRefusedTests(unittest.TestCase):
    def test_trade_shaped_recommendation_raises_at_construction(self):
        inputs = []  # deliberately minimal
        from farm_ontology.agronomy.recommendation import InputRef

        ref = InputRef(
            iri="observation/grid-a", native_support="grid-cell",
            observed_property=None, availability_iso=None, is_forecast=False,
            licence_instrument="none", licence_permits_financial_use=False,
            licence_permits_redistribution=False, licence_expiry="none stated",
        )
        for kind in ("hedge", "trade", "short", "trigger"):
            with self.assertRaises(AgronomyRefusal):
                draft_recommendation(
                    kind=kind, inputs=[ref],
                    rationale=[RationaleStep("R", "r", True)],
                    payload={}, drafted_at=AT_IRRIGATION,
                    expires_at=AT_IRRIGATION + timedelta(hours=1),
                )

    def test_no_wall_clock_anywhere_deterministic_replays(self):
        rows = daily_season_rows()
        reading = phenology_reading(rows, sowing=SOWING, emergence=None)
        one = irrigation_advisory(rows[:40], reading=reading, at=AT_IRRIGATION)
        two = irrigation_advisory(rows[:40], reading=reading, at=AT_IRRIGATION)
        self.assertEqual(one.to_payload(), two.to_payload())


class FixtureDrivenEndToEndTests(unittest.TestCase):
    def test_full_chain_fixtures_to_signed_recommendation_candidate(self):
        rows = daily_season_rows()
        reading = phenology_reading(rows, sowing=SOWING, emergence=None)
        advice = irrigation_advisory(
            rows, reading=reading, sensor_rows=sensor_projection_rows(),
            parcel=PARCEL, at=AT_IRRIGATION,
        )
        windows, summary = scan_spray_windows(hourly_rows(), at=AT_SPRAY)
        fertility = soil_fertility_note(soil_rows(), at=AT_FERTILITY)

        # Chain the advisory into the record type.
        def _rationale():
            return [
                RationaleStep(
                    "IRRIG-RAW-BREACH" if advice.recommend else "IRRIG-BELOW-RAW",
                    advice.why,
                    True,
                    (("mm", advice.net_irrigation_requirement_mm),),
                )
            ]

        def _payload():
            return {
                "mm": advice.net_irrigation_requirement_mm,
                "recommend": advice.recommend,
                "stage": reading.stage,
                "support": advice.support.render(),
                "coverage": advice.coverage.level,
                "spray_best_verdict": windows[0].verdict if windows else None,
                "spray_unusable_spans": len(summary["unusable_spans"]),
                "fertility_review_required": fertility.review_required,
            }

        def _uncertainty():
            return {
                "stage_band_gdd": reading.uncertainty_gdd,
                "stage": reading.stage,
                "days_band": reading.uncertainty_days,
            }

        record = draft_recommendation(
            kind="irrigation",
            inputs=[_grid_input()],
            rationale=_rationale(),
            payload=_payload(),
            drafted_at=AT_IRRIGATION,
            expires_at=AT_IRRIGATION + timedelta(days=3),
            uncertainty=_uncertainty(),
        )
        payload = record.to_payload()
        self.assertEqual(payload["kind"], "irrigation")
        self.assertFalse(record.permits_financial_use)
        self.assertTrue(record.requires_human_signoff)
        # One chain, one id: the same call again replays identically.
        twin = draft_recommendation(
            kind="irrigation",
            inputs=[_grid_input()],
            rationale=_rationale(),
            payload=_payload(),
            drafted_at=AT_IRRIGATION,
            expires_at=AT_IRRIGATION + timedelta(days=3),
            uncertainty=_uncertainty(),
        )
        self.assertEqual(record.recommendation_id, twin.recommendation_id)


if __name__ == "__main__":
    unittest.main()
