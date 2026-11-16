"""Refusal rules. A failure is recorded and the forbidden record is not stored."""

from __future__ import annotations

from dataclasses import dataclass

from farm_ontology.model import BoundaryVersion, Cropping, Observation
from farm_ontology.namespaces import (
    ERROR_METRICS,
    GAP_REASONS,
    KIND,
    KIND_MASS,
    MIX_VALUES,
    TENURE_VALUES,
    UNIT,
    UNIT_HA,
    UNIT_TONNE,
)
from farm_ontology.policy import CLASS_C_USES
from farm_ontology.timeutil import ensure_utc

PROC_CROP_CUT = "procedure/crop-cut"
PROC_SENSOR = "procedure/sensor"
PROC_RAW_PIXEL = "procedure/raw-pixel"
PROC_GAP_FILL = "procedure/gap-fill"
PROC_FARMER_RECALL = "procedure/farmer-recall"

SAME_DAY_PRODUCTS = frozenset({"reanalysis", "chirps-final"})
GRID_KINDS = frozenset({"grid-cell", "pixel", "township", "station"})


@dataclass(frozen=True)
class Violation:
    rule_id: str
    detail: str


def _procedure_tail(procedure: str) -> str:
    if "/" not in procedure:
        return procedure
    return "procedure/" + procedure.rstrip("/").split("/")[-1]


def _check_clock(obs: Observation, found: list[Violation]) -> None:
    ensure_utc(obs.phenomenon.start, "phenomenon.start")
    ensure_utc(obs.phenomenon.end, "phenomenon.end")
    ensure_utc(obs.generated_at, "generated_at")
    if obs.phenomenon.end <= obs.phenomenon.start:
        found.append(Violation("R-property", "phenomenon interval must end after it starts"))
    if obs.availability_time is not None:
        ensure_utc(obs.availability_time, "availability_time")
    if obs.issue_time is not None:
        ensure_utc(obs.issue_time, "issue_time")
    if obs.result_time is not None:
        ensure_utc(obs.result_time, "result_time")


