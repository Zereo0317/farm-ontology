# Webhook alerting — generic HTTPS receiver (task-10)

Beside the always-on email channel, the project carries a RESERVED,
**disabled** webhook notification channel for future receivers (bot
triage, Slack bridge, phone push). Nothing posts to it today.

## What exists (created 2026-11-18)

| Object | Value | State |
| --- | --- | --- |
| Channel | `projects/seges-ai/notificationChannels/6614179285845624282` ("Webhook placeholder: farm alerts receiver (task-10)") | **disabled**, `type=webhook_tokenauth`, url label `https://example.invalid/farm-alerts-receiver` (a placeholder; delivery CANNOT succeed anywhere until a real receiver exists) |
| Policy | `projects/seges-ai/alertPolicies/17774814249551034582` ("HALT raised - webhook replica") | **disabled** by design, same condition as the email HALT placeholder (`custom.googleapis.com/watchdog/halt_raised`), notifying ONLY the webhook channel |

Disabled-end-to-end is deliberate: a dead `example.invalid` URL would
otherwise turn every alert evaluation into a delivery-error noise loop.

## Receiver contract (what any consumer must implement)

Cloud Monitoring POSTs JSON per notification to the channel URL:

```json
{
  "callerUrl": "...", "apiKey": null, "json": {
    "incidentId": "...", "policyDisplayName": "Uptime DOWN - farm-prod-livez",
    "state": "OPEN|CLOSED", "startedAt": "...", "endedAt": "...",
    "summary": "...", "documentation": {...}
  }
}
```

Receiver obligations (generic, receiver-author decides specifics):
respond 2xx fast (< 10 s), treat `state=CLOSED` as auto-resolution,
and for the HALT policy treat EVERY event as page-the-human priority.

## Enablement runbook (two switches, in order)

1. Stand up the HTTPS receiver accepting the payload shape above.
2. Update the channel to the real URL and enable BOTH ends:
   ```bash
   gcloud alpha monitoring channels update 6614179285845624282 \
     --project=seges-ai --update-labels=url=https://<REAL-RECEIVER> --enabled
   gcloud alpha monitoring policies update 17774814249551034582 \
     --project=seges-ai --enabled
   ```
3. Send ONE synthetic HALT metric point to prove the loop, then zero it:
   ```bash
   # timeSeries:create on custom.googleapis.com/watchdog/halt_raised value 1 -> watch webhook fire -> value 0
   ```
4. Record the drill timestamps in this file.

## Inventory note

With this channel the monitoring surface is: email (segescloud,
production uptime + HALT email placeholder + budget), webhook
(disabled placeholder pair above). Any future chat integration clones
this pattern: create channel → placeholder policy → real receiver →
enable.
