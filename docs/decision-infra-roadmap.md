# Decision-infrastructure roadmap — from record to reliable, commercial, multi-agent system

Written 2026-11-17 after the merge-and-ship day (see `backend-live.md` for how
the current backend went live). This document is the plan of record. It is
written so that each workstream can be picked up by a different agent (or a
human) without context, with write scopes and acceptance criteria per
workstream.

## 0. Ground truth today (all verified live on 2026-11-17)

| Layer | Status | Evidence |
| --- | --- | --- |
| Governance/record core | ✅ green | 1068 tests; licences, `factsAt`, refusal rules, native support preserved |
| GitHub | ✅ converged | 0 open PRs; 122 merged; `main` single source |
| Backend on Cloud Run | ✅ serving | `farm-seges-ai` + `-staging`, `asia-east1`, rev 00046 / staging-00082+ |
| Live farm weather | ✅ live | `/farm/weather` JMA MSM current, Biratori 42.7018152, 142.4071291 |
| Planet scene headers | ✅ live | `/farm/planet` 250 PSScene headers, same-day zero-cloud Dove strips |
| Earth Engine | ✅ live (Screening cap) | catalog 200 via runtime identity; registration=unknown |
| Hazard feeds recorded | ✅ in repo | JMA torrential/snow/marine, USDM, two-week/seasonal headers |
| Decision advisory | ⚠️ manual | memo endpoint states rules; no engine generates recommendations |
| Actuation | ❌ none | no machine/drone/valve interface anywhere |
| Record persistence | ⚠️ ephemeral risk | `record.py` writes to local FS; container FS is ephemeral |
| Public exposure | ⚠️ unauthenticated | allUsers invoker; fine for reads, wrong for future commands |

Hard date: **the Planet trial expires 2026-12-17.** Decision checkpoint
**2026-11-30**: purchase or accept the downgrade to header-only Open Data.

## 1. Principle that must survive commercialisation

The record's honesty rules are the product. Commercial readiness means
unlocking classes by attaching real, machine-readable grants — never by
loosening the rules. Every workstream below inherits:

1. refuse when an input is missing; a gap is published, never guessed;
2. native support travels with every value; joins never rewrite support;
3. `permits_financial_use` flips only on a written grant (the "certificate");
4. `factsAt`/`associatedAt` point-in-time semantics everywhere.

## 2. Workstreams (multi-agent decomposition)

Each workstream = one shared-board task with its own write scope. Agents own
their scope; the Lead reviews diffs and runs the suite.

### WS1 · Infra hardening and reliability (agent: `infra`)

Scope: `Dockerfile`, `.gcloudignore`, `.github/workflows/*`, `deploy/`,
GCP resources. Touches nothing under `farm_ontology/agronomy` or `markets`.

| # | Deliverable | Detail | Done when |
| --- | --- | --- | --- |
| 1.1 | Durable record store | Gen-2 Cloud Run + GCS bucket volume mount (or a thin GCS dir shim) wired to the existing record-dir env seam; bucket = `farm-seges-ai-records`, versioning on | a new observation survives instance recycle; rollback test documented |
| 1.2 | Scheduled backup/export | Nightly `gsutil -m rsync`/compose of the record dir to an archive bucket; retention 90d rolling | restore drill documented and exercised once |
| 1.3 | Uptime + alerts | Monitoring uptime checks from `asia-northeast1` + secondary region on `/livez` and `/farm/weather`; alert policy → email + webhook | alert fired and acknowledged in a fault drill |
| 1.4 | Structured logs + errors | JSON request logs with request-id, latency, route; bind Cloud Error Reporting (stack traces already land in Logging) | one Error Reporting entry per fault class exists |
| 1.5 | CI gates | Workflow: unittest → `compileall` → Docker build → deploy **staging** on green main; prod deploy is a separate, tagged workflow | merge-to-prod impossible without green pipeline |
| 1.6 | Secret rotation runbook | Steps to rotate `Planet-labs` without downtime (add version → smoke `/farm/planet` → disable old); postmortem note for the 2026-11-17 `\r\n` incident | runbook in `deploy/`; drill performed |
| 1.7 | Traffic-shift gotcha codified | Helper script/flag to always `update-traffic --to-latest` post-deploy | deploy helper used for every deploy |
| 1.8 | Cost guardrails | Budget alert ¥threshold on `seges-ai`; monthly cost dump into `reports/` | first report committed |

### WS2 · Scheduled ingestion pipelines (agent: `pipeline`; depends on WS1.1)

Scope: `farm_ontology/ingest*`, `pipelines/`, new Scheduler jobs. All data
enters through the existing adapters and Store — never around them.

