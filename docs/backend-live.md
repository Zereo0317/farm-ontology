# Backend live on Cloud Run (2026-11-17)

The decision record ships as the Cloud Run service `farm-seges-ai` on the
`seges-ai` project. The image builds from this repository's merged `main`
with `gcloud run deploy --source .`.

## Facts after the 2026-11-17 merge + ship

| Item | Value |
| --- | --- |
| Service (prod) | `farm-seges-ai`, region `asia-east1`, URL https://farm-seges-ai-451400509859.asia-east1.run.app |
| Service (staging) | `farm-seges-ai-staging`, same region |
| Commits served | from merged `main` at `prod-d90d614` (after absorbing 122 cursor branches) |
| Test suite at ship time | 1068 tests, green |
| Farm pin | Hiroki Tomiyasu field, Biratori, Hokkaido — 42.7018152 N, 142.4071291 E (`FARM_LAT` / `FARM_LON`) |
| Earth Engine | catalog check HTTP 200 through the Cloud Run runtime identity (compute SA); SA holds `roles/earthengine.viewer`; registration stays `unknown`, so `permits_financial_use` stays false and the use class stays Screening |
| Planet Labs | Trial activated 2026-11-17 in the browser (`zereo0317@gmail.com`, account ID `34a96e83-bf8c-4002-b5e1-7c2757d6500b`, valid until **2026-12-17**). The trial's own API key lives in the Insights Account → Settings (key rotates per account; it authenticates BOTH the legacy Data API and is the seat holder for the Sentinel-Hub-based APIs). Working key stored as Secret Manager version (`Planet-labs` v3) and consumed live by `/farm/planet`: **250 PSScene headers around the farm point, including same-day zero-cloud SuperDove strips**. The pre-trial key in v1 belonged to an account without an active subscription (its 401/403 fingerprint: account probe 403, Data search 401) |
| Insights Platform trial contents | 3,000 monitoring credits; 1 OAuth client seat; **Planet Sandbox Data** (Analysis-Ready PlanetScope, PlanetScope, SkySat, Soil Water Content planetary variable, Planet Mosaics, road/building detection), Open Data, bring-your-own-data; Catalog/Statistical/Process/OGC APIs; Sentinel-Hub OAuth client creation not yet surfaced in this account's UI |
| Open-Meteo | live `jma_msm` current block for the farm point; stored support stays the 0.05 deg grid cell |

## Deployment notes (pitfalls encountered)

1. `.gcloudignore` must NOT exclude the `Dockerfile` (first build failed for
   exactly that reason; fixed on `654a42f`).
2. On this service a `--source` deploy created and readied the revision but
   did not move traffic; `gcloud run services update-traffic
   farm-seges-ai --to-revisions <rev>=100` finished the rollout. Watch
   `latestCreatedRevisionName` against `traffic.revisionName`.
3. Repository-local git identity: the bulk merge needs
   `user.name`/`user.email` set (they were blank on this machine and every
   merge commit died before the author could appear).

## Ops runbooks index (added 2026-11-18, WS1)

Operational procedures now live in `deploy/`:

| Document | What it covers |
| --- | --- |
| [deploy/GCP_SETUP.md](../deploy/GCP_SETUP.md) | Everything provisioned in GCP (record bucket, SA roles, uptime checks, alert policies incl. the HALT placeholder, budget, CI federation) with reproducible commands |
| [deploy/staging-cutover.md](../deploy/staging-cutover.md) | The applied staging GCS-backend switch + verification + prod cutover procedure (documented, not yet executed) |
| [deploy/rollback.md](../deploy/rollback.md) | Rollback + restore drill checklist (recreate instance → envs → secret mount → observations intact from GCS) |
| [deploy/rotate-planet-key.md](../deploy/rotate-planet-key.md) | Planet key rotation runbook + the 2026-11-17 `\r\n` secret postmortem |
| [deploy/budget.md](../deploy/budget.md) | Monthly cost guard (TWD 2,000 ≈ ¥10k on `seges-ai`), thresholds and notification path |
| [deploy/set-traffic.sh](../deploy/set-traffic.sh) / [.ps1](../deploy/set-traffic.ps1) | Post-deploy `update-traffic --to-latest` helper (the traffic-shift gotcha) |
| [deploy/nightly-export.md](../deploy/nightly-export.md) | WS1.2: nightly record snapshot job (`farm-nightly-export`), 03:30 JST, manifest + verification |
| [deploy/record-retention-policy.md](../deploy/record-retention-policy.md) | 90-day rolling archive retention — POLICY ONLY, lifecycle activation approval-gated |
| [deploy/webhook-alerting.md](../deploy/webhook-alerting.md) | Reserved DISABLED webhook alert channel + HALT replica policy + enablement runbook |
| [deploy/alert-ack-drill.md](../deploy/alert-ack-drill.md) | The executed end-to-end alert ACK drill with timestamps (2026-11-18) |
| [deploy/cost-optimization.md](../deploy/cost-optimization.md) | Sprint-I cost inventory (estimates), right-size review, applied safe subset + honest savings ledger |
| [deploy/create-observation-job.sh](../deploy/create-observation-job.sh) | Cloud Run job proving one observation round-trips through the record store |
| [deploy/update-staging-env.sh](../deploy/update-staging-env.sh) | Point staging at the GCS record backend idempotently |

Durable record storage itself: `farm_ontology/record_store.py`
(`FARM_RECORD_BACKEND=gcs|local`); deployment notes below are unchanged.

## Secrets and roles

- `gcloud secrets add-iam-policy-binding Planet-labs --member=serviceAccount:451400509859-compute@developer.gserviceaccount.com --role=roles/secretmanager.secretAccessor`
- `gcloud projects add-iam-policy-binding seges-ai --member=serviceAccount:451400509859-compute@developer.gserviceaccount.com --role=roles/earthengine.viewer`

No key or credential is stored in the repository.

## Audit trail (2026-11-17, this merge day)

| Step | Result |
| --- | --- |
| Worktree inventory | 122 worktrees; 109 local branches unmerged into `origin/main` |
| Bulk merge | 104 fast/content merges clean; 4 conflicts (`test_supply_decision.py`, `supply_decision.py`) union-resolved with tests run per branch |
| Remote sweep | 13 remote-only branch heads (the `-5464`/`-6c2c`/`-0266` lineages) merged; `cursor/cited-soil-refetch-5464` was a duplicate-implementation collision and took the refetched supersets deliberately |
| GitHub | `origin/main` reached `d90d614`; open PR count 0; 122 PRs auto-marked MERGED |
| Cleanup | 121 worktree registrations removed, 121 worktree directories deleted, all merged local branches deleted; one checkout remains |
| Ship | staging first (`00080`/`00081`), then prod (`00044`, traffic pinned to 100%) |
| Debt fixed | dead `ui.py`/`ui_page.html` already gone with the sweep; git identity trap documented; secret-rotation path made redeploy-free; weather/Planet/EE failures all degrade to explicit `gap` objects, never invented values |
