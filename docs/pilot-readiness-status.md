# Pilot readiness — implementation status

This is an engineering status record, not a field, legal, or financial
certification. Main commit `110e1e94bc913346ae531b12b1aed01800db28bb` was
deployed to the farm production backend, field web, and public landing on
2026-11-22. The production workflows and Cloud Run traffic readback succeeded;
see the release evidence below.

## Release blockers

- Provider rights must be checked independently for each data source and
  use. The deployed public metadata path fails closed without verified rights;
  this does not grant commercial rights or establish the terms of any source.
- The web shared-token gate is containment only. Individual identities,
  farm-scoped authorization, revocation, and two-farm isolation are not
  implemented. Boundary POST uses same-origin JSON and a size limit, but rate
  limiting is not yet implemented. Existing clients need the login gate.
- The deployed landing copy describes research and evidence limits. It does
  not establish investment performance, farmer outcomes, or an opportunity
  to trade. Any future finance claims require evidence and review before use.
- The nightly exporter requires `FARM_ARCHIVE_BUCKET` to identify a separate
  bucket. Provision access, retention, independent administrative protection,
  and run an isolated restore drill before releasing the exporter. Local
  archive storage is not an independent failure domain.
- The deployed backend and frontend revisions are recorded below. The web
  workflow builds and deploys an immutable image digest after its checks;
  backend production promotion used the tested staging image. Keep these
  release gates for subsequent changes.
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

## 2026-11-22 production release

- Source: `110e1e94bc913346ae531b12b1aed01800db28bb` (`main`).
- Backend production promotion: GitHub Actions run `44970636758` succeeded
  after the matching staging deployment and production smoke. Cloud Run
  `farm-seges-ai-00064-xnc` is latest ready and receives 100% traffic.
- Field web: GitHub Actions run `44970463505` succeeded, including production
  deployment and smoke. Cloud Run `farm-seges-ai-web-00030-8mn` is latest
  ready and receives 100% traffic.
- Public landing: GitHub Actions run `44970463478` succeeded, including apex
  smoke. Cloud Run `farm-seges-ai-landing-00020-dj4` is latest ready and
  receives 100% traffic.
- The backend `/livez` and weather promotion checks, the web gate/value-route
  checks, and the landing locale/apex checks passed in their release
  workflows. A direct local PowerShell HTTPS probe could not complete because
  the workstation rejected the remote certificate chain; it is not counted as
  independent endpoint evidence.
- Backend release source keeps financial-use metadata closed without verified
  provider rights. Class C remains closed. The paper ledger and synthetic
  backtest are research tools; there is no broker integration or live order
  execution.
