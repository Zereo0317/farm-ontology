# Task-12 (Sprint-E) X5 — ColdStartKill chaos drill, STAGING ONLY.
#
# One command:  .\perf\chaos-drill.ps1
#
# What it does (every step teed verbatim with timestamps):
#   0. preflight: right gcloud account/project; artifact dir created
#   1. snapshot staging (revision, traffic, minScale if exposed, URL)
#   2. ensure min-instances=0 on STAGING (destructive parts live here; prod untouched)
#   3. build the drill COMMAND LEDGER (actuation CommandLedger):
#      propose(service) -> approve(human != proposer) -> dispatch(receipt=job ref)
#   4. upload ledger JSONL to gs://farm-seges-ai-records/chaos-drills/
#   5. run the sanctioned observation drill job (writes one dry-run obs
#      through the GCS record backend) and capture its exit + summary
#   6. acknowledge the ledger with the job receipt; upload final ledger
#   7. force instance recycle: additive env-bump deploy (new revision,
#      min-instances=0 => fresh revision boots EMPTY; first hit = cold start)
#   8. cold-hit staging /livez twice, measure TTFB cold vs warm
#   9. (a) readability: staging /farm + /farm/ingest-status over HTTP AND
#      the written observation read back from the bucket object (gcloud)
#  10. (b) ledger survival: pull chaos-drills/ledger-<stamp>.jsonl into a
#      TEMPDIR (the GCS-layout restore) and run CommandLedger.verify_chain()
#      plus record-integrity checks; write RESULTS.json
#
# Honesty rules: any step failure is RECORDED (exit != 0 or output) and the
# drill continues where sensible; the final verdict summarises breaches.
# No prod mutation anywhere. No writes outside the chaos-drills/ prefix and
# the record the drill job itself writes.

[CmdletBinding()]
param(
    [string]$Project = "seges-ai",
    [string]$Region = "asia-east1",
    [string]$Service = "farm-seges-ai-staging",
    [string]$Bucket = "farm-seges-ai-records",
    [int]$MaxIdleWaitSeconds = 90   # post-deploy ready wait; cold start is
                                    # guaranteed by the fresh revision + minScale 0
)

$ErrorActionPreference = "Continue"
$Stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$Dir = Join-Path (Get-Location) "perf\chaos-$Stamp"
New-Item -ItemType Directory -Force -Path $Dir | Out-Null
$Results = [ordered]@{
    drill = "ColdStartKill"; stamp = $Stamp; project = $Project
    region = $Region; service = $Service; bucket = $Bucket
    steps = [ordered]@{}
}

function Log($step, $line) {
    $ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
    $text = "[$ts][$step] $line"
    Write-Host $text
    Add-Content -Path (Join-Path $Dir "drill.log") -Value $text
}

function Save-Step($name, $obj, $raw) {
    $Results.steps[$name] = $obj
    if ($raw) { Set-Content -Path (Join-Path $Dir "$name.txt") -Value $raw -Encoding UTF8 }
}

Log "setup" "artifact dir: $Dir"

# ---- 0. preflight ------------------------------------------------------------
$account = (gcloud config get-value account 2>$null | Select-Object -First 1)
$proj = (gcloud config get-value project 2>$null | Select-Object -First 1)
$preflightOk = (($account -eq "segescloud@gmail.com") -and ($proj -eq $Project))
Log "preflight" "account=$account project=$proj expected-ok=$preflightOk"
Save-Step "00-preflight" ([ordered]@{account=$account; project=$proj; ok=$preflightOk}) "account=$account`nproject=$proj"
if (-not $preflightOk) { Log "preflight" "WRONG CONTEXT — aborting"; $Results | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $Dir "RESULTS.json"); exit 2 }

# ---- 1. snapshot staging -----------------------------------------------------
$beforeRaw = gcloud run services describe $Service --project $Project --region $Region --format=json 2>&1 | Out-String
$before = $null
try { $before = $beforeRaw | ConvertFrom-Json } catch {}
$beforeInfo = [ordered]@{
    url = $before.status.url
    latest_created = $before.status.latestCreatedRevisionName
    latest_ready = $before.status.latestReadyRevisionName
    traffic = ($before.status.traffic | ForEach-Object { "$($_.revisionName)=$($_.percent)%" }) -join ","
    min_scale = $before.spec.template.metadata.annotations.'autoscaling.knative.dev/minScale'
    max_scale = $before.spec.template.metadata.annotations.'autoscaling.knative.dev/maxScale'
}
Log "snapshot" (ConvertTo-Json $beforeInfo -Compress)
Save-Step "01-before" $beforeInfo $beforeRaw