| # | Deliverable | Done when |
| --- | --- | --- |
| 2.1 | Weather worker | Hourly pull of `/farm/weather` content → committed as observation with availability time; dedupe by phenomenon+issue time |
| 2.2 | Planet nightly refresh | 22:00 JST daily quick-search for the farm point; new/changed scene headers appended; **alert on new acquisitions** (webhook) |
| 2.3 | Sandbox NDVI baseline (trial-window) | Weekly Sentinel-2 (Sandbox, 10 m) statistical-API NDVI at the farm cell; stored as its own 10 m support, never mixed with 5 km |
| 2.4 | JMA/USDM hazard watcher | Daily capture of the recorded-header feeds; any new warning → immediate notification channel entry |
| 2.5 | Ingest observability | Every run writes a success/failure row; three consecutive failures → alert |

### WS3 · Agronomy decision engine v0 (agent: `agronomy`; feeds on WS2 data but develops against fixtures)

Scope: `farm_ontology/agronomy/*`, its tests. The engine proposes; humans or
(Phase 4) safety-cased controllers dispose.

| # | Deliverable | Inputs required (else refuse with gap) | Output |
| --- | --- | --- | --- |
| 3.1 | Soybean phenology tracker | sowing date or emergence obs + air temps → GDD accumulation | stage class + uncertainty band |
| 3.2 | Irrigation adviser v0 | FAO-56 dual-Kc ET₀×Kc vs recorded rainfall + (optional) soil-moisture reading | mm deficit + "recommend/defer" + why; **refuses parcel-level claim without on-farm sensor** (uses grid support, honestly labelled) |
| 3.3 | Spray-window adviser | stage + wind (≥2 m/s cap) + rain window + temp bounds | GO/NO-GO windows next 48 h |
| 3.4 | Fertility planner skeleton | soil test (pending WS4 kit) → placeholder that refuses with "needs soil chemistry" until data exists | explicit gap object |
| 3.5 | Recommendation record type | every recommendation is a first-class record: inputs, licences, uncertainties, expiry | replayable; rejected uses still refused |

### WS4 · Field sensing and positioning pilot (agent: `fieldhw`)

Scope: `hardware/` docs, `farm_ontology/fieldkit` extensions. Procurement
needs human card approval — agent prepares the basket.

| # | Deliverable | Notes |
| --- | --- | --- |
| 4.1 | Sensor kit BOM | 2× capacitive soil-moisture probes (0.05 m³/m³ class accuracy), tipping-bucket rain gauge, leaf-wetness, air T/RH shield; LTE-M or LoRaWAN→gateway; unit cost logged to `reports/` |
| 4.2 | Calibration protocol | factory cal recorded + field cross-check vs gravimetric; error metric becomes the licence-grade badge that finally allows "hectare weather" claims inside sensor coverage |
| 4.3 | Ingest adapter | device JSON → CalibratedSensor observation path (existing sensor_iri/error plumbing) |
| 4.4 | Positioning upgrade | boundary walked with RTK (phone+NTRIP trial or base loan) → parcel polygon replaces point-pin; GPS accuracy recorded in metres, ending the `unknown` era |
| 4.5 | Boundary governance | polygon versioned as BoundaryVersion; the spatial-join refusal rules already protect downstream misuse |

### WS5 · Machine/actuator interface — specification first (agent: `actuation`; depends on WS4 for geometry)

Scope: `farm_ontology/actuation/*` (new). **No live machine control until
Phase 4 gate.** Design principle mirrors the record: a command is a record
too.

| # | Deliverable | Notes |
| --- | --- | --- |
| 5.1 | ISO 11783-10 TaskSet export | prescription maps (irrigation/spray zones) exported as TaskSet ZIP from polygon+recommendation; tractors/controller accept it offline |
| 5.2 | Drone spray packet | KML geofence + dosage table for the drone operator (human flies, we provide the prescription) |
| 5.3 | Command ledger spec | hash-chained (reuse the `ontolaw` DecisionLedger pattern): proposed → approved-by-human → dispatched → acknowledged; states machine-readable |
| 5.4 | Closed-loop gate definition | min-instances=1 + authN + watchdog + kill-switch contract — written down as the Phase-4 entry exam |

### WS6 · Licence certificate workflow — commercial unlock engine (agent: `licences`; independent, start now)

Scope: `farm_ontology/licences/*`, `docs/legal/*`.

| # | Deliverable | Done when |
| --- | --- | --- |
| 6.1 | Grant object v2 | machine-readable `LicenceGrant` subclasses: issuer, seat/scope, territories, purpose, expiry, evidence URL; JSON+TTL |
| 6.2 | Unlock ledger | per-feed `permits_financial_use` derived ONLY from a valid grant; expired grant ⇒ automatic demotion to Screening (fail closed) |
| 6.3 | The contract punch-list tracked as data | Planet commercial (post-trial), EE commercial registration → `permitsFinancialUse true`, Open-Meteo Q9/business tier, official JMA-derived commercial feed, drone/pesticide regs (航空法・農水省), company incorporation status |
| 6.4 | Publication texts | memo/publication generator emits per-grant attributions; audit test asserts texts stay truthful |

