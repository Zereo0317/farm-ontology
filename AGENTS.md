# AGENTS.md — operative guide for agents working on farm-ontology

Read this file first, then `docs/decision-infra-roadmap.md` (the plan of
record with per-workstream scope) and the ops docs you are about to touch
(`docs/backend-live.md`, `docs/web-ops.md`, `deploy/`). Board tasks carry
the detailed spec per sprint; this file is the standing handbook.

## 0. Environment facts (verified live 2026-11-18)

```pwsh
gcloud config get-value account   # segescloud@gmail.com
gcloud config get-value project   # seges-ai
gh auth status                    # Zereo0317
```

- Region is always **`asia-east1`** for the farm stack.
- **The project is shared.** `seges-ai` hosts 20+ Cloud Run services and
  hundreds of jobs from sibling products (noesis-\*, seges-\*, kairos, …).
  Touch **only** `farm-seges-ai*` resources; never "clean up" anything else.
- Farm footprint: services `farm-seges-ai` (prod), `-staging`, `-web`;
  jobs `farm-ingest-{workers,planet,ndvi,hazard}`, `farm-nightly-export`,
  plus drill/probe jobs; 5 schedulers `farm-sched-*`; bucket
  `gs://farm-seges-ai-records`; secrets `Planet-labs`, `web-access-token`.
- Python ≥ 3.11, **stdlib-only** (`pyproject.toml` declares zero deps).
- The repository is private; `main` is the single source of truth.

## 1. Repo layout (who owns what)

| Module | Owner (sprint/board) |
| --- | --- |
| `farm_ontology/` core (model, store, rules, policy, publish, query, build, timeutil, identity, namespaces, fieldkit, record_store) | foundational; changes need Lead review — everything depends on it |
| `farm_ontology/adapters/`, feed modules, `pipelines/` | pipeline (WS2, task-2 lineage) |
| `farm_ontology/agronomy/` | agronomy (WS3) |
| `farm_ontology/sensors/`, `fieldkit`, `hardware/` | fieldhw (WS4) |
| `farm_ontology/actuation/` | actuation (WS5) |
| `farm_ontology/licences/`, `grants/`, `docs/legal/` | licences (WS6) |
| `farm_ontology/markets/` | markets (WS7) |
| `web/`, `Dockerfile.web` | web (WS8) |
| `Dockerfile`, `.gcloudignore`, `.github/workflows/`, `deploy/` | infra (WS1) |
| `perf/` | QA sprints (Sprint-E lineage) |
| `README.md`, `AGENTS.md`, `.gitignore` | hygiene sprints |
| `docs/` | shared; add, never silently delete |

Write scopes on board tasks are **advisory fences**, not locks: overlaps are
warned, edits stay visible to all; the Lead reviews the final diff and runs
the suite.

## 2. Branching / worktree conventions

- Every task starts from **fresh `origin/main`**:
  `git worktree add ..\farm-ont-ws-<name> -b ws/<sprint>/<name> origin/main`
- Sprint-scoped branch names only (examples: `ws/licences/grant-engine`,
  `ws/sprint/repo-hygiene`, `ws/fix/D7-...`).
- Work only inside your worktree; one task = one branch = one push.
- Before the final push, `git merge origin/main` (or `main`) and re-run the
  suite — leads do not review a stale branch.
- CRLF: the repo keeps files LF; on Windows expect checkout warnings
  (`LF will be replaced by CRLF`) — cosmetic; `ontology/*.ttl` is pinned
  `eol=lf` by `.gitattributes`. Never "fix" line endings repo-wide.

## 3. Board task flow (shared board)

1. `team_task_get` → read the whole card, **including** any spec updates
   parked by the Lead in teammates' replies; card text wins over memory.
2. `team_task_update` claim (with the current revision).
3. Read every file the card names BEFORE writing; verify claims against
   repo/GCP reality (count services, open the files) — facts, not folklore.
4. Implement inside the worktree, tests green, merge main, push.
5. `team_task_update` complete with a factual summary (branch, files, test
   deltas, blocked-on-human items) and message the Lead the same.

## 4. Deploy rituals

Backend (record API):

```pwsh
# staging: AUTOMATIC on every green push to main (test.yml); it pins traffic:
gcloud run services update-traffic farm-seges-ai-staging --region asia-east1 --to-latest
# prod: MANUAL, auditable (.github/workflows/deploy-prod-tag.yml, workflow_dispatch)
#   → only after staging /livez is green on the same commit.
```

- **The update-traffic ritual is mandatory**: a `--source` deploy creates
  and readies a revision but may serve 0 % of it. Verify
  `latestCreatedRevisionName` == serving revision; helper
  `deploy/set-traffic.(sh|ps1)`.
- Web app (`farm-seges-ai-web`): CI via `.github/workflows/web-image.yml`
  on pushes touching `web/**`; image built **on Cloud Build** from the
  staged context `.dockerbuild-web/` (`web/tools/web-image-build.ps1`) —
  a repo-root `--source` deploy cannot see `web/` because `.gcloudignore`
  excludes it (deliberate). The **image digest is the rollback anchor**;
  roll back = dispatch the workflow with `image_ref=<digest>`
  (`deploy/web-rollback.md`).
- `--set-env-vars` / `--set-secrets` on `run services update` **REPLACE**
  the whole set — always pass the complete list (one web revision once
  served half-blind because of this).
