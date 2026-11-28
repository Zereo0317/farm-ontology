"""Provider-neutral, read-only contract for normalized sensor adapters.

This validates the evidence envelope produced by a device-specific adapter.
It does not implement a network protocol, talk to hardware, or claim
SensorThings API conformance. Vendor adapters must preserve source semantics
and pass this contract before mapping the event into the farm record store.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
import re

from farm_ontology.agronomy.common import deterministic_id


class DeviceContractGap(ValueError):
    """A normalized device event is incomplete or conflicts with its manifest."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"[device-gap:{code}] {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class PropertyBinding:
    property_id: str
    unit_id: str
    native_support: str
    calibration_required: bool = True


@dataclass(frozen=True)
class SensorAdapterManifest:
    """Versioned capability record for one installed sensor and adapter."""

    manifest_id: str
    manifest_version: str
    adapter_id: str
    adapter_version: str
    protocol: str
    vendor: str
    product_model: str
    firmware_version: str
    external_device_id: str
    site_id: str
    bindings: tuple[PropertyBinding, ...]
    read_only: bool = True


@dataclass(frozen=True)
class NormalizedMeasurement:
    """One adapter output before it is mapped into an ontology Observation."""

    manifest_id: str
    manifest_version: str
    adapter_id: str
    adapter_version: str
    external_device_id: str
    site_id: str
    property_id: str
    value: float
    unit_id: str
    native_support: str
    feature_ref: str
    phenomenon_time: datetime
    generated_at: datetime
    available_at: datetime
    uncertainty: float
    quality: str
    calibration_ref: str | None
    licence_ref: str
    source_ref: str
    raw_payload_sha256: str
    sequence_id: str


@dataclass(frozen=True)
class AcceptedMeasurement:
    """Validated event envelope and replay-stable event identity."""

    event_id: str
    manifest: SensorAdapterManifest
    measurement: NormalizedMeasurement
    validated_at: datetime


_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")


def _require_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DeviceContractGap("missing-field", f"{field} must be a non-empty string")
    return value


def _aware(value: object, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise DeviceContractGap("invalid-time", f"{field} must be a timezone-aware datetime")
    return value


def _finite(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DeviceContractGap("invalid-number", f"{field} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise DeviceContractGap("invalid-number", f"{field} must be a finite number")
    return number


def validate_normalized_measurement(
    manifest: SensorAdapterManifest,
    measurement: NormalizedMeasurement,
    *,
    as_of: datetime,
    max_age_seconds: int,
) -> AcceptedMeasurement:
    """Validate identity, meaning, support, quality, lineage, and freshness.

    An accepted value retains the exact support declared by the sensor
    manifest. The validator never promotes point support to a field or parcel.
    This is an input contract only; a caller still has to perform the normal
    licensing, domain, and store admission checks.
    """

    now = _aware(as_of, "as_of")
    if not isinstance(max_age_seconds, int) or isinstance(max_age_seconds, bool) or max_age_seconds < 0:
        raise DeviceContractGap("invalid-max-age", "max_age_seconds must be a non-negative integer")
    for name in (
        "manifest_id", "manifest_version", "adapter_id", "adapter_version",
        "protocol", "vendor", "product_model", "firmware_version",
        "external_device_id", "site_id",
    ):
        _require_text(getattr(manifest, name), f"manifest.{name}")
    if manifest.read_only is not True:
        raise DeviceContractGap("sensor-write-capability", "sensor adapter manifests must be read-only")
    if not manifest.bindings:
        raise DeviceContractGap("empty-manifest", "at least one property binding is required")
    if len({binding.property_id for binding in manifest.bindings}) != len(manifest.bindings):
        raise DeviceContractGap("duplicate-binding", "property_id bindings must be unique")

    identity_fields = (
        "manifest_id", "manifest_version", "adapter_id", "adapter_version",
        "external_device_id", "site_id",
    )
    for name in identity_fields:
        if getattr(measurement, name) != getattr(manifest, name):
            raise DeviceContractGap("manifest-identity-mismatch", f"measurement {name} does not match manifest")
    binding = next((item for item in manifest.bindings if item.property_id == measurement.property_id), None)
    if binding is None:
        raise DeviceContractGap("unsupported-property", f"property {measurement.property_id!r} is not registered")
    if measurement.unit_id != binding.unit_id:
        raise DeviceContractGap("unit-mismatch", "measurement unit differs from the registered property binding")
    if measurement.native_support != binding.native_support:
        raise DeviceContractGap("support-mismatch", "measurement native support differs from the registered binding")
    _require_text(measurement.feature_ref, "measurement.feature_ref")
    _require_text(measurement.licence_ref, "measurement.licence_ref")
    _require_text(measurement.source_ref, "measurement.source_ref")
    _require_text(measurement.sequence_id, "measurement.sequence_id")
    _require_text(measurement.quality, "measurement.quality")
    if measurement.quality != "valid":
        raise DeviceContractGap("quality-refused", f"measurement quality is {measurement.quality!r}")
    if binding.calibration_required and not measurement.calibration_ref:
        raise DeviceContractGap("calibration-required", "property binding requires a calibration reference")
    if measurement.calibration_ref is not None:
        _require_text(measurement.calibration_ref, "measurement.calibration_ref")
    if not isinstance(measurement.raw_payload_sha256, str) or not _SHA256.fullmatch(measurement.raw_payload_sha256):
        raise DeviceContractGap("raw-digest-invalid", "raw payload digest must be lowercase SHA-256 hex")
    phenomenon = _aware(measurement.phenomenon_time, "measurement.phenomenon_time")
    generated = _aware(measurement.generated_at, "measurement.generated_at")
    available = _aware(measurement.available_at, "measurement.available_at")
    if phenomenon > generated or generated > available:
        raise DeviceContractGap("time-order-invalid", "require phenomenon_time <= generated_at <= available_at")
    if available > now:
        raise DeviceContractGap("future-availability", "measurement availability time is after as_of")
    if (now - phenomenon).total_seconds() > max_age_seconds:
        raise DeviceContractGap("measurement-stale", "phenomenon time exceeds the configured maximum age")
    value = _finite(measurement.value, "measurement.value")
    uncertainty = _finite(measurement.uncertainty, "measurement.uncertainty")
    if uncertainty < 0:
        raise DeviceContractGap("uncertainty-invalid", "uncertainty must be non-negative")

    identity = {
        "manifest_id": manifest.manifest_id,
        "manifest_version": manifest.manifest_version,
        "adapter_id": manifest.adapter_id,
        "adapter_version": manifest.adapter_version,
        "external_device_id": manifest.external_device_id,
        "site_id": manifest.site_id,
        "property_id": measurement.property_id,
        "phenomenon_time": phenomenon.isoformat(),
        "sequence_id": measurement.sequence_id,
        "native_support": binding.native_support,
        "raw_payload_sha256": measurement.raw_payload_sha256,
    }
    # Validate numerical fields without changing the source event. Consumers
    # may use these parsed values for calculations and preserve the raw record.
    if not math.isfinite(value + uncertainty):
        raise DeviceContractGap("numeric-overflow", "value and uncertainty cannot be safely combined")
    return AcceptedMeasurement(
        event_id=deterministic_id("sensor-event", identity),
        manifest=manifest,
        measurement=measurement,
        validated_at=now,
    )


__all__ = [
    "AcceptedMeasurement",
    "DeviceContractGap",
    "NormalizedMeasurement",
    "PropertyBinding",
    "SensorAdapterManifest",
    "validate_normalized_measurement",
]
