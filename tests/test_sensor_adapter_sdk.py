from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from farm_ontology.sensors.adapter_sdk import (
    AdapterRegistry,
    AdapterSdkError,
    LocalSensorOutbox,
    SyntheticSoilVwcAdapter,
    synthetic_soil_uplink,
)


NOW = datetime(2026, 11, 28, 4, 0, tzinfo=timezone.utc)


def registered_event(registry: AdapterRegistry, *, sequence: str = "1", value: float = 23.0):
    payload = synthetic_soil_uplink(
        value_percent=value,
        phenomenon_time=NOW - timedelta(seconds=15),
        generated_at=NOW - timedelta(seconds=5),
        available_at=NOW,
        sequence_id=sequence,
        source_ref=f"fixture:uplink:{sequence}",
    )
    return registry.normalize(
        "adapter.synthetic-soil-vwc",
        "1.0.0",
        payload,
        as_of=NOW,
        max_age_seconds=60,
    )


class SensorAdapterSdkTests(unittest.TestCase):
    def setUp(self):
        self.adapter = SyntheticSoilVwcAdapter.create()
        self.registry = AdapterRegistry()
        self.registry.register(self.adapter)

    def test_exact_adapter_version_required_and_duplicate_rejected(self):
        with self.assertRaisesRegex(AdapterSdkError, "adapter-version-duplicate"):
            self.registry.register(self.adapter)
        with self.assertRaisesRegex(AdapterSdkError, "adapter-version-unregistered"):
            self.registry.get("adapter.synthetic-soil-vwc", "2.0.0")

    def test_synthetic_soil_uplink_passes_contract_and_is_replay_stable(self):
        event_a = registered_event(self.registry)
        event_b = registered_event(self.registry)
        self.assertEqual(event_a.event_id, event_b.event_id)
        self.assertEqual(event_a.measurement.property_id, "soil-vwc")
        self.assertEqual(event_a.measurement.native_support, "point-soil-probe")
        self.assertEqual(event_a.measurement.value, 23.0)

    def test_stale_synthetic_measurement_fails_closed(self):
        payload = synthetic_soil_uplink(
            value_percent=23.0,
            phenomenon_time=NOW - timedelta(hours=1),
            generated_at=NOW - timedelta(minutes=59),
            available_at=NOW,
            sequence_id="old",
        )
        with self.assertRaisesRegex(ValueError, "measurement-stale"):
            self.registry.normalize(
                "adapter.synthetic-soil-vwc", "1.0.0", payload,
                as_of=NOW, max_age_seconds=60,
            )

    def test_outbox_deduplicates_queued_event_and_replays_then_removes(self):
        event = registered_event(self.registry)
        with tempfile.TemporaryDirectory() as temp:
            outbox = LocalSensorOutbox(temp, max_pending_events=3, max_pending_bytes=10_000)
            self.assertTrue(outbox.enqueue(event))
            self.assertFalse(outbox.enqueue(event))
            self.assertEqual(outbox.status()["pending_events"], 1)
            seen = []
            result = outbox.replay(lambda item: seen.append(item.event_id) or True)
            self.assertEqual(result, {"delivered": 1, "deferred": 0, "pending": 0})
            self.assertEqual(seen, [event.event_id])
            self.assertEqual(outbox.pending(), ())

    def test_outbox_roundtrip_preserves_normalized_envelope_and_raw_digest(self):
        event = registered_event(self.registry)
        with tempfile.TemporaryDirectory() as temp:
            outbox = LocalSensorOutbox(temp)
            outbox.enqueue(event)
            (restored,) = outbox.pending()
            self.assertEqual(restored.event_id, event.event_id)
            self.assertEqual(restored.manifest, event.manifest)
            self.assertEqual(restored.measurement, event.measurement)
            self.assertEqual(
                restored.measurement.raw_payload_sha256,
                event.measurement.raw_payload_sha256,
            )

    def test_outbox_retains_deferred_and_exception_events(self):
        event = registered_event(self.registry)
        with tempfile.TemporaryDirectory() as temp:
            outbox = LocalSensorOutbox(temp)
            outbox.enqueue(event)
            result = outbox.replay(lambda item: False)
            self.assertEqual(result, {"delivered": 0, "deferred": 1, "pending": 1})
            with self.assertRaisesRegex(RuntimeError, "sink offline"):
                outbox.replay(lambda item: (_ for _ in ()).throw(RuntimeError("sink offline")))
            self.assertEqual(outbox.status()["pending_events"], 1)

    def test_outbox_enforces_capacity_and_refuses_corrupt_queue_files(self):
        first = registered_event(self.registry, sequence="1")
        second = registered_event(self.registry, sequence="2")
        with tempfile.TemporaryDirectory() as temp:
            outbox = LocalSensorOutbox(temp, max_pending_events=1, max_pending_bytes=10_000)
            outbox.enqueue(first)
            with self.assertRaisesRegex(AdapterSdkError, "queue-full-events"):
                outbox.enqueue(second)
            path = next(Path(temp).glob("*.json"))
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaisesRegex(AdapterSdkError, "queue-entry-corrupt"):
                outbox.pending()

    def test_outbox_enforces_byte_capacity(self):
        event = registered_event(self.registry)
        with tempfile.TemporaryDirectory() as temp:
            outbox = LocalSensorOutbox(temp, max_pending_events=10, max_pending_bytes=1)
            with self.assertRaisesRegex(AdapterSdkError, "queue-full-bytes"):
                outbox.enqueue(event)


if __name__ == "__main__":
    unittest.main()
