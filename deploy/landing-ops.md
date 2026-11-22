# Seges landing deployment

The public apex `seges.ai` is served by the `farm-seges-ai-landing` Cloud Run
service through the `seges-site-worker` Cloudflare Worker. The Worker origin is
already configured; a landing release deploys only the Cloud Run service.

## Forward release

`.github/workflows/landing-image.yml` runs on `main` changes under `landing/`
or `Dockerfile.landing`. It typechecks and tests the landing, builds a Cloud
Build image, resolves its immutable digest, creates a no-traffic revision,
verifies the revision image and 100% traffic shift, then smoke-checks `/en`,
`/ja`, `/zh-TW`, and `https://seges.ai/`. A failed post-shift check restores the
previous serving revision. The workflow does not replace service environment
variables or secrets.

## Rollback

Use the service's previous healthy revision as the immediate rollback anchor:

```powershell
gcloud run services describe farm-seges-ai-landing --project=seges-ai --region=asia-east1 --format="yaml(status.traffic,status.latestReadyRevisionName)"
gcloud run services update-traffic farm-seges-ai-landing --project=seges-ai --region=asia-east1 --to-revisions <known-good-revision>=100
```

The image digest remains the durable rebuild anchor. Never pin by tag alone.
