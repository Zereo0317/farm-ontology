"""Fail-closed, profile-driven irrigation candidate evaluator.

This is a decision-support optimizer, not an actuator or a replacement for
the existing soybean balance. It ranks caller-provided bounded candidates
only when the exact site profile contains reviewed parameters. The optimizer
uses a conservative upper estimate of root-zone depletion and refuses tea
recommendations while the South China starter profile has no verified
irrigation parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

from farm_ontology.agronomy.common import AgronomyGap
from farm_ontology.agronomy.profiles import (
    CropSiteProfile,
    ProfileContext,
)
from farm_ontology.agronomy.state_estimation import StateEstimate


REQUIRED_PARAMETERS = {
    "root-zone-stress-threshold-mm": "mm",
    "root-zone-refill-capacity-mm": "mm",
    "application-efficiency": "fraction",
    "max-gross-irrigation-mm": "mm",
}


@dataclass(frozen=True)
class IrrigationCandidate:
    """One candidate already bounded by the site's hydraulic model."""

    candidate_id: str
    gross_application_mm: float
    pump_energy_kwh: float


@dataclass(frozen=True)
class IrrigationOptimization:
    """Replayable candidate ranking; never authorizes a command."""

    profile_id: str
    profile_version: str
    state_key: str
    selected_candidate_id: str
    gross_application_mm: float
    effective_application_mm: float
    projected_depletion_upper_mm: float
    objective_cost: float
    feasible_candidates: tuple[dict, ...]
    rejected_candidates: tuple[dict, ...]
    parameter_ids: tuple[str, ...]
    control_authorized: bool = False
    mode: str = "advisory-only"

    def to_payload(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "state_key": self.state_key,
            "selected_candidate_id": self.selected_candidate_id,
            "gross_application_mm": self.gross_application_mm,
            "effective_application_mm": self.effective_application_mm,
            "projected_depletion_upper_mm": self.projected_depletion_upper_mm,
            "objective_cost": self.objective_cost,
            "feasible_candidates": [dict(row) for row in self.feasible_candidates],
            "rejected_candidates": [dict(row) for row in self.rejected_candidates],
            "parameter_ids": list(self.parameter_ids),
            "control_authorized": False,
            "mode": self.mode,
        }


