# GCP setup ledger — `seges-ai` (WS1, executed 2026-11-17/18)

Everything in this file was actually created on 2026-11-17/18 by the infra
agent (task-1), unless marked TODO/deferred. Commands are recorded so a
fresh laptop can reproduce the whole setup. Auth used throughout:
`segescloud@gmail.com`, project `seges-ai`,
billing account `015C1C-DA2C8B-11E228` (currency TWD).

## 1. Durable record store

### Bucket

```bash
gcloud storage buckets create gs://farm-seges-ai-records \
  --project=seges-ai --location=asia-east1 \
  --uniform-bucket-level-access --default-storage-class=STANDARD
gcloud storage buckets update gs://farm-seges-ai-records --versioning
```

State: exists, `ASIA-EAST1`, UBLA on, `versioning_enabled: true` (plus the
default 7-day soft-delete policy). Location choice rationale: co-located
with the service (`asia-east1`), NOT the org-default `asia-northeast1`,
because the record writes originate in the Tokyo-adjacent Cloud Run
region `asia-east1` (README-level geography: the farm is Biratori,
Hokkaido; the deployment region decision predates WS1).

### IAM (service account = the Cloud Run runtime identity)

The runtime service account `451400509859-compute@developer.gserviceaccount.com`
(authenticated via the instance metadata server token; no key files) was
granted, on the bucket:

```bash
gcloud storage buckets add-iam-policy-binding gs://farm-seges-ai-records \
  --member=serviceAccount:451400509859-compute@developer.gserviceaccount.com \
  --role=roles/storage.objectUser
```

`storage.objectUser` covers create/read/list/update on objects
(no bucket admin). Because the service previously also needed
`roles/secretmanager.secretAccessor` (Planet-labs) and
`roles/earthengine.viewer` (project) — see docs/backend-live.md — the
cumulative identity is sufficient for the backend switch with ZERO new
credentials.

### Seeding (2026-11-17)

The 3 observations + 1 feedback note + farm pin that existed on the laptop
were uploaded read-only from the main checkout:

```bash
gcloud storage cp -r <laptop>/farm-ontology/field-notes gs://farm-seges-ai-records/
```

Objects now under `gs://farm-seges-ai-records/field-notes/`: `biratori-pin.json`,
`obs-20261116T130426Z.json`, `obs-20261116T130945Z.json`,
`obs-20261116T133128Z.json`, `notes/note-feedback-20261116T131001Z.json`,
plus drill observations `obs-20261117T090320Z.json`,
`obs-20261117T090330Z.json`, `obs-20261117T090850Z.json`.

## 2. Staging backend switch (actually applied)

```bash
gcloud run services update farm-seges-ai-staging \
  --project=seges-ai --region=asia-east1 \
  --update-env-vars=FARM_RECORD_BACKEND=gcs,FARM_RECORD_BUCKET=farm-seges-ai-records
gcloud run services update-traffic farm-seges-ai-staging \
  --project=seges-ai --region=asia-east1 --to-latest
```

Post-change revision `farm-seges-ai-staging-00085-fmk` verified with env
`FARM_RECORD_BACKEND=gcs`, `FARM_RECORD_BUCKET=farm-seges-ai-records`,
traffic 100% `LATEST`. Full narrative + proof: `deploy/staging-cutover.md`.

## 3. Durability drill (Cloud Run job)

Image: `asia-east1-docker.pkg.dev/seges-ai/farm/drill:obsdrill-20261117d`
(built via `gcloud builds submit --region=asia-east1` from this repo;
Artifact Registry repo `farm` created for it). The image's command override
`--args=python,-m,farm_ontology.record_store` runs the drill entry point.

```bash
./deploy/create-observation-job.sh   # deploys + executes + waits
```

State: Cloud Run job `farm-observation-drill` exists (SA =
runtime identity, env = gcs backend vars, `FARM_RECORD_DIR=/tmp/farm-records`);
execution `farm-observation-drill-ph9fd` SUCCEEDED 2026-11-17 09:08Z,
writing `obs-20261117T090850Z.json` to the bucket.

## 4. Uptime checks + alerts

```bash
# NOTE: checker regions are the SIX coarse sets (asia-pacific etc.);
# 'asia-northeast1' is NOT selectable, and >=3 regions are required.
gcloud monitoring uptime create farm-prod-livez \
  --resource-type=uptime-url \
  '--resource-labels=host=farm-seges-ai-451400509859.asia-east1.run.app,project_id=seges-ai' \
  --path=/livez --protocol=https --period=5 --timeout=10 \
  '--regions=asia-pacific,usa-iowa,europe'
# same with --path=/farm/weather and display name farm-prod-weather
```

