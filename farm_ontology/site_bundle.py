"""Versioned site deployment package, separate from farm decisions.

The package pins the site/jurisdiction, regional data placement, crop profile,
device manifests, and per-operation rollout level. It is configuration only:
it does not prove a legal transfer, device compatibility, field acceptance, or
eligibility for live commands. Those claims require separate evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Mapping

from farm_ontology.agronomy.common import canonical_json


class SiteBundleError(ValueError):
    """A site bundle is incomplete, unsupported, or internally inconsistent."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"[site-bundle:{code}] {detail}")
        self.code = code
        self.detail = detail


ROLLOUT_LEVELS = ("observe", "shadow", "assisted", "supervised", "autonomous")
OPERATIONS = ("irrigation", "fertigation", "pesticide")
_SLUG = re.compile(r"\A[a-z0-9][a-z0-9-]{1,62}\Z")
_COUNTRY = re.compile(r"\A[A-Z]{2}\Z")
_LOCALE = re.compile(r"\A[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8})*\Z")


@dataclass(frozen=True)
class OperationRollout:
    operation: str
    current_level: str
    target_level: str
    profile_ref: str
    compatibility_evidence_ref: str = ""
    safety_case_ref: str = ""
    operator_release_required: bool = True


@dataclass(frozen=True)
class SiteBundle:
    """Immutable, reviewable site configuration; secrets are never included."""

    bundle_id: str
    bundle_version: str
    site_id: str
    country_code: str
    region_id: str
    data_residency_country: str
    data_plane_provider: str
    data_plane_region: str
    timezone: str
    locale: str
    unit_system: str
    boundary_version_ref: str
    crop_profile_ref: str
    device_manifest_refs: tuple[str, ...]
    operation_rollouts: tuple[OperationRollout, ...]
    source_refs: tuple[str, ...]
    cross_border_transfer_refs: tuple[str, ...] = ()
    schema_version: str = "1.0"

    def to_payload(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "bundle_id": self.bundle_id,
            "bundle_version": self.bundle_version,
            "site_id": self.site_id,
            "country_code": self.country_code,
            "region_id": self.region_id,
            "data_residency_country": self.data_residency_country,
            "data_plane_provider": self.data_plane_provider,
            "data_plane_region": self.data_plane_region,
            "timezone": self.timezone,
            "locale": self.locale,
            "unit_system": self.unit_system,
            "boundary_version_ref": self.boundary_version_ref,
            "crop_profile_ref": self.crop_profile_ref,
            "device_manifest_refs": list(self.device_manifest_refs),
            "operation_rollouts": [
                {
                    "operation": row.operation,
                    "current_level": row.current_level,
                    "target_level": row.target_level,
                    "profile_ref": row.profile_ref,
                    "compatibility_evidence_ref": row.compatibility_evidence_ref,
                    "safety_case_ref": row.safety_case_ref,
                    "operator_release_required": row.operator_release_required,
                }
                for row in self.operation_rollouts
            ],
            "source_refs": list(self.source_refs),
            "cross_border_transfer_refs": list(self.cross_border_transfer_refs),
        }

    def content_sha256(self) -> str:
        """Content digest for review/change detection; not a signature."""
        return hashlib.sha256(canonical_json(self.to_payload())).hexdigest()


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SiteBundleError("required-field", f"{field} must be a non-empty string")
    return value.strip()