### WS7 · Markets/finance workstream (agent: `markets`; independent, guards和方法层)

Scope: `farm_ontology/markets/*`, `docs/legal/*`. Timeline: dashboards now;
anything resembling advice only after WS6 unlocks + legal memo signed off.

| # | Deliverable | Guardrail |
| --- | --- | --- |
| 7.1 | Point-in-time dataset builder | WASDE/AMS/FAO-FPI/industrial indices → as-of-known-then matrices (leak-proof by construction thanks to `factsAt`) — usable for backtests later |
| 7.2 | Supply-shock dashboard | threshold flags on recorded feeds → human analyst alert feed |
| 7.3 | Regulatory memo | Japan FIEA (投資助言業 boundary), US futures bona-fide hedge exemption, EU MiFID II only if customers there; conclusion: sell **decision-support to the operator**, not investment advice, until licensed |
| 7.4 | Hedge-decision pack v0 (post-unlock) | if soybeans + insured quantity + commercial data grants all valid: produce scenario tables (revenue bands vs price bands) with explicit "not advice; sign-off required" stamp |

### WS8 · Field web app hosting (agent: `web`)

Scope: `web/`, Cloud Run service `farm-seges-ai-web`.

| # | Deliverable | Done when |
| --- | --- | --- |
| 8.1 | Deploy the existing Next.js field page | hosted behind identity (Firebase/Auth0 free tier or IAP); writes go to the durable store |
| 8.2 | Mobile UX pass | one-hand recording in the field; QR "open this farm" flow |
| 8.3 | Advisories panel | render `/farm/weather`, `/farm/planet` latest, and (Phase 2+) recommendations with their uncertainty stamps |

## 3. Phasing (each phase ships user value; the Planet clock drives pacing)

| Phase | Window | Contents | Exit criteria |
| --- | --- | --- | --- |
| P0 hardening | now → 11-24 | WS1 all; WS2.1-2.2; licence punch-list started (WS6.3) | records survive recycle; alerts proven by drill; first nightly Planet delta |
| P1 automation | 11-24 → 12-15 | WS2 complete; WS3.1-3.3 live on staging→prod; WS7.1-7.2 dashboard v0 | advisers answer with stamped recommendations; NDVI 10 m baseline exists |
| **Trial checkpoint** | **11-30** | **Decide: purchase Planet plan or trial-lapse plan** | commercial decision recorded in WS6.3 ledger |
| P2 field truth | 12-01 → 12-31 | WS4 kit deployed + calibrated; parcel polygon surveyed; WS8 hosted | first calibrated on-farm sensor row in the record; accuracy ≠ unknown |
| P3 commercial spine | 01-2027 | grants signed→classes unlocked (WS6.2 flips green per feed); markets pack v0 with human sign-off (WS7.4) | every feed's licence state explicit; publication tests truthful |
| P4 actuation pilot | Q1-Q2 2027 | WS5 executed against real machines behind the Phase-4 gate | command ledger shows proposed→approved→dispatched→acked loop in drill |

## 4. Reliability targets (and how we police them)

| Metric | Target | Mechanism |
| --- | --- | --- |
| API availability | 99.5 %/月 | uptime checks + SLO burn alert |
| Weather freshness | ≤ 20 min stale, 06-22 JST | freshness check inside weather worker; breach → alert |
| Planet nightly | runs before 03:00 JST daily | scheduler + success row; 3 strikes → alert |
| Record durability | zero-loss | versioned GCS + nightly export + restore drill |
| Seed honesty | 100 % | CI test asserting every public renderer emits gap-vs-value correctly |
| Cost | < ¥10k/mo cloud pre-commercial | budget alerts + monthly report |

## 5. Risk register (top 6)

| Risk | Mitigation |
| --- | --- |
| Planet trial lapses mid-build | nightly cadence only needs header refresh; downgrade path = Open Data + Sentinel-2; checkpoint 11-30 |
| Stdlib server too hot for actuation era | Phase-4 gate requires min-instances + health-probe redesign review (FastAPI/Uvicorn allowed then; standard library fine until real connections) |
| Licence grants expire unnoticed | WS6.2 auto-demotion + expiry alarms — the system that never lies also never forgets |
| Sensor data quality scandal (uncalibrated "truth") | WS4.2 mandatory calibration protocol; unsensorised claims stay grid-labelled |
| Advice liability creep | WS7.3 memo + UI stamps; humans sign; no auto-trade by design |
| Solo-founder bandwidth | this board of tasks IS the delegation surface; Lead reviews diffs only |

## 6. Immediate next actions (this week)

1. WS1.1 durable store + WS1.3 uptime/alerts (biggest reliability wins);
2. WS2.2 nightly Planet watcher — makes the trial window maximally informative;
3. WS6.3 start the commercial punch-list (esp. EE registration + Planet quote);
4. WS3.2 irrigation v0 against fixtures (sensor-independent parts);
5. Decide Planet purchase at the 11-30 checkpoint.
