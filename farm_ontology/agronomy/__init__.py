"""WS3 agronomy decision engine — the engine proposes, humans dispose.

Everything in this package follows the record's honesty rules
(``docs/decision-infra-roadmap.md`` §1):

1. refuse when an input is missing; a gap is published, never guessed;
2. native support travels with every value; joins never rewrite support;
3. ``permits_financial_use`` stays FALSE in v0; flipping it is a written
   grant (WS6), never an engine decision;
4. timestamps are injected; there is no wall-clock read anywhere.

The honest-claims ladder for spatial support is::

    grid-support (native NxN km)
      → probe-support (instrument-point, probe footprint)
        → parcel-support (only when a sensor itself reports an area)

A ladder step is climbed only by explicit, machine-checkable evidence.
Nothing in this package ever claims hectares on behalf of a sensor.
"""

from farm_ontology.agronomy.common import (
    CONFIG_VERSION,
    DRAFTED_BY,
    PERMITS_FINANCIAL_USE_V0,
    USE_CLASS_FIELD_OPS,
    AgronomyError,
    AgronomyGap,
    AgronomyRefusal,
    Gap,
    SupportDeclaration,
    canonical_json,
)
from farm_ontology.agronomy.fertility import (
    REQUIRED_SOIL_ANALYTES,
    SoilReading,
    soil_fertility_note,
)
from farm_ontology.agronomy.irrigation import (
    DEFAULT_IRRIGATION_CONFIG,
    CoverageEligibility,
    CoverageLevel,
    IRRIGATION_CONFIG_SOURCE_NOTE,
    IrrigationAdvice,
    SoilProfile,
    has_calibrated_coverage,
    irrigation_advisory,
)
from farm_ontology.agronomy.phenology import (
    EMERGENCE_CREDIT_GDD,
    GDD_BASE_C,
    GDD_CAP_CONTRIBUTION_C,
    GDD_THRESHOLDS,
    PHENOLOGY_SOURCE_NOTE,
    THRESHOLD_TABLE_VERSION,
    PhenologyReading,
    daily_gdd_contribution,
    phenology_reading,
)
from farm_ontology.agronomy.recommendation import (
    KINDS,
    REFUSED_KINDS,
    InputRef,
    RationaleStep,
    RecommendationRecord,
    draft_recommendation,
    input_ref_from_observation,
    recommendation_id_for,
)
from farm_ontology.agronomy.spray_windows import (
    MIN_RUN_HOURS,
    RAINFAST_HOURS,
    SPRAY_CONFIG,
    SPRAY_SOURCE_NOTE,
    SprayWindow,
    Verdict,
    scan_spray_windows,
)

__all__ = [
    # common
    "CONFIG_VERSION",
    "DRAFTED_BY",
    "PERMITS_FINANCIAL_USE_V0",
    "USE_CLASS_FIELD_OPS",
    "AgronomyError",
    "AgronomyGap",
    "AgronomyRefusal",
    "Gap",
    "SupportDeclaration",
    "canonical_json",
    # phenology
    "EMERGENCE_CREDIT_GDD",
    "GDD_BASE_C",
    "GDD_CAP_CONTRIBUTION_C",
    "GDD_THRESHOLDS",
    "PHENOLOGY_SOURCE_NOTE",
    "THRESHOLD_TABLE_VERSION",
    "PhenologyReading",
    "daily_gdd_contribution",
    "phenology_reading",
    # irrigation
    "DEFAULT_IRRIGATION_CONFIG",
    "CoverageEligibility",
    "CoverageLevel",
    "IRRIGATION_CONFIG_SOURCE_NOTE",
    "IrrigationAdvice",
    "SoilProfile",
    "has_calibrated_coverage",
    "irrigation_advisory",
    # spray windows
    "MIN_RUN_HOURS",
    "RAINFAST_HOURS",
    "SPRAY_CONFIG",
    "SPRAY_SOURCE_NOTE",
    "SprayWindow",
    "Verdict",
    "scan_spray_windows",
    # fertility
    "REQUIRED_SOIL_ANALYTES",
    "SoilReading",
    "soil_fertility_note",
    # recommendation
    "KINDS",
    "REFUSED_KINDS",
    "InputRef",
    "RationaleStep",
    "RecommendationRecord",
    "draft_recommendation",
    "input_ref_from_observation",
    "recommendation_id_for",
]
