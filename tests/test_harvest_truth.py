"""Harvest-truth intake tests (Sprint-X1, task-18): parse → store →
self-score → teaser. Fixtures synthetic; season context from the
committed fieldtest capture; all offline."""

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from farm_ontology.agronomy.common import AgronomyGap
from farm_ontology.fieldtest.harness import adapt_fixture, load_site_fixture
from farm_ontology.fieldtest.sites import get_site
from farm_ontology.harvest_truth import (
    HIT_TOLERANCE_DAYS,
    TEMPLATE_ID,
    blank_template,
    build_harvest_observation,
    intake_harvest_truth,
    landing_teaser,
    parse_template,
    predicted_stage_crossing,
    score_weigh_date_against_model,
)
from farm_ontology.store import Store
from farm_ontology.timeutil import parse_time

ROOT = Path(__file__).resolve().parents[1]
HARVEST_FIXTURES = ROOT / "fixtures" / "harvest"

AT = datetime(2026, 10, 1, 2, 0, tzinfo=timezone.utc)   # after the HIT visit
AT_MISS = datetime(2026, 10, 26, 2, 0, tzinfo=timezone.utc)  # after the MISS visit
SOWING = parse_time("2026-05-20T09:00:00+09:00")  # Biratori 2026 default
PARCEL = "observation/boundary/demo-not-a-real-farm"


def _load(name: str) -> dict:
    doc = json.loads((HARVEST_FIXTURES / name).read_text(encoding="utf-8"))
    doc.pop("_readme", None)
    doc.pop("_version", None)
    return doc


def _season_rows() -> list[dict]:
    fixture = load_site_fixture(get_site("biratori-hidaka"))
    return adapt_fixture(fixture)["phenology_rows"]


class ParseTests(unittest.TestCase):
    def test_blank_template_refuses_with_missing_parcel_first(self):
        with self.assertRaises(AgronomyGap) as ctx:
            parse_template(blank_template())
        self.assertEqual(ctx.exception.gap, "missing-parcel")

    def test_parcel_but_nothing_witnessed_is_empty_truth(self):
        bundle = blank_template()
        bundle["parcel_iri"] = PARCEL
        bundle["collection_date"] = "2026-09-30"
        with self.assertRaises(AgronomyGap) as ctx:
            parse_template(bundle)
        self.assertEqual(ctx.exception.gap, "empty-truth")
        self.assertIn("ONE evidence item", ctx.exception.remediation)

    def test_wrong_or_missing_template_id_refused(self):
        bundle = _load("founder-filled-hit.json")
        bundle["template"] = "harvest-truth-v0"
        with self.assertRaises(AgronomyGap) as ctx:
            parse_template(bundle)
        self.assertEqual(ctx.exception.gap, "unknown-template")
        self.assertIn("founder-template-blank", ctx.exception.remediation)

    def test_hit_fixture_parses_with_every_witness_kind(self):
        doc = parse_template(_load("founder-filled-hit.json"))
        kinds = {fact.kind for fact in doc.witnessed}
        self.assertEqual(
            kinds,
            {"weigh-ticket", "moisture", "grade-certificate", "photos",
             "gps-pins"},
        )
        self.assertTrue(doc.dictated_over_phone)
        self.assertTrue(doc.stated_as_recall)
        self.assertEqual(doc.gross_weight_kg, 4820.0)
        self.assertEqual(doc.weighed_at.date().isoformat(), "2026-09-30")

    def test_mass_without_weighed_at_refused(self):
        bundle = _load("founder-filled-hit.json")
        bundle["weigh_ticket"]["weighed_at"] = None
        with self.assertRaises(AgronomyGap) as ctx:
            parse_template(bundle)
        self.assertEqual(ctx.exception.gap, "malformed-truth-row")
        self.assertIn("weigh_ticket.weighed_at", ctx.exception.missing[0])

    def test_moisture_without_instrument_refused(self):
        bundle = _load("founder-filled-hit.json")
        bundle["moisture"]["measured_with"] = None
        with self.assertRaises(AgronomyGap) as ctx:
            parse_template(bundle)
        self.assertEqual(ctx.exception.gap, "malformed-truth-row")
        self.assertIn("moisture.measured_with", ctx.exception.missing[0])

    def test_impossible_moisture_refused(self):
        bundle = _load("founder-filled-hit.json")
        bundle["moisture"]["percent"] = 140.0
        with self.assertRaises(AgronomyGap):
            parse_template(bundle)

    def test_negative_mass_refused(self):
        bundle = _load("founder-filled-hit.json")
        bundle["weigh_ticket"]["gross_weight_kg"] = -5.0
        with self.assertRaises(AgronomyGap):
            parse_template(bundle)

    def test_unknown_keys_surfaced_not_silently_dropped(self):
        bundle = _load("founder-filled-hit.json")
        bundle["yasai_counter"] = 3  # dictated noise
        doc = parse_template(bundle)
        self.assertIn("yasai_counter", doc.unknown_keys_ignored)


