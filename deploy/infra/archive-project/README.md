# Farm archive infrastructure

This stack provisions resources in the dedicated farm archive project and
farm-prefixed resources in `seges-ai`. It creates a private archive bucket, a
private versioned Terraform state bucket inside the archive project, job-only
runtime identities, and a project-scoped cost budget. The existing export
scheduler is deliberately outside Terraform state by default; its current
enabled cadence remains unchanged until the activation gate is complete.

The stack does not manage sibling services, jobs, buckets, IAM, or billing
resources. No provisioning or apply was performed for this code change.

## Owner inputs

Confirm the globally available archive project and bucket names, billing
account, owner-approved monthly TWD budget and alert recipient, WIF deployer
service account, and Terraform state operator principal. Put them in a private
`terraform.tfvars` copied from the example. The example values are not approved
account settings. Do not commit the private file.

## Two-phase state bootstrap and rollout

The remote state bucket cannot exist until the separate archive project has
been created. Bootstrap the project and state bucket under local Terraform
state, then migrate that state into the bucket. The state file is ignored by
Git; protect it in the operator's local environment during this short phase.

1. Initialize without the remote backend and create only the archive project,
   its required APIs, the state bucket, and the explicit state operator grant:

   ```powershell
   terraform -chdir=deploy/infra/archive-project init -backend=false
   terraform -chdir=deploy/infra/archive-project plan `
     -target=google_project.archive `
     -target=google_project_service.archive_services `
     -target=google_storage_bucket.terraform_state `
     -target=google_storage_bucket_iam_member.terraform_state_operator `
     -out=archive-bootstrap.tfplan
   terraform -chdir=deploy/infra/archive-project apply archive-bootstrap.tfplan
   ```

   Review the bootstrap plan first. It must contain only those four resource
   addresses. Do not pass `-auto-approve`.
2. Verify the bucket's actual gcloud JSON fields and migrate the local state
   into the new bucket:

   ```powershell
   pwsh -File deploy/infra/archive-project/bootstrap-state.ps1
   terraform -chdir=deploy/infra/archive-project init -migrate-state `
     -backend-config="bucket=farm-seges-ai-iac-state" `
     -backend-config="prefix=farm/archive"
   ```

   The verifier is read-only. It accepts gcloud's snake_case flat fields and
   nested snake_case fields. No import is needed for the state bucket because
   it is already represented in the local state being migrated. Confirm the
   remote state is usable before securely removing local state and plan files.
3. Run a full remote-state plan and review every resource. The default
   `enable_archive_schedule=false` means the existing
   `farm-sched-record-export` resource has Terraform `count = 0`; Terraform
   does not import, pause, update, or replace it during initial infrastructure
   setup. The existing scheduler keeps its current cadence. Apply only after
   the reviewed plan contains farm-scoped changes and no unrelated resources.
4. Build/deploy the exporter with the digest-pinning helper and execute its
   smoke run. Verify the produced manifest, digest, byte count, and member set.
5. Run the bounded isolated restore drill and preserve its JSON receipt. Only
   after smoke and restore evidence are accepted, set
   `enable_archive_schedule=true`, import the existing scheduler at the
   count-indexed address, review the exact plan, and apply to activate the
   30-minute cadence:

   ```powershell
   terraform -chdir=deploy/infra/archive-project import `
     'google_cloud_scheduler_job.archive_export[0]' `
     projects/seges-ai/locations/asia-east1/jobs/farm-sched-record-export
   terraform -chdir=deploy/infra/archive-project plan -out=archive-activate.tfplan
   terraform -chdir=deploy/infra/archive-project apply archive-activate.tfplan
   ```

   Import alone changes Terraform state, not the live scheduler. The apply is
   the explicit activation that moves it to twice-hourly runs.

## IAM boundaries

- The archive exporter service account is in `seges-ai` so the existing Cloud
  Run job can attach it. It reads source records, writes only pipeline run and
  alert artifacts in the source bucket, and creates/reads archive objects; it
  cannot delete archive objects or administer buckets.
- Cloud Scheduler receives `roles/run.invoker` on only
  `farm-nightly-export`. The scheduler resource itself remains unmanaged until
  the explicit activation phase.
- The state bucket lives in the separate archive project, enforces uniform
  bucket access and public access prevention, and explicitly grants
  `roles/storage.objectAdmin` only to the configured Terraform operator at
  bucket scope. Runtime identities receive no explicit state-bucket grant.
  Project owners and inherited organization/project roles can still access
  resources; bucket IAM does not override inherited grants.
- Persistent project, bucket, IAM, scheduler, service-account, and budget
  resources have `prevent_destroy` guards. Keep a separate protected backup of
  the remote state.

## Retention, limits, and targets

The archive begins with 90-day unlocked bucket retention. Lifecycle rules
expire only `.tar.gz` snapshots under `field-archive/` after 90 days; current
versions use object age, while noncurrent generations use days since becoming
noncurrent. Manifest JSON remains. The scratch bucket expires current and
noncurrent `restore-drills/` objects after seven days. Do not lock retention
without separate owner approval.

The restore tool bounds manifest downloads at 1 MiB, archive downloads at
2 GiB, members at 100,000, each JSON member at 64 MiB, and total expanded
content at 8 GiB. It checks remote object sizes before download, validates
member metadata before any scratch-bucket write, verifies archive and restored
object digests, and never writes to the production record bucket.

The 30-minute cadence targets RPO ≤ 1 hour. The 4-hour RTO target is evidenced
only by a timed restore drill that confirms digest, exact member paths, object
digests, and elapsed time. Failure rows are currently artifacts; human-facing
alert delivery and a missing-run watchdog remain operational gates. A budget
alert is project-filtered at 50%, 90%, and 100%, and does not cap spend. The
archive amount must fit the existing farm-wide TWD 2,000/month budget.

## Separate web access-control follow-up

The web authentication branch still needs a dedicated identity foundation
before its OIDC membership-write denial can be accepted: a private,
farm-prefixed access bucket in `seges-ai`; a dedicated web runtime service
account with read-only access to membership objects plus only the exact
record-store permissions needed by the field app; and a constrained
`roles/iam.serviceAccountUser` attachment grant for the web deployer. The live
web service currently uses the shared default compute identity. Keep this as a
separate reviewed infrastructure task; do not grant web access to the archive
or Terraform state bucket, and do not treat this archive stack as closing the
web identity gate.
