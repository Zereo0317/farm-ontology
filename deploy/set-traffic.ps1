# Post-deploy traffic pin for the farm-seges-ai services (Power twin of set-traffic.sh).
#
# WHY THIS EXISTS (the traffic-shift gotcha): on this service a --source deploy
# creates and readies a new revision but does NOT always move the 100% traffic
# tag to it (2026-11-17 ship day, backend-live.md note 2). Every deploy of the
# services MUST end with gcloud run services update-traffic <svc> --to-latest.
#
# Usage:
#   .\set-traffic.ps1                # staging, then prod
#   .\set-traffic.ps1 staging        # staging only
#   .\set-traffic.ps1 prod           # prod only
# Requires: gcloud authenticated on project seges-ai.
param(
    [Parameter(Position = 0)]
    [ValidateSet('staging', 'prod', 'all')]
    [string]$Target = 'all'
)

$ErrorActionPreference = 'Stop'
$Project = if ($env:GCP_PROJECT) { $env:GCP_PROJECT } else { 'seges-ai' }
$Region = if ($env:FARM_REGION) { $env:FARM_REGION } else { 'asia-east1' }

function Invoke-Pin([string]$Service) {
    $describe = {
        param($Fmt)
        gcloud run services describe $Service --project=$Project --region=$Region --format="$Fmt" 2>$null
    }
    $before = & $describe 'value(status.traffic[0].percent,status.traffic[0].revisionName)'
    Write-Host "== ${Service} before: percent/revision = $(if ($before) { $before } else { '<none>' })"
    gcloud run services update-traffic $Service --project=$Project --region=$Region --to-latest | Out-Host
    $after = ((& $describe 'value(status.traffic[0].percent,status.traffic[0].revisionName)') -split '\s+' | Where-Object { $_ }) -join ' '
    $latest = & $describe 'value(status.latestCreatedRevisionName)'
    Write-Host "== ${Service} after: percent/revision = $after"
    $pinned = (($after -split '\s+') | Where-Object { $_ })[1]
    if ($pinned -eq $latest) {
        Write-Host "== ${Service}: traffic pinned to latest revision ${latest} OK"
    }
    else {
        Write-Warning "== ${Service}: traffic (${pinned}) != latest (${latest}); re-check manually"
        exit 1
    }
}

if ($Target -in 'staging', 'all') { Invoke-Pin 'farm-seges-ai-staging' }
if ($Target -in 'prod', 'all') { Invoke-Pin 'farm-seges-ai' }
