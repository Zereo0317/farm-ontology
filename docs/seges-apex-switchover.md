# seges.ai apex switchover record (2026-11-19)

## What changed

The apex **seges.ai** now serves the **five-locale farm landing**
(TanStack Start build of the founder's `seges-farm-landing-page.zip`,
vendored to `landing/`, commit `70b3605a`) instead of the previous
company-tools site.

Mechanism: **zero scripts were rewritten** — the long-lived edge worker
`seges-site-worker` (which fronts the apex) had its `SITE_ORIGIN`
plain_text binding swapped from
`https://seges-kadpjlgt4q-de.a.run.app` (old company site) to
`https://farm-seges-ai-landing-451400509859.asia-east1.run.app`
(the new farm landing). The `CF_WORKER_SECRET` secret_text binding was
preserved untouched. Change made via the Workers **settings PATCH
(multipart `settings` part)** — script idempotent, recorded at
`.tmp/cf-bind-origin3.ps1`.

Cloud Run side: the backend (`farm-seges-ai`, rev `00060-7bq`) now
serves `POST /leads` + `OPTIONS /leads` preflight + token-gated
`GET /leads`; the landing's `WaitlistForm`/`BriefingForm` POST leads
cross-origin with a "已收進帳本 / 已存此機" badge.

## Live verification (2026-11-19 morning)

| Check | Result |
| --- | --- |
| `seges.ai/` | 200 — Farm Ontology landing, en-negotiated |
| `/zh-TW` | 200 — 「機器把田做壞了，你還是站得住一個倉位。」`lang="zh-Hant-TW"` |
| `/zh-CN` | 200 — 机器把田做坏了… |
| `/ja`, `/th` | 200 — locale markers hit |
| old-site strings on apex | gone ("Business collaboration" absent) |
| live-ledger SSR | farm label + coordinates + temperature fields pre-rendered from our backend |
| leads E2E | preflight 204 → POST → hash `1618de7a…` → object at `gs://farm-seges-ai-records/field-notes/leads/20261118/…json` → admin read-back count=1 |
| funnel (leading off apex) | landing's internal routes `/[locale]/start` & `/[locale]/report` still 200; our deeper systems live under farm.seges.ai / run.app |

## Rollback (one command class, no redeploy)

Re-run `.tmp/cf-bind-origin3.ps1 -NewOrigin https://seges-kadpjlgt4q-de.a.run.app`
→ apex flips back to the original company site in seconds. The old site's
Cloud Run service was never touched (its direct URL is 403-restricted but
its data/deployment remains; the worker binding was the only switch).

## Collector for leads

```pwsh
curl -s -H "X-Access-Token: <web-access-token>" `
  https://farm-seges-ai-451400509859.asia-east1.run.app/leads
```

Items landing there: `pro-waitlist` (farmer funnel incl.
access-code-request), `governance-briefing` (institutional), each with
name/email/org/role/needs/locale/consent/hash/received_at.

## Notes / known imperfections

- Old company site retains NO route on the apex now. If specific legacy
  paths must survive temporarily (e.g. /tools), the worker script has a
  locale-routing block that could be extended; not done — founder said
  "replace".
- The landing's IG/QR campaign should point at `https://seges.ai` (apex)
  so Accept-Language negotiation picks the language before the user
  chooses one manually.
- Zone-level DNS has no A/AAAA records (edge worker owns the apex via
  custom domain) — nothing to update there.
