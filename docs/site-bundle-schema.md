# Site deployment bundle schema v1

`farm_ontology.site_bundle` defines the first machine-validated configuration
boundary for repeatable multi-farm deployments. A bundle is an immutable,
reviewable description of one site and its operating region. It binds stable
references to the surveyed boundary, crop profile, device manifests, source
records, and the independent rollout level for irrigation, fertigation, and
pesticide operations.

The package intentionally carries references rather than credentials,
private farm geometry, or legal documents. A SHA-256 digest detects content
changes for review; it is not a signature, an identity proof, or an approval.
The loader rejects missing and unknown fields so a newer schema cannot be
silently treated as v1.

## Required fields

| Field | Meaning |
| --- | --- |
| `bundle_id`, `bundle_version` | Stable package identity and operator-controlled revision. |
| `site_id`, `country_code`, `region_id` | Tenant-scoped site identity and jurisdiction tags; these are not a surveyed coordinate or legal boundary. |
| `data_residency_country`, `data_plane_provider`, `data_plane_region` | Declared storage/compute placement. A country mismatch requires at least one cross-border review evidence reference. |
| `timezone`, `locale`, `unit_system` | Presentation and time interpretation (`SI` or `US-CUSTOMARY`). Installers must resolve timezone support and validate device clocks. |
| `boundary_version_ref`, `crop_profile_ref` | References to independently versioned geometry and agronomy records. |
| `device_manifest_refs` | Zero or more references to the site inventory and per-device compatibility evidence. Empty means no device has been admitted. |
| `operation_rollouts` | Exactly one row per operation (`irrigation`, `fertigation`, `pesticide`) with current/target level and a profile reference. |
| `source_refs` | At least one provenance reference for the declared deployment configuration. |
| `cross_border_transfer_refs` | Optional evidence references, required when declared site country and data-residency country differ. Recording a reference is not legal approval. |

Each operation can be staged through `observe`, `shadow`, `assisted`,
`supervised`, and `autonomous`. A current level cannot exceed its target.
`supervised` and `autonomous` require compatibility and safety-case evidence
references and keep the operator-release requirement enabled. These checks
only validate bundle structure. The current actuator implementation, field
acceptance, local safety interlocks, owner releases, and applicable rules
remain separate gates; the bundle cannot unlock live control by itself.

## Example starter configuration

This is a schema illustration, not an accepted deployment or agronomic
recommendation. `cn-local-region`, pending references, and rollout targets
must be replaced after the actual provider, farm, devices, local agronomy,
and responsible reviewers are established. No coordinates, threshold,
application rate, or water volume are inferred.

```json
{
  "schema_version": "1.0",
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
  "device_manifest_refs": [],
  "operation_rollouts": [
    {"operation":"irrigation","current_level":"shadow","target_level":"supervised","profile_ref":"irrigation-profile:site-pending","compatibility_evidence_ref":"","safety_case_ref":"","operator_release_required":true},
    {"operation":"fertigation","current_level":"shadow","target_level":"shadow","profile_ref":"fertigation-profile:site-pending","compatibility_evidence_ref":"","safety_case_ref":"","operator_release_required":true},
    {"operation":"pesticide","current_level":"shadow","target_level":"shadow","profile_ref":"pesticide-profile:site-pending","compatibility_evidence_ref":"","safety_case_ref":"","operator_release_required":true}
  ],
  "source_refs": ["source:site-survey-pending"],
  "cross_border_transfer_refs": []
}
```

Parse and validate without side effects:

```python
import json
from farm_ontology.site_bundle import parse_site_bundle

bundle = parse_site_bundle(json.load(open("site-bundle.json", encoding="utf-8")))
print(bundle.content_sha256())  # review/change digest, not a signature
```

## Installer checks beyond schema validation

1. Resolve every reference through the tenant's controlled evidence registry;
   reject missing, stale, or wrong-site targets.
2. Compare country/provider/region to the signed data-location decision,
   customer contract, feed licences, backup plan, and local retention rules.
   Get jurisdiction-specific review before any cross-border data movement.
3. Bind each device manifest entry to exact make/model, firmware, interface
   version, calibration, units, native spatial support, and witnessed test.
4. Confirm the crop profile is locally reviewed and contains evidence,
   applicability limits, uncertainty, and explicit unknowns. A profile
   reference does not imply valid tea irrigation or pest-control values.
5. Promote one operation at a time using the forward-deploy acceptance gates.
   Fertigation and pesticide remain separate approvals even when they share
   pumps, sensors, or weather inputs.
6. Sign or otherwise authenticate the reviewed bundle in the deployment
   system, record who approved it, and compare the digest before install.
   Signature and approval handling is not implemented by this schema module.

See [`forward-deploy-installation.md`](forward-deploy-installation.md) for
the field procedure and [`global-tech-stack-baseline-2026-11.md`](global-tech-stack-baseline-2026-11.md)
for interoperability choices and standards sources.
