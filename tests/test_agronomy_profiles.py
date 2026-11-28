"""Contracts for versioned and fail-closed crop/site profile packages."""

import unittest

from farm_ontology.agronomy.common import AgronomyGap
from farm_ontology.agronomy.phenology import (
    CULTIVAR_GDD_PROFILES,
    DEFAULT_CULTIVAR_PROFILE,
    GDD_THRESHOLDS,
)
from farm_ontology.agronomy.profiles import (
    Applicability,
    CropSiteProfile,
    CropSiteProfileRegistry,
    DEFAULT_CROP_SITE_PROFILES,
    EvidenceSource,
    ProfileContext,
    SOUTH_CHINA_TEA_PROFILE,
    SourcedParameter,
    UnavailableParameter,
)


class CropSiteProfileTests(unittest.TestCase):
    def setUp(self):
        self.tea = ProfileContext(
            crop_taxon="Camellia sinensis",
            country_code="CN",
            region_id="CN-SOUTH-TEA",
            cultivar_id="local-cultivar-unknown",
            elevation_m=640,
        )

    def test_southern_china_tea_is_explicit_starter_with_no_quantitative_claims(self):
        profile = DEFAULT_CROP_SITE_PROFILES.get("tea-south-china-starter", "0.1.0")
        self.assertIs(profile, SOUTH_CHINA_TEA_PROFILE)
        self.assertTrue(profile.applies_to(self.tea))
        self.assertEqual(profile.parameters, ())
        self.assertTrue(profile.capability_gaps)
        for parameter in ("fertilizer-rate", "irrigation-mm"):
            with self.subTest(parameter=parameter), self.assertRaises(AgronomyGap) as caught:
                profile.require_parameter(parameter, self.tea)
            self.assertEqual(caught.exception.gap, "profile-parameter-missing")

    def test_tea_known_unknowns_keep_context_source_and_evidence_requirements(self):
        profile = SOUTH_CHINA_TEA_PROFILE
        pest_unknown = next(item for item in profile.unavailable_parameters if item.parameter_id == "pest-action-threshold")
        pesticide_unknown = next(item for item in profile.unavailable_parameters if item.parameter_id == "pesticide-rate")
        self.assertEqual(pest_unknown.context_source_ids, ("moa-cn-tea-pest-guidance-2024",))
        self.assertIn("locally-validated-pest-threshold", pest_unknown.required_evidence)
        self.assertIn("current-china-registration-label-for-tea-and-target", pesticide_unknown.required_evidence)
        for parameter in ("pest-action-threshold", "pesticide-rate"):
            with self.subTest(parameter=parameter), self.assertRaises(AgronomyGap) as caught:
                profile.require_parameter(parameter, self.tea)
            self.assertEqual(caught.exception.gap, "profile-parameter-unavailable")
            self.assertTrue(caught.exception.missing)

    def test_tea_profile_refuses_neighbouring_or_non_tea_context(self):
        profile = SOUTH_CHINA_TEA_PROFILE
        for context in (
            ProfileContext("Camellia sinensis", "CN", "CN-NORTH-TEA"),
            ProfileContext("Glycine max", "CN", "CN-SOUTH-TEA"),
        ):
            with self.subTest(context=context), self.assertRaises(AgronomyGap) as caught:
                profile.require_parameter("pest-action-threshold", context)
            self.assertEqual(caught.exception.gap, "profile-out-of-scope")

    def test_unverified_parameter_and_unscoped_parameter_fail_closed(self):
        source = EvidenceSource("paper-1", "Trial", "Local trial report v1")
        applicability = Applicability("Camellia sinensis", ("CN",), ("CN-SOUTH-TEA",), ("cultivar-a",))
        parameter = SourcedParameter("leaf-wetness-hours", 8.0, "h", applicability, ("paper-1",))
        profile = CropSiteProfile(
            "test-tea", "1.0.0", "Camellia sinensis", ("CN",), ("CN-SOUTH-TEA",),
            (source,), (parameter,),
        )
        registry = CropSiteProfileRegistry((profile,))
        with self.assertRaises(AgronomyGap) as caught:
            registry.get("test-tea", "1.0.0").require_parameter("leaf-wetness-hours", self.tea)
        self.assertEqual(caught.exception.gap, "parameter-out-of-scope")
        matching_context = ProfileContext("Camellia sinensis", "CN", "CN-SOUTH-TEA", "cultivar-a")
        with self.assertRaises(AgronomyGap) as caught:
            profile.require_parameter("leaf-wetness-hours", matching_context)
        self.assertEqual(caught.exception.gap, "parameter-unverified")

    def test_verified_parameter_requires_verification_receipt_and_matches_scope(self):
        source = EvidenceSource("trial", "Replicated local trial", "Trial report §4", "https://example.invalid/trial")
        scope = Applicability("Camellia sinensis", ("CN",), ("CN-SOUTH-TEA",), ("cultivar-a",), 500, 800)
        parameter = SourcedParameter(
            "leaf-wetness-hours", 8.0, "h", scope, ("trial",), "verified", "agronomist-17", "2026-11-20",
        )
        profile = CropSiteProfile(
            "local-tea", "1.0.0", "Camellia sinensis", ("CN",), ("CN-SOUTH-TEA",),
            (source,), (parameter,),
        )
        accepted = ProfileContext("Camellia sinensis", "CN", "CN-SOUTH-TEA", "cultivar-a", 640)
        self.assertEqual(profile.require_parameter("leaf-wetness-hours", accepted), parameter)
        too_low = ProfileContext("Camellia sinensis", "CN", "CN-SOUTH-TEA", "cultivar-a", 400)
        with self.assertRaises(AgronomyGap):
            profile.require_parameter("leaf-wetness-hours", too_low)

    def test_invalid_verified_receipts_and_unknown_sources_are_rejected(self):
        source = EvidenceSource("src", "Title", "Citation")
        scope = Applicability("Camellia sinensis", ("CN",), ("CN-SOUTH-TEA",))
        with self.assertRaises(ValueError):
            SourcedParameter("x", 1, "unit", scope, ("src",), "verified", "", "2026-01-01")
        with self.assertRaises(ValueError):
            CropSiteProfile("bad", "1", "Camellia sinensis", ("CN",), ("CN-SOUTH-TEA",), (source,), (
                SourcedParameter("x", 1, "unit", scope, ("missing-source",)),
            ))
        with self.assertRaises(ValueError):
            CropSiteProfile(
                "bad-unknown", "1", "Camellia sinensis", ("CN",), ("CN-SOUTH-TEA",), (source,),
                unavailable_parameters=(UnavailableParameter("threshold", ("missing-source",), "unknown", ("trial",)),),
            )

    def test_unknown_profile_version_has_no_fallback(self):
        with self.assertRaises(KeyError):
            DEFAULT_CROP_SITE_PROFILES.get("tea-south-china-starter", "latest")

    def test_existing_soybean_phenology_default_is_unchanged(self):
        self.assertEqual(DEFAULT_CULTIVAR_PROFILE, "hokkaido-short")
        self.assertEqual(tuple(GDD_THRESHOLDS), CULTIVAR_GDD_PROFILES["hokkaido-short"].thresholds)
        self.assertIn("generic-extension", CULTIVAR_GDD_PROFILES)


if __name__ == "__main__":
    unittest.main()
