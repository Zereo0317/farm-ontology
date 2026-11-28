# Global farm stack baseline — 2026-11

Reviewed 2026-11-28 against upstream release and standards sources. This is
the implementation baseline for the adapter SDK, supervised-irrigation
simulator and rollout tooling. A protocol's existence does not imply support
for every device that uses it.

## Repository runtime and CI

| Layer | Current repository | 2026-11 baseline / decision |
| --- | --- | --- |
| Farm core | Python `>=3.11`, stdlib-only; Docker `python:3.12-slim`; CI tests 3.12 | Keep core dependency-free. Run CI on 3.11–3.15. Keep the production image on 3.12 until the multi-version matrix and image build are green; change the production runtime in a separate verified release. Python.org lists 3.15.2 and 3.14.10 as current stable releases. |
| Web CI runtime | Web CI uses Node 20; landing CI uses Node 24 | Use Node 24 LTS consistently for web tooling. Node 20 reached EOL on 2026-03-24; Node 24 and 26 are LTS. Keep the web framework and npm package graph unchanged in this hardware/control work. |
| GitHub Actions | checkout v4, setup-python v5, setup-node v4, Google auth/setup-gcloud v2, setup-terraform v3 | Move to checkout v7, setup-python v7, setup-node v7, Google auth v3, setup-gcloud v3, and setup-terraform v4. These current releases use Node 24; the Google action v3 pair requires a Node 24-capable runner. |
| Terraform CI | Terraform 1.8.5 | Validate with Terraform 1.17.2, released 2026-11-11. Keep the module's declared minimum separate from CI's tested version. |
| Protocol dependencies | None in the core | The SDK and simulator remain stdlib-only. Any future protocol client belongs in a separately versioned edge adapter package/container, with a lockfile, SBOM, CVE review, device/firmware compatibility tuple and offline fixtures. Do not add MQTT/Modbus libraries to the core package. |

## Device and observation interfaces

| Need | 2026-11 interface baseline | Boundary |
| --- | --- | --- |
| Sensor observations across systems | OGC SensorThings API 2.0 (published 2026-11-04), based on ISO 19156:2023 and aligned to OData 4.01; HTTP and MQTT bindings | Northbound observation exchange; it does not replace radio/bus drivers. Implement named conformance classes and Annex A tests before claiming SensorThings conformance. |
| Semantic model | Stable W3C SOSA/SSN Recommendation + ISO 19156:2023 | Map the internal observation envelope to agreed concepts. The internal record remains the governed evidence store. |
| Low-power field radio | LoRaWAN plus the correct regional parameters and an exact device/network-server profile; consider LoRa Alliance TS014-1.0.0 capability profiles and TS018-1.0.0 QR onboarding | MAC version must be selected against target hardware certification and regional band; do not hard-code one global radio profile or handle root keys in the shared cloud service. Network server / Join Server remain separate from the farm adapter. |
| Local event transport | OASIS MQTT 5.0 | Use authenticated TLS, per-device/topic authorization, persistent outbox, explicit expiry and idempotency. QoS 1 delivery can duplicate events; deterministic event IDs and dedupe remain required. |
| Irrigation controller bus | Modbus Application Protocol V1.1b3; Serial Line Implementation Guide V1.02 for new serial implementations; Modbus Security for TLS/X.509 where supported | Require a per-model register map, scaling/endianness proof and read-only commissioning. Never expose raw Modbus TCP to the public internet. |
| Industrial controller option | OPC UA core parts around 1.05.07; OPC UA FX 1.00.04 is a newer field-level option | Use only where the named controller/gateway supports the applicable profile. It is not a universal farm connector. |
| Machinery prescription exchange | ISO 11783-10:2015 and ISO 11783-11:2011 | Existing repository TaskSet is an internal structural profile. Require the exact terminal/firmware import, operation, unit and rate bilateral test; do not claim ISO conformance from ZIP validation. |
| Machinery control safety | ISO 25119-1:2018 + Amendment 1:2020, marked for revision | Safety lifecycle reference only. Qualified safety engineering, local interlocks and field evidence are separate acceptance gates; repository checks are not certification. |
| Imagery and geospatial assets | STAC 1.1 and STAC API 1.0; OGC API Features for vector features | Asset discovery and geospatial feature exchange only; not real-time sensing or control. Preserve source CRS, native support, acquisition time, licence and uncertainty. |

