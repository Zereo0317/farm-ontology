from __future__ import annotations

import unittest
from datetime import datetime, timezone

from farm_ontology.agronomy.common import AgronomyGap
from farm_ontology.agronomy.irrigation_optimizer import IrrigationCandidate, optimize_irrigation_candidates
from farm_ontology.agronomy.profiles import (
    Applicability,
    CropSiteProfile,
    EvidenceSource,
    ProfileContext,
    SOUTH_CHINA_TEA_PROFILE,
    SourcedParameter,
)
from farm_ontology.agronomy.state_estimation import StateEstimate


NOW = datetime(2026, 11, 28, 4, 0, tzinfo=timezone.utc)
TEA = ProfileContext("Camellia sinensis", "CN", "CN-SOUTH-TEA", "local-cultivar", 200.0)


def verified_profile(**overrides):
    source = EvidenceSource("site-review-v1", "Reviewed pilot parameters", "local field validation report")
    values = {
        "root-zone-stress-threshold-mm": (55.0, "mm"),
        "root-zone-refill-capacity-mm": (90.0, "mm"),
        "application-efficiency": (0.82, "fraction"),
        "max-gross-irrigation-mm": (30.0, "mm"),
    }
    values.update(overrides)
    applicability = Applicability("Camellia sinensis", ("CN",), ("CN-SOUTH-TEA",), ("local-cultivar",), 100.0, 300.0)
    parameters = tuple(
        SourcedParameter(
            name, value, unit, applicability, (source.source_id,),
            "verified", "local-agronomist", "2026-11-20",
        )
        for name, (value, unit) in values.items()
    )
    return CropSiteProfile(
        "tea-south-china-test", "1.0.0", "Camellia sinensis", ("CN",),
        ("CN-SOUTH-TEA",), (source,), parameters=parameters,
    )


def state(value=70.0, variance=4.0):
    return StateEstimate(
        "root-depletion|site:tea1|zone:z1|layer:0-40cm|support:probe-array:1",
        value, variance, "mm-depletion", NOW, "state:forecast:1",
    )


class IrrigationOptimizerTests(unittest.TestCase):
    def test_tea_starter_fails_closed_without_quantitative_parameters(self):
        with self.assertRaisesRegex(AgronomyGap, "profile-parameter-missing"):
            optimize_irrigation_candidates(
                profile=SOUTH_CHINA_TEA_PROFILE,
                context=TEA,
                state=state(),
                forecast_et_mm=2.0,
                forecast_rain_mm=0.0,
                uncertainty_multiplier=1.0,
                candidates=(IrrigationCandidate("off", 0.0, 0.0),),
                water_cost_per_mm=1.0,
                energy_cost_per_kwh=0.1,
            )

    def test_selects_lowest_cost_candidate_meeting_uncertainty_adjusted_stress_bound(self):
        result = optimize_irrigation_candidates(
            profile=verified_profile(), context=TEA, state=state(),
            forecast_et_mm=3.0, forecast_rain_mm=4.0, uncertainty_multiplier=2.0,
            candidates=(
                IrrigationCandidate("off", 0.0, 0.0),
                IrrigationCandidate("small", 24.0, 1.0),
                IrrigationCandidate("large", 30.0, 2.0),
            ),
            water_cost_per_mm=1.0, energy_cost_per_kwh=1.0,
        )
        self.assertEqual(result.selected_candidate_id, "small")
        self.assertAlmostEqual(result.projected_depletion_upper_mm, 53.32)
        self.assertFalse(result.control_authorized)
        self.assertEqual(result.mode, "advisory-only")
        self.assertIn("application-efficiency", result.parameter_ids)

    def test_refuses_unverified_wrong_unit_and_out_of_scope_parameters(self):
        profile = verified_profile(**{"application-efficiency": (82.0, "percent")})
        with self.assertRaisesRegex(AgronomyGap, "irrigation-profile-unit-mismatch"):
            optimize_irrigation_candidates(
                profile=profile, context=TEA, state=state(), forecast_et_mm=1,
                forecast_rain_mm=0, uncertainty_multiplier=1,
                candidates=(IrrigationCandidate("off", 0, 0),),
                water_cost_per_mm=1, energy_cost_per_kwh=1,
            )
        with self.assertRaisesRegex(AgronomyGap, "parameter-unverified"):
            unverified = verified_profile()
            changed = tuple(
                SourcedParameter(**{**item.__dict__, "verification_status": "unverified", "verified_by": "", "verified_at": ""})
                if item.parameter_id == "application-efficiency" else item
                for item in unverified.parameters
            )
            profile_unverified = CropSiteProfile(**{**unverified.__dict__, "parameters": changed})
            optimize_irrigation_candidates(
                profile=profile_unverified, context=TEA, state=state(), forecast_et_mm=1,
                forecast_rain_mm=0, uncertainty_multiplier=1,
                candidates=(IrrigationCandidate("off", 0, 0),),
                water_cost_per_mm=1, energy_cost_per_kwh=1,
            )

    def test_rejects_candidates_exceeding_hydraulic_or_stress_limits(self):
        with self.assertRaisesRegex(AgronomyGap, "irrigation-no-feasible-candidate"):
            optimize_irrigation_candidates(
                profile=verified_profile(), context=TEA, state=state(80, 1),
                forecast_et_mm=5, forecast_rain_mm=0, uncertainty_multiplier=2,
                candidates=(IrrigationCandidate("oversize", 40, 1),),
                water_cost_per_mm=1, energy_cost_per_kwh=1,
            )

    def test_equal_objectives_have_deterministic_tie_break(self):
        result = optimize_irrigation_candidates(
            profile=verified_profile(), context=TEA, state=state(40, 1),
            forecast_et_mm=1, forecast_rain_mm=0, uncertainty_multiplier=1,
            candidates=(IrrigationCandidate("b", 0, 1), IrrigationCandidate("a", 0, 1)),
            water_cost_per_mm=0, energy_cost_per_kwh=1,
        )
        self.assertEqual(result.selected_candidate_id, "a")


if __name__ == "__main__":
    unittest.main()
