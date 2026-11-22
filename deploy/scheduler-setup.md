# WS2 scheduled ingestion — Cloud Scheduler → Cloud Run Jobs

Workstream WS2 (`pipelines/`, `farm_ontology.ingest_*`,
`farm_ontology/pipelines/hazards.py`, `tests/test_ingest_*.py`). This
document is the operational half: how the four scheduled workers reach
production, what they write, and where their alerts land.

Design in one sentence: **schedulers trigger Cloud Run JOBS** (the
`create-job` + `create-schedule` pattern proven by
[`create-observation-job.sh`](create-observation-job.sh)); every job runs
`python pipelines/run_worker.py <job>`; every artifact lands in the
durable record bucket under `pipelines/`; **the artifact IS the alert**
(no notification plumbing lives in the workers).

## 1. One-time worker image

Workers are just this repository running a different entry point. Build
and push the worker image once per ship (reuses the standard
`.gcloudignore`; `Dockerfile` already copies `pipelines/`):

```bash
gcloud builds submit --tag asia-east1-docker.pkg.dev/seges-ai/farm/farm-worker:ws2-<stamp> .
```

Alternatively the deployed SERVICE image is usable as a worker (same
layers, override entry args); pinning matters: always reference an
immutable digest or a freshly stamped tag — never `:latest` (the
traffic-shift lesson, applied to jobs).

## 2. Bind the schedules

```bash
WORKER_IMAGE=asia-east1-docker.pkg.dev/seges-ai/farm/farm-worker:ws2-<stamp> \
  ./deploy/create-schedulers.sh
```

The script deploys one job per worker and binds its schedule in
`Asia/Tokyo`. Re-running is idempotent: `jobs deploy` updates in place;
standing schedules are left untouched unless `UPDATE_SCHEDULES=1`.

## 3. The cron table (all times Asia/Tokyo)

| Job              | Cron (JST)    | Cadence | Writes |
| ---              | ---           | ---     | --- |
| `weather-hourly` | `20 * * * *`  | hourly at :20 | ≤1 new row/run (equal phenomenon-hour+values deduped); freshness ≤ 2 h |
| `planet-nightly` | `0 22 * * *`  | nightly 22:00 | new scene-id rows only (set-diff vs `state/planet-last.json`); acquisition alert per new scene |
| `hazard-daily`   | `30 7 * * *`  | daily 07:30 | the recorded JMA/USDM header rows; alert per unseen warning signature |
| `ndvi-weekly`    | `0 6 * * MON` | Mondays 06:00 | one 10 m NDVI stats row; armed only after the OAuth client exists (§6) |

Scheduling rationale: weather trails the MSM assimilation cycles past
the top of the hour; Planet after the evening strips publish; hazards
before the morning advisory cycle; NDVI before the work week. All are
deliberately off the round hour to dodge burst contention.

The crons above are also mirrored in code
(`pipelines/run_worker.SCHEDULER_CRONS_JST`) with a test asserting the
mirror; edit both sides together.

## 4. IAM and runtime

| Thing | Value | Why |
| --- | --- | --- |
| Job SA | `451400509859-compute@developer.gserviceaccount.com` | the same compute SA the services and the drill job use |
| Bucket role | `roles/storage.objectUser` on `farm-seges-ai-records` | already granted (WS1); covers `pipelines/**` automatically — REUSED, nothing new to grant |
| Invocation | `roles/run.invoker` for the Cloud Scheduler service agent (`service-451400509859@gcp-sa-cloudscheduler.iam.gserviceaccount.com`) | the agent needs it once per project to launch the jobs (usually already present when the first schedule was created) |
| Record env | `FARM_RECORD_BACKEND=gcs`, `FARM_RECORD_BUCKET=farm-seges-ai-records` | identical to the services |
| Secrets | none mounted by the workers | house rule: workers never fetch secrets. Planet/Stats API credentials stay on the read service (and §6) |

Schedules live in `asia-east1` next to the jobs; the AppEngine-cron
side of Cloud Scheduler is not used — `gcloud run jobs create-schedule`
owns the binding, retries (`max-retries=1`), and the task timeout.

## 5. Artifact layout in `gs://farm-seges-ai-records/pipelines/`

