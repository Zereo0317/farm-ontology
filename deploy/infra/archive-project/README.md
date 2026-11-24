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

### Break-glass pause and IAM rotation

After Terraform has imported the scheduler, do not set
`enable_archive_schedule=false`: `prevent_destroy` intentionally blocks the
resulting destroy plan. For an emergency pause, first run
`gcloud scheduler jobs pause farm-sched-record-export --project=seges-ai
--location=asia-east1`, record the incident, then update Terraform state and
the reviewed schedule configuration before resuming. Do not apply the normal
activation plan during incident response.

The Terraform-state operator grant is intentionally rotatable. For an operator
change, update `terraform_state_operator_member` and review a plan containing
only the expected IAM-member replacement. `create_before_destroy` adds the new
principal before removing the old one. Verify the replacement can read and
write remote state before completing the rotation; never remove the last
usable state operator before the replacement is tested.

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
- The web runtime identity receives objectViewer on its dedicated membership
  bucket, viewer/create on the farm tenant record managed folder, and
  secretAccessor on the OIDC/session and Planet-labs secrets. Promotion
  rejects direct project IAM assignments, any direct runtime binding on the
  parent records bucket, and extra/conditional access-bucket or record-folder
  bindings. Inherited org/folder/group grants still require owner-side
  effective-IAM review.
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

## Web access-control foundation

This stack also creates a separate private membership bucket in `seges-ai`,
two empty OIDC/session Secret Manager entries, and the dedicated
`farm-web-runtime` and `farm-web-deployer` service accounts. The runtime gets
read-only access to membership objects, accessor on only the OIDC/session and
existing `Planet-labs` secrets, and viewer plus create-only permissions on the
`field-notes/farms/` managed folder of the existing records bucket. It cannot
list legacy root records, read pipeline/archive/state data, overwrite or
delete records, or modify memberships through its direct grants. These folder
permissions support the web record bridge's list/get/first-write-only
contract; tenant authorization still requires end-to-end acceptance.
Their IDs are intentionally fixed because the GitHub identity and promotion
checks pin these exact principals.
An explicitly configured user or group principal receives the membership
administrator role. Mirror Terraform output
`web_membership_administrator_member` to GitHub's
`FARM_WEB_MEMBERSHIP_ADMINISTRATOR`; the promotion gate compares complete
direct bucket and managed-folder IAM policies against the expected principals.

The web deployer is distinct from the shared compute/exporter identity. Its
GitHub WIF grant binds only the repository's `main` branch subject. It gets
Cloud Run Developer on `farm-seges-ai-web`, Artifact Registry Reader on
`cloud-run-source-deploy`, Service Account User on the web runtime, and
only IAM-policy metadata reader permissions needed by the promotion gate. The
project-level custom role contains only `resourcemanager.projects.getIamPolicy`;
it has no project-wide Cloud Run deploy role. The configured Terraform operator
receives `secretVersionAdder` on the two new secrets; the operator must add
the provider-issued OIDC client secret and random session key as versions.
Secret payloads are not stored in Terraform state.

No identity-provider client or farmer membership is created here. Before the
runtime is used, review effective organization/folder/project IAM inherited by
the shared-project resources, including custom and group grants; this stack
cannot remove inherited access. The live web service keeps its current
identity until OIDC configuration and farmer acceptance are completed, and
the dedicated runtime is attached only on a no-traffic candidate revision.
