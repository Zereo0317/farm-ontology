param()
# fetch seges-site-worker script (multipart), extract js part, save locally
$cfg = Get-ChildItem "$env:APPDATA\xdg.config\.wrangler" -Recurse -Filter 'default.toml' -ErrorAction SilentlyContinue | Select-Object -First 1
$oauth = (Select-String -Path $cfg.FullName -Pattern 'oauth_token = "([^"]+)"').Matches[0].Groups[1].Value
$acct = '8ddbc0187e7ea54fe377dd0a5f75fb58'
$out = 'C:\Users\user\Documents\deepseek-harness\default-workspace\.tmp\seges-site-worker.js'

$response = Invoke-WebRequest -Uri "https://api.cloudflare.com/client/v4/accounts/$acct/workers/scripts/seges-site-worker" -Headers @{ Authorization = "Bearer $oauth" } -UseBasicParsing
$raw = if ($response.Content -is [byte[]]) { [Text.Encoding]::UTF8.GetString($response.Content) } else { $response.Content }

# multipart: find the part whose Content-Disposition names the script
$pattern = '(?s)Content-Disposition: form-data; name="seges-site-worker\.js"[^\r\n]*\r?\n\r?\n(.*?)\r?\n--[0-9a-f]+'
$m = [regex]::Match($raw, $pattern)
if (-not $m.Success) { throw "script part not found; head: $($raw.Substring(0,300))" }
[IO.File]::WriteAllText($out, $m.Groups[1].Value, [Text.UTF8Encoding]::new($false))
Write-Output "saved $($m.Groups[1].Value.Length) chars -> $out"
