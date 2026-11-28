# Farm Ontology forward-deploy manual

**Audience:** field deployment lead, farm operator, integrator, and cloud
operator. **Scope:** repeatable installation and commissioning across farms,
regions, and cloud providers. **Revision:** 2026-11-28.

This is an operational deployment procedure, not a claim that the repository
already supports plug-and-play hardware or closed-loop machine control. The
current repository contains governed records, sensor payload validation, an
offline command ledger, a structurally validated TaskSet export profile, and
a human-flown drone packet. It has no generic hardware drivers, live machine
transport, local safety-gateway software, multi-cloud installer, or field
acceptance against a real controller. Complete the procedures below with the
farm's integrator; mark unavailable capabilities as blockers rather than
simulating successful commissioning.

## 1. Deployment boundary and rollout states

Use a **cloud-first, multi-region service** for shared records, imagery,
weather feeds, model execution, fleet management, and cross-farm reporting.
Choose primary and recovery regions per customer data-residency rules, feed
licences, latency, and recovery objectives. Keep a **local safety gateway** at
each site as the final command-policy and equipment boundary. It should
validate identity, freshness, site/device scope, interlocks, limits, and
operator HALT state; it must reject commands that fail a check. Cloud
availability must never be required for a device's safe stop. Define each
actuator's loss-of-network behavior with its manufacturer and farm safety
owner; do not assume that holding the last value is safe.

During a WAN/cloud outage, the intended operating policy is: reject new
cloud-originated actuation; keep local protection and safe-stop behavior
available; buffer timestamped observations and signed receipts locally;
replay after reconnection with deduplication and ordering checks. This
store-and-forward and safety-gateway behavior is **planned architecture**,
not a tested feature of this repository. If the site lacks an independently
validated safety controller, operate in read-only/manual mode.

| State | Permitted activity | Exit evidence |
| --- | --- | --- |
| Survey | inventory, read-only inspection, connectivity checks | signed site worksheet and compatibility verdicts |
| Read-only | ingest observations; inspect dashboards and data gaps | stable telemetry, time/unit/location checks, calibration records |
| Shadow | generate recommendations and proposed commands; no device writes | shadow review across the agreed representative period; false-alert and missed-event review |
| Human-authorized | operator reviews and authorizes individual actions using existing equipment controls | documented operator training, approvals, safety and regulatory sign-off |
| Controlled automation | only explicitly approved device, action, zone, limits, and time window | local safety case, witnessed field drill, stop/recovery drill, change approval |

Promotion is per site, device, action, and operating condition. A green
dashboard or successful data import does not authorize control. Irrigation,
fertigation, and pesticide application require separate acceptance; legal
product labels, local permits, weather restrictions, and qualified operator
requirements remain authoritative.

## 2. Before travelling to the farm

### 2.1 Establish the deployment record

Create a site record and name the deployment lead, farm owner, local safety
owner, agronomist, network contact, and incident contact. Record:

- country/jurisdiction, site timezone, language, units, data-residency
  requirements, retention requirements, and permitted cloud regions;
- farm, parcel and management-zone identifiers; crop, cultivar, planting
  system, crop stage source, slope/aspect, irrigation zones and water source;
- connectivity and power survey; expected outage duration; gateway location,
  enclosure, grounding, lightning/surge protection, cellular/Wi-Fi/Ethernet/
  LoRaWAN coverage, and backhaul owner;
- each data feed's owner, licence, permitted purpose, refresh rate, spatial
  support, and expiry/renewal contact;
- the farm's safe state, emergency stop authority, escalation path, and
  conditions requiring manual operation.

Do not put credentials, personal data, or precise private farm locations in
public issue trackers or unsecured field notes. Use the approved customer
record store and access policy.

### 2.2 Inventory devices and interfaces

Inventory every sensor, gateway, controller, pump, valve, injector,
fertilizer spreader, sprayer, weather station, camera, and imagery feed. Give
each a stable site-scoped ID and capture the following before procurement or
connection:

| Field | Record |
| --- | --- |
| Identity | manufacturer, exact model, serial/asset ID, firmware, owner, physical location, zone served |
| Function | sensor measurement or actuator function; crop/use context; device criticality |
| Interface | physical connector/radio; protocol and version; network direction; API/manual; vendor support status |
| Data contract | field names, units, coordinate reference, time basis, sample/command rate, quality flags, native spatial support |
| Calibration | calibration method, certificate/activity, uncertainty/error metric, due date, reference instrument |
| Control contract | read-only vs write capability; command units/ranges; acknowledgement, timeout, retry/idempotency behavior; local interlocks and fail-safe state |
| Evidence | adapter/version, bench and field test result, test date, test operator, known gaps, vendor confirmation |