def _string_refs(values: object, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise SiteBundleError("invalid-refs", f"{field} must be an array of references")
    refs = tuple(_required_text(item, f"{field}[{index}]") for index, item in enumerate(values))
    if not allow_empty and not refs:
        raise SiteBundleError("required-refs", f"{field} must contain at least one reference")
    if len(set(refs)) != len(refs):
        raise SiteBundleError("duplicate-ref", f"{field} cannot contain duplicate references")
    return refs


def validate_site_bundle(bundle: SiteBundle) -> SiteBundle:
    """Validate structure and rollout consistency without granting authority."""

    if bundle.schema_version != "1.0":
        raise SiteBundleError("unsupported-schema", f"schema_version {bundle.schema_version!r} is not supported")
    for field in (
        "bundle_id", "bundle_version", "site_id", "region_id", "data_plane_provider",
        "data_plane_region", "timezone", "unit_system", "boundary_version_ref", "crop_profile_ref",
    ):
        _required_text(getattr(bundle, field), field)
    _required_text(bundle.country_code, "country_code")
    _required_text(bundle.data_residency_country, "data_residency_country")
    _required_text(bundle.locale, "locale")
    if not _SLUG.fullmatch(bundle.site_id):
        raise SiteBundleError("site-id-invalid", "site_id must be a lowercase slug")
    if not _COUNTRY.fullmatch(bundle.country_code) or not _COUNTRY.fullmatch(bundle.data_residency_country):
        raise SiteBundleError("country-code-invalid", "country codes must be uppercase ISO-3166 alpha-2 shaped values")
    if not _LOCALE.fullmatch(bundle.locale):
        raise SiteBundleError("locale-invalid", "locale must be a BCP-47-shaped tag such as zh-CN or en-AU")
    if bundle.unit_system not in {"SI", "US-CUSTOMARY"}:
        raise SiteBundleError("unit-system-invalid", "unit_system must be SI or US-CUSTOMARY")
    if bundle.country_code != bundle.data_residency_country and not bundle.cross_border_transfer_refs:
        raise SiteBundleError(
            "cross-border-evidence-missing",
            "data residency differs from site country but no transfer evidence reference is recorded",
        )
    device_refs = _string_refs(bundle.device_manifest_refs, "device_manifest_refs", allow_empty=True)
    source_refs = _string_refs(bundle.source_refs, "source_refs")
    transfer_refs = _string_refs(bundle.cross_border_transfer_refs, "cross_border_transfer_refs", allow_empty=True)
    if not isinstance(bundle.operation_rollouts, tuple) or len(bundle.operation_rollouts) != len(OPERATIONS):
        raise SiteBundleError("operation-set-invalid", f"exactly one rollout record is required for {OPERATIONS}")
    seen: set[str] = set()
    for row in bundle.operation_rollouts:
        if row.operation not in OPERATIONS or row.operation in seen:
            raise SiteBundleError("operation-set-invalid", "operation records must contain each supported operation exactly once")
        seen.add(row.operation)
        if row.current_level not in ROLLOUT_LEVELS or row.target_level not in ROLLOUT_LEVELS:
            raise SiteBundleError("rollout-level-invalid", f"unsupported rollout level for {row.operation}")
        if ROLLOUT_LEVELS.index(row.current_level) > ROLLOUT_LEVELS.index(row.target_level):
            raise SiteBundleError("rollout-level-regression", f"current level exceeds target for {row.operation}")
        _required_text(row.profile_ref, f"{row.operation}.profile_ref")
        if row.current_level in {"supervised", "autonomous"}:
            _required_text(row.compatibility_evidence_ref, f"{row.operation}.compatibility_evidence_ref")
            _required_text(row.safety_case_ref, f"{row.operation}.safety_case_ref")
            if row.operator_release_required is not True:
                raise SiteBundleError("operator-release-required", f"{row.operation} requires an operator release")
    # References are validated without resolving or inferring their targets.
    # Local deployments must resolve them against their signed/controlled registry.
    return bundle


def parse_site_bundle(document: Mapping[str, object]) -> SiteBundle:
    """Parse an exact v1 JSON-like mapping; reject unknown keys and omissions."""

    if not isinstance(document, Mapping):
        raise SiteBundleError("document-invalid", "site bundle must be a mapping")
    required = {
        "schema_version", "bundle_id", "bundle_version", "site_id", "country_code", "region_id",
        "data_residency_country", "data_plane_provider", "data_plane_region", "timezone", "locale",
        "unit_system", "boundary_version_ref", "crop_profile_ref", "device_manifest_refs",
        "operation_rollouts", "source_refs",
    }
    allowed = required | {"cross_border_transfer_refs"}
    missing = sorted(required - set(document))
    unknown = sorted(set(document) - allowed)
    if missing:
        raise SiteBundleError("missing-fields", f"missing site bundle fields: {missing}")
    if unknown:
        raise SiteBundleError("unknown-fields", f"unknown site bundle fields: {unknown}")
    operation_docs = document["operation_rollouts"]
    if not isinstance(operation_docs, (tuple, list)):
        raise SiteBundleError("operation-set-invalid", "operation_rollouts must be an array")
    rows: list[OperationRollout] = []
    operation_keys = {
        "operation", "current_level", "target_level", "profile_ref",
        "compatibility_evidence_ref", "safety_case_ref", "operator_release_required",
    }
    for index, item in enumerate(operation_docs):
        if not isinstance(item, Mapping):
            raise SiteBundleError("operation-row-invalid", f"operation_rollouts[{index}] must be a mapping")
        if set(item) - operation_keys or not {"operation", "current_level", "target_level", "profile_ref"}.issubset(item):
            raise SiteBundleError("operation-row-fields-invalid", f"operation_rollouts[{index}] has missing or unknown fields")
        rows.append(OperationRollout(**item))
    try:
        device_refs = _string_refs(document["device_manifest_refs"], "device_manifest_refs", allow_empty=True)
        source_refs = _string_refs(document["source_refs"], "source_refs")
        transfer_refs = _string_refs(document.get("cross_border_transfer_refs", ()), "cross_border_transfer_refs", allow_empty=True)
    except SiteBundleError:
        raise
    kwargs = {key: document[key] for key in required if key not in {"operation_rollouts", "device_manifest_refs", "source_refs"}}
    kwargs["device_manifest_refs"] = device_refs
    kwargs["operation_rollouts"] = tuple(rows)
    kwargs["source_refs"] = source_refs
    kwargs["cross_border_transfer_refs"] = transfer_refs
    try:
        bundle = SiteBundle(**kwargs)
    except TypeError as error:
        raise SiteBundleError("document-invalid", str(error)) from error
    return validate_site_bundle(bundle)


__all__ = [
    "OPERATIONS",
    "ROLLOUT_LEVELS",
    "OperationRollout",
    "SiteBundle",
    "SiteBundleError",
    "parse_site_bundle",
    "validate_site_bundle",
]
