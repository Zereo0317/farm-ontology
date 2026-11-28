"""Versioned, applicability-scoped crop and site profile packages.

This registry is a provenance and eligibility boundary, not an agronomic
model. A parameter is usable only when its source, verification receipt, and
the requested field context all match. Missing or out-of-scope values are
named gaps; this module never fills them from a neighbouring crop or region.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
from farm_ontology.agronomy.common import AgronomyGap


@dataclass(frozen=True)
class ProfileContext:
    """The minimum identity needed to decide if a package applies."""

    crop_taxon: str
    country_code: str
    region_id: str
    cultivar_id: str | None = None
    elevation_m: float | None = None


@dataclass(frozen=True)
class EvidenceSource:
    """A source record. Verification is an explicit, reviewable assertion."""

    source_id: str
    title: str
    citation: str
    uri: str = ""

    def __post_init__(self) -> None:
        if not self.source_id or not self.title or not self.citation:
            raise ValueError("source_id, title, and citation are required")


@dataclass(frozen=True)
class Applicability:
    """Closed-world scope for a parameter; empty dimensions are not wildcards."""

    crop_taxon: str
    country_codes: tuple[str, ...]
    region_ids: tuple[str, ...]
    cultivar_ids: tuple[str, ...] = ()
    elevation_min_m: float | None = None
    elevation_max_m: float | None = None

    def __post_init__(self) -> None:
        if not self.crop_taxon or not self.country_codes or not self.region_ids:
            raise ValueError("applicability requires crop, country, and region scope")
        if (
            self.elevation_min_m is not None
            and self.elevation_max_m is not None
            and self.elevation_min_m > self.elevation_max_m
        ):
            raise ValueError("elevation_min_m must not exceed elevation_max_m")

    def matches(self, context: ProfileContext) -> bool:
        if context.crop_taxon != self.crop_taxon:
            return False
        if context.country_code not in self.country_codes:
            return False
        if context.region_id not in self.region_ids:
            return False
        if self.cultivar_ids and context.cultivar_id not in self.cultivar_ids:
            return False
        if self.elevation_min_m is not None or self.elevation_max_m is not None:
            if context.elevation_m is None:
                return False
            if self.elevation_min_m is not None and context.elevation_m < self.elevation_min_m:
                return False
            if self.elevation_max_m is not None and context.elevation_m > self.elevation_max_m:
                return False
        return True


@dataclass(frozen=True)
class SourcedParameter:
    """One parameter with source and verification state kept alongside value."""

    parameter_id: str
    value: object
    unit: str
    applicability: Applicability
    source_ids: tuple[str, ...]
    verification_status: str = "unverified"
    verified_by: str = ""
    verified_at: str = ""

    def __post_init__(self) -> None:
        if not self.parameter_id or not self.unit or self.value is None:
            raise ValueError("parameter_id, non-null value, and unit are required")
        if not self.source_ids:
            raise ValueError(f"{self.parameter_id}: at least one source_id is required")
        if self.verification_status not in {"unverified", "verified"}:
            raise ValueError(f"{self.parameter_id}: invalid verification_status")
        if not _immutable_value(self.value):
            raise ValueError(f"{self.parameter_id}: value must use immutable scalar/tuple data")
        if self.verification_status == "verified":
            if not (self.verified_by and self.verified_at):
                raise ValueError(f"{self.parameter_id}: verified values require verified_by and verified_at")
            try:
                date.fromisoformat(self.verified_at)
            except ValueError as error:
                raise ValueError(f"{self.parameter_id}: verified_at must be an ISO date") from error


@dataclass(frozen=True)
class UnavailableParameter:
    """A named unknown with context sources and the evidence needed to fill it."""

    parameter_id: str
    context_source_ids: tuple[str, ...]
    reason: str
    required_evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.parameter_id or not self.reason:
            raise ValueError("unavailable parameter requires parameter_id and reason")
        if not self.context_source_ids or not self.required_evidence:
            raise ValueError(f"{self.parameter_id}: context sources and required_evidence are required")


@dataclass(frozen=True)
class CropSiteProfile:
    """Immutable, versioned profile package for one crop and site envelope."""

    profile_id: str
    version: str
    crop_taxon: str
    countries: tuple[str, ...]
    regions: tuple[str, ...]
    sources: tuple[EvidenceSource, ...]
    parameters: tuple[SourcedParameter, ...] = ()
    unavailable_parameters: tuple[UnavailableParameter, ...] = ()
    capability_gaps: tuple[str, ...] = ()
    description: str = ""

    def __post_init__(self) -> None:
        if not self.profile_id or not self.version or not self.crop_taxon:
            raise ValueError("profile_id, version, and crop_taxon are required")
        if len({item.parameter_id for item in self.parameters}) != len(self.parameters):
            raise ValueError("parameter_id values must be unique within a profile")
        parameter_ids = {item.parameter_id for item in self.parameters}
        unavailable_ids = {item.parameter_id for item in self.unavailable_parameters}
        if len(unavailable_ids) != len(self.unavailable_parameters):
            raise ValueError("unavailable parameter_id values must be unique")
        if parameter_ids.intersection(unavailable_ids):
            raise ValueError("a parameter cannot be both available and unavailable")
        if not self.countries or not self.regions:
            raise ValueError("profile country and region scope must be explicit")
        source_ids = {item.source_id for item in self.sources}
        if len(source_ids) != len(self.sources):
            raise ValueError("source_id values must be unique within a profile")
        for item in self.unavailable_parameters:
            if any(source_id not in source_ids for source_id in item.context_source_ids):
                raise ValueError(f"{item.parameter_id}: unknown context source_id")
        for item in self.parameters:
            if not item.parameter_id or not item.unit:
                raise ValueError("parameter_id and unit are required")
            if item.value is None:
                raise ValueError(f"{item.parameter_id}: omit an unavailable value instead of storing None")
            if not item.applicability.country_codes or not item.applicability.region_ids:
                raise ValueError(f"{item.parameter_id}: country and region scope must be explicit")
            if item.applicability.crop_taxon != self.crop_taxon:
                raise ValueError(f"{item.parameter_id}: applicability crop differs from profile")
            if not set(item.applicability.country_codes).issubset(self.countries):
                raise ValueError(f"{item.parameter_id}: applicability countries exceed profile scope")
            if not set(item.applicability.region_ids).issubset(self.regions):
                raise ValueError(f"{item.parameter_id}: applicability regions exceed profile scope")
            if not item.source_ids or any(source_id not in source_ids for source_id in item.source_ids):
                raise ValueError(f"{item.parameter_id}: every parameter needs known source_ids")
            if item.verification_status not in {"unverified", "verified"}:
                raise ValueError(f"{item.parameter_id}: invalid verification_status")

    def applies_to(self, context: ProfileContext) -> bool:
        return (
            context.crop_taxon == self.crop_taxon
            and context.country_code in self.countries
            and context.region_id in self.regions
        )

    def require_parameter(self, parameter_id: str, context: ProfileContext) -> SourcedParameter:
        """Return a verified in-scope parameter or fail closed with a named gap."""
        if not self.applies_to(context):
            raise AgronomyGap(
                "profile-out-of-scope",
                f"profile {self.profile_id}@{self.version} does not apply to "
                f"{context.crop_taxon}/{context.country_code}/{context.region_id}",
                missing=("applicable-profile",),
            )
        parameter = next((item for item in self.parameters if item.parameter_id == parameter_id), None)
        if parameter is None:
            unavailable = next(
                (item for item in self.unavailable_parameters if item.parameter_id == parameter_id), None
            )
            if unavailable is not None:
                raise AgronomyGap(
                    "profile-parameter-unavailable",
                    f"{parameter_id} is explicitly unknown: {unavailable.reason}; "
                    f"context source_ids={list(unavailable.context_source_ids)}",
                    missing=unavailable.required_evidence,
                    remediation="supply the listed evidence and publish a new reviewed profile version",
                )
            raise AgronomyGap(
                "profile-parameter-missing",
                f"profile {self.profile_id}@{self.version} has no sourced value for {parameter_id}",
                missing=(parameter_id,),
                remediation="add a reviewed parameter with applicable evidence and a verification receipt",
            )
        if not parameter.applicability.matches(context):
            raise AgronomyGap(
                "parameter-out-of-scope",
                f"{parameter_id} is not applicable to the requested field context",
                missing=(f"applicable:{parameter_id}",),
            )
        if parameter.verification_status != "verified":
            raise AgronomyGap(
                "parameter-unverified",
                f"{parameter_id} has source metadata but no verification receipt",
                missing=(f"verified:{parameter_id}",),
            )
        return parameter


class CropSiteProfileRegistry:
    """Read-only registry that rejects duplicate identities and unknown ids."""

    def __init__(self, profiles: tuple[CropSiteProfile, ...]):
        keyed = {(profile.profile_id, profile.version): profile for profile in profiles}
        if len(keyed) != len(profiles):
            raise ValueError("profile_id/version identities must be unique")
        self._profiles = keyed

    def get(self, profile_id: str, version: str) -> CropSiteProfile:
        try:
            return self._profiles[(profile_id, version)]
        except KeyError as error:
            known = sorted(f"{name}@{revision}" for name, revision in self._profiles)
            raise KeyError(f"unknown crop/site profile {profile_id}@{version}; known: {known}") from error

    def versions(self) -> tuple[tuple[str, str], ...]:
        return tuple(sorted(self._profiles))


def _immutable_value(value: object) -> bool:
    """Keep profile values deeply immutable and portable in package manifests."""
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, tuple):
        return all(_immutable_value(item) for item in value)
    return False


# The existing engine's soybean tables remain authoritative for their current
# callers. This package is only a profile/provenance manifest; the source notes
# explicitly retain their VERIFY status and it does not alter any default.
_SOYBEAN_SOURCE = EvidenceSource(
    source_id="soybean-engine-spec-v0",
    title="Agronomy decision engine v0 source notes",
    citation="docs/agronomy-engine-spec.md sections 2-3; current soybean defaults",
)
SOYBEAN_HOKKAIDO_PROFILE = CropSiteProfile(
    profile_id="soybean-hokkaido",
    version="1.0.0",
    crop_taxon="Glycine max",
    countries=("JP",),
    regions=("JP-HKD",),
    sources=(_SOYBEAN_SOURCE,),
    capability_gaps=("fertilizer-dose", "pesticide-dose", "field-validated-irrigation-trigger"),
    description=(
        "Manifest for the retained Hokkaido soybean engine profile. Existing "
        "phenology defaults remain unchanged; source notes are not promoted "
        "to verified global agronomic parameters."
    ),
)

_TEA_SOURCE = EvidenceSource(
    source_id="moa-cn-tea-pest-guidance-2024",
    title="2024年茶树病虫害防控技术方案",
    citation="中华人民共和国农业农村部, 2024, 茶树病虫害分區防控指導",
    uri="https://www.moa.gov.cn/ztzl/2024cg/jszd_29651/202403/P020240322565099338361.pdf",
)
SOUTH_CHINA_TEA_PROFILE = CropSiteProfile(
    profile_id="tea-south-china-starter",
    version="0.1.0",
    crop_taxon="Camellia sinensis",
    countries=("CN",),
    regions=("CN-SOUTH-TEA",),
    sources=(_TEA_SOURCE,),
    unavailable_parameters=(
        UnavailableParameter(
            parameter_id="pest-action-threshold",
            context_source_ids=("moa-cn-tea-pest-guidance-2024",),
            reason=(
                "the cited national guidance provides prevention and monitoring context, "
                "not a verified numeric threshold for this site's pest, cultivar, and season"
            ),
            required_evidence=(
                "locally-validated-pest-threshold",
                "target-pest-identification-and-monitoring-method",
                "crop-stage-and-site-applicability-review",
            ),
        ),
        UnavailableParameter(
            parameter_id="pesticide-rate",
            context_source_ids=("moa-cn-tea-pest-guidance-2024",),
            reason="no product-specific, current registration-label evidence is included",
            required_evidence=(
                "current-china-registration-label-for-tea-and-target",
                "label-dose-and-application-constraints",
                "local-human-review",
            ),
        ),
    ),
    capability_gaps=(
        "locally-validated-pest-disease-thresholds",
        "cultivar-and-phenology-calendar",
        "soil-and-leaf-analysis-interpretation",
        "fertilizer-product-rates-and-timing",
        "pesticide-registration-label-and-rates",
        "terrace-irrigation-trigger-and-application-rate",
        "local-weather-and-pest-observation-baselines",
    ),
    description=(
        "Starter envelope for field discovery in southern Chinese tea farms. "
        "The cited guidance supports prevention and monitoring context; it "
        "does not provide a verified site-specific threshold or product rate. "
        "No quantitative tea recommendation is enabled."
    ),
)


DEFAULT_CROP_SITE_PROFILES = CropSiteProfileRegistry(
    (SOYBEAN_HOKKAIDO_PROFILE, SOUTH_CHINA_TEA_PROFILE)
)


def require_profile_parameter(
    registry: CropSiteProfileRegistry,
    profile_id: str,
    version: str,
    parameter_id: str,
    context: ProfileContext,
) -> SourcedParameter:
    """Convenience function for consumers that should never infer a fallback."""
    return registry.get(profile_id, version).require_parameter(parameter_id, context)


__all__ = [
    "Applicability",
    "CropSiteProfile",
    "CropSiteProfileRegistry",
    "DEFAULT_CROP_SITE_PROFILES",
    "EvidenceSource",
    "ProfileContext",
    "SOUTH_CHINA_TEA_PROFILE",
    "SOYBEAN_HOKKAIDO_PROFILE",
    "SourcedParameter",
    "UnavailableParameter",
    "UnavailableParameter",
    "require_profile_parameter",
]
