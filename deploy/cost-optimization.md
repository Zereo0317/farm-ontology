# GCP cost optimization — Sprint-I (task-16, 2026-11-18)

Executed by infra. Scope: the FARM estate only (`farm-*` services, jobs,
images, monitors, records) on project `seges-ai`. Constraint honored:
zero availability impact; no secrets/tokens/domains touched. The other
estates sharing the project (noesis-*, verify-*, trust-*, kairos-*) are
out of scope and UNTOUCHED, except where a project-global surface
(the `_Default` log sink) got one narrowly-filtered exclusion.

## 1. Inventory — current month (2/3 through November)

Billing-export availability: **NO BigQuery billing export is wired**
(`bq ls` shows no cost datasets). Therefore the numbers below are
CONFIG+USAGE-DERIVED ESTIMATES from gcloud metering, priced at
asia-east1 list rates (Cloud Run request-based: ~$0.24 vCPU-h /
~$0.025 GiB-h; AR $0.10/GB-mo; Logging first 50 GiB/mo free;
Logs retention 30 d free bucket; Secrets $0.06/version- mo). Currency:
the billing account bills in **TWD**; ¥ conversions at ballpark.

| Surface | Config (verified 2026-11-18) | Est. TWD/mo (≈¥) | Basis |
| --- | --- | --- | --- |
| Cloud Run `farm-seges-ai` (prod) | cpu **2**/512Mi (rev 00057-2lz), maxScale 3, min 0, request-based, LOW traffic | 20–50 (¥100–250) | mostly scale-to-zero; spike seconds ×2 cpu after the postfix round |
| Cloud Run `farm-seges-ai-staging` | cpu 1/512Mi, min 0 | 5–20 (¥25–100) | lighter |
| Cloud Run `farm-seges-ai-web` | 1/512Mi, cc 80, min 0 | 5–20 (¥25–100) | idle-most |
| Cloud Run JOBS (6: export, drill, ingest×5 minus workers, probe-egress) | all **1 vCPU/512Mi**, 1–2 min/day each | 2–5 (¥10–25) | per-second while executing, short-lived |
| Artifact Registry `farm` | was 5 images (~0.75 GB) → **4 after prune** (~0.6 GB) | ~2 (¥10) | $0.10/GB-mo |
| Cloud Build | ~25–40 builds this month × ~15 s | ~1 (¥5) | regional build minutes, seconds-long |
| Cloud Logging (farm services) | measured **3.0 MB/day** ⇒ ~90–100 MB/mo — deep inside the 50 GiB FREE ingestion; _Default retention 30 d | ~0 today (¥0) | free tier; grows with traffic+checks |
| GCS records bucket | versioned, few KB live, small archive | ~0.1 (¥0.5) | sub-GB |
| Monitoring | 3 uptime checks (≤10 free tier), 5 alert policies, 2 channels | 0 (¥0) | free allotment |
| Scheduler | 3 farm schedules (weather/planet/hazard) + ndvi + export = 5 (3 free) | 0–1 (¥0–5) | $0.10/job over 3 |
| Secret Manager | ~4–6 active versions (web token, Planet, misc) | ~5 (¥25) | $0.06/version-mo |
| Networking egress | KB–MB/day JSON APIs | <2 (¥10) | no CDN/media egress |
| **FARM ESTATE TOTAL (estimate)** | | **≈ 40–65 TWD/mo (≈¥200–320)** | |

Budget adequacy: guard = **TWD 2,000/mo (≈¥10k)** → utilization ≈ 2–3 %.
VERDICT: ADEQUATE — comfortable headroom through commercial launch.
NOT in the GCP bill (documented as such): Planet trial (lapses 12-17),
Open-Meteo free tier, Earth Engine Screening.

Material telemetry gap, honestly recorded: without a billing export
the estimates above cannot be reconciled against the invoice until the
human console is checked. Wiring the BigQuery export (dataset +
schedule) is the ONE structural follow-up that makes this a real
ledger instead of an estimate; it adds its own small BQ cost and is
deferred to lead (see §3).

## 2. Right-size review (per the card)

