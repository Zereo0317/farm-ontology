#!/usr/bin/env pwsh
# WS8 helper: stage a minimal docker build context for the web app and build
# the image on Cloud Build (no local docker engine is required on this host).
# Adopted by CI: .github/workflows/web-image.yml invokes this script on every
# main push touching web/**, tagging images ci-<shortsha>; keep the staging
# recipe single-sourced here so local and CI build byte-identical contexts.
#
# The root .gcloudignore excludes web/, and a repo-root `gcloud run deploy
# --source .` cannot see the web app; the curated staging sidesteps that
# without touching the root infra files (their scope belongs to WS1).
#
# Usage: pwsh -File .build/web-image-build.ps1 [-TagSuffix ws8-v1]
param(
  [string]$TagSuffix = "ws8-v1",
  [string]$Region = "asia-east1",
  [string]$Project = "seges-ai"
)

$ErrorActionPreference = "Stop"
# Script lives at web/tools/; the repo checkout is two levels up.
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$stage = Join-Path $repo ".dockerbuild-web"

# Fresh staging dir (git-ignored via .git/info/exclude).
if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
New-Item -ItemType Directory -Path $stage | Out-Null

# 1. Dockerfile: the .web file renamed to the canonical name inside the context.
Copy-Item (Join-Path $repo "Dockerfile.web") (Join-Path $stage "Dockerfile")

# 2. Portably mirror web/ (minus node_modules/.next/logs) — robocopy is
# Windows-only and CI runners are Ubuntu; Copy-Tree keeps ONE recipe for both.
$script:skipDirs = @("node_modules", ".next", "__pycache__", ".pytest_cache", ".venv", "venv")

function Copy-Tree([string]$Src, [string]$Dst, [string]$ExtFilter = "") {
  New-Item -ItemType Directory -Force -Path $Dst | Out-Null
  foreach ($item in (Get-ChildItem -LiteralPath $Src -Force)) {
    if ($item.PSIsContainer) {
      if ($script:skipDirs -notcontains $item.Name) {
        Copy-Tree -Src $item.FullName -Dst (Join-Path $Dst $item.Name) -ExtFilter $ExtFilter
      }
    }
    elseif ($ExtFilter -eq "" -or $item.Extension -eq $ExtFilter) {
      Copy-Item -LiteralPath $item.FullName -Destination (Join-Path $Dst $item.Name) -Force
    }
  }
}

Copy-Tree -Src (Join-Path $repo "web") -Dst (Join-Path $stage "web")
Get-ChildItem (Join-Path $stage "web") -Filter *.log -Recurse -File -ErrorAction SilentlyContinue |
  Remove-Item -Force

# Record bridge needs the stdlib-only farm_ontology package + its manifest.
Copy-Tree -Src (Join-Path $repo "farm_ontology") -Dst (Join-Path $stage "farm_ontology") -ExtFilter ".py"
Copy-Item (Join-Path $repo "vocabulary-manifest.json") $stage -Force

# 3. Explicit ignore file: gcloud would otherwise derive one from the repo
# .gitignore and could strip files the Dockerfile needs.
Set-Content -Path (Join-Path $stage ".gcloudignore") -Value "build-log.txt`n.git"

$image = "$Region-docker.pkg.dev/$Project/cloud-run-source-deploy/farm-seges-ai-web:$TagSuffix"
Write-Host "Building $image via Cloud Build..."
gcloud builds submit (Join-Path $stage ".") --project $Project --tag $image
if ($LASTEXITCODE -ne 0) { throw "Cloud Build failed" }
Write-Host "IMAGE=$image"
