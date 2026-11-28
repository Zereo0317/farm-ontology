"""Stdlib-only sensor adapter registry, simulator, and offline outbox.

This is a local SDK boundary, not a network client. Vendor/protocol adapters
decode their source payloads into ``NormalizedMeasurement``; the common
validator checks evidence before an event may be buffered. The synthetic
adapter below exercises this path without a broker, radio, or device.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Callable, Mapping, Protocol

from farm_ontology.agronomy.common import canonical_json
from farm_ontology.sensors.device_contract import (
    AcceptedMeasurement,
    DeviceContractGap,
    NormalizedMeasurement,
    PropertyBinding,
    SensorAdapterManifest,
    validate_normalized_measurement,
)


class AdapterSdkError(ValueError):
    """Named adapter, fixture, or queue boundary failure."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"[adapter-sdk:{code}] {detail}")
        self.code = code
        self.detail = detail


class SensorAdapter(Protocol):
    """A versioned source decoder. Implementations must not perform I/O here."""

    manifest: SensorAdapterManifest

    def decode(self, payload: Mapping[str, object]) -> NormalizedMeasurement:
        """Return one normalized event; transport metadata must be explicit."""


class AdapterRegistry:
    """Exact-version registry; no nearest-version or vendor fallback."""

    def __init__(self) -> None:
        self._adapters: dict[tuple[str, str], SensorAdapter] = {}

    def register(self, adapter: SensorAdapter) -> None:
        manifest = getattr(adapter, "manifest", None)
        if not isinstance(manifest, SensorAdapterManifest):
            raise AdapterSdkError("manifest-missing", "adapter must expose a SensorAdapterManifest")
        key = (manifest.adapter_id, manifest.adapter_version)
        if key in self._adapters:
            raise AdapterSdkError("adapter-version-duplicate", f"adapter version already registered: {key}")
        if manifest.read_only is not True:
            raise AdapterSdkError("sensor-write-capability", "sensor SDK accepts read-only adapters only")
        self._adapters[key] = adapter

    def get(self, adapter_id: str, version: str) -> SensorAdapter:
        try:
            return self._adapters[(adapter_id, version)]
        except KeyError as error:
            raise AdapterSdkError(
                "adapter-version-unregistered",
                f"no exact adapter version registered for {(adapter_id, version)!r}",
            ) from error

    def normalize(
        self,
        adapter_id: str,
        version: str,
        payload: Mapping[str, object],
        *,
        as_of: datetime,
        max_age_seconds: int,
    ) -> AcceptedMeasurement:
        adapter = self.get(adapter_id, version)
        event = adapter.decode(payload)
        try:
            return validate_normalized_measurement(
                adapter.manifest,
                event,
                as_of=as_of,
                max_age_seconds=max_age_seconds,
            )
        except DeviceContractGap:
            raise


@dataclass(frozen=True)
class SyntheticSoilVwcAdapter:
    """Offline fixture decoder for the first soil-moisture SDK path.

    The payload is a local fixture format; it is not a LoRaWAN, ChirpStack,
    MQTT, or vendor wire format.
    """

    manifest: SensorAdapterManifest

    @classmethod
    def create(
        cls,
        *,
        site_id: str = "site:tea-demo",
        device_id: str = "soil-probe-01",
        depth_cm: float = 20.0,
        calibration_ref: str = "calibration:soil-probe-01:v1",
    ) -> "SyntheticSoilVwcAdapter":
        manifest = SensorAdapterManifest(
            manifest_id=f"sensor-manifest:{site_id}:{device_id}",
            manifest_version="1.0.0",
            adapter_id="adapter.synthetic-soil-vwc",
            adapter_version="1.0.0",
            protocol="fixture",
            vendor="synthetic",
            product_model="soil-vwc-fixture",
            firmware_version="fixture-1",
            external_device_id=device_id,
            site_id=site_id,
            bindings=(PropertyBinding(
                property_id="soil-vwc",
                unit_id="http://qudt.org/vocab/unit/PERCENT",
                native_support="point-soil-probe",
                calibration_required=True,
            ),),
            read_only=True,
        )
        return cls(manifest=manifest)

    def decode(self, payload: Mapping[str, object]) -> NormalizedMeasurement:
        if not isinstance(payload, Mapping):
            raise AdapterSdkError("fixture-invalid", "synthetic payload must be a mapping")
        required = (
            "phenomenon_time", "generated_at", "available_at", "sequence_id",
            "value_percent", "calibration_ref", "licence_ref", "source_ref",
            "calibration_valid_until", "depth_cm",
        )
        missing = [name for name in required if name not in payload]
        if missing:
            raise AdapterSdkError("fixture-missing-field", f"synthetic payload missing {missing}")
        try:
            raw = canonical_json(dict(payload))
        except (TypeError, ValueError) as error:
            raise AdapterSdkError("fixture-not-json", "synthetic payload must be canonical-JSON serializable") from error
        raw_hash = hashlib.sha256(raw).hexdigest()
        calibration_ref = _require_fixture_text(payload["calibration_ref"], "calibration_ref")
        licence_ref = _require_fixture_text(payload["licence_ref"], "licence_ref")
        source_ref = _require_fixture_text(payload["source_ref"], "source_ref")
        sequence_id = _require_fixture_text(payload["sequence_id"], "sequence_id")
        return NormalizedMeasurement(
            manifest_id=self.manifest.manifest_id,
            manifest_version=self.manifest.manifest_version,
            adapter_id=self.manifest.adapter_id,
            adapter_version=self.manifest.adapter_version,
            external_device_id=self.manifest.external_device_id,
            site_id=self.manifest.site_id,
            property_id="soil-vwc",
            value=payload["value_percent"],
            unit_id="http://qudt.org/vocab/unit/PERCENT",
            native_support="point-soil-probe",
            feature_ref=f"https://example.invalid/farm/{self.manifest.site_id}/instrument/{self.manifest.external_device_id}",
            phenomenon_time=_parse_time(payload["phenomenon_time"], "phenomenon_time"),
            generated_at=_parse_time(payload["generated_at"], "generated_at"),
            available_at=_parse_time(payload["available_at"], "available_at"),
            uncertainty=payload.get("uncertainty_percent", 0.0),
            quality=payload.get("quality", "valid"),
            calibration_ref=calibration_ref,
            licence_ref=licence_ref,
            source_ref=source_ref,
            raw_payload_sha256=raw_hash,
            sequence_id=sequence_id,
        )


