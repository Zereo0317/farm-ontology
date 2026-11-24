[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$ArchiveBucket,
  [string]$SourceBucket = "farm-seges-ai-records",
  [string]$Project = "seges-ai",
  [string]$Region = "asia-east1",
  [switch]$ExecuteSmoke
)

$ErrorActionPreference = "Stop"
if ($Project -ne "seges-ai" -or $Region -ne "asia-east1") {
  throw "Farm exporter deployment is restricted to seges-ai / asia-east1."
}
if ($SourceBucket -ne "farm-seges-ai-records" -or $SourceBucket -eq $ArchiveBucket) {
  throw "Source and archive buckets must be distinct; source must be farm-seges-ai-records."
}
if (-not $ArchiveBucket.StartsWith("farm-seges-ai-records-archive", [StringComparison]::Ordinal)) {
  throw "Archive bucket must use the dedicated farm-seges-ai-records-archive prefix."
}

$activeProject = (& gcloud config get-value project 2>$null).Trim()
if ($activeProject -ne $Project) {
  throw "Active gcloud project must be $Project (found '$activeProject')."
}

$commit = (& git rev-parse --short=12 HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or -not $commit) { throw "Run from a Git checkout with a committed source revision." }
$dirty = (& git status --porcelain)
if ($LASTEXITCODE -ne 0 -or $dirty) {
  throw "Commit or discard local changes before building the production exporter image."
}
$imageTag = "asia-east1-docker.pkg.dev/$Project/farm/farm-worker:archive-$commit"

Write-Output "Building exporter source at commit $commit."
& gcloud builds submit . `
  --project=$Project `
  --region=$Region `
  --tag=$imageTag
if ($LASTEXITCODE -ne 0) { throw "Cloud Build failed; exporter job was not changed." }

$digest = (& gcloud artifacts docker images describe $imageTag --project=$Project --format="value(image_summary.digest)").Trim()
if ($LASTEXITCODE -ne 0 -or $digest -notmatch '^sha256:[0-9a-f]{64}$') {
  throw "Could not resolve the just-built immutable image digest; exporter job was not changed."
}
$image = "asia-east1-docker.pkg.dev/$Project/farm/farm-worker@$digest"

# Pass the complete environment in one --set-env-vars flag. On Cloud Run this
# replaces the whole set; do not split it into multiple flags.
$envVars = "FARM_RECORD_BACKEND=gcs,FARM_RECORD_BUCKET=$SourceBucket,FARM_ARCHIVE_BUCKET=$ArchiveBucket,GCP_PROJECT=$Project,FARM_RECORD_DIR=/tmp/farm-records"
$deployArgs = @(
  "run", "jobs", "deploy", "farm-nightly-export",
  "--project=$Project", "--region=$Region", "--image=$image",
  "--service-account=farm-seges-ai-archive-exporter@$Project.iam.gserviceaccount.com",
  "--args=python,-m,pipelines.record_export",
  "--max-retries=1", "--task-timeout=10m",
  "--set-env-vars=$envVars"
)

Write-Output "Deploying farm-nightly-export with a pinned image digest."
& gcloud @deployArgs
if ($LASTEXITCODE -ne 0) { throw "Exporter job update failed." }

if ($ExecuteSmoke) {
  Write-Output "Executing one archive smoke run."
  & gcloud run jobs execute farm-nightly-export --project=$Project --region=$Region --wait
  if ($LASTEXITCODE -ne 0) { throw "Archive smoke execution failed; do not change the scheduler cadence." }
  & gcloud storage ls "gs://$ArchiveBucket/field-archive/manifest/"
  if ($LASTEXITCODE -ne 0) { throw "Archive manifest listing failed; do not change the scheduler cadence." }
  Write-Output "Smoke execution completed. Verify the newest manifest, digest and member count before applying the scheduler change."
} else {
  Write-Output "Job updated; scheduler was not changed. Use -ExecuteSmoke and verify the manifest before enabling the 30-minute schedule."
}

Write-Output "image=$image"
