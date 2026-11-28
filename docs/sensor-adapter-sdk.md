# Sensor adapter SDK and local outbox

Status: **offline SDK and simulator only**. No broker, radio, network server,
physical sensor, or actuator is contacted by this implementation.

## What this adds

`farm_ontology.sensors.adapter_sdk` defines a small stdlib-only interface for
versioned read-only sensor decoders, an exact-version registry, a deterministic
soil-moisture fixture adapter, and a bounded local event outbox. All decoded
events pass through `validate_normalized_measurement` before queueing. The
event retains its manifest and adapter version, device/site identity, measured
property and unit, native support, phenomenon/generated/available times,
uncertainty and quality, calibration/licence/source references, sequence ID,
and a SHA-256 digest of the raw fixture.

The fixture is **not** an MQTT, LoRaWAN, ChirpStack, or vendor wire payload.
It tests the normalized boundary without pretending a named product or
firmware combination has been integrated. Future protocol packages should
decode their input to `NormalizedMeasurement`, register a unique adapter
version, then use the same evidence validator and outbox.

## Queue behavior

- Enqueue atomically creates one immutable file per deterministic event ID.
- A repeated event already waiting in the queue returns `False`; it is not
  copied again.
- Event count and byte caps refuse new telemetry when full. The caller must
  alert or stop intake; it must not delete unacknowledged entries to make room.
- Replay is at-least-once. A file is removed only after the caller's sink
  returns `True`, meaning the sink durably accepted the event or recognized
  the same event ID as already stored.
- A crash after the sink commits but before queue removal can replay a
  duplicate. Sinks must deduplicate by `event_id`; multiple processes must
  not share one queue directory.
- Corrupt queue files fail closed and remain for recovery. The queue has no
  silent repair or event dropping policy.

The callback-based sink is the integration seam. The existing governed
`ingest_device_json` accepts a narrow legacy JSON contract and the base
`Observation` record does not yet retain every field in the normalized event
(raw digest, source reference, adapter identity, and the full unit/error
evidence). Therefore this SDK does not silently map a generic event into the
Store and lose lineage. A producer-to-Store mapping must be added with an
explicit provenance-preserving `Observation` extension and tests before a
protocol adapter is accepted into a farm record.

## Standards context checked 2026-11

- [OGC SensorThings API 2.0](https://docs.ogc.org/is/23-019/23-019.html) was
  published 2026-11-04 and defines observation semantics plus HTTP and MQTT
  bindings. It is a northbound data API, not a LoRaWAN radio or Modbus driver.
- [OASIS MQTT 5.0](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html)
  is the published transport baseline. QoS 1 may redeliver messages; stable
  event IDs and idempotent sinks are required.
- LoRaWAN radio/network-server integration is a distinct adapter. The LoRa
  Alliance's [TS014 device-capabilities API](https://resources.lora-alliance.org/document/ts014-1-0-0-end-device-capabilities-api)
  and [TS018 device-identification QR profile](https://resources.lora-alliance.org/home/ts018-1-0-0-lorawan-device-identification-qr-codes-for-automated-onboarding)
  are useful onboarding inputs; region plan, radio certification, gateway,
  network server, join server/key custody, codec and exact device firmware
  still require a named profile and acceptance evidence.

The references guide future adapters; they do not make this SDK conformant
with those standards. Each production adapter needs source-specific mapping
fixtures, protocol/schema checks, endpoint/device bilateral testing, security
review, and a recorded compatibility tuple.

## Next acceptance steps

1. Add site inventory and select the first actual sensor, firmware, gateway,
   and network-server combination.
2. Implement its isolated protocol decoder and tests for normal, malformed,
   duplicate, stale, out-of-order, calibration-expiry, and offline replay
   cases. Keep protocol dependencies outside `farm_ontology` core.
3. Extend observation persistence so the adapter lineage and quality fields
   survive Store admission without rewriting native support.
4. Run a read-only bench and field acceptance with the named equipment before
   enabling the adapter for real farm data.