def _parse_time(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise AdapterSdkError("fixture-time-invalid", f"{field} must be a non-empty ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise AdapterSdkError("fixture-time-invalid", f"{field} is not valid ISO-8601") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AdapterSdkError("fixture-time-naive", f"{field} must include a timezone offset")
    return parsed


def _require_fixture_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AdapterSdkError("fixture-field-invalid", f"{field} must be a non-empty string")
    return value


class LocalSensorOutbox:
    """Bounded local at-least-once queue for accepted measurements.

    Events are atomically created as immutable files and remain until a sink
    callback confirms durable acceptance. If the process exits after sink
    acceptance but before queue removal, replay can deliver a duplicate; sinks
    must deduplicate using ``AcceptedMeasurement.event_id``. Only one local
    outbox process should write a queue directory at a time.
    """

    _EVENT_ID = re.compile(r"\Asensor-event:[0-9a-f]{32}\Z")

    def __init__(
        self,
        directory: str | Path,
        *,
        max_pending_events: int = 1000,
        max_pending_bytes: int = 16 * 1024 * 1024,
    ) -> None:
        if isinstance(max_pending_events, bool) or not isinstance(max_pending_events, int) or max_pending_events <= 0:
            raise AdapterSdkError("queue-cap-invalid", "max_pending_events must be a positive integer")
        if isinstance(max_pending_bytes, bool) or not isinstance(max_pending_bytes, int) or max_pending_bytes <= 0:
            raise AdapterSdkError("queue-cap-invalid", "max_pending_bytes must be a positive integer")
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.max_pending_events = max_pending_events
        self.max_pending_bytes = max_pending_bytes

    @staticmethod
    def _event_json(event: AcceptedMeasurement) -> bytes:
        document = {
            "event_id": event.event_id,
            "validated_at": event.validated_at.isoformat(),
            "manifest": asdict(event.manifest),
            "measurement": asdict(event.measurement),
        }
        for key, value in document["measurement"].items():
            if isinstance(value, datetime):
                document["measurement"][key] = value.isoformat()
        return canonical_json(document)

    def _path(self, event_id: str) -> Path:
        if not isinstance(event_id, str) or not self._EVENT_ID.fullmatch(event_id):
            raise AdapterSdkError("event-id-invalid", "event_id must be a sensor-event SHA-256 prefix")
        digest = hashlib.sha256(event_id.encode("utf-8")).hexdigest()
        return self.directory / f"{digest}.json"

    def _pending_paths(self) -> list[Path]:
        paths = sorted(self.directory.glob("*.json"))
        if any(not path.is_file() for path in paths):
            raise AdapterSdkError("queue-entry-invalid", "queue directory contains a non-file event entry")
        return paths

    def _usage(self) -> tuple[int, int]:
        paths = self._pending_paths()
        return len(paths), sum(path.stat().st_size for path in paths)

    def enqueue(self, event: AcceptedMeasurement) -> bool:
        """Atomically add an event; return False when it is already pending."""
        if not isinstance(event, AcceptedMeasurement):
            raise AdapterSdkError("event-invalid", "outbox accepts validated AcceptedMeasurement values only")
        target = self._path(event.event_id)
        content = self._event_json(event)
        if target.exists():
            try:
                existing = json.loads(target.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise AdapterSdkError("queue-entry-corrupt", f"cannot verify pending event {target.name}") from error
            if existing.get("event_id") != event.event_id:
                raise AdapterSdkError("event-id-collision", "existing queue file has a different event id")
            if canonical_json(existing) != content:
                raise AdapterSdkError("event-payload-conflict", "same event id has different pending content")
            return False
        count, used_bytes = self._usage()
        if count >= self.max_pending_events:
            raise AdapterSdkError("queue-full-events", "pending event limit reached; refuse new telemetry")
        if used_bytes + len(content) > self.max_pending_bytes:
            raise AdapterSdkError("queue-full-bytes", "pending byte limit reached; refuse new telemetry")
        fd, temporary_name = tempfile.mkstemp(prefix=".pending-", dir=self.directory)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, target)
            except FileExistsError:
                return False
        finally:
            temporary.unlink(missing_ok=True)
        return True

    def pending(self) -> tuple[AcceptedMeasurement, ...]:
        events: list[AcceptedMeasurement] = []
        for path in self._pending_paths():
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
                manifest_doc = document["manifest"]
                manifest_doc["bindings"] = tuple(PropertyBinding(**row) for row in manifest_doc["bindings"])
                manifest = SensorAdapterManifest(**manifest_doc)
                measurement_doc = document["measurement"]
                for key in ("phenomenon_time", "generated_at", "available_at"):
                    measurement_doc[key] = _parse_time(measurement_doc[key], key)
                measurement = NormalizedMeasurement(**measurement_doc)
                accepted = AcceptedMeasurement(
                    event_id=document["event_id"],
                    manifest=manifest,
                    measurement=measurement,
                    validated_at=_parse_time(document["validated_at"], "validated_at"),
                )
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                raise AdapterSdkError("queue-entry-corrupt", f"invalid queue event {path.name}") from error
            if self._path(accepted.event_id) != path:
                raise AdapterSdkError("queue-entry-path-mismatch", f"event identity does not match {path.name}")
            events.append(accepted)
        events.sort(key=lambda item: (item.measurement.phenomenon_time, item.event_id))
        return tuple(events)

    def replay(self, deliver: Callable[[AcceptedMeasurement], bool]) -> dict[str, int]:
        """Deliver pending events in event time order; retain false/failed rows.

        ``deliver`` must return True only after the sink has durably accepted
        the event or confirmed it already exists under the same event id.
        Exceptions propagate; the current and later files remain queued.
        """
        if not callable(deliver):
            raise AdapterSdkError("sink-invalid", "deliver must be a callable idempotent sink")
        delivered = deferred = 0
        queued = self.pending()
        for index, event in enumerate(queued):
            if deliver(event) is True:
                self._path(event.event_id).unlink(missing_ok=True)
                delivered += 1
            else:
                deferred = len(queued) - index
                break
        return {"delivered": delivered, "deferred": deferred, "pending": len(self._pending_paths())}

    def status(self) -> dict[str, int]:
        count, used = self._usage()
        return {
            "pending_events": count,
            "pending_bytes": used,
            "max_pending_events": self.max_pending_events,
            "max_pending_bytes": self.max_pending_bytes,
        }


def synthetic_soil_uplink(
    *,
    value_percent: float,
    phenomenon_time: datetime,
    generated_at: datetime,
    available_at: datetime,
    sequence_id: str,
    calibration_valid_until: str = "2027-12-31",
    uncertainty_percent: float = 2.0,
    calibration_ref: str = "calibration:soil-probe-01:v1",
    licence_ref: str = "licence:site-owned-sensor-data",
    source_ref: str = "fixture:uplink",
) -> dict[str, object]:
    """Return a deterministic local fixture frame; no radio/MQTT is used."""
    return {
        "phenomenon_time": phenomenon_time.isoformat(),
        "generated_at": generated_at.isoformat(),
        "available_at": available_at.isoformat(),
        "sequence_id": sequence_id,
        "value_percent": value_percent,
        "uncertainty_percent": uncertainty_percent,
        "calibration_ref": calibration_ref,
        "calibration_valid_until": calibration_valid_until,
        "depth_cm": 20.0,
        "licence_ref": licence_ref,
        "source_ref": source_ref,
        "quality": "valid",
    }


__all__ = [
    "AdapterRegistry",
    "AdapterSdkError",
    "LocalSensorOutbox",
    "SensorAdapter",
    "SyntheticSoilVwcAdapter",
    "synthetic_soil_uplink",
]
