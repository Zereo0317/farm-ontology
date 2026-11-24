# Web identity cutover readiness

The web code uses per-person OpenID Connect sessions and checks farm membership
on every farm API request. This change is fail-closed when identity or the
membership store is missing. Keep the existing production revision serving
traffic until every gate below is verified on a candidate revision and an
authorized farmer account.

## Required runtime configuration

Configure these values on a candidate revision only:

| Variable | Required value |
| --- | --- |
| `FARM_OIDC_ISSUER` | Exact HTTPS issuer advertised by the selected Google Identity Platform / OIDC provider. |
| `FARM_OIDC_CLIENT_ID` | OAuth client ID registered for this web application. |
| `FARM_OIDC_CLIENT_SECRET` | Secret Manager reference for the OAuth client secret; never a literal in deployment commands. |
| `FARM_OIDC_REDIRECT_URI` | Exact HTTPS public URL ending in `/api/auth/callback`; it must be registered at the identity provider. |
| `FARM_SESSION_SECRET` | Secret Manager reference to at least 32 random bytes, stable for all instances of the revision. |
| `FARM_ACCESS_BUCKET` | Dedicated bucket containing only farm access-control membership records. |

The runtime service account needs read-only object access to the access bucket.
Memberships are read from `farms/<farm_id>/members/<sha256(issuer + NUL +
subject)>.json`. Each document must match the requested farm and actor hash,
have role `viewer`, `operator`, or `admin`, status `active`, and a future
`expires_at`. Membership edits remain a separate, explicitly authorized
administrative workflow; do not grant write access to the web runtime.

Do not copy the legacy `WEB_ACCESS_TOKEN` into the new revision as a fallback.
The app does not use it. An unconfigured candidate should show a 503 gap on
protected pages and the login route, and 401 for unauthenticated farm APIs.

## Candidate checks

1. Verify deployment metadata without printing secret values. Confirm all six
   variables are present and each secret variable is a Secret Manager
   reference. Confirm the candidate service account can read the dedicated
   access bucket and cannot write membership objects.
2. With the candidate receiving no production traffic, request `/livez`,
   `/api/auth/login`, `/`, and an unauthenticated farm API. Expected results:
   health succeeds, login redirects to the configured provider, the page
   redirects to login, and the API returns a JSON 401 gap.
3. Sign in using the authorized pilot farmer account. Confirm the callback
   sets an HttpOnly, Secure, SameSite=Lax session cookie, and verify a viewer
   can read only its assigned farm while operator writes require the operator
   role. Confirm an unassigned farm is denied and a revoked membership is
   denied on the next request.
4. Verify observation, note, and boundary retries with the same payload and
   request UUID return the original record; changing the payload under that
   UUID must be refused. Confirm legacy unscoped records do not appear in the
   tenant list.
5. Verify authorized advisory calls use `/farm/<farm_id>/weather`,
   `/planet`, and `/licences`. Unconfigured farm feeds must render an explicit
   gap. Confirm public report and locale routes still work.
6. Only after these checks pass, use the normal reviewed deployment process
   to move traffic. Keep the prior image digest and revision available for
   immediate rollback. Never use `--to-latest` until the candidate is approved.

## Current production gate

The existing production revision is configured for the legacy shared-token
gate and has no `FARM_OIDC_*`, `FARM_SESSION_SECRET`, or `FARM_ACCESS_BUCKET`
configuration. No farmer membership has been verified against the new access
store. This branch is therefore a code candidate only and is **not ready for
production traffic**. Do not promote it until the runtime configuration and
at least one authorized farmer membership have been established and all
candidate checks pass.