class StoreIntakeTests(unittest.TestCase):
    def test_hit_intake_stores_mass_observation_under_store_law(self):
        store = Store()
        outcome = intake_harvest_truth(
            store, _load("founder-filled-hit.json"), at=AT,
            season_rows=_season_rows(), sowing=SOWING,
        )
        self.assertTrue(outcome.observation_result.ok)
        stored = store.observations[outcome.observation_result.iri]
        self.assertEqual(stored.result.unit_iri.split("/")[-1], "KiloGM")
        self.assertEqual(
            stored.result.quantity_kind_iri.split("/")[-1], "Mass"
        )
        self.assertEqual(stored.use_class, "Screening")
        self.assertFalse(stored.licence.permits_financial_use)
        self.assertEqual(stored.feature_kind, "parcel-unregistered")
        self.assertTrue(outcome.teaser_line)  # season context supplied

    def test_dictation_is_typed_as_farmer_recall(self):
        store = Store()
        outcome = intake_harvest_truth(
            store, _load("founder-filled-hit.json"), at=AT
        )
        stored = store.observations[outcome.observation_result.iri]
        self.assertEqual(stored.procedure.rsplit("/", 1)[-1], "farmer-recall")
        self.assertTrue(stored.stated_as_recall)

    def test_self_typed_is_harvest_intake_not_recall(self):
        bundle = _load("founder-filled-miss.json")  # dictated_over_phone false
        store = Store()
        outcome = intake_harvest_truth(store, bundle, at=AT_MISS)
        stored = store.observations[outcome.observation_result.iri]
        self.assertEqual(stored.procedure.rsplit("/", 1)[-1], "harvest-intake")
        self.assertFalse(stored.stated_as_recall)

    def test_replay_same_store_is_refused_new_store_replays_same_iri(self):
        bundle = _load("founder-filled-hit.json")
        first = Store()
        outcome_one = intake_harvest_truth(first, dict(bundle), at=AT)
        outcome_dup = intake_harvest_truth(first, dict(bundle), at=AT)
        self.assertFalse(outcome_dup.observation_result.ok)  # R-parallel
        self.assertEqual(
            outcome_dup.observation_result.refusal.rule_id, "R-parallel"
        )
        second = Store()
        outcome_two = intake_harvest_truth(second, dict(bundle), at=AT)
        self.assertEqual(
            outcome_one.observation_result.iri,
            outcome_two.observation_result.iri,
        )  # deterministic, content-bound identity

    def test_no_mass_bundle_stored_with_explicit_unsupported_statement(self):
        bundle = _load("founder-filled-hit.json")
        bundle["weigh_ticket"] = {
            "ticket_number": None, "gross_weight_kg": None,
            "weighed_at": None, "scale_description": None,
        }
        store = Store()
        outcome = intake_harvest_truth(store, bundle, at=AT_MISS)
        self.assertTrue(outcome.observation_result.ok)
        stored = store.observations[outcome.observation_result.iri]
        self.assertIsNone(stored.result)
        self.assertIsNotNone(stored.unsupported_reason)
        self.assertIn("moisture", stored.unsupported_reason)


