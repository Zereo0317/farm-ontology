# Global interoperability profile

**Reviewed:** 2026-11-28. **Purpose:** a build-and-acceptance profile for
connecting farm-ontology to sensors, geospatial services, imagery catalogs,
and agricultural machinery across regions. This document records standards
and evidence boundaries; it does not declare this repository compliant with
any external standard.

## Status vocabulary

- **Reference:** standard selected for an interface/model design; no
  implementation or conformance claim follows.
- **Implemented profile:** repository code implements a stated subset or
  mapping. The subset is not automatically conformant to the complete
  standard.
- **Compatible with a named endpoint/device:** an interoperability test has
  passed against that exact product, firmware, profile, configuration, and
  test fixture. Compatibility is scoped; it is not standards certification.
- **Conformant/certified:** use only after all applicable normative
  conformance requirements have been tested. For OGC certification, cite the
  product and certificate/test report. Never infer this status from JSON
  shape, schema validation, or one successful exchange.

## Standards map and repository evidence

| Standard | Use in the system | Evidence/status in this repository (reviewed 2026-11-28) |
| --- | --- | --- |
| [OGC SensorThings API 2.0](https://docs.ogc.org/is/23-019/23-019.html) | Network-facing sensor/observation exchange; its model is aligned to observations, measurements, and samples. HTTP and MQTT bindings are specified. | **Reference; no SensorThings service/client conformance evidence found.** The current sensor path consumes device JSON locally in `farm_ontology/sensors/ingest.py`; `farm_ontology/sensors/device_contract.py` adds a local normalized-envelope validator, but neither implements this API. OGC publication identifies v2.0 as approved 2026-09-14 and published 2026-11-04. |
| [ISO 19156:2023](https://www.iso.org/standard/82463.html) and [W3C SOSA/SSN Recommendation](https://www.w3.org/TR/vocab-ssn/) | Shared observation, result, procedure, sensor, feature-of-interest and sampling semantics. Use SOSA as a lightweight semantic mapping target; keep ISO 19156 as the conceptual observation model. | **Reference; partial vocabulary use, no complete exchange mapping or conformance suite found.** `ontology/fd-decision.ttl`, `farm_ontology/namespaces.py`, and `farm_ontology/query.py` reference SOSA, but repository `Observation` records and sensor ingest remain internal contracts. The W3C 2017 Recommendation remains the cited stable baseline; the 2026 SSN 2023 edition is a Working Draft and is not used here as a normative baseline. |
| [STAC 1.1 Community Standard](https://docs.ogc.org/cs/25-004/25-004.html) and [STAC API 1.0](https://docs.ogc.org/cs/25-005/25-005.html) | Discover and describe satellite, drone, DEM, and derived geospatial assets, with links to the actual data assets. | **Reference; no STAC Item, Catalog, or API implementation evidence found.** A raster/NDVI feed existing by itself would not prove STAC support. |
| [OGC API – Features](https://www.ogc.org/standards/ogcapi-features/) | Read/query parcel, field, zone, trap, and other vector features through a standard web API. Part 1 Core uses WGS 84 longitude/latitude; CRS-by-reference and other parts have their own requirements. | **Reference; no conformant API or OGC validator result found.** Internal geometry handling or GeoJSON output alone is not OGC API Features conformance. |
| [ISO 11783-10:2015](https://www.iso.org/standard/61581.html) | Task Controller / farm-management information exchange for machinery operations. | **Implemented farm-ontology TaskData profile, not full ISO conformance.** `farm_ontology/actuation/taskset_export.py` emits an offline TaskSet-shaped ZIP and validates against the repository's own profile schema. `docs/actuation-interface-spec.md` explicitly says controller acceptance is unproven. ISO lists the 2015 edition as current after review/confirmation in 2026. |
| [ISO 11783-11:2011](https://www.iso.org/standard/57849.html) | Mobile Data Element Dictionary identifiers used with ISO 11783 process data. | **Reference; no registered MDD mapping or controller acceptance evidence found.** Do not invent or locally assign standard identifiers. ISO lists the 2011 edition as current after confirmation in 2021. |
| [ISO 25119-1:2018](https://www.iso.org/standard/69025.html) | Safety lifecycle principles for safety-related control-system parts on agricultural/forestry machinery. Relevant before any closed-loop or safety-related control is designed or marketed. | **Governance reference only; no safety lifecycle assessment or conformity evidence found.** The existing Phase-4 gate and human approval are not ISO 25119 compliance. ISO lists the 2018 edition as published and to be revised; monitor the ISO project page and assess applicable parts/editions with a qualified safety engineer before a safety claim. |

No single item above covers the whole farm stack. The model/ontology layer,
data APIs, geospatial asset catalogs, machinery interchange, and machinery
safety assurance are separate acceptance scopes.

## Adapter contract for every region and vendor

Implement each device/feed/controller as a versioned adapter behind a
vendor-neutral internal contract. The adapter manifest and every accepted
record must retain, where applicable:

1. **Identity and provenance:** provider, product/model, firmware or API
   version, adapter version, external identifier, raw-payload digest, and
   source/authority URL or identifier. Keep the unmodified source payload
   available under its licence and retention policy.
2. **Time:** source phenomenon/event time, source generation/issue time,
   ingest/availability time, timezone or UTC offset, and timestamp quality.
   Do not replace missing times with ingest time or the local clock.
3. **Meaning and units:** observed property/concept identifier, source code
   and local name/synonyms, quantity, unit identifier, conversion method and
   uncertainty. Reject unknown units or meanings instead of guessing.
4. **Spatial and sampling support:** source CRS and axis order, geometry or
   sensor location, native footprint/depth/height, resolution, method and
   sample interval. Unknown support stays unknown; an observation does not
   become a field/parcel claim through a spatial join.
5. **Quality and authority:** calibration status/evidence/expiry, quality
   flags and error bounds, licence and permitted use, consent/grant if
   required, and the exact processing steps. Preserve missing/invalid values
   as explicit gaps or refusals.
6. **Capability and failure behavior:** supported operations and fields,
   pagination/rate limits, offline buffering and replay behavior, duplicate
   identity rules, retry policy, timeout behavior, and a health check. Unknown
   device/operation, stale credentials, invalid payload, or unsupported
   semantics must fail closed and produce an auditable reason.

Adapters may translate syntax and identifiers, but must not silently change
support, time meaning, calibration, licence, or decision authority. Maintain
a mapping table from external codes to internal concepts with source,
version, and reviewer. Keep vendor-specific extensions namespaced so a new
vendor does not change the shared ontology contract.

## Acceptance path

For every adapter release, record the standard/version/profile, vendor and
firmware/API version, tested operations, fixture/source provenance, test
results, known exclusions, and reviewer. Use the following gates:

1. **Mapping review:** review external-to-internal concept, unit, time, CRS,
   support, licence, and uncertainty mappings. Include unknown and malformed
   cases; all must refuse or remain explicitly unknown.
2. **Offline producer tests:** deterministic fixtures for normal, boundary,
   duplicate/replay, missing-field, invalid-unit/time/CRS, stale calibration,
   unsupported extension, and licence-expiry cases. Assert that raw
   provenance and native support survive each conversion.
3. **Protocol/schema checks:** validate against the exact published API
   version and its conformance classes, OpenAPI/schema, or normative
   requirements. Schema validity is necessary where specified, but is not a
   complete conformance test. For OGC API – Features parts with available
   executable tests, run [OGC TEAM Engine](https://cite.ogc.org/te2/) and
   retain its report.
4. **Bilateral endpoint/device acceptance:** test against the named deployed
   service, physical sensor, or controller using actual firmware/configuration;
   check round-trip IDs, timestamp semantics, units, spatial support,
   retries/offline recovery, and operator-visible refusals. For machinery,
   a generated ZIP parsing against our own XSD is only structural validation;
   controller import, task interpretation, unit/rate correctness, and a
   supervised field drill are separate gates.
5. **Release evidence:** publish the compatibility tuple
   `(adapter version, external product/version, profile version, tested
   operations, test date, result)` and regression fixtures. Keep external
   certification claims separate and link only to the actual certificate or
   compliance report.

For closed-loop actuation, adapter acceptance is not permission to actuate.
The existing Phase-4 gate, human approval, command ledger, watchdog, and
kill-switch contract continue to govern that separate authorization.

## Official references

- [OGC SensorThings API 2.0 specification](https://docs.ogc.org/is/23-019/23-019.html)
- [ISO 19156:2023](https://www.iso.org/standard/82463.html)
- [W3C SOSA/SSN Recommendation](https://www.w3.org/TR/vocab-ssn/)
- [STAC 1.1 specification](https://docs.ogc.org/cs/25-004/25-004.html); [STAC API 1.0 specification](https://docs.ogc.org/cs/25-005/25-005.html)
- [OGC API – Features](https://www.ogc.org/standards/ogcapi-features/); [OGC compliance program](https://www.ogc.org/how-our-compliance-program-works/); [OGC TEAM Engine](https://cite.ogc.org/te2/)
- [ISO 11783-10:2015](https://www.iso.org/standard/61581.html); [ISO 11783-11:2011](https://www.iso.org/standard/57849.html)
- [ISO 25119-1:2018](https://www.iso.org/standard/69025.html)
