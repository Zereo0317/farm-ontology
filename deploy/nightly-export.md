# Nightly record export (WS1.2 tail, task-10)

Historical run record (2026-11-18). The original job wrote to the SAME
bucket as the source: it did not protect against bucket loss and snapshot
immutability was not established. This implementation now requires a distinct
`FARM_ARCHIVE_BUCKET` for GCS; provision and independently protect that bucket,
then configure and test a restore before deploying the changed job. Local
archives on the same disk are not an independent backup.

## What runs

`pipelines/record_export.py` (entry `python -m pipelines.record_export`,
Cloud Run job **`farm-nightly-export`**):

1. reads JSON objects of the field record through the SAME record-store
   seam the services use (`field-notes/**`, both roots),
2. composes one deterministic gzipped tar (sorted members, fixed
   mtime/uid/gid ⇒ byte-identical for identical inputs):
   `field-archive/<UTC-day>/record-snapshot-<UTC-stamp>-<sha256>.tar.gz`,
3. verifies the written object by reading it back and comparing
   sha256 AND the member list before declaring success,
4. creates one immutable JSON row per snapshot under
   `field-archive/manifest/<day>/`; the historical daily NDJSON remains readable,
   and identical inputs at the same timestamp deduplicate,
5. logs the run under `pipelines/run-log/<day>-record-export.json`
   (job `record-export`) — inheriting WS2's run-log + 3-strike alert
   machinery (`on_run_finished`) unchanged. A failed export STILL
   writes its failure row; three failed executions fire
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
gcloud storage ls "gs://<archive-bucket>/field-archive/manifest/$(date -u +%Y%m%d)/*.json"
gcloud storage ls -lr gs://farm-seges-ai-records/field-archive/
# image refresh after code changes (see deploy/scheduler-setup.md §1):
gcloud builds submit --region=asia-east1 \
  --tag asia-east1-docker.pkg.dev/seges-ai/farm/farm-worker:sprint-c-<stamp> .
gcloud run jobs deploy farm-nightly-export --project=seges-ai \
  --region=asia-east1 --image=asia-east1-docker.pkg.dev/seges-ai/farm/farm-worker:sprint-c-<stamp> \
  --service-account=451400509859-compute@developer.gserviceaccount.com \
  --max-retries=1 --task-timeout=10m \
  --args=python,-m,pipelines.record_export \
  --set-env-vars FARM_RECORD_BACKEND=gcs,FARM_RECORD_BUCKET=farm-seges-ai-records,FARM_ARCHIVE_BUCKET=<independently-protected-farm-archive-bucket>,GCP_PROJECT=seges-ai,FARM_RECORD_DIR=/tmp/farm-records
```

Retention: see `deploy/record-retention-policy.md` (POLICY DOCUMENT
ONLY — no lifecycle rule is active; this job deletes nothing).

## Remaining release gates

Manifest rows are individually create-only; they are not an independently verified ledger.
Provision a separate archive bucket with restricted access and retention, configure
the job, and perform a timed isolated restore with member hashes and a documented
RPO/RTO. Alert rows are artifacts only; real notification delivery and a missing-
run watchdog remain unimplemented. None of these live operations was performed
by the code change.

## Format and archive-bucket migration

Previous deployments wrote tarballs and `manifest/YYYYMMDD.ndjson` in the
primary `farm-seges-ai-records` bucket. New deployments require a distinct
archive bucket and create tarballs whose names include the full content digest,
with one JSON manifest object per snapshot in `manifest/YYYYMMDD/`. No code
automatically copies prior snapshots, deletes them, or searches across buckets.
The internal manifest reader can combine historical NDJSON and new JSON rows
only when they are present in the same configured backend. Consumers that read
the old NDJSON path directly must be updated to enumerate both formats; scripts
that assume the old tarball name must use each manifest's `archive_object`.

Before cutover, operators should inventory the old bucket and choose whether to
copy historical snapshots and NDJSON into the independently protected archive.
For any copy, verify each manifest and archived object's SHA-256 and counts,
retain the source until the restore drill is accepted, and document access and
retention. The repository contains no completed archive restore tool or
end-to-end restore drill for either format. The code change itself performs no
migration, provisioning, retention configuration, or restore.

Observation, note, and boundary creation use unique IDs but do not yet accept
client idempotency keys. A caller retry after a lost response can create a
duplicate. Mutable pipeline state remains last-writer-wins; neither limitation
is resolved by the archive changes.