def observation_violations(
    obs: Observation,
    boundary_iris: set[str],
    previous: Observation | None,
    survey_point_iris: set[str] | None = None,
) -> list[Violation]:
    found: list[Violation] = []
    _check_clock(obs, found)

    if obs.use_class in CLASS_C_USES:
        found.append(
            Violation(
                "R-classC",
                "use class Settlement, hedge, trigger, or nature-unit is closed",
            )
        )
    elif obs.use_class != "Screening":
        found.append(
            Violation(
                "R-gate",
                "ingest assigns Screening; a higher class is a separate gate",
            )
        )

    if "://" not in obs.observed_property or obs.observed_property.lower() in {
        "rain",
        "yield",
    }:
        found.append(
            Violation("R-property", "observed property must be an IRI, not a bare label")
        )

    if obs.is_forecast:
        if obs.issue_time is None or obs.lead_seconds is None:
            found.append(
                Violation(
                    "R-issue",
                    "a forecast needs an issue time distinct from phenomenon time, and a stored lead",
                )
            )
        elif obs.issue_time >= obs.phenomenon.start:
            found.append(
                Violation(
                    "R-issue",
                    "issue time must be earlier than phenomenon time",
                )
            )
        else:
            expected = int((obs.phenomenon.start - obs.issue_time).total_seconds())
            if obs.lead_seconds != expected:
                found.append(
                    Violation(
                        "R-issue",
                        "lead time must be the stored interval from issue time to phenomenon time",
                    )
                )
            if obs.availability_time is None or obs.availability_time < obs.issue_time:
                found.append(
                    Violation(
                        "R-issue",
                        "a forecast availability time is on or after issue time",
                    )
                )
    else:
        if not obs.availability_known:
            pass
        elif obs.availability_time is None:
            found.append(
                Violation("R-lookahead", "availability time is missing and not marked unknown")
            )
        elif obs.availability_time < obs.phenomenon.start:
            found.append(
                Violation(
                    "R-lookahead",
                    "availability time is before phenomenon time for a past observation",
                )
            )
        elif (
            obs.product_kind in SAME_DAY_PRODUCTS
            and obs.availability_time.date() == obs.phenomenon.start.date()
        ):
            rule = "R-reanalysis" if obs.product_kind == "reanalysis" else "R-lookahead"
            found.append(
                Violation(
                    rule,
                    "availability on the phenomenon day would make a lagged product look known that day",
                )
            )

    if obs.availability_time is not None and obs.generated_at < obs.availability_time:
        found.append(
            Violation("R-lookahead", "version time is before availability time")
        )

    if obs.product_kind == "reanalysis" and obs.operations_observation:
        found.append(
            Violation(
                "R-reanalysis",
                "a reanalysis fact is not a real-time operations observation",
            )
        )

    tail = _procedure_tail(obs.procedure)
    if obs.product_kind == "gap-fill" or tail == PROC_GAP_FILL:
        if tail in {PROC_SENSOR, PROC_RAW_PIXEL}:
            found.append(
                Violation(
                    "R-gapfill",
                    "a gap-filled value cannot use a sensor or raw-pixel procedure",
                )
            )
        if tail != PROC_GAP_FILL:
            found.append(
                Violation("R-gapfill", "a gap-filled value must name the fill procedure")
            )
        if obs.use_class != "Screening" and obs.use_class not in CLASS_C_USES:
            found.append(Violation("R-gapfill", "a gap-filled index stays at Screening"))

    if obs.nodata and obs.result is not None:
        found.append(Violation("R-zero", "nodata is not stored as a numeric result"))
    if obs.gap_reason is not None:
        if obs.gap_reason not in GAP_REASONS:
            found.append(Violation("R-zero", "unknown gap reason"))
        if obs.result is not None:
            found.append(Violation("R-zero", "a gap is not a zero and not a filled value"))

    if obs.stated_as_recall and tail == PROC_CROP_CUT:
        found.append(
            Violation(
                "R-property",
                "farmer recall is not stored under the crop-cut procedure",
            )
        )
    if tail == PROC_CROP_CUT and obs.feature_of_interest in (survey_point_iris or set()):
        found.append(
            Violation(
                "R-foi",
                "a 0-5 km privacy-displaced survey point is not a crop-cut location",
            )
        )

    if obs.result is None:
        if obs.gap_reason is None and obs.unsupported_reason is None:
            found.append(
                Violation(
                    "R-property",
                    "a result is required unless the fact is a gap or an explicit unsupported statement",
                )
            )
    else:
        if not obs.result.unit_iri.startswith(UNIT):
            found.append(Violation("R-unit", "the result unit must be a QUDT unit IRI"))
        if not obs.result.quantity_kind_iri.startswith(KIND):
            found.append(
                Violation("R-unit", "the result quantity kind must be a QUDT kind IRI")
            )
        per = obs.result.per_unit_iri
        if obs.result.unit_iri == UNIT_TONNE and per == UNIT_HA and (
            obs.result.quantity_kind_iri == KIND_MASS
        ):
            found.append(
                Violation(
                    "R-unit",
                    "tonnes and tonnes per hectare do not share a quantity kind",
                )
            )
        if obs.result.unit_iri == UNIT_TONNE and per is None and (
            obs.result.quantity_kind_iri != KIND_MASS
        ):
            found.append(
                Violation("R-unit", "a production mass uses the mass quantity kind")
            )

    feature_is_boundary = (
        obs.feature_of_interest in boundary_iris or is_boundary_kind(obs.feature_kind)
    )
    if feature_is_boundary and obs.native_resolution is not None:
        found.append(
            Violation(
                "R-foi",
                "a grid or pixel resolution cannot be stored as a measurement of the farm boundary",
            )
        )
    if obs.spatial_support in {"grid-cell", "pixel", "township"} and feature_is_boundary:
        found.append(
            Violation(
                "R-foi",
                "the feature of interest of a grid, pixel, or township value is that grid, pixel, or township",
            )
        )
    if obs.feature_kind in GRID_KINDS and obs.feature_of_interest in boundary_iris:
        found.append(
            Violation(
                "R-foi",
                "the feature of interest must be the cell, pixel, township, or station",
            )
        )
    if obs.spatial_support == "grid-cell" and obs.feature_kind != "grid-cell":
        found.append(
            Violation("R-support", "grid-cell support requires a grid-cell feature")
        )

    if obs.hectare_weather_claim:
        if not obs.sensor_iri or not obs.calibration_activity:
            found.append(
                Violation(
                    "R-sensor",
                    "hectare weather requires a sensor and a calibration activity",
                )
            )
        if obs.feature_kind != "instrument-point":
            found.append(
                Violation(
                    "R-sensor",
                    "hectare weather is about the instrument, not an uninstrumented boundary",
                )
            )
    if feature_is_boundary and (obs.sensor_iri or tail == PROC_SENSOR):
        found.append(
            Violation(
                "R-sensor",
                "a sensor value is not written onto a boundary that has no sensor",
            )
        )

    if obs.personal_data and not obs.licence.lawful_basis:
        found.append(
            Violation("R-personal", "personal data requires a lawful basis or it does not load")
        )

    if obs.licence.permits_financial_use:
        instrument = (obs.licence.instrument or "").strip().lower()
        if instrument in {"", "public on the web", "grant not recorded"}:
            found.append(
                Violation(
                    "R-licence",
                    "financial use requires a grant, not a note that the grant is missing",
                )
            )
        if not obs.licence.territory or obs.licence.territory == "not stated":
            found.append(Violation("R-licence", "financial use requires a territory"))
        registration = obs.method.ee_registration
        if registration in {None, "", "unknown", "noncommercial"}:
            found.append(
                Violation(
                    "R-licence",
                    "noncommercial or unknown Earth Engine registration forces financial use false",
                )
            )

    if previous is not None:
        if previous.native_resolution != obs.native_resolution:
            found.append(
                Violation(
                    "R-support",
                    "native resolution is immutable; a revision cannot launder the cell size",
                )
            )
        if previous.feature_of_interest != obs.feature_of_interest:
            found.append(
                Violation(
                    "R-foi",
                    "a revision cannot move the feature of interest onto a different object",
                )
            )
        if obs.revision_of != previous.iri:
            found.append(
                Violation(
                    "R-parallel",
                    "a reprocess cites the previous version and does not replace it in place",
                )
            )

    if obs.error is not None and obs.error.metric not in ERROR_METRICS:
        found.append(Violation("R-error", "unknown error metric"))
    return found


