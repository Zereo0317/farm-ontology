# Farm archive infrastructure

This stack provisions only resources whose IDs begin with `farm-seges-ai`.
It creates a separate archive project, the private archive bucket, a job-only
exporter identity, an invoke-only scheduler identity, the farm export
scheduler, a restricted Terraform state bucket, and a project-scoped cost
budget. It does not manage or delete sibling services, jobs, buckets, IAM, or
billing resources.

## Safety and apply sequence

1. Confirm `farm-seges-ai-records-archive` and the bucket name are available.
   Confirm the billing amount/email and the WIF deployer service account in a
   private `terraform.tfvars` copied from the example. Never commit that file.
2. Review the full Terraform plan and ensure every proposed resource is
   farm-prefixed. No project, bucket, budget, or scheduler apply is included in
   this code task.
3. Bootstrap `farm-seges-ai-iac-state` with
   `pwsh -File deploy/infra/archive-project/bootstrap-state.ps1`. The script
   creates only that bucket when absent and verifies location, public access,
   uniform access, and object versioning when present.
4. Initialize the remote state and import the bootstrap bucket and existing
   scheduler before planning:

   ```powershell
   terraform -chdir=deploy/infra/archive-project init `
     -backend-config="bucket=farm-seges-ai-iac-state" `
     -backend-config="prefix=farm/archive"
   terraform -chdir=deploy/infra/archive-project import `
    google_storage_bucket.terraform_state farm-seges-ai-iac-state
   terraform -chdir=deploy/infra/archive-project import `
     google_cloud_scheduler_job.archive_export `
     projects/seges-ai/locations/asia-east1/jobs/farm-sched-record-export
   terraform -chdir=deploy/infra/archive-project plan -out=archive.tfplan
   ```

   Do not apply until import is complete and the plan shows no changes to
   resources outside this stack. Project and bucket resources have
   `prevent_destroy`; the archive lifecycle deletes only `.tar.gz` snapshots
   under `field-archive/` after 90 days. Manifests remain. Retention is
   initially unlocked and must stay unlocked until a separate retention
   approval.

5. After the infrastructure apply, build and deploy the worker with the
   immutable image script. The script requires an explicit archive bucket and
   configures the complete environment set. Run its smoke mode before
   enabling the scheduler cadence in Terraform.
6. Run the isolated restore drill and retain its JSON receipt with the
   deployment record. The scratch restore bucket is separate from both the
   record and archive buckets and expires drill objects after seven days.

## IAM boundaries

- The archive exporter service account is created in `seges-ai` so the
  existing Cloud Run job can attach it without cross-project service-account
  federation. On the source bucket it can read records and can update only
  `pipelines/run-log/` and `pipelines/alerts/`. On the archive bucket it can
  create and read objects, but cannot delete them or administer the bucket.
- Cloud Scheduler receives `roles/run.invoker` on only
  `farm-nightly-export`; it cannot update or delete jobs.
- No runtime service account receives access to the Terraform state bucket.
- The archive project, archive bucket, state bucket, scheduler, service
  accounts, and budget all have Terraform destroy protection. This is not a
  substitute for a separately controlled backup of Terraform state.

## Targets and limits

The scheduler runs every 30 minutes in Tokyo time, with one retry, to leave
margin around the **RPO ≤ 1 hour** objective. Each export must complete within
10 minutes. The **RTO ≤ 4 hours** objective is met only after an operator
restores an archive to the scratch bucket, verifies its digest/member set,
and records elapsed time. A scheduled job or successful upload alone is not
proof of either objective. The existing export code records artifact-only
failure alerts; delivery of those alerts to a person is still a separate
operational gate.

The archive budget amount is a required input because the existing farm-wide
budget is TWD 2,000/month. Set an archive threshold that fits within the
farm-wide cost target and verify both budgets after provisioning; budgets
notify but do not cap spend.