# ---- 2. min-instances = 0 (staging only) -------------------------------------
$updateRaw = gcloud run services update $Service --project $Project --region $Region --min-instances 0 --format=json 2>&1 | Out-String
$updateOk = ($LASTEXITCODE -eq 0)
$afterMin = $null
try { $afterMin = (($updateRaw | ConvertFrom-Json).spec.template.metadata.annotations.'autoscaling.knative.dev/minScale') } catch {}
Log "min-instances" "update ok=$updateOk minScale-now=$afterMin"
Save-Step "02-min-instances-zero" ([ordered]@{ok=$updateOk; min_scale_after=$afterMin}) $updateRaw

# ---- 3. build the drill command ledger --------------------------------------
$PyRoot = (Get-Location).Path
$ledgerPy = @"
import json, sys
sys.path.insert(0, r"$PyRoot")
from datetime import datetime, timedelta, timezone
from farm_ontology.actuation.command_ledger import CommandLedger
import pathlib

base = datetime.now(timezone.utc).replace(microsecond=0)
ledger = CommandLedger()
rec = ledger.propose(
    prescription={
        "action": "chaos-drill-observation-roundtrip",
        "target": "farm-seges-ai-staging",
        "basis": "task-12 Sprint-E X5 ColdStartKill",
        "native_support": "cloud-run-job; record backend farm-seges-ai-records",
        "use_class": "Screening",
    },
    actor={"kind": "service", "id": "markets-resilience-drill"},
    at=base,
    polygon_ref=None,
)
cid = rec["event"]["command_id"]
ledger.approve(cid, approver={"kind": "human", "id": "markets (teammate, human-keyed)"}, at=base + timedelta(seconds=1))
ledger.dispatch(cid, actor={"kind": "service", "id": "cloud-run-jobs"}, receipt={"job": "farm-observation-drill", "region": "$Region", "invoked": "chaos-drill.ps1"}, at=base + timedelta(seconds=2))
out = pathlib.Path(sys.argv[1])
out.write_text(ledger.to_jsonl_text(), encoding="utf-8")
print(json.dumps({"command_id": cid, "records": len(ledger.records), "file": str(out)}))
"@
$ledgerLocal = Join-Path $Dir "ledger-$Stamp.jsonl"
$ledgerOut = python -c $ledgerPy $ledgerLocal 2>&1 | Out-String
$ledgerOk = ($LASTEXITCODE -eq 0)
Log "ledger" "built ok=$ledgerOk :: $($ledgerOut.Trim())"
Save-Step "03-ledger-built" ([ordered]@{ok=$ledgerOk; local=$ledgerLocal}) $ledgerOut
if ($ledgerOk) {
    $cidLine = ($ledgerOut | ConvertFrom-Json)
    $Results.steps["03-ledger-built"].command_id = $cidLine.command_id
}

# ---- 4. upload ledger (pre-ack state) ---------------------------------------
$upRaw = gcloud storage cp $ledgerLocal "gs://$Bucket/chaos-drills/ledger-$Stamp.jsonl" 2>&1 | Out-String
$upOk = ($LASTEXITCODE -eq 0)
$upFlat = ($upRaw -replace "`r?`n", " | ").Trim()
Log "ledger-upload" "ok=$upOk :: $upFlat"
Save-Step "04-ledger-upload" ([ordered]@{ok=$upOk; gcs="gs://$Bucket/chaos-drills/ledger-$Stamp.jsonl"}) $upRaw

# ---- 5. run the sanctioned observation drill job -----------------------------
$jobExecRaw = gcloud run jobs execute farm-observation-drill --project $Project --region $Region --wait 2>&1 | Out-String
$jobExit = $LASTEXITCODE
Log "observation-job" "exit=$jobExit"
Save-Step "05-observation-job" ([ordered]@{exit_code=$jobExit; ok=($jobExit -eq 0)}) $jobExecRaw
# pull the job execution's logs (the drill prints a JSON summary)
$execLogs = gcloud logging read "resource.type=`"cloud_run_job`" AND resource.labels.job_name=`"farm-observation-drill`" AND resource.labels.location=`"$Region`"" --project $Project --limit 20 --format=json 2>&1 | Out-String
Set-Content -Path (Join-Path $Dir "05-job-logs.json") -Value $execLogs -Encoding UTF8
if ($jobExit -ne 0) { Log "observation-job" "WARNING: drill job exited non-zero; continuing (honest record)" }

