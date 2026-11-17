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
| Planet Labs | `PLANET_API_KEY` mounts from Secret Manager secret `Planet-labs:latest`; both documented schemes (HTTP Basic, `api-key`) are tried. Discriminator result 2026-11-17: the key value is byte-identical to the owner-provided key and Planet's account probe returns 403 for it (key recognized) while Data search returns 401 — the key authenticates but its principal has **no active Insights subscription**. Activating the plan is enough; no redeploy, no secret change |
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