```
run-log/<timestamp>-<id>-<job>.json   one row per execution:
                                      {job, started, finished, ok, row_count, error, ...}
run-log/YYYYMMDD-<job>.json           legacy daily row; overwritten events cannot be recovered
alerts/YYYYMMDD-<job>-ALERT.json   3 consecutive failures (evidence trail inside)
alerts/YYYYMMDD-<job>-acquisitions-*.json   new Planet scene ids
alerts/YYYYMMDD-<job>-warnings-*.json       unseen hazard signatures
state/planet-last.json             scene-id snapshot the nightly diff rewinds against
state/hazard-seen-warnings.json    warning signatures already flagged
weather/|planet/|hazards/|ndvi/    the data rows themselves
```

Layout is invariant between the local and GCS backends (tests assert
it): `pipelines/run_worker.py --local-root DIR` produces exactly the
same tree a job produces in the bucket.

## 6. NDVI is mocked until the OAuth client exists (explicit)

The weekly Statistical-API call is OFFLINE by design. Real-call
prerequisites (tracked with task-6/Insights, see
`docs/backend-live.md`: "Sentinel-Hub OAuth client creation not yet
surfaced"): create the OAuth client on the Insights Platform, mount
`client_id:client_secret` in Secret Manager, then arm with:

```
FARM_SANDBOX_STAT_API=https://services.sentinel-hub.com/api/v1
FARM_SANDBOX_CLIENT=<secret-mount-name>   # holds id:secret
FARM_SANDBOX_TOKEN_URL=(optional override)
```

Until armed, the weekly run REFUSES loudly (logged failure; 3 strikes
fire the standard alert — an honest smell that the prerequisite is
late). Tests always inject the transport; nothing in CI touches the
network.

Similarly, `farm_ontology.pipelines.hazards.fetch_hazard(force=True)`
requires `FARM_HAZARD_FETCH_ENABLED=1` — the scheduled default replays
the recorded in-repo fixtures; a live header parser graduates in a
later task.

## 7. Alerts: the artifact IS the trigger (current policy)

Workers WRITE `alerts/**.json` and do nothing else — no SMTP, no
webhook, no credentials (house rules). Two consumers already exist:

1. **Humans**: `gsutil ls gs://farm-seges-ai-records/pipelines/alerts/`
   is the alert inbox; each row carries its own evidence trail
   (windowed run rows) and `suggested_action`.
2. **Infra watchdog (future)**: watching the `alerts/` prefix and
   translating standing alerts into the existing
   [`GCP_SETUP.md`](GCP_SETUP.md) channels (uptime-check email policy /
   HALT placeholder) is infra's seam; this document is the hook. A
   log-based metric on object creations under `pipelines/alerts/` plus
   the standing alert policy is the expected shape — wired by infra,
   not WS2.

## 8. Verification drills (once, after first deploy)

```bash
gcloud run jobs execute farm-worker-weather-hourly --project=seges-ai \
  --region=asia-east1 --wait
gsutil ls "gs://farm-seges-ai-records/pipelines/run-log/*-weather-hourly.json"
gcloud run jobs execute farm-worker-weather-hourly --project=seges-ai \
  --region=asia-east1 --wait     # AGAIN: row_count must read 0 (dedupe)
gsutil ls gs://farm-seges-ai-records/pipelines/state/
```

Failure drill (3-strike alert): temporarily break a worker (e.g. set
`FARM_RECORD_BUCKET=wrong-bucket` on one job) and execute it three
times; the third run must create
`alerts/<UTC-day>-<job>-ALERT.json` with the evidence trail. Restore
the env afterwards.

Status surface: `GET /farm/ingest-status` on the deployed service sums
up last runs, strikes, and standing alerts per job from the same
bucket — gaps when a job has never run.

## Readiness follow-up: execution freshness watchdog

`python -m pipelines.ingest_watchdog` checks run history, including the record
export job, against last-success age limits (weather 2 h, daily jobs/export
30 h, NDVI 8 days) and flags three consecutive failed executions. Missing,
stale, malformed or future-dated evidence is unhealthy. A successful execution
does not prove that underlying data are live or fresh; the hazards job may
replay fixtures and NDVI may not be armed. Old daily-overwritten history cannot
be reconstructed.

The runner does not send by default. `--deliver` explicitly requires a valid
HTTPS `FARM_WATCHDOG_RECEIVER`; it posts unhealthy reports and exits nonzero
on missing configuration or delivery failure. There is no silent fallback and
redirects are refused. This code is not scheduled or provisioned: configure a
receiver and credentials through the deployment's approved operational
channel, independently monitor the watchdog itself, and run a witnessed
delivery and acknowledgement drill before claiming alert coverage. Do not put
secrets in the receiver URL. The existing disabled Cloud Monitoring webhook
placeholder remains separate.
