# Global farm feedback loop: architecture and implementation boundary

Status: implementation architecture and scoped primitive. This document does
not claim that the repository currently controls field equipment or has been
validated across crops, countries, or vendors. See the [interoperability
profile](global-interoperability-profile.md) and
[forward-deploy installation manual](forward-deploy-installation.md) for the
device and commissioning boundaries.

## Goal

Support different farms through one stable evidence and decision core, with
versioned site packages and replaceable data/device adapters. A southern
China tea terrace is the first deployment profile, not a set of global
defaults. The same decision path must work when a site has only weather and
manual scouting, and improve as calibrated local sensors and verified
equipment become available.

## Decision and feedback path

```text
farm/site package + capability registry
  ├─ geometry, zones, crop/cultivar/season, local rules, units and locale
  └─ registered feeds, sensors, actuators, safety limits and evidence
          │
          ▼
standard adapters → immutable observations and provenance
          │             (time, native support, units, calibration, licence,
          │              method/version, quality, uncertainty)
          ▼
state estimation per declared property × zone/support × layer × time
          │             (publish residuals and updated uncertainty)
          ▼
crop-specific models and risk rules
  ├─ water balance / irrigation need
  ├─ nutrient diagnosis / fertiliser response
  └─ pest/disease risk / scouting and treatment window
          ▼
constrained recommendation with evidence, expiry, uncertainty and gaps
          ▼
local safety and legal policy → human or eligible controller
          ▼
device adapter → command receipt → measured delivery → field outcome
          └──────────────────────► immutable outcome and model evaluation
```

Each arrow is a versioned interface. An adapter may normalize a vendor
protocol and units; it may not invent calibration, rewrite spatial support,
or turn a missing value into a default. If a required input is absent or
invalid, the result is a named gap and no command is emitted.

## Feedback update contract

`farm_ontology.agronomy.state_estimation.assimilate_measurement` currently
implements the first primitive in this path: scalar Kalman assimilation of a
single calibrated measurement into a prior state. It requires exact equality
of the explicit `state_key` and unit, a calibration reference, acceptable
quality, aware timestamps, positive finite variances, non-future/non-stale
measurement, and a fresh prior. The caller must encode the spatial support,
management zone and layer in the key. The result contains the residual,
normalized residual, gain, posterior variance, deterministic replay id and
source references. Its payload is explicitly advisory-only and records
`actuation_authorized: false`.

This primitive does not do spatial interpolation, sensor fusion across
different supports, crop-model parameter learning, fertilizer/pesticide
dose optimization, or live actuation. It must not be used as proof that an
estimated probe state represents a full terrace or parcel. Broader assimilation
requires a named model and validation data for the property, support, crop,
region and season.

## Closed-loop safety boundary

The operational loop must separate four quantities that are often conflated:

1. **Need estimate:** e.g. root-zone water depletion, nutrient limitation, or
   pest risk with uncertainty and evidence.
2. **Recommendation:** a bounded action proposal derived from a named crop,
   local profile, label/rule set and current evidence.
3. **Command:** an authorized request for a specific device, location, rate,
   timing and quantity, with an immutable command identity.
4. **Outcome:** measured delivery and later field response, including failure
   to deliver, weather interruption, runoff/drainage, phytotoxicity or no
   observed effect.

The command ledger and Phase-4 gate remain the authorization boundary. The
state estimator cannot approve or dispatch commands. Irrigation, fertiliser
and pesticide operations need separate capability profiles and acceptance
tests. For pesticide operations, the local package must match the registered
product, crop, target, label dose, pre-harvest interval, re-entry period,
weather limits and jurisdiction. Unknown or mismatched facts block issue.
Equipment auto-control additionally requires a validated adapter, independent
interlocks, watchdog, human-accessible HALT, recorded field drill, and all
repository human gates. No such cross-vendor live control is established by
this change.

## Learning loop and evaluation

Store each forecast, recommendation, command state transition, device
acknowledgement, delivered amount, follow-up observation, and adverse event
as linked but distinct records. Keep the original forecast and recommendation
immutable. Later outcomes append calibration/evaluation records; they never
rewrite the evidence that was available when the decision was made.

Evaluate by held-out farm/zone and season, not a random row split. Report at
least calibration error, residual distribution, false alarm/miss rates,
lead time, delivered-vs-commanded quantity, water/nutrient/chemical use,
yield or quality outcomes, adverse events, and subgroup performance by crop,
region, cultivar and device. A model/profile version may advance only with
reviewed evidence and rollback metadata. Until local evidence exists, the
system stays in observation or shadow mode.

## Rollout levels

| Level | System action | Minimum evidence |
| --- | --- | --- |
| Observe | Ingest sensors, imagery, weather and scout records | Inventory, provenance, calibration and site-package checks |
| Shadow | Produce recommendations without sending commands | Local-season replay, missing-input/refusal checks, expert review |
| Assisted | Human reviews and manually executes a bounded recommendation | Commissioned device mapping, legal/product checks, delivery and outcome records |
| Supervised control | Eligible command is transmitted with a human release and independent safety interlocks | Device-specific acceptance, authority gate, watchdog/HALT drill, rollback and audit |
| Autonomous control | A previously validated operation is automated under narrow, explicit limits | Jurisdictional authorization, safety case, per-site/crop/actuator validation, ongoing monitoring and human stop capability |

Levels are assigned per operation and device, not per farm account. Passing
one level for irrigation does not enable fertiliser or pesticide control.

## Global core versus local configuration

Keep vocabulary, provenance, time semantics, measurement envelopes,
decision/event lineage and failure behavior in the common core. Put crop and
cultivar coefficients, pest thresholds, soil interpretation, local pesticide
registrations, water rules, language, calendar, units, geofences and allowed
operations in signed, versioned site/region packages with source and review
dates. A package is not publishable for a decision until every required field
has a source, owner and validity interval. Unknown values remain unknown.

For the tea pilot, do not copy soybean phenology, soil profile, irrigation
coefficients or generic spray thresholds into a tea package. Populate tea
profile values only from traceable local agronomic sources and site
measurements, then validate with the local agronomist and operator before
shadow recommendations are treated as decision support.

## Remaining implementation work

1. Define and validate a canonical site-package schema with release signing,
   provenance and compatibility checks.
2. Add a device capability registry and adapter contract, then implement
   read-only ingestion for the first sensor/gateway models. Record protocol,
   firmware, calibration and command capabilities per device.
3. Extend state estimation from one property/layer to validated temporal and
   spatial models without support laundering; add residual monitoring and
   drift alarms.
4. Add immutable action-outcome records linking command, device acknowledgement,
   measured delivery and field response.
5. Add tea-specific irrigation, fertility and pest packages with local sources
   and expert-reviewed calibration; keep pesticide rate decisions gated by
   registered labels and jurisdiction rules.
6. Exercise cloud and edge operation under WAN loss, duplicate/out-of-order
   events, power loss, clock drift, sensor failure, actuator failure and
   emergency HALT; prove idempotent replay and safe recovery.
7. Run shadow-mode field validation and adverse-event review before enabling
   any operation beyond manual assistance.
