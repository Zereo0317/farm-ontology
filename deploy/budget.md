# Budget guard — `seges-ai` (created 2026-11-18)

Goal (roadmap WS1.8): alert below ¥10k/month cloud spend before any
commercial operation. NO spend-blocking needed at this stage — alert-only.

## What exists

| Field | Value |
| --- | --- |
| Budget name | `farm-seges-ai monthly cost guard (about JPY 10k in TWD)` |
| Id | `fac1247c-bd2b-4a1b-8d4e-f1557c02f1d4` |
| Billing account | `015C1C-DA2C8B-11E228` (currency **TWD**) |
| Scope | project `seges-ai` (number `451400509859`) only |
| Amount | **TWD 2,000 / month** (calendar MONTH, all credits included) ≈ ¥10,000 |
| Thresholds | 50 % (TWD 1,000 ≈ ¥5k) and 90 % (TWD 1,800 ≈ ¥9k), CURRENT_SPEND |
| Notifications | Monitoring channel `2125437968708098086` ("Budget alerts - hyuchen869", email) via `schemaVersion 1.0` |

Verification:

```bash
gcloud billing budgets list --billing-account=015C1C-DA2C8B-11E228 \
  --format="value(displayName,budgetAmount,budgetFilter.projects,thresholdRules)"
```

## How it got here (worth knowing next time)

1. `gcloud billing projects describe seges-ai` → billing account
   `015C1C-DA2C8B-11E228`, billing enabled.
2. `gcloud billing accounts describe <acct>` revealed the currency is **TWD**,
   not JPY: a naive `--budget-amount=10000` would have guarded at
   ≈ ¥47k (5× looser than intended). First budget was deleted and
   recreated at TWD 2,000 ≈ ¥10k.
3. Plain `gcloud billing budgets create` cannot attach the project filter
   nor a notification channel (it landed unfiltered across ALL projects on
   the account — deleted). The create was redone through the
   `billingbudgets.googleapis.com/v1` REST API with:
   - `budgetFilter.projects=["projects/451400509859"]`
   - `notificationsRule.monitoringNotificationChannels=["projects/seges-ai/.../2125437968708098086"]`
   - header `X-Goog-User-Project: seges-ai` (the API otherwise rejects
     user-credential calls without a quota project).
4. Intermediate unfiltered budget deleted; final state re-listed and
   verified (exactly one seges-ai-scoped farm budget remains).

## Blocked-by-IAM?

NONE. Creation, filtering and channel attachment all succeeded with the
`segescloud@gmail.com` billing-admin path. (A pre-existing manual budget
"seges-ai (50%=3.5usd/day soft, 100%=7usd/day HARD)" also watches this
project; both coexist harmlessly — that one watches USD burn rates, ours
the ¥10k guardrail.)

## Monthly report duty

First cost dump into `reports/` is owed by the NEXT infra touch (cron the
Cloud Billing "BigQuery export" or run
`gcloud billing accounts list` + billing reports export manually); this
task created the guard but did not generate a cost report.
