from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from farm_ontology.sensors.device_contract import (
    DeviceContractGap,
    NormalizedMeasurement,
    PropertyBinding,
    SensorAdapterManifest,
    validate_normalized_measurement,
)


NOW = datetime(2026, 11, 28, 4, 0, tzinfo=timezone.utc)


def manifest(**changes):
    values = {
        "manifest_id": "sensor-manifest:gw-1:soil-01",
        "manifest_version": "1.0.0",
        "adapter_id": "adapter:example-lorawan",
        "adapter_version": "0.2.0",
        "protocol": "LoRaWAN/1.0.4",
        "vendor": "Example",
        "product_model": "SoilProbe-X",
        "firmware_version": "1.2.3",
        "external_device_id": "soil-01",
        "site_id": "site:tea-01",
        "bindings": (PropertyBinding("soil-vwc", "m3/m3", "point:soil-01:0-20cm"),),
    }
    return SensorAdapterManifest(**{**values, **changes})


def event(**changes):
    values = {
        "manifest_id": "sensor-manifest:gw-1:soil-01",
        "manifest_version": "1.0.0",
        "adapter_id": "adapter:example-lorawan",
        "adapter_version": "0.2.0",
        "external_device_id": "soil-01",
        "site_id": "site:tea-01",
        "property_id": "soil-vwc",
        "value": 0.23,
        "unit_id": "m3/m3",
        "native_support": "point:soil-01:0-20cm",
        "feature_ref": "instrument:soil-01",
        "phenomenon_time": NOW - timedelta(seconds=10),
        "generated_at": NOW - timedelta(seconds=5),
        "available_at": NOW,
        "uncertainty": 0.02,
        "quality": "valid",
        "calibration_ref": "calibration:soil-01:v3",
        "licence_ref": "licence:local-sensor-data",
        "source_ref": "gateway:gw-1:frame-920",
        "raw_payload_sha256": "a" * 64,
        "sequence_id": "920",
    }
    return NormalizedMeasurement(**{**values, **changes})


class SensorDeviceContractTests(unittest.TestCase):
    def test_accepts_valid_event_with_deterministic_identity_and_native_support(self):
        first = validate_normalized_measurement(manifest(), event(), as_of=NOW, max_age_seconds=60)
        replay = validate_normalized_measurement(manifest(), event(), as_of=NOW, max_age_seconds=60)
        self.assertEqual(first.event_id, replay.event_id)
        self.assertEqual(first.measurement.native_support, "point:soil-01:0-20cm")
        self.assertEqual(first.manifest.product_model, "SoilProbe-X")

    def test_refuses_changed_manifest_identity_or_support(self):
        with self.assertRaisesRegex(DeviceContractGap, "manifest-identity-mismatch"):
            validate_normalized_measurement(manifest(), event(adapter_version="0.3.0"), as_of=NOW, max_age_seconds=60)
        with self.assertRaisesRegex(DeviceContractGap, "support-mismatch"):
            validate_normalized_measurement(manifest(), event(native_support="parcel:tea-01"), as_of=NOW, max_age_seconds=60)

    def test_refuses_unknown_property_unit_missing_calibration_and_quality(self):
        cases = [
            (event(property_id="leaf-wetness"), "unsupported-property"),
            (event(unit_id="percent"), "unit-mismatch"),
            (event(calibration_ref=None), "calibration-required"),
            (event(quality="suspect"), "quality-refused"),
        ]
        for reading, reason in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(DeviceContractGap, reason):
                validate_normalized_measurement(manifest(), reading, as_of=NOW, max_age_seconds=60)

    def test_refuses_stale_invalid_time_or_bad_raw_digest(self):
        cases = [
            (event(phenomenon_time=NOW - timedelta(hours=1)), "measurement-stale"),
            (event(available_at=NOW + timedelta(seconds=1)), "future-availability"),
            (event(raw_payload_sha256="not-a-digest"), "raw-digest-invalid"),
            (event(uncertainty=-0.1), "uncertainty-invalid"),
        ]
        for reading, reason in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(DeviceContractGap, reason):
                validate_normalized_measurement(manifest(), reading, as_of=NOW, max_age_seconds=60)

    def test_refuses_manifest_with_write_capability(self):
        with self.assertRaisesRegex(DeviceContractGap, "sensor-write-capability"):
            validate_normalized_measurement(manifest(read_only=False), event(), as_of=NOW, max_age_seconds=60)


if __name__ == "__main__":
    unittest.main()
