# Commercial punch-list (rendered from `grants/punchlist.yaml`)

Written 2026-11-17 · verification date **2026-11-17** · task-6 (WS6 Licence
certificate workflow) · render source: `grants/punchlist.yaml` (the YAML file
is the data of record; keep this render in sync when it changes).

> Standing disclaimer: this is a punch-list of **requirements to verify**,
> not legal conclusions. Every item is **NOT-YET-EXECUTED** until its named
> evidence exists in the repo. Fail-closed reminder: until executed, each
> affected feed evaluates to a refusal (`specimen` / `no_grant` / `expired`)
> and `permits_financial_use` stays false.

## Contract pack (READY-TO-SIGN, awaiting PL-CORPORATE-STATUS)

Applies to any contract sold to a farmer (decision-support or
revenue-share), per `docs/alpha-fairness-doctrine.md` §4 rail 1.

**Concurrent-position disclosure (doctrine §4.1, verbatim, mandatory):**

> "The Company maintains proprietary positions in agricultural commodities.
> When its data indicates materially adverse or favourable conditions for
> Your fields, the Company shall disclose the existence — never the size —
> of related positions in its periodic decision-support report, before the
> affected transaction dates."

Placement: every farmer-facing contract body, before the signatures block.
Guarded byte-for-byte by `tests/test_licences_punchlist.py`.

Signatory block: Company principal **PENDING-PL-CORPORATE-STATUS** (a
not-yet-incorporated entity must not be named as principal); counterparty
and witness per contract. Doctrine §8 governs clause edits (Lead-approved
commit with dated rationale).

---

## PL-PLANET-COMMERCIAL · Planet Labs commercial monitoring plan (post-trial conversion) — `NOT-YET-EXECUTED`

- **Area:** satellite imagery, planetary variables.
- **Current status:** trial activated 2026-11-17 (account
  `34a96e83-bf8c-4002-b5e1-7c2757d6500b`, key = Secret Manager `Planet-labs`
  v3): 3,000 monitoring credits, 1 OAuth client seat, Sandbox Data + Open
  Data + BYOD, Catalog/Statistical/Process/OGC APIs. Trial terminates
  **2026-12-17**. Decision checkpoint **2026-11-30**: purchase, or accept
  downgrade to header-only Open Data + Sentinel-2.
- **Next action:** before 2026-11-30, request a written quote for a
  commercial monitoring plan that converts (1) the **quote path** — sales
  contact through the pricing page; (2) **seats** — at least two (ops +
  continuity) against the single trial seat; (3) the **credit model** —
  replace 3,000 trial credits with real monthly consumption maths sized to
  the nightly psscene refresh + soil-water-content pulls; (4) the
  contractual sentence establishing commercial use of derived products so a
  non-specimen grant can be signed. Record purchase-or-lapse here at the
  checkpoint; if purchased, replace `grants/planet-trial.json`.
- **Owner:** lead + founder (human decision at the 2026-11-30 checkpoint).
- **Evidence to attach:** quote PDF / mail thread; executed MSA or
  order-form URL; countersigned contract; invoice; executed grant JSON
  (`specimen: false`) with the same feed list.
- **Expected unlock:** `planet.psscene` and
  `planet.planetary-variable.soil-water-content` gain
  `permits_financial_use=true` for the granted uses; 10 m-class imagery
  enters the commercial spine (roadmap P3) instead of dying with the trial.