- Prod smoke after any ship: `/livez`, gate (`GET /` → 307), one
  value route. Uptime checks `farm-prod-livez` / `farm-prod-weather`
  alert segescloud@gmail.com.

## 5. Testing discipline

- The suite is **hermetic by default**: `python -m unittest discover -s tests -t .`
  never calls the network; recorded fixtures stand in for live fetches
  (marked `captured_live: false`).
- Live-path tests (~14) are gated behind `FARM_ONLINE_TESTS=1` — opt-in,
  never in CI.
- CI (`test.yml`): byte-compile (`compileall`) → unit tests → Docker build;
  green tests+build deploy **staging** on main pushes. Prod deploys are a
  separate manual workflow — merge-to-prod without green is impossible.
- Rule: every defect fix ships with a producer test that fails on the old
  code. Suite size 2026-11-18: **1686 tests** (14 opt-in skips) — keep it
  green, grow it honestly.

## 6. Known pitfalls ledger (paid for in incidents; never re-learn these)

| Pitfall | Fact |
| --- | --- |
| Blank git identity | bulk merges died author-less on this machine; set `user.name`/`user.email` (repo-local) before any merge campaign (`docs/backend-live.md` §3) |
| Traffic silently unmoved | `--source` deploys ready a revision without serving it → always finish `update-traffic --to-latest` (WS1 "gotcha"; helper in `deploy/`) |
| Secret CRLF poisoning | piping values into `gcloud secrets create --data-file=-` via PowerShell appended `0d 0d 0a` → `Authorization: Basic …\r\n` broke `/farm/planet` mid-serving (2026-11-17). Write secret bytes with `[IO.File]` UTF-8 no-BOM; readers `.trim()` defensively (`deploy/rotate-planet-key.md`) |
| Robocopy on CI | `robocopy` does not exist on Ubuntu runners → repo scripts use a pwsh `Copy-Tree` helper (`ae4b921`) |
| x-forwarded origin/proto | behind the run.app edge the app must derive scheme/host from forwarded headers or login redirects loop (`ws8-v3` web fix, `docs/web-ops.md`) |
| Env flags replace, not merge | `--set-env-vars`/`--set-secrets` wiped the web service's env once (rev `00006`) → always the complete list |
| `.gcloudignore` ate the Dockerfile | first source-build failed excluding it (`654a42f`) — keep `Dockerfile` in |
| `/healthz` is reserved | the run.app edge keeps it; health endpoints are **`/livez`** on both services |
| Digests, not tags | Cloud Run rollbacks pin **explicit image digests**; tags can go stale |
| Windows pipelines vs stdout | DSH sandbox/confined shells can't capture spawned-process stdio (`EPERM`) — inherit or restructure |

## 7. The four human cards (nothing else blocks the roadmap)

1. **Sensor basket** — A (¥112,458) vs B (技適済, ¥126,336) procurement
   decision (`hardware/sensor-kit-bom.md`, `reports/fieldhw-cost-log.md`).
2. **Planet purchase vs lapse** — decide at the **2026-11-30** checkpoint;
   the trial ends **2026-12-17**; lapse path = Open Data + Sentinel-2
   (`docs/legal/commercial-punchlist.md` PL-PLANET-COMMERCIAL).
3. **Company incorporation (会社設立/登記)** — in progress; **gates every
   signature** (vendor contracts, executed grants, the farmer contract
   pack) until the 登記事項証明書 + 法人番号 exist.
4. **Kill-switch contract signature** — the load-bearing Phase-4 gate fact
   (emergency HALT authority, `docs/alpha-fairness-doctrine.md` §6).

Agents prepare baskets, quotes, memos, and drafts; humans sign.

## 8. Charter lines (break these and the record is worthless)

1. **Stdlib-only Python.** Runtime imports come from the standard library;
   the web app stays dependency-light the same way (no chart lib, no auth
   SDK).
2. **Fail closed.** Missing input, expired grant, unknown registration,
   unreachable feed ⇒ refuse and RECORD; the gap is published, never
   guessed. Expired/absent/unverified licenses demote automatically
   (`farm_ontology/licences/`); a specimen certificate unlocks nothing.
3. **No invented numbers.** Native spatial support, availability time,
   issue time, licence, and an error mark travel with every value;
   joins never rewrite support; uncalibrated ≠ calibrated; unknown metres
   stay `unknown`.
4. **Consent-first.** No real personal data in the record; farmer-level
   data reaches market-facing artefacts only on a written grant
   (`grants/`, v2 objects with purpose/scope/expiry); class C
   (settlement/hedge/trigger/nature-unit) stays closed behind
   `fd:classCPolicy=closed` + the human gate.

## 9. Where the truth lives (fast index)

- Plan & phasing: `docs/decision-infra-roadmap.md` · Doctrine:
  `docs/alpha-fairness-doctrine.md` · Defect history:
  `docs/final-verification-report.md` · Closed switches Q1–Q21:
  `docs/decision-log.md` · Live-service records: `docs/backend-live.md`,
  `docs/web-ops.md` · GCP provisioning: `deploy/GCP_SETUP.md` · Commercial
  gates: `grants/punchlist.yaml` → `docs/legal/commercial-punchlist.md`.
- Current suite badge: 1686 tests OK (14 opt-in skips) @ `main` 2026-11-18.