## Cloud and edge topology

Keep the farm decision core and cloud control plane separate from a site-local
edge gateway. Cloud Run multi-region is a regional-service and traffic-routing
capability, not offline field control. Google's service-health failover
requires at least two regions and at least one minimum instance in each region;
a global Application Load Balancer routes to healthy regional services.
Cloud Storage bucket location controls where object data resides; dual/multi
region replication is asynchronous and has separate cost, consistency and
residency implications. The existing `GcsBackend` authenticates with the GCP
metadata server and is therefore GCP-specific, not a global storage adapter.

The target deployment is regional data planes with a local edge outbox and a
provider-neutral event contract. The tea pilot remains isolated from the
Hokkaido pilot. Select a region and cloud account per jurisdiction, customer
data-residency requirements and source licences; never move farmer or site
records globally just because the application is multi-region. No edge gateway
may depend on Cloud Run availability for safe-stop or local interlocks.

## Rollout implications

1. Keep the standard library core and extend the normalized manifest/envelope
   contract; add an SDK, simulator and durable replay tests before protocol
   packages.
2. Add read-only, named adapter packages only after a farm inventory names the
   gateway, device model, firmware, regional radio plan, calibration and source
   rights. The user has selected SDK-first because the China tea site inventory
   is not in the repository.
3. Build the irrigation simulator and command-receipt loop first. Live
   irrigation requires an exact controller adapter, hydraulic calibration,
   local safe state, hardware interlocks, watchdog/HALT, expiring commands and
   operator release. Fertilizer and pesticide remain distinct capabilities.
4. Treat multi-region routing, data replication, edge store-and-forward and
   device command transport as separate fault domains with independent drills.

## Official references

- [Python release versions](https://www.python.org/doc/versions/)
- [Node.js release schedule](https://nodejs.org/en/about/previous-releases)
- [actions/checkout releases](https://github.com/actions/checkout/blob/main/CHANGELOG.md), [setup-python releases](https://github.com/actions/setup-python/releases), [setup-node releases](https://github.com/actions/setup-node/releases)
- [Google auth action](https://github.com/google-github-actions/auth), [Google setup-gcloud releases](https://github.com/google-github-actions/setup-gcloud/releases), [HashiCorp setup-terraform](https://github.com/hashicorp/setup-terraform)
- [Terraform releases](https://github.com/hashicorp/terraform/releases)
- [OGC SensorThings API 2.0](https://docs.ogc.org/is/23-019/23-019.html), [ISO 19156:2023](https://www.iso.org/standard/82463.html), [W3C SOSA/SSN](https://www.w3.org/TR/vocab-ssn/)
- [LoRa Alliance TS014](https://resources.lora-alliance.org/document/ts014-1-0-0-end-device-capabilities-api), [TS018](https://resources.lora-alliance.org/home/ts018-1-0-0-lorawan-device-identification-qr-codes-for-automated-onboarding)
- [OASIS MQTT 5.0](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html)
- [Modbus specifications](https://www.modbus.org/modbus-specifications), [OPC UA Part 4](https://reference.opcfoundation.org/specs/OPC-10000-4)
- [ISO 11783-10](https://www.iso.org/standard/61581.html), [ISO 11783-11](https://www.iso.org/standard/57849.html), [ISO 25119-1](https://www.iso.org/standard/69025.html)
- [STAC 1.1](https://docs.ogc.org/cs/25-004/25-004.html), [STAC API 1.0](https://docs.ogc.org/cs/25-005/25-005.html)
- [Cloud Run multi-region](https://docs.cloud.google.com/run/docs/multiple-regions), [Cloud Run service health](https://docs.cloud.google.com/run/docs/configuring/configure-service-health), [Cloud Storage locations](https://docs.cloud.google.com/storage/docs/locations), [Cloud Storage consistency](https://docs.cloud.google.com/storage/docs/consistency)
