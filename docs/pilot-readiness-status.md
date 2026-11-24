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
- Source now includes per-person OIDC sessions, farm-scoped membership and
  role checks, revocation-on-next-request, tenant-scoped records, and
  idempotent observation/note/boundary writes. Production is still on the
  legacy shared-token revision: no OIDC client/session secrets, dedicated
  access bucket/runtime identity, or farmer membership has been provisioned
  and accepted. Boundary POST uses same-origin JSON and a size limit, but
  distributed rate limiting is not implemented.
- The deployed landing copy describes research and evidence limits. It does
  not establish investment performance, farmer outcomes, or an opportunity
  to trade. Any future finance claims require evidence and review before use.
- Source now includes bounded restore tooling and a Terraform stack for a
  separate farm-only archive project. It has not been provisioned or applied;
  project/bucket names, billing, budget and operator identities still require
  owner confirmation. Complete a timed isolated restore before activating the
  exporter or scheduler. Local archive storage is not an independent failure
  domain.
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

## 2026-11-25 source implementation and backend release follow-up

- Local `main` now contains tenant-scoped record storage and request-UUID
  idempotency for observations, notes, and boundary walks; legacy unscoped
  records remain unassigned. Tenant feed routes return gaps for farms without
  configured feeds.
- Web source now has fail-closed OIDC/PKCE identity, issuer/subject-bound
  sessions, per-request membership/role/revocation checks, bounded request and
  upstream JSON bodies, and matching tenant request IDs. OIDC `azp` validation
  rejects mismatches and requires it for multi-audience tokens.
- Finance controls now honor the authoritative closed Class C switch, reject
  unverifiable approval replay, bind rights/consent scope, and enforce
  evidence freshness. They do not create a live-order path or authorize finance
  activity while Class C is closed.
- Archive infrastructure now uses a separately provisioned project, bounded
  restore validation, read-only-by-default scheduler handling, and a private
  state-bucket operator grant. Its IaC validates but is not applied; timed
  smoke and restore drills are still outstanding.
- The web release workflow now builds tagged candidates without production
  traffic. Promotion requires a manual exact-digest acceptance, a matching
  `FARM_WEB_ACCEPTANCE_DIGEST` in the `web-production` environment, OIDC
  runtime metadata and direct IAM checks, enabled secret versions, then tagged
  login/API smoke checks. The protected environment and its accepted digest
  are not configured in GitHub yet. This protects production from automatic
  cutover to an unconfigured login.
- The archive Terraform stack now defines a private web membership bucket,
  dedicated runtime and main-branch deployer identities, prefix-scoped
  append/read access for `field-notes/farms/`, two empty OIDC/session Secret
  Manager entries and scoped grants. Its scheduler remains disabled by
  default. Terraform 1.8.5 formatting and validation pass in CI and locally.
- The final promotion gate now requires the exact dedicated runtime identity,
  exact membership-bucket and tenant-folder direct grants, no direct runtime
  grant on the parent records bucket, no project grant for the runtime, and a
  single-purpose project IAM metadata role for the deployer. The explicitly
  authorized membership administrator principal must match the Terraform
  output mirrored to GitHub. This still cannot prove effective access from
  inherited organization/folder IAM or group membership.
- GitHub environment `web-production`, acceptance digest, independent reviewer,
  and `FARM_WEB_DEPLOYER_READY` variable are not configured. The candidate
  deploy job stays skipped until the dedicated WIF identity is provisioned.
- Promotion IAM checks inspect the membership bucket, records bucket, tenant
  managed folder, and project direct bindings. Inherited organization/folder
  roles and access through broad groups require a separate owner-side
  effective-IAM review before the membership store is trusted.
- The backend, source changes, and release gates were pushed to `main` at
  `2b82caac498de34e430b3d81190d47c5d6b5ad78`. GitHub run
  `45489929774` passed 1,868 unit tests (14 opt-in skips), 13 archive
  infrastructure contract tests, the web security suite, Docker build, and
  Terraform 1.8.5 formatting/validation. Staging revision
  `farm-seges-ai-staging-00165-cps` served 100% and passed `/livez`.
- The guarded backend production promotion `45490307600` succeeded. Readback
  confirmed `farm-seges-ai-00066-vk7` is latest-created, ready, and serving
  100%, on the exact staged image digest
  `sha256:d2e25a9f5f89a0c403674bbb58b4ba3d546572b62f73ecd1b0350d2d4731b094`.
  Production `/livez` and `/farm/weather` smoke verification passed.
- The updated web bundle was built as candidate digest
  `sha256:08b36961a7cbd2726e1df976ba8cf5ba57369ea69b3930f8d5ea9191ce7248e5`
  in workflow `45488798307`; candidate deploy and production promotion were
  skipped because the dedicated deployer/runtime foundation is not ready.
  Current readback remains `farm-seges-ai-web-00032-bb9` at 100%, with the
  shared compute service account, no OIDC/access-bucket configuration, and
  the legacy token setting. Live web smoke returned `/livez` 200, `/` 307,
  report 200, and unauthenticated boundaries 401. The new farmer-account
  login, membership, tenant-isolation, and revocation flow is not live or
  accepted.
- Landing source was not changed; current readback remains
  `farm-seges-ai-landing-00020-dj4` at 100%.
- Terraform is formatted and validated but not applied. The separate archive
  project, storage resources, identities, secrets, schedule, and restore drill
  remain unprovisioned. Archive promotion therefore cannot be claimed.
- These releases do not close source-rights review, prospective agronomy
  validation, effective inherited-IAM review, distributed rate limiting,
  archive restore/alert drills, legal/operational sign-offs, or Class C. Class
  C remains closed and no broker/order path exists.

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

## 2026-11-24 follow-up release

- Runtime source tested and promoted: `0f8bfa5a8aede4a2e287938cebff805601821766`. The application
  changes are from `6c3badd19136834a98ecc7b2471134625cd8ed8b`; the final
  follow-up only corrects the production verifier's GitHub Actions query to
  request completed runs and check `conclusion=success` itself.
- Verification: GitHub Actions run `45403797712` passed tests, byte compile,
  Docker build, and staging deployment. Staging
  `farm-seges-ai-staging-00162-4g2` receives 100% traffic and passed `/livez`.
  The combined local hermetic suite passed **1,822 tests, 14 skipped**.
- Backend production: promotion run `45404296836` succeeded. Cloud Run
  `farm-seges-ai-00065-mz2` is latest created/ready and receives 100% traffic;
  the workflow verified the staged digest and passed `/livez` plus weather
  smoke before completing.
- Field web: workflow `45402610167` succeeded after building the updated
  backend bundle. Cloud Run `farm-seges-ai-web-00032-bb9` is latest
  created/ready and receives 100% traffic; web gate, report, and protected
  boundary smoke checks passed.
- Landing source was unchanged in this follow-up. Cloud Run
  `farm-seges-ai-landing-00020-dj4` remains latest created/ready at 100%; the
  public apex release and locale smoke passed on the 2026-11-22 release.