class PinsToPolygonTests(unittest.TestCase):
    def test_three_pins_start_the_first_boundary_version(self):
        store = Store()
        outcome = intake_harvest_truth(
            store, _load("founder-filled-hit.json"), at=AT
        )
        self.assertIsNotNone(outcome.boundary_result)
        self.assertTrue(outcome.boundary_result.ok)
        boundary = store.boundaries[
            outcome.boundary_result.iri
        ]
        self.assertEqual(boundary.tenure, "unknown")  # stays unknown, honestly
        self.assertFalse(boundary.accuracy_unknown)
        self.assertAlmostEqual(boundary.accuracy_m, 4.2)  # worst stated pin
        # Typed-decimal contract: JSON numbers degrade to shortest
        # round-trip repr (142.407180 → 142.40718), so the PROVEN floor
        # here is 5; strings preserve the typed 6 (next test).
        self.assertEqual(boundary.coordinate_decimals, 5)
        self.assertEqual(boundary.digitising_method, "gps-corner-pins-phone")
        self.assertTrue(boundary.wkt.startswith("POLYGON (("))

    def test_string_pins_keep_typed_precision(self):
        bundle = _load("founder-filled-hit.json")
        bundle["gps_pins"] = [
            {"corner": "NW", "lat": "42.701852", "lon": "142.407121",
             "accuracy_m": 3.5},
            {"corner": "NE", "lat": "42.701994", "lon": "142.407894",
             "accuracy_m": 4.2},
            {"corner": "SW", "lat": "42.701113", "lon": "142.407180",
             "accuracy_m": 3.9},
        ]
        store = Store()
        outcome = intake_harvest_truth(store, bundle, at=AT)
        boundary = store.boundaries[outcome.boundary_result.iri]
        self.assertEqual(boundary.coordinate_decimals, 6)  # typed, provably

    def test_pin_without_accuracy_makes_whole_version_unknown(self):
        store = Store()
        outcome = intake_harvest_truth(store, _load("founder-filled-miss.json"), at=AT_MISS)
        boundary = store.boundaries[outcome.boundary_result.iri]
        self.assertTrue(boundary.accuracy_unknown)
        self.assertIsNone(boundary.accuracy_m)
        self.assertIn("lacked a stated", boundary.accuracy_note)

    def test_two_pins_make_no_boundary_attempt(self):
        bundle = _load("founder-filled-hit.json")
        bundle["gps_pins"] = bundle["gps_pins"][:2]
        store = Store()
        outcome = intake_harvest_truth(store, bundle, at=AT_MISS)
        self.assertIsNone(outcome.boundary_result)
        self.assertTrue(outcome.observation_result.ok)  # truth still stored

    def test_collinear_pins_refused_not_faked(self):
        bundle = _load("founder-filled-hit.json")
        base_lat = 42.70
        bundle["gps_pins"] = [
            {"corner": "a", "lat": base_lat, "lon": 142.40, "accuracy_m": 3.0},
            {"corner": "b", "lat": base_lat, "lon": 142.41, "accuracy_m": 3.0},
            {"corner": "c", "lat": base_lat, "lon": 142.42, "accuracy_m": 3.0},
        ]
        with self.assertRaises(AgronomyGap) as ctx:
            intake_harvest_truth(Store(), bundle, at=AT)
        self.assertEqual(ctx.exception.gap, "pins-degenerate")


