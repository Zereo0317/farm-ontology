# Nightly record export (WS1.2 tail, task-10)

Executed 2026-11-18 by infra. The nightly export completes the durable
record story: even a catastrophic, versioned-bucket-corruption scenario
leaves one immutable daily snapshot per UTC day.

## What runs

`pipelines/record_export.py` (entry `python -m pipelines.record_export`,
Cloud Run job **`farm-nightly-export`**):

1. reads EVERY object of the field record through the SAME record-store
   seam the services use (`field-notes/**`, both roots),
2. composes one deterministic gzipped tar (sorted members, fixed
   mtime/uid/gid ⇒ byte-identical for identical inputs):
   `field-archive/<UTC-day>/record-snapshot-<UTC-stamp>.tar.gz`,
3. verifies the written object by reading it back and comparing
   sha256 AND the member list before declaring success,
4. appends one row per snapshot to `field-archive/manifest/<day>.ndjson`
   (dedup on the object name ⇒ idempotent re-runs),
5. logs the run under `pipelines/run-log/<day>-record-export.json`
   (job `record-export`) — inheriting WS2's run-log + 3-strike alert
   machinery (`on_run_finished`) unchanged. A failed export STILL
   writes its failure row; three failed days fire
   `pipelines/alerts/<day>-record-export-ALERT.json`.

Schedule: **03:30 JST nightly** (`CRON_TZ=Asia/Tokyo 30 3 * * *`), bound
as the Cloud Scheduler HTTP job `farm-sched-record-export` → the same
OAuth-SA-run convention WS2 proved (`farm-sched-*` family), hitting
`.../jobs/farm-nightly-export:run`. State at creation: ENABLED,
next-fire 2026-11-19T18:30Z (= 2026-11-19 03:30 JST).

## Manifest row (proof of the first run)

Execution `farm-nightly-export-6mqmc` completed 2026-11-18T11:50Z;

```json
{"archive_object": "20261118/record-snapshot-20261118T115029Z.tar.gz", "sha256": "d48604beba006074f2c30c885d1556574401b8fca07eb949f44bfadda5e5be83", "members": 9, "bytes": 1307, "backend": {"backend": "gcs", "bucket": "farm-seges-ai-records", "prefix": "field-notes", "api": "storage.googleapis.com"}, "written_at": "2026-11-18T11:50:29.127428+00:00", "manifest_note": "one row per snapshot object; snapshots are additive, pruning is policy-gated (deploy/record-retention-policy.md)"}
```

The nine members included everything banked through 11:50Z: the three
farm observations + note + pin seeded on 11-17, the three durability-drill
observations, and `obs-20261118T075203Z.json` written the same morning.
Downloaded independently and verified: local sha256 matches the manifest,
tar lists exactly the expected members, individual members parse.

## Operator cheat-sheet

```bash
gcloud run jobs execute farm-nightly-export --project=seges-ai \
  --region=asia-east1 --wait
gcloud storage cat gs://farm-seges-ai-records/field-archive/manifest/$(date -u +%Y%m%d).ndjson
gcloud storage ls -lr gs://farm-seges-ai-records/field-archive/
# image refresh after code changes (see deploy/scheduler-setup.md §1):
gcloud builds submit --region=asia-east1 \
  --tag asia-east1-docker.pkg.dev/seges-ai/farm/farm-worker:sprint-c-<stamp> .
gcloud run jobs deploy farm-nightly-export --project=seges-ai \
  --region=asia-east1 --image=asia-east1-docker.pkg.dev/seges-ai/farm/farm-worker:sprint-c-<stamp> \
  --service-account=451400509859-compute@developer.gserviceaccount.com \
  --max-retries=1 --task-timeout=10m \
  --args=python,-m,pipelines.record_export \
  --set-env-vars FARM_RECORD_BACKEND=gcs,FARM_RECORD_BUCKET=farm-seges-ai-records,GCP_PROJECT=seges-ai,FARM_RECORD_DIR=/tmp/farm-records
```

Retention: see `deploy/record-retention-policy.md` (POLICY DOCUMENT
ONLY — no lifecycle rule is active; this job deletes nothing).