Check compatibility against the actual device and firmware, not merely a
protocol label. A device speaking MQTT, Modbus, OPC UA, LoRaWAN, or ISOBUS is
not automatically supported: map its payload, units, errors, timestamps,
identity, and command acknowledgement into a reviewed adapter contract.
Standards are interoperability aids, not certification or proof of safe
operation. Candidate data mappings include OGC SensorThings API and
SOSA/SSN; geospatial assets can use STAC and OGC API Features. ISO 11783
Task Controller exchange is applicable only to compatible equipment and
requires controller-specific acceptance. See the standards references in
§11.

Assign one verdict to each device: **supported and evidenced**, **adapter
required**, **read-only only**, or **incompatible / not tested**. Do not
connect untested write interfaces. The current code supports a constrained
JSON sensor-ingest shape and offline export artefacts; it does not provide
drivers for the interface examples above.

### 2.3 Compatibility and site acceptance checklist

Before installation, confirm all of the following or record a blocker:

- [ ] device model, firmware and interface contract are documented;
- [ ] field mapping preserves units, timezone, coordinates/CRS, uncertainty,
  calibration, availability time and original spatial support;
- [ ] device identity can be authenticated and credentials can be rotated;
- [ ] telemetry loss, duplicate delivery, clock drift, malformed values and
  sensor replacement have defined handling;
- [ ] actuator commands have bounded ranges, explicit units, expiry, unique
  IDs, acknowledgement, timeout, and duplicate/replay protection;
- [ ] a device-side/local interlock and independent emergency stop are
  available and tested by the equipment owner;
- [ ] operator training, maintenance access, spare parts, and vendor support
  are available for the deployment window;
- [ ] feed/data rights and applicable local rules have been checked by the
  responsible owner.

## 3. Install the site in read-only mode

1. **Approve the site bundle.** Use the machine-checked v1 structure in
   [`site-bundle-schema.md`](site-bundle-schema.md), then attach the full
   deployment records for site ID, timezone, units, locale, parcel/zone
   geometry and provenance, sensor-to-zone mappings, crop/variety package,
   feed licences, retention, contacts, alert destinations, and gateway
   policy. The schema holds reviewed references and separate rollout state
   for irrigation, fertigation, and pesticide; it does not certify the
   referenced evidence or authorize commands. Review the geometry in the
   field; record positioning method and error. Never use a map pin as a
   surveyed boundary.
2. **Provision the cloud tenant and regions.** Select provider-neutral
   deployment targets, primary/recovery region, identity provider, storage,
   backup, logging, monitoring, and recovery objectives. Keep each tenant
   and farm scoped. Validate data residency and feed terms before copying
   data. Configure a tested restore path before production records are
   written.
3. **Provision site identity.** Issue unique identities for gateway and
   devices. Use short-lived credentials or certificates where supported;
   never share a fleet-wide password or embed operator credentials in device
   firmware. Restrict gateway egress to required endpoints, keep admin access
   separate, and record the owner and expiry/rotation date for every secret.
4. **Mount and label equipment.** Install sensors at the surveyed sampling
   locations and agreed depths/heights, away from avoidable shade, runoff,
   spray drift, structures, and machinery interference. Follow the device
   manufacturer and crop protocol. Photograph placement with consent and
   attach device ID, zone, location accuracy, and installation time.
5. **Check gateway basics.** Confirm enclosure, power budget, UPS if required,
   surge/lightning protection, antenna position, ventilation, clock source,
   local storage capacity, and physical access control. Verify local stop
   operation independent of cloud/WAN. If the planned gateway software or
   required interlock is unavailable, leave write paths disconnected.
6. **Connect telemetry only.** Start with one device of each model. Verify
   identity, timestamp/timezone, units, plausible range, calibration
   metadata, quality flag, expected cadence, duplicate handling, and mapped
   zone. Compare readings against a reference or manual observation. Do not
   infer a parcel-wide condition beyond the instrument's documented support.
7. **Calibrate and document.** Follow the device-specific method and record
   raw readings, reference measurements, calculation, error metric, operator,
   activity ID and recalibration due date. Until calibration is valid, label
   the reading uncalibrated and exclude it from claims that require calibrated
   support. The repository's current sensor ingestion requires calibration
   metadata for its governed calibrated-row path; see
   [`calibration-protocol.md`](../hardware/calibration-protocol.md).
