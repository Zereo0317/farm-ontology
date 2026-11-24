# Web service rollback — farm-seges-ai-web

Applies the backend rollback discipline (deploy/rollback.md) to the web
image line. Service: `farm-seges-ai-web`, region `asia-east1`, project
`seges-ai`. CI: `.github/workflows/web-image.yml` tags every main-built image
`ci-<shortsha>` and records its digest; manual builds historically used
`report-v2*` / `report-i18n` tags.

## Current forward-deployment path

`.github/workflows/web-image.yml` tests and builds an immutable candidate on
`main` changes under `web/`, `farm_ontology/`, the vocabulary manifest, or the
workflow itself. A tagged candidate receives no production traffic. Promotion
is a separate manual dispatch: enter the exact digest in
`accepted_image_digest` after farmer-account and tenant-isolation acceptance.
The workflow then checks OIDC runtime configuration, dedicated service
identity, read-only membership-bucket access, and candidate login/API smoke
before moving traffic. A failed post-shift check restores the prior serving
revision. This lane does not replace the farmer's authenticated acceptance.

The manual rollback lane remains available through `workflow_dispatch` with
`image_ref`; repeat the exact digest in `accepted_image_digest`. It preserves
the service's environment and secret configuration. Verify traffic and the
gate plus value routes after any pin; `/livez` alone does not prove an
authenticated journey. The latest
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

## 2. Image pin (the durable rollback): explicit digest via guarded workflow

Cloud Run revisions are immutable, but a code regression may need rolling
BACKWARD across several commits; pin the last known-good IMAGE digest (per
the fleet rule: **always pin by explicit digest — a tag can silently
resolve to something newer than you verified**):

Use GitHub Actions → `web-image` → **Run workflow**. For a previously
validated web candidate, set `promotion_image_ref` and
`accepted_image_digest` to the same full `sha256:<64 lowercase hex>` value.
First provision the dedicated farm web deployer/runtime identities and set the
repository variable `FARM_WEB_DEPLOYER_READY=true`. The `web-production`
environment must hold `FARM_WEB_ACCEPTANCE_DIGEST` with that exact digest,
after a protected reviewer records the farmer-account callback, membership,
tenant-isolation, retry, and write acceptance. The workflow validates
the OIDC configuration, dedicated runtime identity, membership bucket and
secret setup, then smoke-tests a tagged no-traffic revision before promotion.
For an emergency rollback to an older image, use `image_ref` and repeat the
same digest in `accepted_image_digest`; traffic rollback remains protected by
the current serving-revision check. Do not use raw `gcloud run deploy` or
`--to-latest` for a web image pin.

⚠ Do NOT pin by bare tag in an incident (`ci-9fdc1ba1`) — the tag may have
been re-pushed; resolve it to a digest FIRST (`gcloud artifacts docker
images describe ...:TAG --format='value(digest)'`) and pin that.

## 3. Config-level rollback (regression came from env/secret wiring, not code)

The usual suspects are documented in docs/web-ops.md §3 (`--set-env-vars`
FULL-REPLACEMENT semantics) and §4 (secret `\r\n` bytes). Steps:

Capture the complete current revision environment and secret references as
metadata without printing secret payloads. For a known-good configuration,
restore traffic directly to its revision using §1. If the broken configuration
must be repaired forward, use the reviewed `web-production` deployment
procedure and pass the entire intended env/secret set in one operation.
Never replay the legacy-only environment below an OIDC revision: Cloud Run's
`--set-env-vars` and `--set-secrets` flags replace their entire respective
sets.

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

Then verify the authenticated journey against the approved identity provider
and authorized farmer membership, plus one report variant
(`?lang=th&tab=investor`). A health endpoint alone does not prove identity,
tenant isolation, or membership access.

## 5. Dry-run drills (quarterly, ~5 min)

1. `gcloud run revisions list` → pick the previous revision.
2. Exercise §1 (flip traffic), verify §4, flip BACK to latest.
3. Exercise §2 via the CI pin job with the PREVIOUS image's digest, verify,
   return to head.
4. Record both drills in this file's log:

| date | drilled by | path | result |
| --- | --- | --- | --- |
| 2026-11-18 | web (task-13 setup) | §1 + §2 shape reviewed against live revisions | ladder healthy: 00001→00018 all present |
