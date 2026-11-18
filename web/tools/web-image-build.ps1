#!/usr/bin/env pwsh
# WS8 helper: stage a minimal docker build context for the web app and build
# the image on Cloud Build (no local docker engine is required on this host).
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

# 2. web/ without node_modules, .next, build logs.
robocopy (Join-Path $repo "web") (Join-Path $stage "web") /E `
  /XD node_modules .next /XF "*.log" /NFL /NDL /NJH /NJS | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed with code $LASTEXITCODE" }

# Record bridge needs the stdlib-only farm_ontology package + its manifest.
robocopy (Join-Path $repo "farm_ontology") (Join-Path $stage "farm_ontology") *.py /XF "__pycache__" /S /NFL /NDL /NJH /NJS | Out-Null
if ($LASTEXITCODE -ge 8) { throw "farm_ontology copy failed" }
Copy-Item (Join-Path $repo "vocabulary-manifest.json") $stage

# 3. Explicit ignore file: gcloud would otherwise derive one from the repo
# .gitignore and could strip files the Dockerfile needs.
Set-Content -Path (Join-Path $stage ".gcloudignore") -Value "build-log.txt`n.git"

$image = "$Region-docker.pkg.dev/$Project/cloud-run-source-deploy/farm-seges-ai-web:$TagSuffix"
Write-Host "Building $image via Cloud Build..."
gcloud builds submit (Join-Path $stage ".") --project $Project --tag $image
if ($LASTEXITCODE -ne 0) { throw "Cloud Build failed" }
Write-Host "IMAGE=$image"
