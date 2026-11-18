# farm-ontology — a governed farm decision record (live)

A small, tested **decision record** for one farm operation (Biratori,
Hokkaido). It stores what was known, at which time, at which native spatial
support, under which licence, with which error mark — and which uses were
**refused**. It refuses more than it admits, on purpose: a 10 km gridded
value is never a parcel measurement, a join never rewrites support, an
expired licence demotes the feed automatically, and unknown stays `unknown`.

It does not estimate yield. It does not issue a hedge ratio, a parametric
trigger, or a nature unit. **Class C stays closed.**

Charter (four lines, enforced by tests and refusals):

1. **Stdlib-only Python** — no third-party runtime packages.
2. **Fail closed** — refuse and record; a gap is published, never guessed.
3. **No invented numbers** — native support, availability time, and an error
   mark travel with every value, or the value does not exist.
4. **Consent-first** — synthetic parties only; farmer data flows on written
   certificates (grants/); class C stays closed.

## Live system (verified 2026-11-18, project `seges-ai`, region `asia-east1`)

| # | What | Where | Address |
| --- | --- | --- | --- |
| 1 | Decision API (prod) | Cloud Run `farm-seges-ai` | https://farm-seges-ai-451400509859.asia-east1.run.app (`/livez`) |
| 2 | Staging of the same record | Cloud Run `farm-seges-ai-staging` | https://farm-seges-ai-staging-451400509859.asia-east1.run.app |
| 3 | Field web app (Next.js, gated) | Cloud Run `farm-seges-ai-web` | https://farm-seges-ai-web-451400509859.asia-east1.run.app (report: `/report/biratori-1119`) |
| 4 | Ingest workers | Cloud Run **jobs** `farm-ingest-*` + `farm-nightly-export`, fired by 5 ENABLED Cloud Scheduler entries (hourly weather, 22:00 JST Planet, daily hazard, weekly NDVI, 03:30 JST export) | — |
| 5 | Durable record store | GCS bucket `farm-seges-ai-records` (`FARM_RECORD_BACKEND=gcs`) | `gs://farm-seges-ai-records` |

Deploys: staging is automatic on green CI (`test.yml`: unit tests →
byte-compile → Docker build → staging + **traffic pin**); production moves
only via the manual `deploy-prod-tag.yml` workflow; the web app builds and
ships via `web-image.yml`. Every Cloud Run deploy must finish the
**`update-traffic --to-latest` ritual** — a `--source` deploy can create the
revision without moving traffic.

## Quickstart

Tests (Python ≥ 3.11, no third-party packages, hermetic — no network):

```powershell
$env:GCLOUD_CONFIGURATION = "segescloud"
$env:GCP_PROJECT = "seges-ai"
python -m unittest discover -s tests -t .
```

Suite state: **1686 tests, OK (14 opt-in skips)** on 2026-11-18. Live-fetch
tests stay behind `FARM_ONLINE_TESTS=1` so CI never calls the network.

Local field page + record bridge:

```powershell
cd web; npm install; npm run dev          # http://127.0.0.1:3000/
python -m farm_ontology.mcp_stdio
python -m farm_ontology.fieldkit --dry-run --out fixtures\field\dry-run-not-a-farm.json
```

Writes go to `field-notes/` (git-ignored, device-local); on Cloud Run the
same bridge writes the durable GCS store.

Deploy:

```powershell
gcloud run deploy farm-seges-ai --project seges-ai --region asia-east1 --source .
gcloud run services update-traffic farm-seges-ai --region asia-east1 --to-latest
```

Pushes to `main` do this to **staging** automatically; prod is a manual,
auditable workflow. Runbooks: `deploy/` (GCP_SETUP, rotate-planet-key,
rollback, budget, webhook-alerting, nightly-export). Web image:
`pwsh -NoProfile -File web/tools/web-image-build.ps1 -TagSuffix <tag>`
(Cloud Build; a root `--source` deploy cannot see `web/` — the repo-root
`.gcloudignore` excludes it on purpose).

## Where things are

| Path | What |
| --- | --- |
| `farm_ontology/` | the record: model, store, refusal rules, publication, query (`factsAt`), adapters, `agronomy/`, `markets/`, `licences/`, `actuation/`, `pipelines/`, `sensors/`, `fieldkit` |
| `ontology/` | local TTL (`fd-decision.ttl`); upstream ontologies are pinned, not vendored (`vocabulary-manifest.json`) |
| `grants/` | licence **certificates** (v2) + commercial punch-list + `state.json` unlock ledger |
| `web/` | the field app and public report |
| `pipelines/`, `perf/`, `hardware/`, `fixtures/` | workers, load-testing evidence, sensor kit plans, recorded test data |
| `docs/` | plan of record and ops: `decision-infra-roadmap.md` (workstreams + phasing), `alpha-fairness-doctrine.md`, `backend-live.md`, `web-ops.md`, `final-verification-report.md`, `decision-log.md` (Q1–Q21 closed switches), `legal/commercial-punchlist.md`, `field-playbook.md` / `field-sop.md` / `later-routes.md` (the walks) |

## Licence honesty — today's state (2026-11-18)

- `permits_financial_use` is **false everywhere**. Earth Engine registration
  is `unknown` (catalog reads OK via `roles/earthengine.viewer` only);
  Open-Meteo stays at the Q9 non-commercial answer; the Planet trial
  (ends **2026-12-17**, decide by **2026-11-30**) is **not** a commercial
  grant.
- `grants/` contains only **SPECIMEN** certificates (`specimen: true`). The
  evaluator refuses them with reason `specimen` — **a specimen never
  unlocks any feed**. Executed grants replace them one for one after the
  human cards clear (see `docs/legal/commercial-punchlist.md`).
- Admission rules live in the refusal engine (`farm_ontology/rules.py`);
  the unlock ledger (`farm_ontology/licences/`) can only demote, never
  loosen them.

The IRI base `https://github.com/Zereo0317/farm-ontology/ns/` stays
**provisional** until seges.ai serves the namespace (Q1). One live Open-Meteo
sample is recorded in `fixtures/live/` (jma_msm, 0.05° ≈ 5 km support); the
test suite does not call the network.

## What a memo will not say

A memo from `factsAt` can state what was knowable at a time, at what support,
under what licence, with what error mark, and which promotions were refused.
It does not state a parcel yield, a parcel rainfall, a hedge ratio, or a
nature unit. Hectare weather is unsupported unless a calibrated sensor
observation is present.

## Contact / ownership

Owned and operated by the founder (Zereo0317, gcloud `segescloud`);
module ownership and agent conventions: [AGENTS.md](AGENTS.md). Decisions
and closed switches: `docs/decision-log.md`. The card that gates every
commercial unlock: `docs/legal/commercial-punchlist.md`.
