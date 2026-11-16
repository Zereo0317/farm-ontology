import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.build import mint
from farm_ontology.identity import AT, load_synthetic_pilot
from farm_ontology.model import BoundaryVersion, Holding
from farm_ontology.namespaces import MAIZE_AGROVOC
from farm_ontology.store import Store


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.store = Store()
        self.pilot = load_synthetic_pilot(self.store)

    def test_split_and_merge_keep_the_previous_iri(self):
        self.assertIn(self.pilot.split_parent, self.store.boundaries)
        self.assertNotEqual(self.pilot.split_a, self.pilot.split_parent)
        self.assertNotEqual(self.pilot.split_b, self.pilot.split_parent)
        self.assertEqual(
            self.store.boundaries[self.pilot.split_a].predecessors,
            (self.pilot.split_parent,),
        )
        self.assertIn(self.pilot.merge_a, self.store.boundaries)
        self.assertIn(self.pilot.merge_b, self.store.boundaries)
        self.assertEqual(
            self.store.boundaries[self.pilot.merged].predecessors,
            (self.pilot.merge_a, self.pilot.merge_b),
        )
        self.assertNotEqual(self.pilot.parcel, self.store.boundaries[self.pilot.parcel].geometry_iri)

    def test_unknown_tenure_stays_unknown_and_parties_differ(self):
        unknown = self.store.boundaries[self.pilot.unknown_tenure]
        self.assertEqual(unknown.tenure, "unknown")
        self.assertIsNone(unknown.tenure_source)
        customary = self.store.boundaries[self.pilot.customary]
        self.assertEqual(customary.tenure, "customary")
        self.assertEqual(customary.tenure_source, "synthetic-customary-statement")
        self.assertNotEqual(self.pilot.operator, self.pilot.right_holder)
        titled = mint("boundary", "tenure-titled-no-source")
        self.assertNotIn(titled, self.store.boundaries)
        self.assertTrue(
            any(item.rule_id == "R-tenure" for item in self.store.refusals)
        )
        self.assertTrue(
            any(
                item.rule_id == "R-tenure" and "not copied" in item.attempted_change
                for item in self.store.refusals
            )
        )

    def test_eudr_claim_needs_metres_not_six_decimals(self):
        phone = self.store.boundaries[self.pilot.phone]
        self.assertEqual(phone.coordinate_decimals, 6)
        self.assertTrue(phone.accuracy_unknown)
        claimed = self.store.record_eudr_syntax(
            phone.iri,
            commodity="soya",
            production_date=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )
        self.assertFalse(claimed)
        self.assertFalse(self.store.boundaries[phone.iri].eudr_syntactic_claim)
        surveyed = self.pilot.surveyed
        self.assertTrue(
            self.store.record_eudr_syntax(
                surveyed,
                commodity="coffee",
                production_date=datetime(2024, 6, 1, tzinfo=timezone.utc),
            )
        )
        self.assertTrue(self.store.boundaries[surveyed].eudr_syntactic_claim)

    def test_mix_overlap_and_survey_point(self):
        mixed = self.store.croppings[self.pilot.mixed]
        self.assertEqual(mixed.mix, "mixed")
        self.assertEqual(len(mixed.crops), 2)
        self.assertNotIn(mint("cropping", "mono-two-crops"), self.store.croppings)
        self.assertTrue(any(item.rule_id == "R-mix" for item in self.store.refusals))
        reading = self.store.distinct_plots_reading(
            self.pilot.overlap_a,
            self.pilot.overlap_b,
            self.pilot.season,
            at=AT,
        )
        self.assertFalse(reading.ok)
        self.assertEqual(reading.refusal.rule_id, "R-overlap")
        overlap = self.store.overlaps[self.pilot.overlap]
        self.assertGreater(overlap.area_ha, 0)
        self.assertEqual(overlap.method, "equirectangular-box-overlap")
        self.assertIsNone(overlap.disposition)
        survey = mint("boundary", "household-survey-point")
        self.assertNotIn(survey, self.store.boundaries)
        self.assertTrue(self.store.survey_points)
        self.assertTrue(
            all(point.iri not in self.store.boundaries for point in self.store.survey_points.values())
        )

    def test_no_real_person_and_holding_is_not_a_polygon(self):
        self.assertNotIn("wkt", Holding.__dataclass_fields__)
        for party in self.store.parties.values():
            self.assertTrue(party.label.startswith("synthetic-"))
            self.assertFalse(party.personal_data)
        for boundary in self.store.boundaries.values():
            self.assertFalse(boundary.personal_data)
        self.assertNotIn(mint("season", "calendar-year-2024"), self.store.seasons)
        link = self.store.add_label(
            local_iri=mint("crop", "maize"),
            concept_iri=MAIZE_AGROVOC,
            relation="skos:exactMatch",
            language="en",
            extra_grant=False,
            at=AT,
        )
        self.assertTrue(link.ok)
        same = self.store.add_label(
            local_iri=mint("crop", "maize"),
            concept_iri=MAIZE_AGROVOC,
            relation="owl:equivalentClass",
            language="en",
            extra_grant=False,
            at=AT,
        )
        self.assertFalse(same.ok)
        self.assertEqual(same.refusal.rule_id, "R-agrovoc")
        forced = BoundaryVersion(
            **{**self.store.boundaries[self.pilot.phone].__dict__, "iri": mint("boundary", "forced-eudr"), "eudr_syntactic_claim": True}
        )
        forced_result = self.store.add_boundary(forced, at=AT)
        self.assertFalse(forced_result.ok)
        self.assertEqual(forced_result.refusal.rule_id, "R-accuracy")


if __name__ == "__main__":
    unittest.main()
