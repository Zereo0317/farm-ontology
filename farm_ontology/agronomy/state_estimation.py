"""Evidence-bounded scalar state assimilation for closed-loop agronomy.

This module combines a prediction and one calibrated measurement only when
their declared state key and unit match exactly. A state key must encode the
same property, spatial support, crop/management zone and (where relevant)
soil layer. The result is still scoped to that key; it is never promoted to a
parcel estimate and is never an actuator command or recommendation.

The scalar Kalman update is a small, deterministic primitive, not a complete
farm feedback controller. Policy, crop models, event/outcome learning and
actuation authorization remain separate layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math

from farm_ontology.agronomy.common import AgronomyGap, deterministic_id


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AgronomyGap("invalid-state-value", f"{field} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise AgronomyGap("invalid-state-value", f"{field} must be a finite number")
    return result


def _aware(value: datetime, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise AgronomyGap("invalid-state-time", f"{field} must be an aware datetime")
    return value


@dataclass(frozen=True)
class StateEstimate:
    """Prior state estimate with variance and immutable native support key."""

    state_key: str
    value: float
    variance: float
    unit: str
    valid_at: datetime
    source_ref: str


@dataclass(frozen=True)
class CalibratedMeasurement:
    """A sensor measurement already checked against a calibration record."""

    state_key: str
    value: float
    variance: float
    unit: str
    observed_at: datetime
    sensor_ref: str
    calibration_ref: str | None
    calibrated: bool
    quality: str = "valid"


@dataclass(frozen=True)
class Assimilation:
    """Replayable posterior plus diagnostic residual; no action semantics."""

    assimilation_id: str
    state_key: str
    prior_ref: str
    measurement_ref: str
    calibration_ref: str
    observed_at: datetime
    prior_value: float
    prior_variance: float
    measurement_value: float
    measurement_variance: float
    residual: float
    normalized_residual: float
    gain: float
    posterior_value: float
    posterior_variance: float
    unit: str
    algorithm: str = "scalar-kalman-v1"

    def to_payload(self) -> dict:
        return {
            "assimilation_id": self.assimilation_id,
            "state_key": self.state_key,
            "prior_ref": self.prior_ref,
            "measurement_ref": self.measurement_ref,
            "calibration_ref": self.calibration_ref,
            "observed_at": self.observed_at.isoformat(),
            "prior_value": self.prior_value,
            "prior_variance": self.prior_variance,
            "measurement_value": self.measurement_value,
            "measurement_variance": self.measurement_variance,
            "residual": self.residual,
            "normalized_residual": self.normalized_residual,
            "gain": self.gain,
            "posterior_value": self.posterior_value,
            "posterior_variance": self.posterior_variance,
            "unit": self.unit,
            "algorithm": self.algorithm,
            "status": "state-updated-advisory-only",
            "actuation_authorized": False,
        }


def assimilate_measurement(
    prior: StateEstimate,
    measurement: CalibratedMeasurement,
    *,
    as_of: datetime,
    max_age_seconds: int,
) -> Assimilation:
    """Assimilate one fresh, calibrated measurement into a matching prior.

    ``state_key`` must be an explicit, canonical key containing the precise
    target support and layer. This function requires exact key equality and
    does not infer spatial or vertical relationships.
    """

    now = _aware(as_of, "as_of")
    prior_at = _aware(prior.valid_at, "prior.valid_at")
    observed_at = _aware(measurement.observed_at, "measurement.observed_at")
    if not prior.state_key or not measurement.state_key or prior.state_key != measurement.state_key:
        raise AgronomyGap(
            "state-support-mismatch",
            "prior and measurement must have the same explicit state key, including support and layer",
        )
    if not prior.unit or prior.unit != measurement.unit:
        raise AgronomyGap("state-unit-mismatch", "prior and measurement units must match exactly")
    if not measurement.calibrated or not measurement.calibration_ref:
        raise AgronomyGap("uncalibrated-measurement", "state assimilation requires a calibration reference")
    if measurement.quality != "valid":
        raise AgronomyGap("invalid-measurement-quality", f"measurement quality is {measurement.quality!r}")
    if not prior.source_ref or not measurement.sensor_ref:
        raise AgronomyGap("missing-state-lineage", "prior and measurement source references are required")
    if isinstance(max_age_seconds, bool) or not isinstance(max_age_seconds, int) or max_age_seconds < 0:
        raise AgronomyGap("invalid-max-age", "max_age_seconds must be a non-negative integer")
    if observed_at > now:
        raise AgronomyGap("future-measurement", "measurement timestamp is after as_of")
    if observed_at < prior_at:
        raise AgronomyGap("measurement-before-prior", "measurement predates the prior state")
    prior_age = (observed_at - prior_at).total_seconds()
    if prior_age > max_age_seconds:
        raise AgronomyGap("stale-prior-state", f"prior state age {prior_age:g}s exceeds {max_age_seconds}s")
    age = (now - observed_at).total_seconds()
    if age > max_age_seconds:
        raise AgronomyGap("stale-measurement", f"measurement age {age:g}s exceeds {max_age_seconds}s")

    x_prior = _finite_number(prior.value, "prior.value")
    p_prior = _finite_number(prior.variance, "prior.variance")
    z = _finite_number(measurement.value, "measurement.value")
    r = _finite_number(measurement.variance, "measurement.variance")
    if p_prior <= 0 or r <= 0:
        raise AgronomyGap("invalid-state-variance", "prior and measurement variances must be positive")

    innovation_variance = p_prior + r
    residual = z - x_prior
    gain = p_prior / innovation_variance
    posterior = x_prior + gain * residual
    posterior_variance = (p_prior * r) / innovation_variance
    identity = {
        "algorithm": "scalar-kalman-v1",
        "state_key": prior.state_key,
        "prior_ref": prior.source_ref,
        "measurement_ref": measurement.sensor_ref,
        "calibration_ref": measurement.calibration_ref,
        "observed_at": observed_at.isoformat(),
        "unit": prior.unit,
        "prior_value": x_prior,
        "prior_variance": p_prior,
        "measurement_value": z,
        "measurement_variance": r,
    }
    return Assimilation(
        assimilation_id=deterministic_id("assimilation", identity),
        state_key=prior.state_key,
        prior_ref=prior.source_ref,
        measurement_ref=measurement.sensor_ref,
        calibration_ref=measurement.calibration_ref,
        observed_at=observed_at,
        prior_value=x_prior,
        prior_variance=p_prior,
        measurement_value=z,
        measurement_variance=r,
        residual=residual,
        normalized_residual=residual / math.sqrt(innovation_variance),
        gain=gain,
        posterior_value=posterior,
        posterior_variance=posterior_variance,
        unit=prior.unit,
    )


__all__ = [
    "Assimilation",
    "CalibratedMeasurement",
    "StateEstimate",
    "assimilate_measurement",
]