def is_boundary_kind(kind: str) -> bool:
    return kind in {"boundary", "boundary-polygon"}


def boundary_violations(boundary: BoundaryVersion) -> list[Violation]:
    found: list[Violation] = []
    ensure_utc(boundary.boundary_date, "boundary_date")
    if boundary.iri == boundary.geometry_iri:
        found.append(
            Violation("R-foi", "a boundary version is not identical to its geometry literal")
        )
    if boundary.tenure not in TENURE_VALUES:
        found.append(Violation("R-tenure", "tenure is not a recognised value"))
    if boundary.tenure in {"titled", "leased"} and not boundary.tenure_source:
        found.append(
            Violation("R-tenure", f"{boundary.tenure} requires a named source")
        )
    if boundary.accuracy_unknown == (boundary.accuracy_m is not None):
        found.append(
            Violation(
                "R-accuracy",
                "positioning accuracy is a metre value or accuracyUnknown, not both and not neither",
            )
        )
    note = (boundary.accuracy_note or "").lower()
    method = (boundary.digitising_method or "").lower()
    if "privacy" in note or "household-survey" in method:
        found.append(
            Violation(
                "R-accuracy",
                "a privacy-displaced household survey point is not a boundary version",
            )
        )
    if boundary.eudr_syntactic_claim:
        found.append(
            Violation(
                "R-accuracy",
                "the EUDR syntactic flag is computed by the gate; it is not an input bit",
            )
        )
    if boundary.personal_data:
        found.append(
            Violation(
                "R-personal",
                "real personal data is not loaded; Q14 is unanswered",
            )
        )
    return found


def cropping_violations(cropping: Cropping, known_boundaries: set[str]) -> list[Violation]:
    found: list[Violation] = []
    if cropping.mix not in MIX_VALUES:
        found.append(Violation("R-mix", "mix is mono, mixed, or unknown"))
    if cropping.mix == "mono" and len(cropping.crops) != 1:
        found.append(
            Violation("R-mix", "mono is rejected when the crop count is not exactly one")
        )
    if cropping.boundary not in known_boundaries:
        found.append(Violation("R-foi", "cropping cites a boundary that is not in the store"))
    if len(set(cropping.crops)) != len(cropping.crops):
        found.append(Violation("R-mix", "duplicate crop IRIs"))
    return found


def class_b_blockers(
    obs: Observation, region: str, crop: str
) -> list[Violation]:
    """What still blocks a class B reading.

    The public gate calls this only after a named reviewer is set.
    """
    found: list[Violation] = []
    if obs.error is None:
        found.append(
            Violation(
                "R-error",
                "class B needs an error statement whose sample matches, or metric uncalibrated",
            )
        )
        return found
    if obs.error.vendor_confidence is not None and obs.error.metric not in ERROR_METRICS:
        found.append(
            Violation("R-error", "vendor confidence does not satisfy the error shape")
        )
    if obs.error.metric == "vendorConfidence":
        found.append(
            Violation("R-error", "vendor confidence does not satisfy the error shape")
        )
    if obs.error.metric not in ERROR_METRICS:
        found.append(Violation("R-error", "unknown error metric"))
        return found
    if obs.error.metric not in {"uncalibrated", "notApplicable"} and obs.error.value is None:
        found.append(Violation("R-error", "the error value is required for this metric"))
    if obs.error.metric != "uncalibrated":
        if obs.error.sample_region != region or obs.error.sample_crop != crop:
            found.append(
                Violation(
                    "R-error",
                    "the error sample region or crop does not match this fact",
                )
            )
    return found