Created: `farm-prod-livez` (config id `farm-prod-livez-hz7DuEabPGU`) and
`farm-prod-weather` (config id `farm-prod-weather-F1GWoiUz1NA`), 5-minute
period, three checker regions.

Notification channel (email):

```bash
gcloud alpha monitoring channels create --project=seges-ai \
  --display-name="Alert email: segescloud (uptime + HALT placeholder)" \
  --type=email --channel-labels=email_address=segescloud@gmail.com
```

→ `projects/seges-ai/notificationChannels/8915504179369323569`.
(A pre-existing channel `2125437968708098086` "Budget alerts - hyuchen869"
carries budget mail.)

Alert policies (created as
`13313932562381105688` livez-down, `14833930661138030035` weather-down,
`15913247909952847743` HALT placeholder):

- Uptime ×2: `check_passed` GAUGE/BOOL per checker-region series,
  ALIGN_NONE 300 s, condition = any series value < 1 for 60 s
  (= that region saw a failed ping), auto-close 30 min, → email channel.
  Payload shape lessons learned the hard way are in git history:
  `conditionSql` currently REQUIRES `conditions[0].schedule` in this
  API surface, no `duration` field, and there is NO `check_failed`
  metric type (despite older tutorials; enumerate with the metricDescriptors
  REST API to see the real catalog: check_passed/content_mismatch/
  error_code/http_status/request_latency/time_until_ssl_cert_expires).
- HALT placeholder: threshold policy on the CUSTOM metric
  `custom.googleapis.com/watchdog/halt_raised` (INT64 GAUGE descriptor
  created 2026-11-18 via the metricDescriptors REST API so the policy
  validates before the WS5 watchdog exists). Doctrine requirement
  (alpha-fairness §7): channel RESERVED for HALT raised events; dormant
  until something writes the metric.

Fault-drill TODO (first acknowledgment): force a 5xx on staging (e.g. env
`FARM_FORCE_FAULT=1`), watch the alert fire, acknowledge the email, revert.
Not yet exercised (follow-up duty of the operator).

## 5. Budget

See `deploy/budget.md` (short: TWD 2000 ≈ ¥10k/month guard on `seges-ai`,
50 %/90 % thresholds, email channel attached; created 2026-11-18).

## 6. CI federation (Workload Identity Federation for GitHub Actions)

```bash
gcloud iam workload-identity-pools create github \
  --project=seges-ai --location=global \
  --display-name="GitHub Actions OIDC pool"

gcloud iam workload-identity-pools providers create-oidc github \
  --project=seges-ai --location=global --workload-identity-pool=github \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
  --attribute-condition='assertion.repository=="Zereo0317/farm-ontology"'

gcloud iam service-accounts add-iam-policy-binding \
  451400509859-compute@developer.gserviceaccount.com --project=seges-ai \
  --role=roles/iam.workloadIdentityUser \
  --member=principalSet://iam.googleapis.com/projects/451400509859/locations/global/workloadIdentityPools/github/attribute.repository/Zereo0317/farm-ontology

# deployer rights for the CI path (staging deploys, build writes):
gcloud projects add-iam-policy-binding seges-ai \
  --member=serviceAccount:451400509859-compute@developer.gserviceaccount.com \
  --role=roles/run.admin --condition=None
gcloud projects add-iam-policy-binding seges-ai \
  --member=serviceAccount:451400509859-compute@developer.gserviceaccount.com \
  --role=roles/cloudbuild.builds.editor --condition=None
```

All four created (the `--condition=None` is required because this project's
IAM policy already contains conditional bindings). The GitHub workflow in
`.github/workflows/test.yml` consumes exactly this pool/provider path.

## 7. Deferred / not-created

- Nightly record EXPORT bucket + scheduler (WS1.2): owned by the pipeline
  workstream; `deploy/rollback.md` notes GCS versioning + soft-delete as the
  interim floor.
- Custom domain / CDN: untouched.
- Alert WEBHOOK channel: deferred (email suffices solo-founder Stage);
  add later via `gcloud alpha monitoring channels create --type=webhook_token`.
- JSON structured logs/Error Reporting wiring (WS1.4) beyond noting that
  stack traces already land in Logging: not started (kept for the next wave).