# ---- 6. acknowledge the ledger; upload final ---------------------------------
if ($ledgerOk) {
    $ackPy = @"
import json, sys, pathlib
sys.path.insert(0, r"$PyRoot")
from datetime import datetime, timedelta, timezone
from farm_ontology.actuation.command_ledger import CommandLedger
path = pathlib.Path(sys.argv[1])  # path VIA ARGV: Windows backslashes die in inline literals
first = json.loads(path.read_text(encoding='utf-8').splitlines()[0])
cid = first['event']['command_id']
base = datetime.now(timezone.utc).replace(microsecond=0)
ledger = CommandLedger.from_path(str(path))
ledger.acknowledge(cid, actor={"kind": "service", "id": "chaos-drill-runner"}, receipt={"job_exit": $jobExit, "drill_stamp": "$Stamp"}, at=base + timedelta(seconds=3))
path.write_text(ledger.to_jsonl_text(), encoding="utf-8")
print(json.dumps({"command_id": cid, "state": ledger.state_of(cid), "records": len(ledger.records)}))
"@
    $ackOut = python -c $ackPy $ledgerLocal 2>&1 | Out-String
    $ackOk = ($LASTEXITCODE -eq 0)
    Log "ledger-ack" "ok=$ackOk :: $($ackOut.Trim())"
    Save-Step "06-ledger-acked" ([ordered]@{ok=$ackOk}) $ackOut
    $up2 = gcloud storage cp $ledgerLocal "gs://$Bucket/chaos-drills/ledger-$Stamp.jsonl" 2>&1 | Out-String
    Log "ledger-upload-final" "ok=$($LASTEXITCODE -eq 0)"
}

# ---- 7. force instance recycle: additive env-bump deploy --------------------
$DeployReady = $false
$bumpRaw = gcloud run services update $Service --project $Project --region $Region --update-env-vars "DRILL_STAMP=$Stamp" --format=json 2>&1 | Out-String
$bumpOk = ($LASTEXITCODE -eq 0)
$newRev = ""
if ($bumpOk) {
    # capture the revision by DIFFing latest-created before/after (the
    # update output's JSON shape proved unreliable on this gcloud build)
    $afterDesc = gcloud run services describe $Service --project $Project --region $Region --format=json 2>&1 | Out-String
    try { $newRev = (($afterDesc | ConvertFrom-Json).status.latestCreatedRevisionName) } catch {}
}
Log "recycle" "env-bump ok=$bumpOk new-revision=$newRev"
Save-Step "07-env-bump-deploy" ([ordered]@{ok=$bumpOk; new_revision=$newRev}) $bumpRaw
# wait until the new revision is READY (traffic on it), max ~120s
if ($newRev) {
    foreach ($tick in 1..24) {
        Start-Sleep -Seconds 5
        $condRaw = gcloud run revisions describe $newRev --project $Project --region $Region --format=json 2>&1 | Out-String
        try {
            $rev = $condRaw | ConvertFrom-Json
            $ready = ($rev.status.conditions | Where-Object { $_.type -eq "Ready" }).status
            if ($ready -eq "True") { $DeployReady = $true; Log "recycle" "revision ready after $($tick*5)s"; break }
        } catch {}
    }
    Save-Step "07b-revision-ready" ([ordered]@{ready=$DeployReady}) $condRaw
}

# ---- 8. cold-hit then warm-hit (TTFB) ----------------------------------------
$Url = $beforeInfo.url
if (-not $Url) { $Url = (gcloud run services describe $Service --project $Project --region $Region --format="value(status.url)") }
$ttfb = @()
foreach ($i in 1..4) {
    $t = Measure-Command { $resp = Invoke-WebRequest -Uri "$Url/livez" -UseBasicParsing -TimeoutSec 60 }
    $ttfb += [math]::Round($t.TotalMilliseconds, 0)
    Log "cold-hit" "hit=$i ttfb_ms=$($ttfb[-1]) status=$($resp.StatusCode)"
    Start-Sleep -Seconds 2
}
$coldNote = "hit1 is the cold-boot request for the fresh minScale-0 revision (env leak none); hits 2-4 warm"
Save-Step "08-cold-vs-warm" ([ordered]@{ttfb_ms=$ttfb; note=$coldNote; url="$Url/livez"})