def _finite(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AgronomyGap("irrigation-optimizer-invalid-input", f"{name} must be finite numeric")
    result = float(value)
    if not math.isfinite(result):
        raise AgronomyGap("irrigation-optimizer-invalid-input", f"{name} must be finite numeric")
    return result


def _profile_parameter(profile: CropSiteProfile, context: ProfileContext, name: str, unit: str) -> float:
    parameter = profile.require_parameter(name, context)
    if parameter.unit != unit:
        raise AgronomyGap(
            "irrigation-profile-unit-mismatch",
            f"{name} must use {unit}; profile declares {parameter.unit}",
        )
    value = _finite(parameter.value, f"profile.{name}")
    return value


def optimize_irrigation_candidates(
    *,
    profile: CropSiteProfile,
    context: ProfileContext,
    state: StateEstimate,
    forecast_et_mm: float,
    forecast_rain_mm: float,
    uncertainty_multiplier: float,
    candidates: Sequence[IrrigationCandidate],
    water_cost_per_mm: float,
    energy_cost_per_kwh: float,
) -> IrrigationOptimization:
    """Choose the lowest-cost feasible candidate under reviewed site limits.

    Candidates must come from the site hydraulic capability model. The risk
    bound is ``depletion + uncertainty_multiplier * sqrt(variance)``. Forecast
    ET/rain are supplied as already licensed, provenance-bearing values by
    the caller. There are no hidden defaults and no device dispatch here.
    """

    if not profile.applies_to(context):
        raise AgronomyGap("profile-out-of-scope", "irrigation optimizer profile does not apply to context")
    if state.unit != "mm-depletion" or not state.state_key or not state.source_ref:
        raise AgronomyGap(
            "irrigation-state-incomplete",
            "state must declare mm-depletion, an exact support/layer state_key, and source_ref",
        )
    if state.variance <= 0 or not math.isfinite(state.variance):
        raise AgronomyGap("irrigation-state-uncertainty-invalid", "state variance must be finite and positive")
    state_value = _finite(state.value, "state.value")
    et = _finite(forecast_et_mm, "forecast_et_mm")
    rain = _finite(forecast_rain_mm, "forecast_rain_mm")
    risk = _finite(uncertainty_multiplier, "uncertainty_multiplier")
    water_weight = _finite(water_cost_per_mm, "water_cost_per_mm")
    energy_weight = _finite(energy_cost_per_kwh, "energy_cost_per_kwh")
    if min(et, rain, risk, water_weight, energy_weight) < 0:
        raise AgronomyGap("irrigation-optimizer-invalid-input", "forecast and objective inputs must be non-negative")
    if not candidates:
        raise AgronomyGap("irrigation-candidates-missing", "at least one bounded candidate is required")

    parameters = {
        key: _profile_parameter(profile, context, key, unit)
        for key, unit in REQUIRED_PARAMETERS.items()
    }
    threshold = parameters["root-zone-stress-threshold-mm"]
    refill_cap = parameters["root-zone-refill-capacity-mm"]
    efficiency = parameters["application-efficiency"]
    max_gross = parameters["max-gross-irrigation-mm"]
    if threshold < 0 or refill_cap < 0 or max_gross < 0 or not 0 < efficiency <= 1:
        raise AgronomyGap("irrigation-profile-parameter-invalid", "verified irrigation parameters are outside physical bounds")
    if threshold > refill_cap:
        raise AgronomyGap("irrigation-profile-parameter-invalid", "stress threshold exceeds refill capacity")

    upper_depletion = state_value + risk * math.sqrt(state.variance) + et - rain
    if upper_depletion < 0:
        upper_depletion = 0.0
    feasible: list[dict] = []
    rejected: list[dict] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate.candidate_id, str) or not candidate.candidate_id.strip():
            raise AgronomyGap("irrigation-candidate-invalid", "candidate_id must be non-empty")
        if candidate.candidate_id in seen:
            raise AgronomyGap("irrigation-candidate-duplicate", f"duplicate candidate {candidate.candidate_id}")
        seen.add(candidate.candidate_id)
        gross = _finite(candidate.gross_application_mm, "candidate.gross_application_mm")
        energy = _finite(candidate.pump_energy_kwh, "candidate.pump_energy_kwh")
        if gross < 0 or energy < 0:
            raise AgronomyGap("irrigation-candidate-invalid", "candidate application and energy must be non-negative")
        if gross > max_gross:
            rejected.append({"candidate_id": candidate.candidate_id, "reason": "exceeds-profile-maximum"})
            continue
        effective = gross * efficiency
        if effective > refill_cap:
            rejected.append({"candidate_id": candidate.candidate_id, "reason": "exceeds-refill-capacity"})
            continue
        projected = max(0.0, upper_depletion - effective)
        if projected > threshold:
            rejected.append({"candidate_id": candidate.candidate_id, "reason": "stress-bound-not-met"})
            continue
        objective = gross * water_weight + energy * energy_weight
        feasible.append({
            "candidate_id": candidate.candidate_id,
            "gross_application_mm": gross,
            "effective_application_mm": effective,
            "projected_depletion_upper_mm": projected,
            "pump_energy_kwh": energy,
            "objective_cost": objective,
        })
    if not feasible:
        raise AgronomyGap(
            "irrigation-no-feasible-candidate",
            "no supplied candidate satisfies the verified stress, refill, and hydraulic bounds",
            missing=("feasible-hydraulic-candidate",),
        )
    selected = min(feasible, key=lambda row: (row["objective_cost"], row["gross_application_mm"], row["candidate_id"]))
    return IrrigationOptimization(
        profile_id=profile.profile_id,
        profile_version=profile.version,
        state_key=state.state_key,
        selected_candidate_id=selected["candidate_id"],
        gross_application_mm=selected["gross_application_mm"],
        effective_application_mm=selected["effective_application_mm"],
        projected_depletion_upper_mm=selected["projected_depletion_upper_mm"],
        objective_cost=selected["objective_cost"],
        feasible_candidates=tuple(feasible),
        rejected_candidates=tuple(rejected),
        parameter_ids=tuple(REQUIRED_PARAMETERS),
    )


__all__ = [
    "IrrigationCandidate",
    "IrrigationOptimization",
    "REQUIRED_PARAMETERS",
    "optimize_irrigation_candidates",
]
