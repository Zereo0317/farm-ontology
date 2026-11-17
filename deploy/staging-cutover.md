# Staging cutover — GCS record backend (applied 2026-11-17)

Written by infra (task-1). This documents the change that was APPLIED to
staging, its verification, and the prod cutover procedure — deliberately
NOT yet executed for prod.

## What changed on `farm-seges-ai-staging`

| When (UTC) | Revision | Change |
| --- | --- | --- |
| 2026-11-17 08:4x | `farm-seges-ai-staging-00085-fmk` | `FARM_RECORD_BACKEND=gcs`, `FARM_RECORD_BUCKET=farm-seges-ai-records` added (all previous env + `Planet-labs` secret ref preserved); traffic pinned 100 % LATEST via `update-traffic --to-latest` (set-traffic discipline) |

Everything else on the service was left untouched: runtime SA stayed
`451400509859-compute@developer.gserviceaccount.com`, secret mount
`PLANET_API_KEY=Planet-labs:latest` unchanged.

### Verification performed (proof lines)

- Describe after update: latestCreatedRevision = traffic revision =
  `farm-seges-ai-staging-00085-fmk`; env set reads back exactly
  `GCP_PROJECT, EE_PROJECT, SERVICE_VERSION, PLANET_API_KEY(secret), FARM_RECORD_BACKEND=gcs, FARM_RECORD_BUCKET=farm-seges-ai-records`.
  (An intermediate revision `00084-4dz` briefly carried a polluted
  `FARM_RECORD_BACKEND` value caused by PowerShell comma-splitting of
  unquoted `--update-env-vars`; it was replaced within minutes by `00085`
  and never served meaningful traffic. Shell-quoting pitfall recorded in
  `docs/backend-live.md` deployment notes.)
- Bucket-side: durability drill via Cloud Run job
  (`farm-observation-drill`, execution `...-ph9fd`, SUCCEEDED 09:08:41Z)
  wrote `field-notes/obs-20261117T090850Z.json` under the runtime SA with
  NO downloaded credentials — the metadata-server token path works.
- `gcloud storage ls gs://farm-seges-ai-records/field-notes/` listed the
  three seed observations, the seed note, the pin, and the drill
  observation afterwards.

The new writes are LABELLED DRY-RUN observations (synthetic 0 N, 0 E
points, `dry_run: true`, never claimed as farm data) exactly like the
record module's design intends.

## Prod cutover — procedure (NOT executed; do NOT copy-paste blindly)

Prod switching is intentionally a DECIDED-but-not-executed step (it needs
an operator watching /livez, and a careful glance at `/farm` output before
and after):

1. Preflight: `gcloud storage buckets describe gs://farm-seges-ai-records
   --format='value(versioning_enabled)'` → True.
2. Snapshot today's prod envs:
   `gcloud run services describe farm-seges-ai --region=asia-east1
   --format=json(spec.template.spec.containers[0].env)` — keep the output.
3. Switch:
   `gcloud run services update farm-seges-ai --region=asia-east1
   '--update-env-vars=FARM_RECORD_BACKEND=gcs,FARM_RECORD_BUCKET=farm-seges-ai-records'`
   (mind the SHELL QUOTING pitfall above — one comma-split quietly turns
   this into a broken single env var).
4. Pin: `./deploy/set-traffic.sh prod`.
5. Verify `GET /livez` → `{status:"ok"…}`, `GET /farm` reflects the counts
   from the bucket (should read the seeded records), then run the drill job.
6. Watch the `farm-prod-livez` uptime + alert for one period before closing.

Rollback: repeat step 3 with `FARM_RECORD_BACKEND=local` (or remove both
vars), `./deploy/set-traffic.sh prod`. Data safety: everything written
while on gcs stays in the versioned bucket either way.
