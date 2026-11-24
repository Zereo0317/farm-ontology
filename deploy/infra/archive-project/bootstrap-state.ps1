[CmdletBinding()]
param(
  [string]$Project = "seges-ai",
  [string]$Region = "asia-east1",
  [string]$Bucket = "farm-seges-ai-iac-state"
)

$ErrorActionPreference = "Stop"
if ($Project -ne "seges-ai" -or $Bucket -ne "farm-seges-ai-iac-state") {
  throw "This bootstrap is restricted to the approved farm Terraform state bucket in seges-ai."
}

$activeProject = (& gcloud config get-value project 2>$null).Trim()
if ($activeProject -ne $Project) {
  throw "Active gcloud project must be $Project (found '$activeProject')."
}

$uri = "gs://$Bucket"
$existing = & gcloud storage buckets describe $uri --project=$Project --format=json 2>$null
if ($LASTEXITCODE -ne 0) {
  & gcloud storage buckets create $uri `
    --project=$Project `
    --location=$Region `
    --uniform-bucket-level-access `
    --public-access-prevention
  if ($LASTEXITCODE -ne 0) { throw "Could not create the dedicated farm Terraform state bucket." }
  & gcloud storage buckets update $uri --project=$Project --versioning
  if ($LASTEXITCODE -ne 0) { throw "Could not enable object versioning on the state bucket." }
  $existing = & gcloud storage buckets describe $uri --project=$Project --format=json
}

$bucketInfo = $existing | ConvertFrom-Json
if ($bucketInfo.name -ne $Bucket -or $bucketInfo.location -ne $Region) {
  throw "State bucket identity or region does not match the farm-only target."
}
if ($bucketInfo.iamConfiguration.uniformBucketLevelAccess.enabled -ne $true) {
  throw "State bucket must have uniform bucket-level access enabled."
}
if ($bucketInfo.iamConfiguration.publicAccessPrevention -ne "enforced") {
  throw "State bucket must enforce public access prevention."
}
if ($bucketInfo.versioning.enabled -ne $true) {
  throw "State bucket must have object versioning enabled."
}

Write-Output "Verified $uri. Import it into google_storage_bucket.terraform_state before any Terraform plan/apply."
