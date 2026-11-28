# Crop and site profile packages

`farm_ontology.agronomy.profiles` is the versioned registry boundary for
crop- and region-specific parameters. It stores source and applicability
with each value. It is not an agronomic model and does not change the
soybean engine's existing defaults.

## Package contract

Every profile has an immutable `profile_id` and semantic `version`, crop
taxon, country and region IDs, source records, parameters, capability gaps,
and a short description. Parameter IDs are unique inside a profile. Every
parameter carries its unit, one or more registered sources, a closed
applicability scope, and verification state. A parameter marked `verified`
also needs a verifier and verification date. Known unknowns can be recorded
as `UnavailableParameter` entries with contextual source IDs, a reason, and
the evidence needed to close the gap. Unknown profile versions,
missing parameters, mismatched crop/region/cultivar/elevation, and
unverified values raise a named `AgronomyGap`; no nearby profile is selected
as a fallback.

`verified` is a review receipt recorded in the package, not a cryptographic
proof or an independent evaluation of the cited material. Production
promotion still needs the responsible agronomist's review, source/label
checks, local field validation, and the normal operational gates. In
particular, registered pesticide product, crop, target, dose, use count,
pre-harvest interval, and jurisdictional label must be independently
verified before a product instruction can be proposed.

## Starter packages

`soybean-hokkaido@1.0.0` is a provenance manifest only. The existing
`hokkaido-short` default, retained `generic-extension` profile, irrigation
configuration, and all current soybean engine behavior stay unchanged.
This manifest does not promote the source notes currently tagged VERIFY to
verified global parameters.

`tea-south-china-starter@0.1.0` scopes discovery work to `CN` /
`CN-SOUTH-TEA` and `Camellia sinensis`. It cites the Ministry of Agriculture
and Rural Affairs' 2024 tea pest and disease guidance as discovery context;
the guidance citation alone does not establish a site-specific threshold
or rate. The pest threshold and pesticide rate are explicit sourced unknowns
with evidence requirements; they are not placeholder numbers. No numeric
tea parameters are included. It explicitly lists the
local evidence still needed for pest thresholds, phenology, soil and leaf
interpretation, fertilizer rates, registered pesticide instructions,
terrace irrigation and local baselines. Calling `require_parameter` for an
unsupported threshold or dose refuses with `profile-parameter-unavailable`;
other missing values refuse with `profile-parameter-missing`.

## Adding a locally reviewed value

Create a new package version when changing scope or parameters; do not edit a
published version in place. Add a source record with a direct citation, then
add a parameter whose applicability names the exact crop, jurisdiction,
region, and, when needed, cultivar and elevation interval. Keep the
parameter `unverified` until an agronomist records a verification receipt.
Consumers supply an explicit `ProfileContext` and call
`require_parameter(profile_id, version, parameter_id, context)` through the
registry. The existing engine must be separately adapted and validated
before a profile value can influence an algorithm or equipment command.

Example use:

```python
from farm_ontology.agronomy.profiles import (
    DEFAULT_CROP_SITE_PROFILES, ProfileContext, require_profile_parameter,
)

context = ProfileContext("Camellia sinensis", "CN", "CN-SOUTH-TEA")
parameter = require_profile_parameter(
    DEFAULT_CROP_SITE_PROFILES,
    "tea-south-china-starter", "0.1.0", "pest-action-threshold", context,
)
```

The example intentionally raises a gap until a sourced and reviewed
threshold is added in a later package version.

## Irrigation candidate optimizer

`farm_ontology.agronomy.irrigation_optimizer.optimize_irrigation_candidates`
is an advisory-only candidate evaluator. It does not calculate a crop's
water need from generic constants and it does not send a device command. A
caller supplies a provenance-bearing root-zone depletion state, forecast ET
and rainfall, and gross-application/energy candidates already bounded by the
site's hydraulic model. The evaluator uses the state variance to form an
upper depletion estimate, rejects candidates exceeding verified stress,
refill, or maximum-application limits, then minimizes the caller-specified
water and energy cost. No objective weights, weather values, thresholds, or
hydraulic capacity are silently defaulted.

The profile must provide verified, in-scope parameters with these exact IDs
and units: `root-zone-stress-threshold-mm` (`mm`),
`root-zone-refill-capacity-mm` (`mm`), `application-efficiency` (`fraction`),
and `max-gross-irrigation-mm` (`mm`). Parameter applicability must match the
requested crop, country, region, cultivar and elevation envelope. The
South-China tea starter currently has none of these values, so it fails
closed; adding locally measured and agronomist-reviewed values requires a
new profile version. The optimizer returns `control_authorized: false` and
cannot bypass the separate supervised irrigation approval and actuator
safety gates.

The 2026 Jiangxi tea drip-irrigation study is a method-discovery source, not
a parameter source for other farms. It concerns a specific site, soil,
cultivar, terrain and emitter configuration, and reports that slope,
nonlinear soil seepage, irrigation delay and moisture-sensor lag affect
water distribution. Its values must not be copied into the starter package
without local validation: [Agronomy 2026 field study](https://doi.org/10.3390/agronomy16111089).
