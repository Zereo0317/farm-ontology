# Rollback + restore drill checklist (`farm-seges-ai`)

Owner: infra · Last exercised: 2026-11-17 (restore drill done against
`farm-seges-ai-records`; see §4)

Rollback has two independent halves. Losing the CODE is recoverable from git
and Secret Manager; losing the RECORD is not — the field observations are the
irreplaceable part. Hence §3 (record integrity) is checked BEFORE any
redeployment move.

## 1. Preconditions (verify before touching anything)

- [ ] `gcloud` auth = `segescloud@gmail.com`, project = `seges-ai`
- [ ] Last known-good revision name recorded
      (`gcloud run services describe farm-seges-ai --region=asia-east1 --format='value(status.latestReadyRevisionName)'`)
- [ ] Bucket `farm-seges-ai-records` versioning still ON
      (`gcloud storage buckets describe gs://farm-seges-ai-records --format='value(versioning_enabled)'` → True)

## 2. Service rollback (bad deploy)

```bash
# pin traffic back to the good revision by NAME, not percent drift:
gcloud run services update-traffic farm-seges-ai --region=asia-east1 \
  --to-revisions <GOOD_REVISION>=100
# the helper prevents the usual forgetting going FORWARD:
./deploy/set-traffic.sh prod   # after any re-fix deploy
```

Notes: env vars and secrets live on the SERVICE config, not per-revision
traffic split; a rollback by traffic needs no re-mounting.

## 3. Record integrity check (the acceptance criterion)

"a new observation survives instance recycle":

1. Write one dry-run observation through the durable store:
   ```bash
   ./deploy/create-observation-job.sh   # or: gcloud run jobs execute farm-observation-drill --wait
   ```
   Exit 0 + printed JSON summary = the observation round-tripped through GCS
   under the runtime service account (container FS not involved for reads).
2. Confirm the object appeared (and versioning would recover an overwrite):
   ```bash
   gcloud storage ls -l gs://farm-seges-ai-records/field-notes/ | tail -5
   ```

## 4. Restore drill checklist (catastrophic: recreate the instance)

Scenario: container instance lost entirely (project state wiped, revision
history irrelevant, records must come back from the bucket).

1. [ ] Recreate/deploy the service:
      `gcloud run deploy farm-seges-ai --region=asia-east1 --source . --allow-unauthenticated`
2. [ ] Restore environment deltas (beyond defaults):
      `GCP_PROJECT`, `EE_PROJECT`, `FARM_RECORD_BACKEND=gcs`,
      `FARM_RECORD_BUCKET=farm-seges-ai-records`, `SERVICE_VERSION`,
      and mount the Planet secret:
      `--set-secrets PLANET_API_KEY=Planet-labs:latest`
      (copy the exact live envs first:
      `gcloud run services describe farm-seges-ai --region=asia-east1 --format=json(spec.template.spec.containers[0].env)`)
3. [ ] Runtime SA still `451400509859-compute@developer.gserviceaccount.com`;
      re-bind if the project was truly rebuilt:
      - `roles/storage.objectUser` on `gs://farm-seges-ai-records`
      - `roles/secretmanager.secretAccessor` on `Planet-labs`
      - `roles/earthengine.viewer` on the project
4. [ ] Observations intact from GCS: bucket listing matches the last known
      count (seed 2026-11-17: 3 observations + 1 note + pin file; versions
      list via `gcloud storage ls -a gs://farm-seges-ai-records/field-notes/`),
      `GET /farm` and the observation count endpoint report the same numbers
      against the restored backend, one fresh drill observation round-trips
      (`./deploy/create-observation-job.sh`).
5. [ ] Uptime checks still green (`gcloud monitoring uptime list-configs`);
      alert channels intact (email `segescloud@gmail.com`).

## 5. What is intentionally NOT covered

- Cloud SQL/database restore: the record store is GCS; there is no database.
- Prod database migrations: n/a.
- Long-term retention: the nightly archive/export workstream (WS1.2) will add
  a second bucket with 90-day rolling retention; until that exists, GCS
  versioning + soft-delete (7-day) on `farm-seges-ai-records` is the floor.
