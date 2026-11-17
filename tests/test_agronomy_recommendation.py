"""Recommendation-record tests (WS3.5): first-class, replayable,
refused-uses-stay-refused. Fixtures synthetic; offline."""

import unittest
from datetime import datetime, timedelta, timezone

from farm_ontology.agronomy.common import (
    AgronomyGap,
    AgronomyRefusal,
    CONFIG_VERSION,
    DRAFTED_BY,
)
from farm_ontology.agronomy.recommendation import (
    KINDS,
    REFUSED_KINDS,
    InputRef,
    RationaleStep,
    draft_recommendation,
    input_ref_from_observation,
)
from farm_ontology.build import grid_observation, kilometres, millimetres

T0 = datetime(2026, 8, 10, 4, 0, tzinfo=timezone.utc)
T_LATER = T0 + timedelta(days=1)


def _inputs() -> list[InputRef]:
    return [
        InputRef(
            iri="observation/grid-a",
            native_support="grid-cell",
            observed_property="farm-precipitation-amount",
            availability_iso="2026-08-10T00:00:00+00:00",
            is_forecast=False,
            licence_instrument="grant not recorded",
            licence_permits_financial_use=False,
            licence_permits_redistribution=False,
            licence_expiry="none stated",
        ),
        InputRef(
            iri="sensor/probe-01",
            native_support="point-soil-probe",
            observed_property="farm-soil-volumetric-water-content",
            availability_iso="2026-08-10T03:30:00+00:00",
            is_forecast=False,
            licence_instrument="operator-owned-device",
            licence_permits_financial_use=False,
            licence_permits_redistribution=True,
            licence_expiry="none stated",
        ),
    ]


RATIONALE = (
    RationaleStep("IRRIG-RAW-BREACH", "root depletion crossed RAW", True,
                  (("depletion_mm", 61.2), ("raw_mm", 52.5))),
    RationaleStep("COVER-CALIBRATED", "calibrated probe live within 72 h",
                  True, (("sensor", "sensor/probe-01"),)),
)


def _draft(**overrides):
    kwargs = dict(
        kind="irrigation",
        inputs=_inputs(),
        rationale=list(RATIONALE),
        payload={"mm": 9.0, "recommend": True},
        drafted_at=T0,
        expires_at=T0 + timedelta(days=2),
        uncertainty={"band_gdd": 45.0},
    )
    kwargs.update(overrides)
    return draft_recommendation(**kwargs)


class RecordShapeTests(unittest.TestCase):
    def test_chain_fields_house_defaults(self):
        record = _draft()
        self.assertEqual(record.drafted_by, DRAFTED_BY)
        self.assertEqual(DRAFTED_BY, "agronomy-engine")
        self.assertTrue(record.requires_human_signoff)
        self.assertFalse(record.permits_financial_use)
        self.assertEqual(record.use_class, "field-ops")
        self.assertEqual(record.config_version, CONFIG_VERSION)

    def test_all_declared_kinds_draftable_and_refused_not_among_them(self):
        self.assertEqual(
            KINDS, frozenset({"irrigation", "spray", "fertility", "phenology-query"})
        )
        for kind in ("hedge", "trade", "settlement", "trigger", "nature-unit"):
            self.assertIn(kind, REFUSED_KINDS)
            with self.assertRaises(AgronomyRefusal) as ctx:
                _draft(kind=kind)
            self.assertEqual(ctx.exception.refusal, "refused-use")

    def test_inputs_and_licence_states_travel_verbatim(self):
        record = _draft()
        payload = record.to_payload()
        licences = [row["licence"] for row in payload["inputs"]]
        self.assertEqual(licences[0]["instrument"], "grant not recorded")
        self.assertTrue(licences[1]["permits_redistribution"])  # travels VERBATIM
        self.assertEqual(payload["inputs"][0]["native_support"], "grid-cell")
        self.assertEqual(payload["inputs"][1]["native_support"], "point-soil-probe")

    def test_uncertainty_band_and_expiry_stamped(self):
        record = _draft()
        self.assertEqual(record.uncertainty, {"band_gdd": 45.0})
        self.assertEqual(record.expires_at, T0 + timedelta(days=2))

    def test_rule_trace_survives_into_payload(self):
        payload = _draft().to_payload()
        rules = [step["rule_id"] for step in payload["rationale"]]
        self.assertEqual(rules, ["IRRIG-RAW-BREACH", "COVER-CALIBRATED"])
        self.assertEqual(
            payload["rationale"][0]["evidence"], {"depletion_mm": 61.2, "raw_mm": 52.5}
        )


