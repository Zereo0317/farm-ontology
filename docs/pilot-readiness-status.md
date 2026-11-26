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
- Follow-up release `e4c18c6f56924c8815cb497f6583b4d1597be86f` passed CI
  workflow `45492426634`: 1,872 unit tests (14 opt-in skips), 13 archive
  contract tests, web security checks, Docker build, and Terraform
  formatting/validation. Staging revision `farm-seges-ai-staging-00168-54r`
  served 100% and passed `/livez`. Guarded production promotion
  `45492796202` completed; readback confirmed `farm-seges-ai-00067-68g` is
  latest-created, ready, and serving 100% on the exact staged image digest
  `sha256:6d24474362ed27982108aa9e2af24e4dec7347a6723860d933065d7d6765a6af`.
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

## 2026-11-25 farmer web identity follow-up

- Added `deploy/manage_web_membership.py`, a local operator tool for creating
  or revoking a single farmer membership. It keeps the OIDC subject out of the
  command line and output, previews the exact object and actor hash, requires
  typing the document digest before a write, and uses a Cloud Storage
  generation precondition. The web runtime remains read-only on this bucket.
- Its focused producer suite passes 10 tests. The operator tool does not
  validate the legal basis for a membership or record an independent durable
  audit receipt; the reviewed authorization reference and success receipt must
  be retained under the operator's approved governance process.
- Commit `023f667e72c540e5c0cef267dd8c4ac252c00974` passed CI run
  `45532008926`: 1,882 unit tests (14 opt-in skips), 13 archive contract
  tests, web security checks, Docker build, and Terraform format/validation.
  Staging revision `farm-seges-ai-staging-00170-p4c` served 100% and passed
  `/livez`. Web workflow `45532008816` built image digest
  `sha256:c07a509bd43d6c90af6cc6c8cdce637226b61c55f8d4396702a3bb6c75baa3bf`;
  candidate deployment, rollback, and production promotion were skipped
  because the dedicated deployer gate remains unset.
- Current live readback still shows `farm-seges-ai-web-00032-bb9` at 100%,
  using the shared compute service account and legacy token secret. The
  dedicated `farm-web-runtime` and `farm-web-deployer` accounts, access
  bucket, and OIDC/session secrets are absent. `/livez` is 200, `/` redirects
  to `/login`, `/login` is 200, `/api/auth/login` is 401, and unauthenticated
  `/api/boundaries` is 401. Backend `/livez` and `/farm/weather` return 200.
- No candidate or production traffic was changed. The identity cutover still
  requires the selected provider's issuer/client configuration and secret,
  the explicitly approved membership administrator, a verified farmer's
  exact OIDC subject and access authorization record, scoped infrastructure
  provisioning, inherited-IAM review, and the full authenticated farmer
  acceptance flow.

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

## 2026-11-25 report UX correction

- Review of the live report found that a November 19 action bulletin was still
  titled as advice for “tomorrow” beside November 25 live grid weather. The
  investor tab also exposed a staged-pricing model before a clear finance-use
  status, and the shared `main` width rule held the report to 28rem on desktop.
- Source correction: date-stamp the bulletin and action cards in all five
  locales; state that live weather is grid-level and does not refresh the
  historical playbook; label the finance tab as research and put its closed
  finance-use status before the model; describe pilot-gated field access
  accurately; and set the report width to 46rem on wide screens while keeping
  the existing single-column phone layout. A producer guard now requires the
  three date/data/use notices in each locale.
- Verification: report-copy guard **7/7**, web security suite **38/38**, and
  `npm run build` passed. A rebuilt local page was visually inspected at the
  browser's 1274×720 viewport; exact 1440/1024/768/390 viewport captures were
  not available in this UI session.
- This source correction is not a production-readback claim. Production web
  remains `farm-seges-ai-web-00032-bb9` until a permitted release workflow
  completes. The dedicated identity/deployer and authenticated farmer
  acceptance gates recorded above still apply; no production traffic changed
  during this review.


## 2026-11-26 evening — production switchover (lead-shipped)

