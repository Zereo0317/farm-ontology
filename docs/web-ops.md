# Web service ops — farm-seges-ai-web

Release history and current serving revision are tracked in
[`pilot-readiness-status.md`](pilot-readiness-status.md). On 2026-11-22,
Cloud Run revision `farm-seges-ai-web-00030-8mn` was verified at 100% traffic
after the production web workflow passed its build, test, traffic, and smoke
checks. The older WS8 revision numbers and build IDs below are historical.

The Next.js field app (`web/`) is hosted as Cloud Run service
**`farm-seges-ai-web`**, project `seges-ai`, region `asia-east1`. The page's
observati­on writes keep flowing through the stdlib record bridge
(`python -m farm_ontology.page_io`) into the durable record store
(`FARM_RECORD_BACKEND=gcs`, bucket `gs://farm-seges-ai-records`, prefix
`field-notes/`), so a phone in the field writes the same record shape the
backend does. Live feed data (weather / Planet headers / licence verdicts) is
proxied read-only from the decision backend.

## 1. What runs where

| Piece | Place |
| --- | --- |
| Field page + panels | `web/app/page.tsx` (client sheet `web/app/field-sheet.tsx`) |
| Advisories panel | `web/app/advisories.tsx` (server component) |
| Advisories proxy | `web/app/api/advisories/route.ts` ← `web/lib/backend.ts` (`FARM_API_BASE`, revalidate 60 s, gap shape on upstream failure) |
| Access gate | `web/middleware.ts` + `web/app/login/page.tsx` + `web/app/api/access/route.ts` |
| Health (uptime) | `/livez` — `/healthz` is reserved by the run.app edge, as on the backend |
| QR deep link | `/farm/<farm_id>` → farm-specific field sheet without coordinates in the URL |
| Record writes | `web/lib/record.ts` spawns `python -m farm_ontology.page_io`; on Cloud Run the GCS backend writes with the runtime service account (`FARM_RECORD_DIR=/tmp/field-notes` satisfies the bridge's eager local `mkdir` — see §3) |

## 2. Build (Docker proven on Cloud Build; this host has no docker engine)

This workstation has no Docker daemon, so the image is built **on Cloud
Build** — which is simultaneously the required "build succeeds in Docker"
proof and the deployment artefact factory. The repo-root `.gcloudignore`
excludes `web/`, so a repo-root `--source` deploy cannot see the web app;
instead `web/tools/web-image-build.ps1` stages a curated context
(`web/` without `node_modules`/`.next`, the stdlib-only `farm_ontology/`,
`vocabulary-manifest.json`) with `Dockerfile.web` renamed to `Dockerfile`:

```powershell
pwsh -NoProfile -File web/tools/web-image-build.ps1 -TagSuffix ws8-v5
# → gcloud builds submit .dockerbuild-web/. --project seges-ai \
#     --tag asia-east1-docker.pkg.dev/seges-ai/cloud-run-source-deploy/farm-seges-ai-web:ws8-v5
```

Image recipe (`Dockerfile.web`, multi-stage, non-root):

1. `deps` + `builder` on `node:20-slim` — `npm ci --ignore-scripts`, then
   `node node_modules/next/dist/bin/next build` (direct-node invocation, the
   `.bin` exec-bit pitfall from docs/backend-live.md). `output: "standalone"`
   is set in `web/next.config.ts`.
2. `runner` on `node:20-slim` — adds `python3-minimal` +
   `python-is-python3` (record bridge) and `ca-certificates`, copies the
   standalone server + static assets + `farm_ontology/`, runs as the
   non-root `node` user, listens on `PORT 8080`.

### Cloud Build proof (real logs, 2026-11-18)

Every iteration was built remotely by Cloud Build (kaniko) — the Docker
proof, this host having no docker engine at all:

| Tag | Build ID (success) | Image digest (sha256) |
| --- | --- | --- |
| `ws8-v1` | `d5f2e161-a98c-4893-824f-29b48eecd09d` | `9b93e8a8c644e658fa79071cfd528f8ea7423313d7449997d61c56f0aebd3454` |
| `ws8-v2` (+python runtime layer) | `ae68d942-e878-4437-98a8-5ca2c1d99ad9` | `40064e8c8b3066be32ecbab53757c6e788d2b2432fc82b6affb9e23c92d540a5` |
| `ws8-v3` (x-forwarded-origin fix) | `b2d399c4-e0fa-458a-b55e-c36e1b25c00c` | `b28d4374848fe04f75beba07445734c6192cd6b2bac547525264158b1846350e` |
| `ws8-v4` (secret-trim hardening) | `082f3f1e-2531-47b3-9f7b-276c69dc585c` | (see `gcloud builds list`) |
| `ws8-v5` (**serving image**) | `3d0f09ab-43c7-40e8-af84-cc19cf2b4a3c` | (see `gcloud builds list`) |

Typical build: `STATUS: SUCCESS`, 2 min 20 – 3 min, `SOURCE:
gs://seges-ai_cloudbuild/source/…tgz`. Log excerpts retained in the branch
history via these tables; full raw logs live in Cloud Build (region
`asia-east1`).

## 3. Deploy

**Service URL: https://farm-seges-ai-web-451400509859.asia-east1.run.app**
(revision `farm-seges-ai-web-00007-qsd`, serving 100 % at ship time).

```bash
# One-time: the shared field token (never committed; regenerated per rotation)
openssl rand -hex 32 | gcloud secrets create web-access-token --data-file=- --project seges-ai
gcloud secrets add-iam-policy-binding web-access-token --project seges-ai \
  --member=serviceAccount:451400509859-compute@developer.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor

gcloud run deploy farm-seges-ai-web --project seges-ai --region asia-east1 \
  --image asia-east1-docker.pkg.dev/seges-ai/cloud-run-source-deploy/farm-seges-ai-web:TAG \
  --allow-unauthenticated \
  --set-secrets WEB_ACCESS_TOKEN=web-access-token:latest \
  --set-env-vars FARM_API_BASE=https://farm-seges-ai-451400509859.asia-east1.run.app \
  --set-env-vars FARM_RECORD_BACKEND=gcs,FARM_RECORD_BUCKET=farm-seges-ai-records \
  --memory 512Mi --cpu 1 --max-instances 2 --timeout 60
```

`--allow-unauthenticated` is intentional: the middleware gate (§4) sits in
front of every route; upstream reachability alone exposes only the login page
and `/livez`. After deploy, mind the WS1 traffic-shift gotcha:
`gcloud run services update-traffic farm-seges-ai-web --region asia-east1 --to-latest`
when `latestCreatedRevisionName` ≠ serving revision.

⚠ **Env-var semantics**: `--set-env-vars` on `run services update` REPLACES
the entire env set (it does not merge) — list every variable in one flag, as
the final revision does (one revision `00006` briefly served with only
`FARM_RECORD_DIR` and degraded to the local backend; restored in `00007`):
`FARM_API_BASE`, `FARM_RECORD_BACKEND=gcs`, `FARM_RECORD_BUCKET`,
`FARM_RECORD_DIR=/tmp/field-notes`.

## 4. Identity plan — shared-cookie gate (the FREE tier actually deployable today)

Choices considered: IAP needs a Cloud Organization (this project is a
gmail-account project); Firebase Auth is free but drags the JS SDK, a project
console, and a login domain setup into a tool used twice a day by a crew of
one. Chosen instead — a **shared-cookie gate**, ~60 lines, no dependencies:

* `WEB_ACCESS_TOKEN` (Secret Manager `web-access-token`) is the single shared
  crew token. Unset ⇒ gate off (local dev).
* `web/middleware.ts` requires cookie `farm_access == WEB_ACCESS_TOKEN` for
  every route except `/login`, `/api/access`, `/livez`, `_next/static`.
* Pages redirect to `/login?next=…`; API routes answer the backend's gap
  shape: `401 {"gap":true,"reason":"web gate: unauthenticated",…}` — no
  redirect-following clients, no HTML for JSON consumers.
* `POST /api/access` validates and sets the cookie (HttpOnly, SameSite=Lax,
  Secure, 30 days); a wrong token lands on `/login?error=1`.

Upgrade path (documented, not built): drop in Firebase Auth anonymous
sign-in later by swapping the cookie check for a session-cookie verification
against `firebase-admin` (Node runtime, no build-time keys needed), keeping
this exact middleware shape. The shared token stays the no-browser fallback.

Token hygiene: rotate = create a new secret version + redeploy (zero-downtime
revision); the cookie mirrors the token value, so rotation logs out
everyone — acceptable for a one-crew deployment, and the reason the token is
stored as a secret, never in the repo.

⚠ **Secret byte hygiene** (repeat of the WS1 Planet-key `\r\n` postmortem):
piping a value into `gcloud secrets create --data-file=-` through PowerShell
appended `0d 0d 0a` here. Create the secret from a bytes file instead
(ASCII, 64 chars, no newline) and the app additionally `.trim()`s the env
value defensively. Value actually served = secret version 2.

## 5. Cost note

Cloud Run request-based billing with `min-instances=0`, 512 MiB/1 vCPU,
cap 2 instances: a field crew's traffic (tens of sessions/day, ~100 kB JS)
stays inside the free tier — realistically **≈ ¥0/month**, worst case single-
digit yen on cold starts. Secret Manager: 1 active secret version (≤6 free).
Artifact Registry storage: one image ≈ 200 MB (well inside the 0.5 GB free
tier). The TWD 2,000 budget guard (deploy/budget.md) covers surprises for the
whole project. Middleware/IP allowlists/IAP would cost nothing either but the
org constraint decided the plan above.

## 6. QR "open this farm"

Any QR generator, offline or on a phone: encode the farm-specific path
using that farm's configured identifier:

```
https://farm-seges-ai-web-451400509859.asia-east1.run.app/farm/<farm_id>
```

The farm ID identifies which farm to open; it is not a credential. The signed-in
person still needs active membership for that farm before records can be read or
written. The field sheet asks the person to use device location or enter a
location for each observation, so the QR does not publish precise coordinates.
Legacy `/farm/<lat>,<lon>?farm_id=<farm_id>` links remain accepted after range
validation. Coordinate-only links redirect to `/` because they do not identify
an authorized farm. Print the farm-ID QR on the field clipboard; the flow is
scan → sign in → review farm access → enter an observation → save.

## 7. Verified smoke transcript (2026-11-18, standalone build, gate on)

```
GET  /                                          → 307 → /login?next=%2F
POST /api/access (wrong token)                  → 303 → /login?error=1
POST /api/access (good token)                   → 303 → / + Set-Cookie farm_access … HttpOnly; SameSite=lax; Max-Age=2592000
GET  / (with cookie)                            → 200, field sheet HTML
POST /api/observations (no cookie)              → 401 {"gap":true,"reason":"web gate: unauthenticated",…}
GET  /api/advisories (with cookie)              → {fetched_at,…,weather:{gap:false,data:{…42.7018…}},planet:{…matched:250…},licences:{…}}
GET  /livez                                     → {"status":"ok","service":"farm-seges-ai-web",…}
GET  /farm/42.7018152,142.4071291 (with cookie) → 200, coord inputs pre-filled
GET  /farm/not-coords                           → 307 → /
```

The transcript above records the earlier coordinate-link behavior. Current
farm QR links use `/farm/<farm_id>` and rely on the signed-in membership gate.

Production smoke checklist (runs after deploy, at the bottom of this file):
`/livez`, `GET /` → login redirect, cookie login, `/api/advisories` gap/value
behaviour, deep link.

<!-- DEPLOY-PROOF (inserted at ship time, 2026-11-18 07:50Z) -->

**Production verification transcript** (service
`farm-seges-ai-web-00007-qsd`, gate on, secret version 2):

```
GET  /livez                                                        → 200 {"status":"ok","service":"farm-seges-ai-web",…}
GET  /                       (no cookie)                           → 307 https://…run.app/login?next=%2F     ← gate proof
POST /api/access (wrong token)                                     → 303 /login?error=1
POST /api/access (good token)                                      → 303 / + Set-Cookie farm_access=…; Secure; HttpOnly; SameSite=lax; Max-Age=2592000
GET  /                       (with cookie)                         → 200 field sheet (CO_336 + Advisories markup present)
POST /api/observations (no cookie)                                 → 401 {"gap":true,"reason":"web gate: unauthenticated",…}
POST /api/observations (bad JSON, cookie)                          → 400 {"gap":true,"reason":"request body was not valid JSON",…}
GET  /api/advisories         (with cookie)                         → {"fetched_at":"2026-11-18T07:43:41.989Z","weather":{"gap":false,…temperature_2m:7.8…},"planet":{"matched":250,…},"licences":{…}}
GET  /farm/42.7018152,142.4071291 (with cookie)                   → 200, coordinate inputs pre-filled
GET  /farm/not-coords                                               → 307 → /
POST /api/observations (dry-run, cookie)                           → 200 {"file":"obs-20261118T075203Z.json","observation":{…dry_run:true, class_c_policy:"closed", permits_financial_use:false…}}
gcloud storage ls gs://farm-seges-ai-records/field-notes/obs-20261118T075203Z.json
                                                                   → object present  ← durable-record proof
```

Earlier revisions (proof of iteration, all serving→replaced):
`00001-zrf` (ws8-v2 first ship), `00002-5cf` env-set fix, `00003-n4h`
(ws8-v3 login origin fix), `00004-4j4` (ws8-v4 clean secret), `00005-vbq`
(ws8-v5 hardened routes), `00006-5q5` (env regression, documented in §3),
`00007-qsd` (current: complete env set, GCS writes verified).

<!-- DEPLOY-PROOF-END -->

## 8. Report v2 addendum (2026-11-18 late, task-8 v2 extension)

The public bilingual field report moved to a two-audience format at
[`/report/biratori-1119`](../web/app/report/biratori-1119/page.tsx)
(founder work-order v2): farmer tab (playbook grade cards + pure-SVG evidence
charts + satellite thumbnail + honest soil-gap card) and investor tab
(staged-pricing framework, transparent ROI arithmetic, trust spine,
source/licence list). Implementation notes for the next operator:

* Prose lives in `web/lib/report-copy.ts` (zh-TW + ja; type shape accepts
  zh-CN/en/th later). Guarded by `ReportCopyGuardTests` in
  `tests/test_i18n_schema.py` (structural parity, farmer-voice jargon ban,
  no hardcoded report strings in the page).
* Evidence charts are hand-rolled server SVG (`charts.tsx`) over
  `web/lib/report-1119-data.ts` — zero chart dependencies.
* `GET /api/scene-thumb` proxies the Planet Data-API thumbnail server-side
  (`PLANET_API_KEY`, the same `Planet-labs` Secret Manager secret the
  backend mounts — added to THIS service via `--set-secrets`, so the web
  service now carries TWO secrets). Cache `s-maxage=3600`; failures return a
  labelled inline-SVG gap placeholder, never a broken image.
* Middleware public prefixes now include `/report`, `/api/scene-thumb`,
  `/reports` (source-report copies shipped in `web/public/`, which the
  runner image copies explicitly — standalone output does NOT include
  `public/`), and `/icon.svg`.
* Serving image lineage: `report-v2` → `report-v2b` (public/ + whitelist) →
  `report-v2c` (favicon) → `report-v2d` (icon whitelist) →
  **`report-v2-final` (digest `d5b50c0c…`, revision `00017-hvq`, trust-count
  synced to the suite's real 1,597 OK)**. Python suite: **Ran 1597 · OK
  (skipped=14)** at ship. Screenshots: workspace
  `ws8-report-farmer-mobile.png` (375 px farmer tab) and
  `ws8-report-investor-desktop.png` (1280 px investor tab).

## 9. Testing discipline

* The Python suite is untouched by deploys: this workstream only ever added
  `web/` files, `Dockerfile.web`, `web/tools/web-image-build.ps1`, this doc,
  and the report-copy guard TEST in `tests/test_i18n_schema.py` (suite grew
  1592 → 1597, all green).
* The active CI/release gate is `.github/workflows/web-image.yml`: it runs
  `node --test tests/*.test.cjs`, builds and resolves an immutable image
  digest, deploys that digest as a no-traffic candidate, verifies the 100%
  traffic shift, and smoke-checks `/livez`, the login redirect, a report, and
  the protected boundary route. The GitHub Actions run is linked from the
  current release record.
* `web/node_modules` stays out of git; reproducibility rides on
  `web/package-lock.json` (`npm ci`).

## Pilot security containment (deployed; shared-crew scope only)

`/walk` and `/api/boundaries` require the existing shared access cookie. If
`WEB_ACCESS_TOKEN` is missing, protected routes return 503 instead of opening.
The backend accepts access credentials only via `X-Access-Token`; query-string
credentials on observations and leads are rejected. The existing clients use
this shared token gate. Review platform logs for exposed tokens and rotate
exposed secrets. The shared gate does not implement individual identities,
farm-level authorization, revocation, or cross-farm isolation. Do not onboard
multiple farms until those controls are implemented and tested end to end.
