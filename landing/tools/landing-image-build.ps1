#!/usr/bin/env pwsh
# Stage the landing app into a minimal Cloud Build context and build a tagged image.
param(
  [Parameter(Mandatory = $true)][string]$TagSuffix,
  [string]$Region = "asia-east1",
  [string]$Project = "seges-ai"
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$stage = [IO.Path]::GetFullPath((Join-Path $repo ".dockerbuild-landing"))
$repoPrefix = $repo.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
if (-not $stage.StartsWith($repoPrefix, [StringComparison]::OrdinalIgnoreCase)) {
  throw "Refusing to stage outside the repository: $stage"
}
if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
New-Item -ItemType Directory -Path $stage | Out-Null

Copy-Item -LiteralPath (Join-Path $repo "Dockerfile.landing") -Destination (Join-Path $stage "Dockerfile")
$skipDirs = @("node_modules", ".output", ".vercel", ".tanstack", ".grok", "__pycache__")
function Copy-LandingTree([string]$Source, [string]$Destination) {
  New-Item -ItemType Directory -Force -Path $Destination | Out-Null
  foreach ($item in Get-ChildItem -LiteralPath $Source -Force) {
    if ($item.PSIsContainer) {
      if ($skipDirs -notcontains $item.Name) {
        Copy-LandingTree -Source $item.FullName -Destination (Join-Path $Destination $item.Name)
      }
    } else {
      Copy-Item -LiteralPath $item.FullName -Destination (Join-Path $Destination $item.Name) -Force
    }
  }
}
Copy-LandingTree -Source (Join-Path $repo "landing") -Destination (Join-Path $stage "landing")
Set-Content -LiteralPath (Join-Path $stage ".gcloudignore") -Value ".git`n.output"

$image = "$Region-docker.pkg.dev/$Project/cloud-run-source-deploy/farm-seges-ai-landing:$TagSuffix"
Write-Host "Building $image via Cloud Build..."
gcloud builds submit $stage --project $Project --tag $image
if ($LASTEXITCODE -ne 0) { throw "Cloud Build failed" }
Write-Host "IMAGE=$image"
