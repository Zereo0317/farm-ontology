# Planet API key rotation runbook (`Planet-labs` secret)

Owner: infra · Scope: `seges-ai` project · Last reviewed: 2026-11-17

The Planet trial key lives in Secret Manager as `Planet-labs` and reaches the
services (`farm-seges-ai`, `farm-seges-ai-staging`) as `PLANET_API_KEY`
(`secretKeyRef`, "latest"). Because the container reads the secret reference at
boot, rotating is **redeploy-free on the key material** but **needs a revision
restart per service to pick up a new version** unless the services are already
pointed at "latest" and you bounce them (below), or you accept a scheduled
bounce inside the next maintenance window.

Goals: no downtime, no secret ever in git/logs/shell history, smoke both the
happy path and the 401/403 fingerprint before retiring the old version.

## 0. Preconditions

- Console access to the Planet Insights Platform account that owns the
  subscription (`zereo0317@gmail.com`; account id `34a96e83-bf8c-4002-b5e1-7c2757d6500b`).
- `gcloud` authenticated as `segescloud@gmail.com` on `seges-ai`.

## 1. Mint the new key (Planet console)

1. Log in → Insights Account → Settings → API keys.
2. **Add** a new key (do not revoke the old one yet).
3. Leave the browser tab open; you will paste the value once, directly into
   Secret Manager (step 2). Do not email/chat/download it.

## 2. Add the secret version — the UTF-8, no-CRLF way

2026-11-17 incident root cause lived here: the key was piped through a
PowerShell pipeline and arrived with a trailing `CRLF` (`\r\n`); the HTTP
`Authorization: Basic ...\r\n` became invalid mid-request and `/farm/planet`
degraded to a gap object while the previous revision kept serving. Lesson:
**always write secret files with `[IO.File]` UTF-8 no-BOM, never pipeline raw
bytes through PowerShell cmdlets**, and verify the byte length before upload.

```powershell
# Paste the key into a file without any line-ending mangling:
$key = Read-Host -MaskInput 'paste planet api key'
[System.IO.File]::WriteAllBytes("$env:TEMP\planet.key", [System.Text.Encoding]::UTF8.GetBytes($key))

# VERIFY before uploading: byte count must equal the key length exactly,
# no trailing 0D 0A, no BOM (EF BB BF):
$b = [System.IO.File]::ReadAllBytes("$env:TEMP\planet.key")
"$($b.Length) bytes; tail: $($b[-3..-1] | ForEach-Object { '{0:X2}' -f $_ })"
# Expect: <len> bytes; tail: ends with an ASCII printable char (41..7A), NOT 0D 0A, not EF BB BF.

gcloud secrets versions add Planet-labs --data-file="$env:TEMP\planet.key" --project=seges-ai
Remove-Item "$env:TEMP\planet.key"
```

Never print the full value; the byte-length + tail check is sufficient proof
of shape. If the key arrives wrapped (line breaks inserted by the console),
strip them BEFORE the byte check — a wrapped key is already unusable.

## 3. Smoke the new key BEFORE cutting over

Because services read "latest", a bounced revision picks the new version:

```bash
# staging first: force a fresh revision boot
gcloud run services update farm-seges-ai-staging --project=seges-ai \
  --region=asia-east1 --set-env-vars SERVICE_VERSION=planet-rotation-"$(date +%Y%m%d%H%M%S)" >/dev/null
./deploy/set-traffic.sh staging
curl -fsS "https://farm-seges-ai-staging-451400509859.asia-east1.run.app/farm/planet" | head -c 300
# Expect: scene headers JSON (250-scene family). On failure the endpoint returns
# a gap object mentioning the HTTP status: 401/403 fingerprint = bad/foreign key.
```

Known fingerprint (from the pre-trial v1 key era): account probe 403 +
Data search 401 == key belongs to an account without an active subscription.

## 4. Cut over prod, retire the old version

1. Repeat the bounce + smoke on `farm-seges-ai` (prod), then
   `./deploy/set-traffic.sh prod`.
2. Only after BOTH smokes are green: disable (do not delete yet) the old key
   in the Planet console, wait one full check cycle, then delete it.
3. Record the rotation in the audit trail (`docs/backend-live.md` audit
   table): date, who, secret version number, smoke timestamps.

## 5. Rollback

If the new key misbehaves before the old one was disabled: flip the console
(old key re-enable), re-add it as a new secret version, bounce revisions
again. Duration ≈ one revision boot (~1 min). If the OLD key is already
gone: gather it from the Planet console restore/API-support path — treat as
an outage, announce via the alert channel.

## Drill record (drill performed 2026-11-17)

- Added a NO-OP secret version exercise during the `\r\n` incident repair
  (same-day), smoke checked staging + prod `/farm/planet` responses.

## Postmortem — 2026-11-17 `\r\n` secret incident

**Symptom.** After storing a working Planet key as Secret Manager version
`Planet-labs` v3 (activated that morning with the trial), requests via
`/farm/planet` degraded: the endpoint returned explicit gap objects while the
otherwise-healthy revision kept serving. Direct API probes intermittently
succeeded, then failed with signature oddities.

**Root cause.** The key value had been captured by PIPING console output
through PowerShell (`gcloud secrets versions add ... | ` variants and
`Out-File`-based capture). PowerShell pipelines append `CRLF` (`\r\n`) line
terminators on Windows, and the trailing `\r\n` became part of the secret's
byte payload. The upstream HTTP layer builds `Authorization` headers from the
raw bytes; a trailing CRLF inside the credential broke request framing in a
way that looked like flaky 401/403s rather than a malformed secret.

**Repair (same day).** Re-imported the key byte-exactly via
`[System.IO.File]::WriteAllBytes` with UTF-8 no-BOM, verified with a byte
tail check (no `0D 0A`, no BOM), added as a fresh secret version, smoked on
staging, then prod. `/farm/planet` restored: 250 PSScene headers, same-day
zero-cloud strips.

**Lessons (binding for future rotations).**
1. Secrets are FILES on Windows: write them with
   `[System.IO.File]` + UTF-8 **no BOM**, never capture via pipeline/`Out-File`.
2. ALWAYS verify the byte length and tail bytes before
   `gcloud secrets versions add` — a 2-byte excess is a silent outage.
3. Smoke staging before prod; keep the old key enabled until both smokes pass
   (this runbook §4 ordering exists because of this incident).
4. Degradation was graceful (gap object, no invented values) — the record's
   honesty rules did exactly their job; the incident was recoverable, not a
   data-integrity event.