8. **Check imagery and weather separately.** Record provider, acquisition /
   issue time, resolution/native support, cloud or missing-data mask,
   licence, and local station comparison. Satellite pixels, gridded weather,
   and in-field sensors are distinct supports; do not silently upscale one
   into another.
9. **Observe a baseline.** Run read-only for a representative operating
   period covering relevant crop stages and normal connectivity variation.
   Review missingness, drift, outliers, spatial mismatch, and data latency.
   Fix instrumentation or publish an explicit gap before shadow evaluation.

## 4. Shadow mode and commissioning gates

Shadow mode computes recommendations and proposed actions but cannot send
device commands. Keep operators' normal procedures in control. Store the
inputs and their timestamps, model/rule/config version, uncertainty and
refusal reason, proposed zone/action/quantity, operator's independent field
finding, and outcome. Review both false alarms and missed events; do not use
classification accuracy alone. Set the observation period and minimum number
of relevant events with the agronomist and farm safety owner before the run.

Commission the actions independently:

| Workstream | Minimum evidence before considering automation |
| --- | --- |
| Irrigation | surveyed hydraulic zones; flow/pressure or delivery verification; soil/weather inputs with valid support; bounded runtime/volume; leak, freeze, blocked-line and dry-run checks; local stop and outage behavior witnessed |
| Fertigation | all irrigation evidence plus tank/injector calibration, concentration and compatibility checks, backflow protection, water-quality controls, safe flush/containment procedure, and review by a qualified local agronomist/operator |
| Pesticide application | correct local registration and product label, crop/pest and zone confirmation, label-rate/unit checks by responsible qualified person, weather/drift and buffer constraints, equipment calibration, PPE/re-entry/withholding controls, application log, and independent stop authority |

The system may calculate a candidate quantity only when the required input,
calibration, label/rule, area, unit conversion, and uncertainty checks pass.
Missing or conflicting inputs must block the recommendation. Quantity limits
and rates must come from a current, locally applicable approved source and
be independently reviewed. This manual supplies no pesticide or fertilizer
rate and does not approve autonomous use.

Before any controlled automation, the sign-off packet must include: device
compatibility and field evidence; calibration certificates; shadow report;
hazard/risk review; local regulatory and label review; training record;
cybersecurity review; witnessed command and acknowledgement test; network
loss, stale command, duplicate, sensor fault, power loss and recovery drills;
emergency stop / HALT drill; rollback procedure; and signed approval by the
farm owner, safety owner, agronomist, and system operator. In this repository,
real-device field acceptance and live command plumbing remain unproven; the
software Phase-4 gate and signed kill-switch contract must be satisfied before
live commands are in scope. See
[`actuation-interface-spec.md`](actuation-interface-spec.md) and
[`alpha-fairness-doctrine.md`](alpha-fairness-doctrine.md).

## 5. Offline, degraded, and failure recovery

Post an outage card at the gateway: site ID, local safe-state instructions,
manual equipment controls, stop authority, support contacts, last known-good
configuration version, and steps to isolate the gateway. Keep the emergency
stop accessible when cloud, network, identity provider, or operator UI fails.

| Failure | Required response |
| --- | --- |
| WAN/cloud unavailable | reject new remote actuation; follow the device-specific local safe state; queue only signed, timestamped observations/receipts within bounded storage; switch to manual procedures |
| Gateway or power failure | use independent machine controls and the farm's safe-state procedure; isolate faulty equipment; no automatic failover to an uncommissioned controller |
| Sensor absent, stale, implausible, or calibration expired | mark gap/refuse dependent recommendations; inspect and replace/calibrate; never substitute a nearby or gridded value without explicit support and uncertainty |
| Clock drift or time ambiguity | quarantine time-dependent data/commands until clock is corrected and records are reconciled; do not replay expired commands |
| Cloud region failure | use the documented recovery region only after identity, data freshness, tenant scope and duplicate-command safeguards are verified; fail closed if state is ambiguous |
| Duplicate, delayed, or unacknowledged command | do not blindly retry; inspect local equipment state and receipt; deduplicate by command ID, then have an authorized operator resolve ambiguity |
| Suspected credential compromise | revoke/rotate affected identity, isolate gateway, preserve audit evidence, inspect scope and command history, and reissue credentials after review |
| Unexpected application or device behavior | operator HALT, move equipment to safe state, record event and evidence, notify safety owner; resume only after investigation and re-commissioning of affected path |

