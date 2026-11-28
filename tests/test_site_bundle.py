from __future__ import annotations

import unittest

from farm_ontology.site_bundle import (
    OperationRollout,
    SiteBundle,
    SiteBundleError,
    parse_site_bundle,
    validate_site_bundle,
)


def site_bundle(**changes):
    values = {
        "bundle_id": "tea-site-bundle",
        "bundle_version": "0.1.0",
        "site_id": "south-tea-demo",
        "country_code": "CN",
        "region_id": "CN-SOUTH-TEA",
        "data_residency_country": "CN",
        "data_plane_provider": "customer-selected-regional-provider",
        "data_plane_region": "cn-local-region",
        "timezone": "Asia/Shanghai",
        "locale": "zh-CN",
        "unit_system": "SI",
        "boundary_version_ref": "boundary:survey-pending",
        "crop_profile_ref": "tea-south-china-starter@0.1.0",
        "device_manifest_refs": (),
        "operation_rollouts": (
            OperationRollout("irrigation", "shadow", "supervised", "irrigation-profile:site-pending"),
            OperationRollout("fertigation", "shadow", "shadow", "fertigation-profile:site-pending"),
            OperationRollout("pesticide", "shadow", "shadow", "pesticide-profile:site-pending"),
        ),
        "source_refs": ("source:site-survey-pending",),
        "cross_border_transfer_refs": (),
        "schema_version": "1.0",
    }
    return SiteBundle(**{**values, **changes})


class SiteBundleTests(unittest.TestCase):
    def test_validates_site_scope_and_staged_operation_levels(self):
        package = validate_site_bundle(site_bundle())
        self.assertEqual(package.country_code, "CN")
        self.assertEqual(package.operation_rollouts[0].target_level, "supervised")
        self.assertEqual(package.operation_rollouts[2].current_level, "shadow")
        self.assertEqual(len(package.content_sha256()), 64)

    def test_refuses_cross_border_placement_without_evidence_reference(self):
        with self.assertRaisesRegex(SiteBundleError, "cross-border-evidence-missing"):
            validate_site_bundle(site_bundle(data_residency_country="SG"))
        allowed = validate_site_bundle(site_bundle(
            data_residency_country="SG", cross_border_transfer_refs=("transfer-review:case-1",),
        ))
        self.assertEqual(allowed.data_residency_country, "SG")

    def test_supervised_level_requires_device_compatibility_and_safety_evidence(self):
        row = OperationRollout(
            "irrigation", "supervised", "supervised", "irrigation-profile:v1",
        )
        with self.assertRaisesRegex(SiteBundleError, "compatibility_evidence_ref"):
            validate_site_bundle(site_bundle(operation_rollouts=(
                row,
                OperationRollout("fertigation", "shadow", "shadow", "fertigation-profile:v1"),
                OperationRollout("pesticide", "shadow", "shadow", "pesticide-profile:v1"),
            )))

    def test_parser_rejects_unknown_fields_and_bad_operation_set(self):
        doc = site_bundle().to_payload()
        parsed = parse_site_bundle(doc)
        self.assertEqual(parsed.to_payload(), doc)
        with self.assertRaisesRegex(SiteBundleError, "unknown-fields"):
            parse_site_bundle({**doc, "credentials": {"token": "never"}})
        with self.assertRaisesRegex(SiteBundleError, "operation-set-invalid"):
            validate_site_bundle(site_bundle(operation_rollouts=()))

    def test_parser_refuses_malformed_reference_arrays(self):
        doc = site_bundle().to_payload()
        with self.assertRaisesRegex(SiteBundleError, "invalid-refs"):
            parse_site_bundle({**doc, "device_manifest_refs": "device-1"})

    def test_hash_is_content_bound_and_changes_when_configuration_changes(self):
        first = site_bundle()
        second = site_bundle(locale="en-AU")
        self.assertNotEqual(first.content_sha256(), second.content_sha256())


if __name__ == "__main__":
    unittest.main()
