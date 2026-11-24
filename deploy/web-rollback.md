# Web service rollback — farm-seges-ai-web

Applies the backend rollback discipline (deploy/rollback.md) to the web
image line. Service: `farm-seges-ai-web`, region `asia-east1`, project
`seges-ai`. CI: `.github/workflows/web-image.yml` tags every main-built image
`ci-<shortsha>` and records its digest; manual builds historically used
`report-v2*` / `report-i18n` tags.

## Current forward-deployment path

`.github/workflows/web-image.yml` builds the app on Cloud Build when `main`
changes under `web/`, `farm_ontology/`, the vocabulary manifest, or the
workflow itself. It runs the web routing/security tests before the build,
resolves the immutable Artifact Registry digest, deploys that exact digest as
a no-traffic revision, checks the candidate and serving traffic, then runs
production smoke routes. A failed post-shift check restores the prior serving
revision. This web release lane does not require a separate web staging
service; it deploys only after its build and tests pass.

The manual digest-only rollback lane remains available through
`workflow_dispatch` with `image_ref`. It preserves the service's environment
and secret configuration. Verify traffic and the gate plus value routes after
any pin; `/livez` alone does not prove an authenticated journey. The latest
recorded web/landing/backend release is in
[`docs/pilot-readiness-status.md`](../docs/pilot-readiness-status.md).

## 0. Inventory first (know what you're standing on)

```bash
# Every image ever pushed for the web line, newest first, WITH digests
gcloud artifacts docker images list \
  asia-east1-docker.pkg.dev/seges-ai/cloud-run-source-deploy/farm-seges-ai-web \
  --project seges-ai --format='table(version,digest,tags,updateTime)'

# Which revision serves WHICH image right now + the revision ladder
gcloud run services describe farm-seges-ai-web \
  --project seges-ai --region asia-east1 \
  --format='yaml(status.traffic, status.latestReadyRevisionName)'
gcloud run revisions list --service farm-seges-ai-web \
  --project seges-ai --region asia-east1 \
  --format='table(metadata.name, spec.containers[0].image, status.conditions[@].status, metadata.creationTimestamp)'
```

Record the CURRENT serving revision and its image digest **before** doing
anything — that pair is your known-good anchor (write it in the incident
log, then act).

## 1. Preferred rollback: traffic pin to an existing revision (seconds, zero risk)

Use when the bad deploy is simply the latest revision and a healthy earlier
revision exists. No redeploy, no new revision — instant flip:

```bash
gcloud run services update-traffic farm-seges-ai-web \
  --project seges-ai --region asia-east1 \
  --to-revisions farm-seges-ai-web-00017-hvq=100
```

## 2. Image pin (the durable rollback): explicit digest redeploy

Cloud Run revisions are immutable, but a code regression may need rolling
BACKWARD across several commits; pin the last known-good IMAGE digest (per
the fleet rule: **always pin by explicit digest — a tag can silently
resolve to something newer than you verified**):

```bash
# Pick the digest from the inventory above, then EITHER the CLI:
gcloud run deploy farm-seges-ai-web \
  --project seges-ai --region asia-east1 \
  --image "asia-east1-docker.pkg.dev/seges-ai/cloud-run-source-deploy/farm-seges-ai-web@sha256:d5b50c0c9624e88f4343fe0b8951080b7d60ab512e7fe76df86910f4366ca044" \
  --allow-unauthenticated \
  --set-secrets "WEB_ACCESS_TOKEN=web-access-token:latest,PLANET_API_KEY=Planet-labs:latest" \
  --set-env-vars "FARM_API_BASE=https://farm-seges-ai-451400509859.asia-east1.run.app,FARM_RECORD_BACKEND=gcs,FARM_RECORD_BUCKET=farm-seges-ai-records,FARM_RECORD_DIR=/tmp/field-notes" \
  --memory 512Mi --cpu 1 --max-instances 2 --timeout 60
gcloud run services update-traffic farm-seges-ai-web \
  --project seges-ai --region asia-east1 --to-latest

# OR the CI lane (preferred when GitHub availability is fine — it smoke-tests
# for you): Actions → "web-image" → Run workflow → paste the FULL DIGEST or
# artifact URI into image_ref (leave empty ONLY for forward deploys).
#   dispatch inputs.image_ref examples:
#     d5b50c0c9624e88f4343fe0b8951080b7d60ab512e7fe76df86910f4366ca044
#     sha256:d5b50c0c…
#     asia-east1-docker.pkg.dev/seges-ai/cloud-run-source-deploy/farm-seges-ai-web@sha256:d5b50c0c…
```

⚠ Do NOT pin by bare tag in an incident (`ci-9fdc1ba1`) — the tag may have
been re-pushed; resolve it to a digest FIRST (`gcloud artifacts docker
images describe ...:TAG --format='value(digest)'`) and pin that.

## 3. Config-level rollback (regression came from env/secret wiring, not code)

The usual suspects are documented in docs/web-ops.md §3 (`--set-env-vars`
FULL-REPLACEMENT semantics) and §4 (secret `\r\n` bytes). Steps:

```bash
# See exactly what the serving revision carries
gcloud run services describe farm-seges-ai-web \
  --project seges-ai --region asia-east1 \
  --format='yaml(spec.template.spec.containers[0].env)'

# Repair forward (ALWAYS the complete list in ONE call), or:
# recreate the same env set against the pinned good revision's values.
gcloud run services update farm-seges-ai-web \
  --project seges-ai --region asia-east1 \
  --set-env-vars "FARM_API_BASE=https://farm-seges-ai-451400509859.asia-east1.run.app,FARM_RECORD_BACKEND=gcs,FARM_RECORD_BUCKET=farm-seges-ai-records,FARM_RECORD_DIR=/tmp/field-notes" \
  --set-secrets "WEB_ACCESS_TOKEN=web-access-token:latest,PLANET_API_KEY=Planet-labs:latest"
```

Secret rotations that went sideways: create a corrected VERSION of the
secret (byte-clean: write ASCII bytes to a file, `gcloud secrets versions
add --data-file=...`, no shell pipes) and redeploy; `:latest` picks it up.

## 4. Verify after ANY rollback (the CI smoke, by hand)

```bash
BASE=https://farm-seges-ai-web-451400509859.asia-east1.run.app
curl -s -o /dev/null -w '%{http_code}\n' "$BASE/livez"                      # expect 200
curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' "$BASE/"           # expect 307 … /login?next=%2F
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' "$BASE/api/scene-thumb"  # expect 200 image/png
curl -s -o /dev/null -w '%{http_code}\n' "$BASE/report/biratori-1119"       # expect 200
```

Then eyeball one authenticated page load (login with the crew token) and
one report variant (`?lang=th&tab=investor`) — cheap end-to-end assurance.

## 5. Dry-run drills (quarterly, ~5 min)

1. `gcloud run revisions list` → pick the previous revision.
2. Exercise §1 (flip traffic), verify §4, flip BACK to latest.
3. Exercise §2 via the CI pin job with the PREVIOUS image's digest, verify,
   return to head.
4. Record both drills in this file's log:

| date | drilled by | path | result |
| --- | --- | --- | --- |
| 2026-11-18 | web (task-13 setup) | §1 + §2 shape reviewed against live revisions | ladder healthy: 00001→00018 all present |