- **Sources:** [planet.com/pricing](https://www.planet.com/pricing/)
  (fetched HTTP 200, verified 2026-11-17).

## PL-EE-COMMERCIAL-REGISTRATION · Earth Engine commercial registration flip — `NOT-YET-EXECUTED`

- **Area:** raster processing / exports.
- **Current status:** catalog reads HTTP 200 via the Cloud Run runtime
  identity with `roles/earthengine.viewer`; registration stays `unknown`,
  so `permits_financial_use` stays false and the earth-engine adapter
  refuses sidecars claiming financial use under noncommercial/unknown
  registration (R-licence).
- **Next action:** human completes the commercial-registration path in the
  Earth Engine / Cloud console, documents the resulting registration value
  into `ee_registration` on `MethodVersion`, re-verifies an export-capable
  call end-to-end, and only then attaches an executed grant
  (`specimen: false`) for `earth-engine.export` naming that evidence.
- **Owner:** founder (console actions) + lead (record + grant).
- **Evidence to attach:** registration confirmation (ID/screenshot);
  billing-account linkage; export smoke result; executed grant replacing
  `grants/ee-commercial-specimen.json`.
- **Expected unlock:** `earth-engine.export` permitted for the granted
  uses; export-derived NDVI/indices become commercial-grade inputs with
  support and error statements travelling unchanged.
- **Verify exact steps:** the registration UI path changes; locate the
  current commercial sign-up page from the product documentation root.
- **Sources:**
  [developers.google.com/earth-engine](https://developers.google.com/earth-engine)
  (documentation root reached 2026-11-17);
  [farm-seges-ai (prod)](https://farm-seges-ai-451400509859.asia-east1.run.app)
  (`docs/backend-live.md`: registration=unknown today).

## PL-OPENMETEO-Q9 · Open-Meteo Q9 — business/commercial licence text — `NOT-YET-EXECUTED`

- **Area:** NWP forecast grids.
- **Current status:** Q9 undecided. Adapter assumptions that change only
  when Q9 lands (`farm_ontology/adapters/open_meteo.py`): (1) the header
  "financial use stays false (Q9)" — a business-tier answer lets a *grant*
  decide, with sidecar writers consuming `evaluate()` instead of the
  hard-coded false; (2) **kept forever** — the refusal that Open-Meteo is
  not the legal meteorological authority; (3) **kept** — `jma_msm` native
  0.05 deg / 5 km minima and the no-consensus rule. The free tier is
  consumed with no API key.
- **Next action:** obtain the written business/commercial-tier licence
  text (capability gates, attribution duties, redistribution of derived
  products); founder's Q9 decision memo; attach an executed grant
  `open-meteo-q9` (`specimen: false`) scoped to the decided uses; adjust
  sidecar writers only at that point.
- **Owner:** licences agent (drafts the Q9 memo) + founder (decides).
- **Evidence to attach:** terms snapshot (HTML/PDF) + URL + fetch date;
  licence email thread; signed Q9 memo; executed grant replacing
  `grants/open-meteo-q9-specimen.json`.
- **Expected unlock:** `open-meteo.jma-msm` leaves Screening for the
  granted uses only, attribution preserved in every publication text
  (publication tests stay truthful); anything not granted stays refused.
- **Sources:** [open-meteo.com/en/license](https://open-meteo.com/en/license)
  (fetched HTTP 200; content JS-rendered — capture a snapshot when drafting
  the Q9 memo; verified 2026-11-17).

## PL-JMA-REDISTRIBUTION · JMA redistribution — official data usage terms; 二次提供 — `NOT-YET-EXECUTED`

- **Area:** official weather warnings / hazard feeds.
- **Current status:** torrential-rain, snow, marine warnings and the
  two-week/seasonal headers are recorded from JMA publication. Whether
  commercial redistribution of these (or derivatives) requires JMA-site
  usage-term compliance beyond copyright attribution — or constitutes
  **二次提供** (secondary provision) needing a separate arrangement — is
  **UNVERIFIED**. We never claim to be the legal meteorological authority;
  that adapter refusal is permanent.
- **Next action:** verify the current JMA site usage / copyright notice
  for commercial redistribution; check the 気象業務法 (Meteorological
  Services Act) and related guidance for whether our product pattern
  counts as 二次提供 requiring registration/notification/agreement;
  record findings here (still without legal conclusions); if an agreement
  or notice is required, prepare it for founder signature, then attach an
  executed `jma.hazard` grant.
- **Owner:** founder (external enquiry) + licences agent (evidence pack).
- **Evidence to attach:** JMA terms snapshot + URL + fetch date;
  statute/guidance excerpts with URLs; mail thread with JMA or a
  meteorological-business support body if engaged; executed grant when
  applicable.
- **Expected unlock:** `jma.hazard` permitted only to the extent the terms
  verifiably allow (e.g. redistribution of recorded warnings inside
  commercial advisories); every publication text keeps JMA attribution.
- **Sources:** [jma.go.jp](https://www.jma.go.jp/) (site root — the
  usage/copyright notice sits in the page footer; site paths move, snapshot
  the current terms on entry);
  [e-Gov search: 気象業務法](https://laws.e-gov.go.jp/search?keyword=%E6%B0%97%E8%B1%A1%E6%A5%AD%E5%8B%99%E6%B3%95)
  (check registration/certification duties before commercial weather
  publication; verified 2026-11-17).

## PL-ACTUATION-COMPLIANCE · Actuation-era compliance stubs — `NOT-YET-EXECUTED`

- **Area:** actuation (WS5 prerequisites).
- **Current status:** no machine/drone/valve interface exists yet (roadmap
  ground truth). Three requirement families must be verified before any
  live actuation packet:
  1. **航空法 (drone)** — airframe registration (mandatory since
     2022-06-20 for ≥100 g), Remote ID, flight permission/approval via
     DIPS2.0; beyond-visual-line-of-sight spraying rides the **レベル4
     (level 4)** certified-airframe / certified-pilot framework; spraying
     flights add duties atop generic flight permissions.
  2. **農薬適用基準** — a spray prescription may only cite registered
     crop × agent combinations per the FAMIC/ACIS 農薬登録情報
     (application criteria); aerial (drone) application sits under
     prefectural and MAFF guidance layered on the registered uses.
  3. **ISO11783 data ownership** — the TaskData standard governs
     interchange format, **not** data rights; before the command ledger
     dispatches anything derived from machine telemetry, the machine
     vendor's data-rights terms must be read and a data-sharing agreement
     signed.
- **Next action (design stubs, closed doors by default):** command-ledger
  `propose` refuses a drone packet lacking permit numbers; the
  recommendation engine refuses spray rows not matching registered uses;
  the command ledger refuses telemetry-derived prescriptions absent a
  signed data-sharing agreement. Humans verify each family and record
  evidence here; no live actuation before the Phase-4 gate regardless.
- **Owner:** lead (specs) + actuation agent (stubs) + founder
  (registrations/signature).
- **Evidence to attach:** airframe registration numbers; pilot
  certificates; DIPS2.0 flight-permission receipts; registered-use
  extracts per agent/crop (FAMIC); machine-vendor data-rights excerpts +
  signed data-sharing agreement.
- **Expected unlock:** WS5 deliverables become lawful to execute against
  real machines in the Phase-4 window. These three families are separate
  certificates/evidence attached to command-ledger records — a vendor grant
  alone cannot substitute for them. Packet-producing code does not exist
  yet (WS5 scope); the stubs live here so WS5 inherits closed doors, not
  open guesses.
- **Sources:**
  [mlit.go.jp/koku/drone](https://www.mlit.go.jp/koku/drone/) (registration
  portal, fetched HTTP 200),
  [mlit.go.jp/koku/level4](https://www.mlit.go.jp/koku/level4/) (BVLOS
  framework),
  [mlit.go.jp/koku/permitapproval](https://www.mlit.go.jp/koku/permitapproval/)
  (permission/approval applications) — all linked live from the
  registration portal, verified 2026-11-17;
  [acis.famic.go.jp](https://www.acis.famic.go.jp/) (FAMIC pesticide hub,
  fetched HTTP 200);
  [committee.iso.org/home/tc23](https://committee.iso.org/home/tc23)
  (ISO/TC 23, custodian of the ISO 11783 series — verify the data-ownership
  posture with machine vendors; verified 2026-11-17).

## PL-CORPORATE-STATUS · Corporate status dependency — who signs grants — `NOT-YET-EXECUTED`

- **Area:** corporate / legal identity.
- **Current status:** company incorporation **in progress** (owner-reported,
  2026-11). Until the register (登記) issues, no corporate principal exists
  for countersigning vendor contracts, grants, or the farmer-facing
  contract pack; a purported signature by a not-yet-existing entity is a
  void-risk that would invalidate the very unlock evidence grants carry.
- **Next action:** confirm incorporation completion; obtain the
  登記事項証明書 and 法人番号; fill the contract-pack signatory block with
  the registered entity name and representative; retro-bind every executed
  grant's `issuer`/seat naming to the corporate entity (sole-proprietor
  interim grants must state personal capacity explicitly).
- **Owner:** founder (human; registry actions).
- **Evidence to attach:** certificate of registered matters (scan + fetch
  date); corporate-number notification; updated signatory block; grant
  re-issue notes for any interim grants.
- **Expected unlock:** executed grants attributable to a legal person —
  the prerequisite for PL-PLANET-COMMERCIAL /
  PL-EE-COMMERCIAL-REGISTRATION signatures and for the contract pack to
  leave READY-TO-SIGN.
- **Sources:** [moj.go.jp](https://www.moj.go.jp/) (Ministry of Justice —
  法務局 corporate registration procedures and certificates; verified
  2026-11-17).

---

Checkpoint cadence: revisit this list at every roadmap phase boundary
(P0 hardening → 2026-11-24; trial checkpoint → 2026-11-30; P3 commercial
spine → 2027-01). The unlock ledger (`grants/state.json`) is the
machine-readable half of this file.
