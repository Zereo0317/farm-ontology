# Pilot readiness — implementation status

This is an engineering status record, not a field, legal, or financial
certification. The fixes on the local integration branch are not deployed.

## Release blockers

- The observed production backend still reports `use_class=Settlement` and
  `permits_financial_use=true` on `/farm` (read-only check 2026-11-22).
  The source branch closes that metadata bypass, but it takes effect only
  after a separately authorized, verified deployment. Provider rights must
  be checked independently for each data source and use.
- The web shared-token gate is containment only. Individual identities,
  farm-scoped authorization, revocation, and two-farm isolation are not
  implemented. Boundary POST uses same-origin JSON and a size limit, but rate
  limiting is not yet implemented. Existing clients need the login gate.
- The landing page contains unverified finance and investor-return language;
  source reports have evidence holds but the public landing requires review
  and a separately authorized release.
- The nightly exporter requires `FARM_ARCHIVE_BUCKET` to identify a separate
  bucket. Provision access, retention, independent administrative protection,
  and run an isolated restore drill before releasing the exporter. Local
  archive storage is not an independent failure domain.
- The release workflow changes have not run in GitHub Actions or Cloud Run.
  Backend promotion requires a successful new staging deployment and verified
  image; web forward production promotion remains disabled pending a web
  staging service and same-digest promotion gate.
- Irrigation callers must supply a dated initial state and source availability
  metadata. These fields are assertions, not verified calibration or source
  records. Existing archive fixtures without that evidence refuse. Validate
  agronomy prospectively and bind sensor and product-label evidence before
  growers rely on recommendations.
- Market artefacts deliberately fail closed without trusted provider rights,
  farmer consent, and cap approvals. The research-only capture helper checks
  bytes and units but cannot verify sources, rights, or historical availability
  before capture. The synthetic backtest is not a real-market backtest.
- Actual field trials, equipment purchase and calibration, company formation,
  executed contracts, legal assessment, broker controls, paper-ledger
  reconciliation, emergency drills, and a seasonal validation remain open.

## Verification and operating notes

Run the full hermetic suite and `node --test web/tests/*.test.cjs` with web
workspace dependencies installed. A passing suite does not establish live
service configuration, real-device acceptance, commercial rights, or the
outcome of field trials. Record the tested revision, full commit SHA, exact
image digest, check outputs, owners, and approvals in the release record.