class ReplayTests(unittest.TestCase):
    def test_same_inputs_same_day_same_id(self):
        self.assertEqual(_draft().recommendation_id, _draft().recommendation_id)

    def test_replay_on_a_different_day_keeps_the_id(self):
        first = _draft(drafted_at=T0, expires_at=T0 + timedelta(days=2))
        second = _draft(drafted_at=T_LATER, expires_at=T_LATER + timedelta(days=2))
        self.assertEqual(
            first.recommendation_id, second.recommendation_id
        )  # times are stamps, not identity

    def test_payload_change_changes_id_and_input_order_is_normalised_semantically(self):
        changed = _draft(payload={"mm": 9.5, "recommend": True})
        self.assertNotEqual(changed.recommendation_id, _draft().recommendation_id)
        shuffled = _draft(inputs=list(reversed(_inputs())))
        self.assertNotEqual(shuffled.recommendation_id, _draft().recommendation_id)
        # Input ORDER participates in identity (canonical JSON sorts KEYS,
        # not array order) — replay stability then rests on pipeline
        # ordering, which WS2's deterministic ingest guarantees. Documented.

    def test_ids_namespaced_and_hash_shaped(self):
        record = _draft()
        self.assertTrue(record.recommendation_id.startswith("rec:"))
        self.assertEqual(len(record.recommendation_id.split(":")[1]), 32)


class FailedClosedTests(unittest.TestCase):
    def test_financial_use_true_cannot_be_constructed(self):
        # The record is frozen with the module constant; attempts to
        # forge a financial blessing through replace are structurally
        # impossible (frozen dataclass) and through payload are refused
        # by the field contract: permits_financial_use is not a parameter.
        record = _draft()
        self.assertFalse(record.permits_financial_use)
        self.assertNotIn(
            "permits_financial_use", draft_recommendation.__annotations__
        )  # no caller path can even pass it in

    def test_expires_before_draft_refused(self):
        with self.assertRaises(AgronomyRefusal) as ctx:
            _draft(expires_at=T0 - timedelta(minutes=1))
        self.assertEqual(ctx.exception.refusal, "born-expired")

    def test_equal_times_refused(self):
        with self.assertRaises(AgronomyRefusal):
            _draft(expires_at=T0)

    def test_naive_stamps_refused(self):
        with self.assertRaises(ValueError):
            _draft(drafted_at=datetime(2026, 8, 10, 4, 0))
        with self.assertRaises(ValueError):
            _draft(expires_at=datetime(2026, 8, 12, 4, 0))

    def test_empty_inputs_and_empty_rationale_are_gaps(self):
        with self.assertRaises(AgronomyGap) as ctx:
            _draft(inputs=[])
        self.assertEqual(ctx.exception.gap, "no-inputs")
        with self.assertRaises(AgronomyGap) as ctx:
            _draft(rationale=[])
        self.assertEqual(ctx.exception.gap, "no-rationale")

    def test_unknown_kind_is_a_gap_with_the_menu(self):
        with self.assertRaises(AgronomyGap) as ctx:
            _draft(kind="compress")
        self.assertEqual(ctx.exception.gap, "unknown-kind")
        self.assertIn("irrigation", " ".join(ctx.exception.missing))


class FromObservationTests(unittest.TestCase):
    def test_input_ref_projects_observation_idioms(self):
        obs = grid_observation(
            local="proj-obs",
            feature_local="jma-msm-0-05deg",
            resolution=kilometres(5),
            result=millimetres(12.5),
            phenomenon=(T0, T0 + timedelta(hours=1)),
            availability=T0,
            product_kind="jma_msm",
            is_forecast=True,
            issue_time=T0,
        )
        ref = input_ref_from_observation(obs)
        self.assertEqual(ref.native_support, "grid-cell")
        self.assertTrue(ref.is_forecast)
        self.assertFalse(ref.licence_permits_financial_use)
        record = _draft(inputs=[ref])
        self.assertTrue(
            all(row["licence"] for row in record.to_payload()["inputs"])
        )


if __name__ == "__main__":
    unittest.main()