class SelfScoringTests(unittest.TestCase):
    def test_predictable_crossing_then_hit_fixture(self):
        rows = _season_rows()
        crossing_date, cumulative = predicted_stage_crossing(
            rows, sowing=SOWING, stage="R8"
        )
        # Crossing-day granularity: the banked GDD overshoots the
        # threshold by whatever the crossing day contributed (≤ cap 20).
        self.assertGreaterEqual(cumulative, 1050.0)
        self.assertLess(cumulative, 1070.0)
        hit = score_weigh_date_against_model(
            rows, sowing=SOWING,
            actual_weigh_date=parse_time("2026-09-30T11:20:00+09:00"),
            parcel_iri=PARCEL,
        )
        self.assertEqual(hit.predicted_r8_date, crossing_date.isoformat())
        self.assertEqual(hit.outcome, "hit")
        self.assertTrue(hit.plausible_order)
        self.assertEqual(hit.cultivar_profile, "hokkaido-short")

    def test_miss_fixture_scores_late_harvest_with_gdd_head_room(self):
        row = score_weigh_date_against_model(
            _season_rows(), sowing=SOWING,
            actual_weigh_date=parse_time("2026-10-25T15:45:00+09:00"),
            parcel_iri=PARCEL,
        )
        self.assertEqual(row.outcome, "miss")
        self.assertGreater(row.delta_days, HIT_TOLERANCE_DAYS)
        self.assertGreater(row.delta_gdd_days, 0.0)
        self.assertTrue(row.plausible_order)

    def test_premature_weigh_flags_the_order_problem(self):
        row = score_weigh_date_against_model(
            _season_rows(), sowing=SOWING,
            actual_weigh_date=parse_time("2026-08-20T10:00:00+09:00"),
            parcel_iri=PARCEL,
        )
        self.assertEqual(row.outcome, "miss")
        self.assertFalse(row.plausible_order)
        self.assertTrue(any("moisture%" in note for note in row.notes))

    def test_tolerance_boundary_is_inclusive(self):
        rows = _season_rows()
        crossing, _ = predicted_stage_crossing(
            rows, sowing=SOWING, stage="R8"
        )
        edge = datetime.combine(
            crossing, datetime.min.time(), tzinfo=timezone.utc
        ).replace(hour=12)
        boundary_row = score_weigh_date_against_model(
            rows, sowing=SOWING, actual_weigh_date=edge,
            tolerance_days=0,
        )
        self.assertEqual(boundary_row.delta_days, 0)
        self.assertEqual(boundary_row.outcome, "hit")

    def test_season_rows_too_short_refuse_instead_of_extrapolating(self):
        with self.assertRaises(AgronomyGap) as ctx:
            score_weigh_date_against_model(
                _season_rows()[:40],  # through early July only
                sowing=SOWING,
                actual_weigh_date=parse_time("2026-09-30T11:20:00+09:00"),
            )
        self.assertEqual(ctx.exception.gap, "stage-never-reached")
        self.assertIn("no date is extrapolated", ctx.exception.args[0])

    def test_teaser_line_shape(self):
        row = score_weigh_date_against_model(
            _season_rows(), sowing=SOWING,
            actual_weigh_date=parse_time("2026-09-30T11:20:00+09:00"),
            parcel_iri=PARCEL,
        )
        teaser = landing_teaser(row)
        self.assertIn("prediction vs actual", teaser)
        self.assertIn(f"model R8 {row.predicted_r8_date}", teaser)
        self.assertIn("weigh 2026-09-30", teaser)
        self.assertIn("HIT", teaser)
        self.assertIn("engine agronomy-engine-v0", teaser)


class IntakeWithoutSeasonContextTests(unittest.TestCase):
    def test_truth_stored_and_scoring_honestly_absent(self):
        store = Store()
        outcome = intake_harvest_truth(
            store, _load("founder-filled-hit.json"), at=AT
        )
        self.assertIsNone(outcome.validation_row)
        self.assertIsNone(outcome.teaser_line)
        self.assertTrue(outcome.observation_result.ok)
        self.assertIn("validation", outcome.to_payload())

    def test_outcome_payload_refusal_path_is_public(self):
        store = Store()
        bundle = _load("founder-filled-hit.json")
        intake_harvest_truth(store, bundle, at=AT)
        again = intake_harvest_truth(store, _load("founder-filled-hit.json"), at=AT)
        payload = again.to_payload()
        self.assertFalse(payload["observation_ok"])
        self.assertEqual(payload["refusal"]["rule_id"], "R-parallel")


if __name__ == "__main__":
    unittest.main()


