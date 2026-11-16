import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.build import millimetres, mint, tonnes_per_hectare_as_mass
from farm_ontology.identity import load_synthetic_pilot
from farm_ontology.model import ErrorStatement, Party, Quantity
from farm_ontology.namespaces import KIND_LENGTH
from farm_ontology.publish import check_publication, render_fact
from farm_ontology.rules import class_b_blockers
from farm_ontology.store import Store
from tests.support import NOW, sample_grid


class RuleTests(unittest.TestCase):
    def test_units_gaps_recall_and_sensors(self):
        store = Store()
        bad_unit = sample_grid(
            iri=mint("observation", "bare-unit"),
            result=Quantity(1.0, "mm", KIND_LENGTH),
        )
        self.assertEqual(store.add_observation(bad_unit, at=NOW).refusal.rule_id, "R-unit")
        mixed_kind = sample_grid(
            iri=mint("observation", "yield-as-mass"),
            result=tonnes_per_hectare_as_mass(3.0),
        )
        self.assertEqual(store.add_observation(mixed_kind, at=NOW).refusal.rule_id, "R-unit")
        zero = sample_grid(iri=mint("observation", "nodata-zero"), nodata=True, result=millimetres(0))
        self.assertEqual(store.add_observation(zero, at=NOW).refusal.rule_id, "R-zero")
        gap_zero = sample_grid(
            iri=mint("observation", "gap-zero"),
            gap_reason="cloud",
            result=millimetres(0),
        )
        self.assertEqual(store.add_observation(gap_zero, at=NOW).refusal.rule_id, "R-zero")
        gap = sample_grid(
            iri=mint("observation", "cloud-gap"),
            gap_reason="cloud",
            result=None,
            native_resolution=sample_grid().native_resolution,
        )
        self.assertTrue(store.add_observation(gap, at=NOW).ok)
        filled_wrong = sample_grid(
            iri=mint("observation", "filled-raw"),
            product_kind="gap-fill",
            procedure=mint("procedure", "raw-pixel"),
        )
        self.assertEqual(store.add_observation(filled_wrong, at=NOW).refusal.rule_id, "R-gapfill")
        filled = sample_grid(
            iri=mint("observation", "filled"),
            product_kind="gap-fill",
            procedure=mint("procedure", "gap-fill"),
        )
        self.assertTrue(store.add_observation(filled, at=NOW).ok)
        recall_as_cut = sample_grid(
            iri=mint("observation", "recall-as-cut"),
            procedure=mint("procedure", "crop-cut"),
            stated_as_recall=True,
            native_resolution=None,
            feature_of_interest=mint("sample", "recall"),
            feature_kind="admin-unit",
            spatial_support="admin-unit",
        )
        self.assertIn(
            "crop-cut",
            store.add_observation(recall_as_cut, at=NOW).refusal.attempted_change,
        )
        recall = sample_grid(
            iri=mint("observation", "recall"),
            procedure=mint("procedure", "farmer-recall"),
            stated_as_recall=True,
            native_resolution=None,
            feature_of_interest=mint("sample", "recall-ok"),
            feature_kind="admin-unit",
            spatial_support="admin-unit",
        )
        self.assertTrue(store.add_observation(recall, at=NOW).ok)
        self.assertEqual(store.observations[recall.iri].use_class, "Screening")
        claim = sample_grid(
            iri=mint("observation", "hectare-claim"),
            hectare_weather_claim=True,
            native_resolution=None,
            feature_of_interest=mint("sensor", "s1"),
            feature_kind="instrument-point",
            spatial_support="instrument-point",
        )
        self.assertEqual(store.add_observation(claim, at=NOW).refusal.rule_id, "R-sensor")
        instrumented = sample_grid(
            iri=mint("observation", "instrumented"),
            hectare_weather_claim=True,
            native_resolution=None,
            feature_of_interest=mint("sensor", "s1"),
            feature_kind="instrument-point",
            spatial_support="instrument-point",
            sensor_iri=mint("sensor", "s1"),
            calibration_activity=mint("activity", "calibration"),
        )
        self.assertTrue(store.add_observation(instrumented, at=NOW).ok)

    def test_personal_licence_split_sample_and_strip(self):
        store = Store()
        personal = sample_grid(iri=mint("observation", "person"), personal_data=True)
        self.assertEqual(store.add_observation(personal, at=NOW).refusal.rule_id, "R-personal")
        self.assertFalse(
            store.add_party(
                Party(mint("party", "blocked-person"), "operator", "synthetic-blocked", True),
                at=NOW,
            ).ok
        )
        licence = sample_grid().licence.__class__(
            instrument="grant not recorded",
            permits_financial_use=True,
            permits_redistribution=False,
            attribution="none stated",
            purpose="screening",
            territory="Taiwan",
            expiry="none stated",
        )
        financial = sample_grid(iri=mint("observation", "financial"), licence=licence)
        self.assertEqual(store.add_observation(financial, at=NOW).refusal.rule_id, "R-licence")
        cut = mint("observation", "cut-1")
        self.assertEqual(
            store.add_fit(used=(cut,), error_cut=cut, at=NOW).refusal.rule_id,
            "R-split-sample",
        )
        self.assertTrue(store.add_fit(used=(cut,), error_cut=mint("observation", "other"), at=NOW).ok)
        self.assertEqual(check_publication("use_class: Screening\nspatial_support: x\nlicence: x\n")[0].rule_id, "R-strip")
        self.assertEqual(check_publication(render_fact(sample_grid())), [])
        language = store.add_label(
            local_iri=mint("crop", "maize"),
            concept_iri="http://aims.fao.org/aos/agrovoc/c_12332",
            relation="skos:exactMatch",
            language="sw",
            extra_grant=False,
            at=NOW,
        )
        self.assertEqual(language.refusal.rule_id, "R-language")

    def test_class_b_blockers_and_reviewer(self):
        plain = sample_grid()
        self.assertEqual(class_b_blockers(plain, "Taiwan", "maize")[0].rule_id, "R-error")
        uncalibrated = sample_grid(
            error=ErrorStatement(
                metric="uncalibrated",
                sample_region="other",
                sample_crop="other",
                sample_season="2024",
                citation="not-a-matching-study",
                held_out=False,
                independent_of_product=None,
            )
        )
        self.assertEqual(class_b_blockers(uncalibrated, "Taiwan", "maize"), [])
        mismatch = sample_grid(
            error=ErrorStatement(
                metric="rmse",
                sample_region="Ethiopia",
                sample_crop="maize",
                sample_season="2024",
                citation="study",
                held_out=True,
                independent_of_product=True,
                value=millimetres(2.0),
            )
        )
        self.assertEqual(class_b_blockers(mismatch, "Taiwan", "maize")[0].rule_id, "R-error")
        store = Store()
        pilot = load_synthetic_pilot(store)
        cell = sample_grid(iri=mint("observation", "for-gate"))
        self.assertTrue(store.add_observation(cell, at=NOW).ok)
        account = store.promote(
            cell.iri,
            to_class="Portfolio",
            reviewer="worker@seges-ai.iam.gserviceaccount.com",
            checklist={"1": "pass"},
            region="Taiwan",
            crop="maize",
            at=NOW,
        )
        self.assertEqual(account.refusal.rule_id, "R-gate")
        self.assertIn("service account", account.refusal.attempted_change)
        human = store.promote(
            cell.iri,
            to_class="Portfolio",
            reviewer="synthetic-reviewer",
            checklist={"1": "pass"},
            region="Taiwan",
            crop="maize",
            at=NOW,
        )
        self.assertIn("Q13", human.refusal.attempted_change)
        self.assertEqual(store.observations[cell.iri].use_class, "Screening")
        self.assertEqual(pilot.operator.startswith("https://"), True)


if __name__ == "__main__":
    unittest.main()