| Candidate | Finding | Action |
| --- | --- | --- |
| Job machine types | every farm job = 1 vCPU/512Mi; all run 1–2 min/day. NOT obviously fat | DEFER right-sizing: 512→256 Mi saves ≈ TWD 1/mo but risks OOM on the compose-heavy export (tar built in RAM grows with the record); revisit when record > ~50 MB or jobs fail |
| min-instances | all 0 — correct posture pre-commercial (idle cost ≈ 0); a min=1 prod warms tails at REAL idle cost (latency lever, not a cost lever) | NO CHANGE (latency decision stays with lead+founder, cf. RESILIENCE-REPORT-postfix) |
| Log retention (_Default) | 30 d = the standard, FREE — paid tiers only matter above 30 d/1 TB | NO CHANGE |
| Cloud Build frequency | ~1 build/day of work, seconds each | NO CHANGE |
| Budget thresholds | TWD 2,000 vs est. 40–65 actual | KEEP; 50 % threshold ≈ ¥5k still signals true anomalies |
| Container CPU/memory (services) | prod got cpu=2 for latency this week; reverting would LOWER cost but REGRESS the tail-latency decision owned by lead | NO CHANGE here |

## 3. Savings ledger (¥-converted where useful) — APPLIED vs DEFERRED

| # | Lever | Est. saving/mo | Risk | Decision |
| --- | --- | --- | --- | --- |
| 1 | Log-exclusion filter `probe-noise-reduction` on the `_Default` sink (`httpRequest.userAgent=GoogleStackdriverMonitoring OR httpRequest.requestUrl="/livez"`) | ≈ TWD 0.3 today (¥1.5), BUT prevents LINEAR growth: every added uptime check/route stacks probe lines permanently (would be ~TWD 1–3/mo by end of quarter) | ~ZERO: uptime METRICS are computed by the checkers, not from logs; alerting unaffected (policies read `uptime_check/*` metric types). Verified live post-apply | ✅ **APPLIED** (project-global sink, narrowly filtered) |
| 2 | Artifact Registry prune — delete the OLDEST unreferenced drill image (`drill:obsdrill-20261117`, digest `5dd19230…`) | ≈ TWD 0.2–0.4 (¥1–2)/mo at this pace | ~ZERO: only the oldest of FOUR drill tags deleted (keeping the last 3 per card: b/c/d); the live drill job references `obsdrill-20261117d` — re-verified its image field after deletion | ✅ **APPLIED** |
| 3 | Job memory right-size (512→256 Mi) | ≈ TWD 1 (¥5) | OOM risk on ram-built tar export as the record grows | 🔶 DEFERRED — revisit at record > 50 MB |
| 4 | BigQuery billing export wiring | enables REAL actuals (savings = decision quality, not dollars; BQ cost itself ≈ TWD 1–3/mo) | requires BQ dataset + SA perms (lead's console) | 🔶 DEFERRED to lead — the one structural follow-up |
| 5 | min-instances=1 on prod | COST NEGATIVE (raises idle spend); buys tail latency | latency lever | ➖ OUT OF SCOPE here (lead+founder own it per RESILIENCE-REPORT-postfix) |
| 6 | Retention/budget/build-frequency tuning | ≈ 0 (already free-tier optimal) | — | ➖ NO CHANGE |

Applied total impact: **est. TWD 0.5–0.7/mo (≈¥2–3) directly, plus
growth-rate insurance on logs and images.** The honest headline: the
estate is ALREADY cheap (~TWD 40–65/mo, 2–3 % of budget) — the value
of this pass is the verified posture + growth containment, not money
found today.

## 4. Zero-impact evidence

- Probe noise lives only in LOGS; uptime checks (`farm-prod-livez`,
  `farm-prod-weather`) and their alert policies read the
  `monitoring.googleapis.com/uptime_check/*` metrics — verified the
  policies' filters post-change (unchanged).
- The deleted AR image was verified unreferenced: farm-observation-drill
  pins `obsdrill-20261117d`, farm-nightly-export pins the `farm-worker`
  tag (untouched), services were never referenced to the drill repo.
- No service config, revision, secret, schedule, or IAM change in this
  sprint (only the log-sink exclusion list and one image deletion).

## 5. Repeat/heal commands

```bash
# sink exclusion (idempotent to re-add):
gcloud logging sinks update _Default --project=seges-ai \
  --add-exclusion='name=probe-noise-reduction,filter=httpRequest.userAgent=GoogleStackdriverMonitoring OR httpRequest.requestUrl="/livez"'
# image inventory + prune (delete OLDEST unreferenced tags only):
gcloud artifacts docker images list asia-east1-docker.pkg.dev/seges-ai/farm --include-tags
# measured log volume sanity (2-day window):
#   timeSeries query on logging.googleapis.com/byte_count, resource.type=cloud_run_revision
```