When connectivity returns, reconcile buffered records by source event time,
ingest/availability time, device ID, sequence and unique event ID. Reject
duplicates and expired commands. Review gaps and conflicting records before
restarting advisory or control workflows. These recovery behaviors need
implementation and site testing; a runbook entry alone does not prove them.

## 6. Security and operational controls

- Apply least privilege separately to human users, services, gateway, and
  devices. Separate read/observe, approve, administer, and emergency-stop
  roles; require independent approval for high-risk changes and actions.
- Encrypt network links and storage using provider-supported controls; use
  unique device identities, certificate/secret rotation, revocation, secure
  boot/firmware updates where available, and physical tamper controls.
- Restrict the local gateway to outbound connections where practical. Do not
  expose device-control ports to the public internet. Segment farm OT from
  guest and office networks; allowlist necessary destinations and protocols.
- Log human identity, approvals, config/model version, command ID, target,
  payload hash, issue/expiry time, result/receipt, HALT events, and recovery
  actions. Protect logs from modification and retain them to the approved
  schedule. Avoid placing secrets and unnecessary personal data in logs.
- Monitor gateway health, sensor freshness, calibration expiry, queue depth,
  clock status, cloud ingestion, failed authentication, command refusals,
  backups, and cost. Assign alert owners and escalation timeframes.
- Patch gateway OS, firmware, adapters and service dependencies through
  reviewed, signed releases. Maintain a device support/EOL register and a
  vulnerability-response contact. Test changes in a non-production site or
  read-only mode first.
- Review data access, consent, retention, cross-border transfers, feed
  licences and incident-reporting obligations with the farm/customer owner
  under local requirements. Do not treat a technical standard as legal
  authorization.

## 7. Upgrade, rollback, and uninstall

### Upgrade

1. Pin the current site bundle, adapter, firmware, model/rules, and cloud
   release versions; export configuration and verify a restorable backup.
2. Read the release notes and compatibility matrix. Check schema migrations,
   protocol changes, licences, data residency, security advisories, and
   supported rollback path.
3. Install on a test gateway/site or in read-only mode. Re-run telemetry,
   calibration, time, unit, identity, stop, and recovery checks.
4. Schedule a maintenance window with the farm. Pause automated actions and
   confirm equipment is in its approved safe/manual state.
5. Upgrade a canary first. Verify health, records, alerts and receipts; then
   advance one device/zone at a time with named operator approval.
6. Record the version and acceptance evidence. Restore the previous version
   if any gate fails; retain logs and the failed bundle for diagnosis.

### Rollback

Disable new action proposals and command intake; use local equipment controls
to stop or safely complete current operations. Revert the service/config or
adapter to the pinned known-good version using the cloud provider's documented
rollback method. Check that no queued command can execute after rollback,
verify device-side state and data integrity, and resume in read-only/shadow
mode. Do not delete records to make the rollback appear clean. The GCP web
image rollback is provider-specific and documented in
[`../deploy/web-rollback.md`](../deploy/web-rollback.md); it does not roll
back field devices or authorize their control.

### Uninstall / site handover

1. Obtain farm owner approval and identify retention, export, and deletion
   obligations before removing anything.
2. Stop command intake and automation; confirm local safe state and revoke
   gateway write permissions. Disconnect control links before removing
   telemetry.
3. Export requested records/configuration with provenance, timestamps,
   licence and integrity metadata; record recipient and transfer method.
4. Revoke device certificates, tokens, accounts and network rules; remove
   tenant/site mappings and scheduled jobs only after checking shared-resource
   ownership. Never bulk-delete a provider project or shared bucket as part of
   a farm uninstall.
5. Sanitize or return gateway hardware and storage under the approved
   procedure. Verify deletion/retention status with the data owner and give
   the farm an uninstall receipt, remaining-retention schedule, and support
   contact.

## 8. Field sign-off record

Complete and retain one copy for the farm and one in the controlled project
record:

```text
Site / tenant ID:
Country / timezone / cloud regions:
Deployment bundle + software / adapter / firmware versions:
Device inventory and compatibility evidence location:
Boundary / zones version and positioning error:
Feed licences and data-residency approval:
Read-only start / end; gaps and corrective actions:
Shadow period / reviewed events / false alarms / missed events:
Calibration certificates and due dates:
WAN loss / power loss / stale data / duplicate / HALT drill results:
Approved state (survey / read-only / shadow / human-authorized / controlled):
Approved devices, actions, zones, limits, and validity window:
Open blockers and named owners:
Farm owner / safety owner / agronomist / integrator / operator sign-off:
Date and next review:
```

