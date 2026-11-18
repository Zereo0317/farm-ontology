# Task-12 (Sprint-E) X7 — one-command load test wrapper.
#
# Usage:  .\perf\run-load-test.ps1            # prod, k6 if available, else stdlib
#         .\perf\run-load-test.ps1 -Quick     # 60 s sanity pass
#         .\perf\run-load-test.ps1 -Driver stdlib
#
# Prefers k6 (perf/load-test.js + thresholds = the honest bar in-tool);
# falls back to the stdlib-threads driver (perf/load_test.py) — same
# summary shape, because the NUMBERS matter more than the tool.
# k6 exits non-zero when a threshold crosses — that IS the honest breach
# signal, and this wrapper records it as an outcome, never as a crash.

[CmdletBinding()]
param(
    [string]$Base = "https://farm-seges-ai-451400509859.asia-east1.run.app",
    [ValidateSet("auto", "k6", "stdlib")] [string]$Driver = "auto",
    [switch]$Quick
)

$Stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$Root = $PSScriptRoot
$Bar = [ordered]@{ p95_bar_ms = 400; error_bar_pct = 0.5 }

function Find-K6 {
    $cmd = Get-Command k6 -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidate = Get-ChildItem "$env:TEMP\k6-bin" -Recurse -Filter k6.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($candidate) { return $candidate.FullName }
    return $null
}

$k6 = if ($Driver -ne "stdlib") { Find-K6 } else { $null }
$results = [ordered]@{ stamp = $Stamp; base = $Base; driver = $null; exit_code = $null; summary_file = $null; verdict = $null }

if ($k6 -and $Driver -ne "stdlib") {
    Write-Host "driver: k6 ($k6)"
    $results.driver = "k6"
    $durationArgs = @()
    if ($Quick) { $durationArgs = @("--duration", "60s", "--vus", "10") }
    # native metrics dump + the handleSummary verdict land in DIFFERENT
    # files (see load-test.js note on the export/verdict collision)
    & $k6 run @durationArgs --summary-export (Join-Path $Root "k6-metrics.json") (Join-Path $Root "load-test.js") `
        --env "BASE=$Base" 2>&1 | Tee-Object -FilePath (Join-Path $Root "load-test-$Stamp.log")
    $results.exit_code = $LASTEXITCODE
    $results.summary_file = "verdict-k6.json"
} else {
    Write-Host "driver: python-stdlib-threads (k6 not found or forced)"
    $results.driver = "python-stdlib-threads"
    $vu = 50; $seconds = 300
    if ($Quick) { $vu = 10; $seconds = 60 }
    python (Join-Path $Root "load_test.py") --base $Base --vu $vu --seconds $seconds --out (Join-Path $Root "results-stdlib-$Stamp.json") 2>&1 |
        Tee-Object -FilePath (Join-Path $Root "load-test-$Stamp.log")
    $results.exit_code = $LASTEXITCODE
    $results.summary_file = "results-stdlib-$Stamp.json"
}

# Parse the summary and emit the verdict lines the deliverable quotes.
$summaryPath = Join-Path $Root $results.summary_file
if (Test-Path $summaryPath) {
    $summary = Get-Content $summaryPath -Raw | ConvertFrom-Json
    $results.verdict = [ordered]@{
        p50_ms = $summary.p50_ms
        p95_ms = $summary.p95_ms
        p99_ms = $summary.p99_ms
        error_rate_pct = $summary.error_rate_pct
        p95_within_bar = ($summary.p95_ms -lt $Bar.p95_bar_ms)
        errors_within_bar = ($summary.error_rate_pct -lt $Bar.error_bar_pct)
        breach = [bool]$summary.honest_bar.breaching
        verdict_line = if ($summary.honest_bar.breaching) {
            "BREACHED: p95=$($summary.p95_ms)ms (bar <$($Bar.p95_bar_ms)ms), errors=$($summary.error_rate_pct)% (bar <$($Bar.error_bar_pct)%) — recorded verbatim per task-12"
        } else {
            "WITHIN BAR: p95=$($summary.p95_ms)ms < $($Bar.p95_bar_ms)ms, errors=$($summary.error_rate_pct)% < $($Bar.error_bar_pct)%"
        }
    }
    Write-Host $results.verdict.verdict_line
}
Set-Content -Path (Join-Path $Root "wrapper-$Stamp.json") -Value ($results | ConvertTo-Json -Depth 4) -Encoding UTF8
exit 0  # an honest breach is an OUTCOME, not a wrapper failure
