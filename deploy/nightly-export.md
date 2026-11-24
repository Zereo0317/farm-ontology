# Farm record archive operations

The exporter is `pipelines/record_export.py`, run by Cloud Run job
`farm-nightly-export`. Its archive output and the operational infrastructure
are separate concerns: snapshots are deterministic gzip tar files under
`field-archive/<UTC-day>/`, with one JSON manifest per snapshot under
`field-archive/manifest/<UTC-day>/`. Each manifest records the archive object,
SHA-256, member count, byte count, source backend, and write time. Existing
daily NDJSON manifests remain historical records.

## Durability targets and current status

After explicit post-smoke/restore activation, the archive infrastructure stack
in `deploy/infra/archive-project/` sets a 30-minute scheduler cadence in
`Asia/Tokyo`, with one retry, to target RPO of one hour or less. Its default
configuration does not manage or alter the existing export scheduler. The
export task timeout is ten minutes. The Terraform stack places the archive in
a separate farm-only project and bucket, grants a dedicated exporter identity
create/read access there, and starts with 90-day unlocked retention. A
lifecycle rule expires only `.tar.gz` snapshots under `field-archive/`;
manifest JSON is preserved. The scratch restore bucket is separate and
expires drill objects after seven days.

These are configuration targets, not proof of achieved RPO/RTO. The 4-hour
RTO target becomes operationally evidenced only after a timed restore drill
confirms archive digest, exact member paths, restored object digests, and
elapsed time. The exporter currently records failures as artifacts; a
human-facing missing-run watchdog and alert delivery still need an owner and
operational implementation. Do not report the targets as met until monitoring
and a successful timed drill are recorded.

## Historical evidence

The first historical execution completed on 2026-11-18. It wrote to the same
bucket as its source, so it was not an independent backup and does not prove
restore readiness. Its manifest row was:

```json
{"archive_object":"20261118/record-snapshot-20261118T115029Z.tar.gz","sha256":"d48604beba006074f2c30c885d1556574401b8fca07eb949f44bfadda5e5be83","members":9,"bytes":1307}
```

Treat this only as historical evidence; do not use it as evidence that the new
isolated archive is provisioned or serving traffic.

## Safe rollout sequence

1. Read `deploy/infra/archive-project/README.md` and inspect every planned
   resource. Confirm the proposed project and globally unique bucket names,
   owner-approved monthly TWD budget, budget notification recipient, billing
   account, and deployer identity. The checked-in `.tfvars.example` is not a
   set of approved values.
2. Bootstrap the dedicated archive project and state bucket under local state,
   then migrate that state to the private bucket using the infrastructure
   runbook. The existing scheduler remains unmanaged while
   `enable_archive_schedule=false`. No apply was performed by this code task.
3. After an approved apply, build and deploy the worker from the current
   committed source using:

   ```powershell
   pwsh -File deploy/infra/archive-project/deploy-exporter.ps1 `
     -ArchiveBucket farm-seges-ai-records-archive -ExecuteSmoke
   ```

   The helper verifies the active project/region, builds an image, resolves
   its digest, and updates the complete Cloud Run job environment in one
   operation. Verify the newest manifest and job execution before making any
   scheduler change.
4. Perform an isolated restore from a specific manifest and preserve its
   printed JSON receipt with deployment evidence:

   ```powershell
   python deploy/infra/archive-project/restore_archive.py `
     --archive-bucket farm-seges-ai-records-archive `
     --manifest-object field-archive/manifest/YYYYMMDD/<manifest>.json `
     --target-bucket farm-seges-ai-archive-restore
   ```

   After both the smoke and restore are accepted, set
   `enable_archive_schedule=true`, import the existing resource at
   `google_cloud_scheduler_job.archive_export[0]`, review the plan, and apply
   to activate the half-hourly cadence. Import itself does not change the live
   scheduler.

   The restore program downloads and hashes the archive, rejects unsafe or
   non-JSON members, restores only to the dedicated scratch bucket, compares
   the exact restored member paths, and downloads each object again to verify
   its digest. It never writes to the production record bucket. An operator
   must time the whole exercise and record RTO.

## Existing archive migration

Older exports may exist in `farm-seges-ai-records` alongside live records.
No automatic migration runs. Before cutover, inventory the prior tarballs and
NDJSON manifests, decide which history to retain, and copy only after the new
archive project has been separately approved. For each copied snapshot,
verify the manifest, SHA-256, bytes, and member set. Keep source objects until
the isolated restore drill passes. Do not bulk-copy production field records
or delete source history as part of infrastructure provisioning.

## Access and costs

- Exporter identity: source-bucket read access for archive inputs; write access
  on the source bucket limited to `pipelines/run-log/` and `pipelines/alerts/`;
  create/read only on the archive bucket. It has no archive delete permission.
- Scheduler identity: `roles/run.invoker` on only `farm-nightly-export`.
- Restore drill: operator's gcloud identity writes only to the separate
  scratch bucket; no production record bucket is a restore destination.
- Terraform state: dedicated versioned private bucket in the archive project,
  with an explicit bucket-level object-admin grant for the configured
  Terraform operator. Runtime identities get no explicit state grant, though
  inherited project/org administration remains effective. Protect and back up
  Terraform state separately.
- Budget: project-filtered TWD alerts at 50%, 90%, and 100%. A budget sends
  alerts and does not stop spend. The archive amount must fit the farm-wide
  TWD 2,000/month budget and needs owner confirmation.

## Previous single-bucket evidence

The former nightly cadence was 03:30 JST (`30 3 * * *`). Earlier evidence
showed one execution and nine snapshot members, but those records were in the
primary bucket and there was no completed isolated restore procedure. The
scheduler remains outside Terraform state while the activation gate is closed.
After smoke and restore evidence are accepted, import the existing
`farm-sched-record-export` resource at its count-indexed address so Terraform
can apply the new cadence without replacing the scheduler.
