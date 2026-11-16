"""Recorded Q1–Q21 decisions. Closed switches stay closed."""

import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.brains import CenterBrain, FarmBrain
from farm_ontology.config import named_reviewer_placeholder
from farm_ontology.layers import LIVELIHOOD_MISSING, SOIL_MISSING, LivelihoodZoneLayer, SoilProfile
from farm_ontology.manifest import load_manifest
from farm_ontology.model import ErrorStatement, Observation
from farm_ontology.names import LOCAL_NAME_GAPS, match_local_name
from farm_ontology.namespaces import CROP_ONTOLOGY, FAO_LABEL_LANGUAGES, REQUESTED_LABEL_LANGUAGES
from farm_ontology.policy import (
    ACCURACY_TARGET,
    BACKTEST_RAN,
    CLASS_C_POLICY,
    INDEPENDENT_VALIDATOR,
    INSTRUMENT,
    class_c_policy,
    named_reviewer,
)
from farm_ontology.store import Store
from tests.support import NOW, sample_grid

ROOT = Path(__file__).resolve().parents[1]


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self._reviewer = os.environ.pop("FARM_NAMED_REVIEWER", None)

    def tearDown(self):
        if self._reviewer is None:
            os.environ.pop("FARM_NAMED_REVIEWER", None)
        else:
            os.environ["FARM_NAMED_REVIEWER"] = self._reviewer

    def test_recorded_choices_leave_the_closed_switches_closed(self):
        document = load_manifest()
        self.assertEqual(document["iri_base_status"], "provisional-not-a-final-domain")
        self.assertEqual(document["intended_domain"], "seges.ai")
        self.assertFalse(document["domain_attached"])
        self.assertEqual(document["store_choice"], "apache-jena")
        self.assertFalse(document["store_deployed"])
        self.assertEqual(document["envo"]["release"], "v2026-10-23")
        self.assertFalse(document["envo"]["imported"])
        self.assertEqual(
            document["envo"]["sha256"],
            "cc070bc1ceca4bf7b6f745c1f0c09398536f46603ff0db53d22f7454fb182f88",
        )
        self.assertEqual(document["envo"]["envo_basic"], "not-in-release")
        self.assertEqual(document["crop_ontology"]["maize"], "CO_322")
        self.assertEqual(document["crop_ontology"]["banana"], "CO_325")
        self.assertIsNone(document["crop_ontology"]["musa_title"])
        self.assertEqual(
            document["plant_stress"]["license"],
            "http://creativecommons.org/licenses/by/4.0/",
        )
        self.assertFalse(document["plant_stress"]["vendored"])
        self.assertTrue(document["livestock_in_scope"])
        self.assertFalse(document["atol"]["vendored"])
        self.assertFalse(document["eol"]["vendored"])
        self.assertEqual(class_c_policy(), "closed")
        self.assertEqual(CLASS_C_POLICY, "closed")
        self.assertIn("human_gate.py", document["class_c_delegated_to"])
        self.assertIsNone(INSTRUMENT)
        self.assertFalse(document["permits_financial_use"])
        self.assertFalse(document["permits_financial_redistribution"])
        self.assertEqual(INDEPENDENT_VALIDATOR, "宇辰 洪")
        self.assertEqual(ACCURACY_TARGET, "yield for long and short futures and stocks")
        self.assertFalse(BACKTEST_RAN)
        self.assertEqual(named_reviewer_placeholder(), "")
        self.assertIsNone(named_reviewer())
        self.assertEqual(CROP_ONTOLOGY["sorghum"], "CO_324")
        self.assertEqual(CROP_ONTOLOGY["chickpea"], "CO_338")
        self.assertEqual(CROP_ONTOLOGY["groundnut"], "CO_337")
        self.assertEqual(CROP_ONTOLOGY["common bean"], "CO_335")
        self.assertEqual(CROP_ONTOLOGY["potato"], "CO_330")
        self.assertEqual(FAO_LABEL_LANGUAGES, {"en", "fr", "es", "ar", "ru", "zh"})
        self.assertEqual(
            REQUESTED_LABEL_LANGUAGES, {"ja", "zh-TW", "zh-CN", "id", "th", "vi"}
        )
        self.assertIsNone(match_local_name("local maize name"))
        self.assertTrue(LOCAL_NAME_GAPS)
        self.assertFalse(LivelihoodZoneLayer().loaded)
        profile = SoilProfile(feature_iri="profile-slot")
        self.assertEqual(profile.observation_iris, ())
        self.assertIsNone(profile.envo_material_iri)
        self.assertTrue(LIVELIHOOD_MISSING)
        self.assertTrue(SOIL_MISSING)
        center = CenterBrain()
        with self.assertRaises(KeyError):
            center.orchestrate("farm-1")
        asia = FarmBrain("farm-1", "Asia")
        self.assertEqual(CenterBrain((asia,)).orchestrate("farm-1").region, "Asia")
        with self.assertRaises(ValueError):
            FarmBrain("farm-2", "Europe")
        self.assertFalse((ROOT / "LICENSE").exists())

    def test_reviewer_name_does_not_promote_and_extra_labels_need_a_source(self):
        os.environ["FARM_NAMED_REVIEWER"] = "later"
        try:
            self.assertEqual(named_reviewer(), "later")
            store = Store()
            base = sample_grid()
            obs = Observation(
                **{
                    **base.__dict__,
                    "iri": base.iri + "-named",
                    "error": ErrorStatement(
                        metric="uncalibrated",
                        sample_region="synthetic",
                        sample_crop="maize",
                        sample_season="synthetic",
                        citation="none",
                        held_out=False,
                        independent_of_product=None,
                    ),
                }
            )
            # sample_grid mints a fixed IRI. A second local id avoids a collision.
            obs = Observation(**{**obs.__dict__, "iri": obs.iri.replace("sample-cell", "named-cell")})
            stored = store.add_observation(obs, at=NOW)
            self.assertTrue(stored.ok, stored.refusal.attempted_change if stored.refusal else "")
            refused = store.promote(
                obs.iri,
                to_class="Portfolio",
                reviewer="later",
                checklist={"1": "pass"},
                region="synthetic",
                crop="maize",
                at=NOW,
            )
            self.assertFalse(refused.ok)
            self.assertIn("promotions stay off", refused.refusal.attempted_change)
            label = store.add_label(
                local_iri="https://github.com/Zereo0317/farm-ontology/ns/crop/local-name",
                concept_iri="http://aims.fao.org/aos/agrovoc/c_12332",
                relation="skos:exactMatch",
                language="ja",
                extra_grant=True,
                at=datetime(2026, 11, 16, tzinfo=timezone.utc),
            )
            self.assertEqual(label.refusal.rule_id, "R-language")
        finally:
            os.environ.pop("FARM_NAMED_REVIEWER", None)