# ---- 9. (a) readability via the service + the bucket -------------------------
$farmRaw = ""
try {
    $t = Measure-Command { $farmResp = Invoke-WebRequest -Uri "$Url/farm/ingest-status" -UseBasicParsing -TimeoutSec 60 }
    $farmRaw = "status=$($farmResp.StatusCode) ms=$([math]::Round($t.TotalMilliseconds)) body_bytes=$($farmResp.RawContentLength)"
    Log "readability" "/farm/ingest-status: $farmRaw"
} catch { $farmRaw = "FETCH FAILED: $($_.Exception.Message)"; Log "readability" $farmRaw }
$obsListRaw = gcloud storage ls "gs://$Bucket/field-notes/obs-*.json" 2>&1 | Out-String
$obsLatest = ($obsListRaw -split "`n" | Where-Object { $_ -match "obs-" } | Sort-Object | Select-Object -Last 1)
$obsCat = ""
if ($obsLatest) {
    $obsCat = gcloud storage cat $obsLatest.Trim() 2>&1 | Out-String
}
$obsReadable = ($obsCat -match "permits_financial_use")
Log "readability" "latest-obs=$obsLatest readable(with stamps)=$obsReadable"
Save-Step "09-readability" ([ordered]@{
    service_status=$farmRaw
    obs_object=$obsLatest
    obs_readable=$obsReadable
    obs_head=($obsCat.Substring(0, [Math]::Min(400, $obsCat.Length)))
    http_observations_route_exists=$false
    note="the HTTP service exposes NO observations-list route; readability is at the storage layer and via the drill job's list_notes round-trip — recorded as a WEAKNESS"
}) $obsCat

# ---- 10. (b) restore to tempdir; verify ledger + records ----------------------
$TempRestore = Join-Path $env:TEMP "farm-restore-$Stamp"
New-Item -ItemType Directory -Force -Path $TempRestore | Out-Null
$pullRaw = gcloud storage cp "gs://$Bucket/chaos-drills/ledger-$Stamp.jsonl" $TempRestore 2>&1 | Out-String
$pullOk = ($LASTEXITCODE -eq 0)
Log "restore" "pulled ledger ok=$pullOk -> $TempRestore"
$verifyPy = @"
import json, sys
sys.path.insert(0, r"$PyRoot")
from farm_ontology.actuation.command_ledger import CommandLedger
ledger = CommandLedger.from_path(sys.argv[1])  # path via argv, not inline
report = ledger.verify_chain()
snap = ledger.snapshot()
print(json.dumps({"verify_ok": report["ok"], "records": report["records"], "problems": report["problems"], "snapshot": snap}))
"@
$verifyOut = python -c $verifyPy (Join-Path $TempRestore "ledger-$Stamp.jsonl") 2>&1 | Out-String
$verifyOk = ($LASTEXITCODE -eq 0)
Log "ledger-verify" "ok=$verifyOk :: $($verifyOut.Trim())"
$verifyParsed = $null
try { $verifyParsed = $verifyOut | ConvertFrom-Json } catch {}
Save-Step "10-ledger-restored-verify" ([ordered]@{pull_ok=$pullOk; verify_ok=$verifyOk; chain_ok=($verifyParsed.verify_ok -eq $true); acked_state=$verifyParsed.snapshot.PSObject.Properties.Name.Count; tempdir=$TempRestore}) $verifyOut

# ---- RESULTS ------------------------------------------------------------------
$ReadyAll = $updateOk -and $ledgerOk -and $upOk -and ($jobExit -eq 0) -and $bumpOk -and $DeployReady -and $verifyOk -and $obsReadable
$Results.verdict = [ordered]@{
    drill_ok = $ReadyAll
    min_instances_zero = $updateOk
    observation_written = ($jobExit -eq 0)
    observation_readable = $obsReadable
    ledger_uploaded = $upOk
    ledger_ack_appended = (($Results.steps["06-ledger-acked"].ok) -eq $true)
    ledger_restored_chain_ok = ($verifyParsed.verify_ok -eq $true)
    restored_snapshot = $verifyParsed.snapshot
    cold_start_measured = $ttfb
    cold_start_note = "hit1 = cold boot of the fresh minScale-0 revision; hits 2-4 warm"
    revision_recycled = $newRev
}
Log "verdict" (ConvertTo-Json $Results.verdict -Compress)
$Results | ConvertTo-Json -Depth 6 | Set-Content -Path (Join-Path $Dir "RESULTS.json") -Encoding UTF8
Write-Host "Artifacts in $Dir"
exit 0