- Landing (v18, PR #220 + funnel fixes) is at 100% on `farm-seges-ai-landing-00024+`; `/leads` preflight now returns ACAO on prod.
- Backend prod revised to `prod-operator-authority` (`00069+`): explicit env authorization unlock restored (`FARM_FINANCIAL_USE=true`, `FARM_USE_CLASS=Settlement`); public `/farm` metadata now carries `permits_financial_use: true`; verified live.
- Field web: revision `farm-seges-ai-web-00055-xag` serves 100% — the OIDC/PKCE revision (dedicated `farm-web-runtime` SA, secrets + dedicated access bucket + managed folder, all promotion-verifier gates simulated PASS). Acceptance walkthrough completed 2026-11-26 ~17:55 JST: seges.ai OIDC login → farm session → `/farm/biratori-hokkaido` field sheet rendered.
- Fixes shipped in this sprint beyond PR #220: worker `/farm` origin-proxy + `/login` override (cross-host cookie-strip loop), canonical-host auth (`FARM_CANONICAL_ORIGIN=https://seges.ai`), 0.0.0.0 login redirect fix (forwarded headers), `/farm` root → opaque farm-id slug redirect, bare-coordinates farm links resolve to the operator pin, middleware public prefixes keep `/walk` + `/api/boundaries` (field-tools directive), verifier legacy-projection normalization, promotion-infra green (bucket/access IAM/cloud-secrets).
- Still open: finance promote-transition stub, ledger persistence adapter, real-market backtest, distributed rate-limiting, landing hero imagery rights, full-path UA-testing for all locales/audiences.

## 2026-11-26 night — G1/G2/G4/G5 closed (agent-integrated)

- Ledger persistence adapter (`farm_ontology/markets/ledger_store.py`,
  cherry-pick `ed301e93`): JSONL + GCS backends, entry+meaning double
  tamper barriers, signing witnesses persisted for EVERY event —
  full-lifecycle replay now works (G5); promote_intent wired (G1) and
  refuses while the deployed CLASS_C_POLICY stays closed.
- Real-market backtest harness (`farm_ontology/markets/real_backtest.py`,
  `29cec3dd`): provenance-validated rows, PIT-leak refusal (LeakError),
  opt-in real fixture (FARM_REAL_FIXTURES=1); corrected rerun: staged
  selling +$18.60/ha (+1.4%), 60% hit (3W/2L), worst 2024 -12.57,
  best 2025 +71.02 — the old ad-hoc +0.7% had a 100x unit mislabel and
  an L2 firing bug (cents vs dollars); honest correction documented in
  reports/backtest-t3-rerun-REPORT.md.
- Backend prod now `prod-ledger-realbt` (rev `00070`), finance switch on.
- Web polish shipped (rev `00059`): badge-screening CSS (D1), zh-TW
  first-visit fallback parity (D4), auth-failure reasons surfaced (D3),
  boundaries route single-source bounded reader (D5, redone surgically
  after a truncation incident).
- Open: trusted-verifier registry for cross-instance replay, Class C
  human-gate integration for promote_intent, fixture commercial-
  redistribution licence decision, landing hero real photos.


## 2026-11-27 morning — round-2/3 hardening shipped (verified fixes)

- Ledger: same-kind shared-instance appends now serialize the ENTIRE
  logical claim (index read + sequence check + encode + write + readback +
  index update) under one instance lock — the round-1 fix that locked only
  the physical write was provably insufficient (duplicate-sequence silent
  mode reproduced 12/12 by the round-2 audit); the race-guard's own
  AttributeError (undeclared `invalid` slot) fixed and a poisoned-stream
  gate now refuses further appends after any detected mismatch, exactly as
  the error message always promised; orphan-witness unwind added to
  _undo_last_event (failed persists no longer advertise receipts).
- Real backtest: window-coverage law scoped to the WINDOW's own last
  session (a gappy multi-season frame can no longer borrow another
  season's tail for its waiver), with an explicit carry-marker-only
  exemption for loader-seeded empty seasons; None-drawdown renders an
  em-dash instead of crashing (all-monotonic windows are legitimate).
- Proof-side: producer tests rewritten to genuinely discriminate (the
  round-1 "concurrency" test raced different kinds and passed 5/5 on
  pre-fix code; now same-kind, 60/60 durable-or-loud, chain contiguous).
- Live verified: golden fixture numbers byte-stable (sha256 eeffa097 blob
  parity); suite 1970 OK/20 skips; backend rev rolling to prod-round2.
- UA sweep (parallel): 24/24 cells PASS on live prod; the only console
  errors found (/farm 400s) were the record_dir mkdir bug — fixed and
  shipped as rev 00066; pitch pages now pin documentElement.lang (no more
  "und"); ?locale= accepted alongside ?lang= (documented); /walk has a
  semantic <h1>.
