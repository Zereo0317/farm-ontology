param()
$cfg = Get-ChildItem "$env:APPDATA\xdg.config\.wrangler" -Recurse -Filter 'default.toml' -ErrorAction SilentlyContinue | Select-Object -First 1
$oauth = (Select-String -Path $cfg.FullName -Pattern 'oauth_token = "([^"]+)"').Matches[0].Groups[1].Value
$acct = '8ddbc0187e7ea54fe377dd0a5f75fb58'
$scriptPath = 'C:\Users\user\Documents\deepseek-harness\default-workspace\.tmp\seges-site-worker.js'
$name = 'seges-site-worker'

$metadata = @{
  main_module = 'seges-site-worker.js'
  bindings = @(
    @{ type = 'plain_text'; name = 'SITE_ORIGIN'; text = 'https://farm-seges-ai-landing-451400509859.asia-east1.run.app' }
  )
  keep_bindings = @('secret_text')
  compatibility_date = '2026-07-01'
} | ConvertTo-Json -Depth 5

$scriptBytes = [IO.File]::ReadAllBytes($scriptPath)
$metaBytes = [Text.Encoding]::UTF8.GetBytes($metadata)
$boundary = "----dshtake" + [Guid]::NewGuid().ToString('N')
$ms = New-Object System.IO.MemoryStream
$w = New-Object System.IO.BinaryWriter($ms)
$crlf = "`r`n"
$w.Write([Text.Encoding]::UTF8.GetBytes("--$boundary$crlf"))
$w.Write([Text.Encoding]::UTF8.GetBytes('Content-Disposition: form-data; name="metadata"; filename="metadata.json"' + $crlf))
$w.Write([Text.Encoding]::UTF8.GetBytes('Content-Type: application/json' + $crlf + $crlf))
$w.Write($metaBytes)
$w.Write([Text.Encoding]::UTF8.GetBytes($crlf))
$w.Write([Text.Encoding]::UTF8.GetBytes("--$boundary$crlf"))
$w.Write([Text.Encoding]::UTF8.GetBytes('Content-Disposition: form-data; name="seges-site-worker.js"; filename="seges-site-worker.js"' + $crlf))
$w.Write([Text.Encoding]::UTF8.GetBytes('Content-Type: application/javascript+module' + $crlf + $crlf))
$w.Write($scriptBytes)
$w.Write([Text.Encoding]::UTF8.GetBytes($crlf))
$w.Write([Text.Encoding]::UTF8.GetBytes("--$boundary--$crlf"))
$w.Flush()
$body = $ms.ToArray()

# 1. upload a new VERSION (keeps existing secret)
$resp = Invoke-WebRequest -Method Post `
  -Uri "https://api.cloudflare.com/client/v4/accounts/$acct/workers/scripts/$name/versions" `
  -Headers @{ Authorization = "Bearer $oauth" } `
  -ContentType "multipart/form-data; boundary=$boundary" `
  -Body $body -UseBasicParsing
$json = $resp.Content | ConvertFrom-Json
if (-not $json.success) { throw "version upload failed: $($json.errors | ConvertTo-Json -Compress)" }
$versionId = $json.result.id
Write-Output "version uploaded: $versionId"

# 2. deploy that version to 100%
$deployBody = (@{ resources = @(@{ script = $name; version_id = $versionId }) } | ConvertTo-Json -Depth 5)
$deploy = Invoke-WebRequest -Method Post `
  -Uri "https://api.cloudflare.com/client/v4/accounts/$acct/workers/scripts/$name/deployments" `
  -Headers @{ Authorization = "Bearer $oauth"; "Content-Type" = "application/json" } `
  -Body $deployBody -UseBasicParsing
$dj = $deploy.Content | ConvertFrom-Json
Write-Output "deploy success: $($dj.success)"