If any field relevant to a proposed action is missing, keep the site at the
last safe state and record the gap. No signature here supersedes a required
company, regulatory, equipment, licence, or contract gate.

## 9. Current repository capability ledger

Status below is deliberately bounded to repository evidence available on
2026-11-28. **Implemented** means code or an existing documented environment
exists; it does not mean the feature has been proven on a farm machine.

| Capability | Evidence/status | Deployment implication |
| --- | --- | --- |
| Governed observation records and refusal/gap semantics | Implemented in repository; see project tests and record docs | Can preserve provenance when callers supply required fields; does not establish sensor truth |
| Fixed-shape sensor JSON ingestion with calibration metadata | Implemented for named sensor classes | Integrator must build/test device-specific adapters; no generic drivers/discovery |
| Hash-chained command ledger and human approval states | Implemented offline | Local file ledger is not secure remote transport or a gateway |
| TaskSet profile export and structural validation | Implemented offline; ISO 11783-10 controller acceptance is explicitly unproven | Treat as an exchange artefact until tested on each approved controller |
| Drone spray packet | Human-facing packet only | No autopilot, aircraft link, or autonomous flight support |
| Cloud backend and web service | Existing GCP deployment is documented for the named pilot | Does not establish provider-neutral provisioning or global multi-region failover |
| Local safety gateway, generic protocol adapters, store-and-forward recovery | Planned | Must be implemented and independently tested before relying on these behaviors |
| Automated agronomic recommendation and closed-loop control | Planned / gated | Keep read-only, shadow, or existing human-controlled operation until all site gates pass |

## 10. Scoped GCP pilot profile

This profile is only for the existing Farm Ontology pilot deployment; it is
not a universal install recipe and does not imply support for a new farm,
region, provider, or hardware stack. The repository's current Farm GCP
footprint is in project `seges-ai`, region `asia-east1`, and resources must
remain limited to the `farm-seges-ai*` family plus explicitly documented
Farm-owned jobs, schedulers, bucket and secrets. The project is shared with
other products. Verify current ownership and live state before any change.

Use [`../deploy/GCP_SETUP.md`](../deploy/GCP_SETUP.md),
[`backend-live.md`](backend-live.md), [`web-ops.md`](web-ops.md), and the
relevant rollback document for the current pilot's exact Cloud Run, bucket,
monitoring and web procedures. Follow their staging-first, traffic-shift,
secret-preservation and digest-pinned rollback rules. Do not copy the pilot's
region, identities, bucket, credentials, or product-specific feed setup into
another deployment. The current pilot is not a live actuator deployment;
do not attach equipment control based on this profile.

## 11. Standards and local references

Check applicable edition, implementation profile, licence, and local rules
when designing each adapter. A standards mapping is not a plug-and-play
claim.

- [OGC SensorThings API](https://docs.ogc.org/is/23-019/23-019.html):
  sensor/observation data interoperability.
- [W3C/OGC SOSA/SSN](https://www.w3.org/TR/vocab-ssn/): semantic description
  of sensors, observations, and procedures.
- [OGC STAC](https://www.ogc.org/standards/stac/): catalog metadata for
  satellite and other spatiotemporal assets.
- [OGC API Features](https://www.ogc.org/standards/ogcapi-features/): access
  patterns for geographic features and boundaries.
- [ISO 11783-10](https://www.iso.org/standard/61581.html): agricultural
  machinery Task Controller data interchange; validate with the actual
  implement/controller vendor.
- [ISO 25119-1](https://www.iso.org/standard/69025.html): safety-related
  control systems for tractors and machinery for agriculture and forestry;
  use a qualified machinery-safety process for applicable systems.
- Internal: [`decision-infra-roadmap.md`](decision-infra-roadmap.md),
  [`actuation-interface-spec.md`](actuation-interface-spec.md),
  [`alpha-fairness-doctrine.md`](alpha-fairness-doctrine.md),
  [`../hardware/calibration-protocol.md`](../hardware/calibration-protocol.md),
  and [`../deploy/GCP_SETUP.md`](../deploy/GCP_SETUP.md).

## 12. Installation closeout

Before leaving the site, confirm the farm has the approved operating state,
emergency-stop instructions, current support contacts, known gaps, next
calibration/maintenance dates, configuration backup location, and a copy of
the signed commissioning record. Leave unapproved control connections
physically disconnected and mark their status in the device inventory.
