[CmdletBinding()]
param(
  [string]$Project = "farm-seges-ai-records-archive",
  [string]$Region = "asia-east1",
  [string]$Bucket = "farm-seges-ai-iac-state"
)

$ErrorActionPreference = "Stop"
if (-not $Project.StartsWith("farm-seges-ai-records-archive", [StringComparison]::Ordinal) -or
    $Region -ne "asia-east1" -or $Bucket -ne "farm-seges-ai-iac-state") {
  throw "State verification is restricted to the dedicated farm archive project and state bucket."
}

$uri = "gs://$Bucket"
$json = & gcloud storage buckets describe $uri --project=$Project --format=json
if ($LASTEXITCODE -ne 0 -or -not $json) {
  throw "State bucket must already exist in the dedicated archive project; bootstrap it through the reviewed Terraform phase."
}

$jsonPath = [IO.Path]::GetTempFileName()
try {
  [IO.File]::WriteAllText($jsonPath, ($json -join [Environment]::NewLine), [Text.UTF8Encoding]::new($false))
  & python (Join-Path $PSScriptRoot "verify_state_bucket.py") --json $jsonPath --bucket $Bucket --region $Region
  if ($LASTEXITCODE -ne 0) { throw "State bucket settings failed verification." }
} finally {
  Remove-Item -LiteralPath $jsonPath -Force -ErrorAction SilentlyContinue
}

Write-Output "Verified $uri. Its Terraform state IAM grant is managed in the archive project."
