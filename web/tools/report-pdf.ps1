# report-pdf.ps1 — I4: the "reports in PDF" pipeline.
# Prints a live report route to a branded PDF via Playwright's page printer.
#
# Usage:
#   pwsh -File web\tools\report-pdf.ps1                                  # biratori-1119 -> reports\biratori-1119.pdf
#   pwsh -File web\tools\report-pdf.ps1 -Url https://seges.ai/zh-TW/report -Out reports\landing-report.pdf
#
# Requires: npx playwright (browsers installed once: npx playwright install chromium).
# The report routes are public (no token gate), so no auth cookie is needed.

param(
  [string]$Url = "https://farm-seges-ai-web-451400509859.asia-east1.run.app/report/biratori-1119",
  [string]$Out = "reports\biratori-1119.pdf"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)   # repo root
$outPath = Join-Path $root $Out
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $outPath) | Out-Null

Write-Host "Printing $Url -> $outPath"
npx --yes playwright pdf $Url $outPath --paper-format A4 --wait-for-timeout 4500
if ($LASTEXITCODE -ne 0) { throw "playwright pdf failed (exit $LASTEXITCODE)" }
Write-Host "Done: $((Get-Item $outPath).Length) bytes"

