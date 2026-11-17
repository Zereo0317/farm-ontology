# Arbitrage playbook — rails and scenario state machine (structure only)

Written 2026-11-17 (markets, task-7). This document is **structure only**:
it fixes the state machine, the permitted instrument families per state,
the leverage/premium cap TEMPLATES, and the licence + compliance rail
that governs each transition. It contains **no numerical signals, no
trigger levels, no live positions**. Human strategies populate the
templates later, only after the WS6 unlock ledger flips the feeds and
the regulatory memo (§7 of the roadmap) stands signed.

Governed by `docs/alpha-fairness-doctrine.md` §3-§5 and
`docs/legal/regulatory-perimeter.md`. Executable enforcement:
`farm_ontology/markets/rails.py` (validated in CI).

---

## 1. The state machine

Four signal states over the recorded feeds, decided by a HUMAN analyst
(no software assigns trading states — shock flags from `shock_watch`
inform, never decide):

```
                     ┌──────────────────────────────┐
   recorded feeds ──▶│ analyst review (human)       │◀── periodic re-entry
   + shock flags     │ doctrine §3 assignment        │
                     └───────┬─────────────┬─────────┘
              confident-loss ▼             ▼ confident-gain
                     ┌─────────────┐  ┌─────────────┐
                     │ BEAR path   │  │ BULL path   │
                     │ hedge own   │  │ forward     │
                     │ physical    │  │ physical +  │
                     │ book        │  │ input pre-  │
                     │             │  │ investment  │
                     └──────┬──────┘  └──────┬──────┘
                            │                │
   hazard-imminent flags    ▼                ▼
                     ┌─────────────┐  ┌─────────────┐
                     │ DEFENSIVE   │  │ HARVEST     │
                     │ de-risk +   │  │ (paired     │
                     │ farmer SOP  │  │ with BEAR)  │
                     └──────┬──────┘  └─────────────┘
                            ▼ wide uncertainty bands / ≈50-50
                     ┌─────────────────┐
                     │ VOLATILITY path │  (cost-capped options only;
                     │ STRADDLE/COLLAR │   no directional bias)
                     └─────────────────┘
```

Transitions are one-way into a hedge or TWO-WAY back to `analyst
review`; a state NEVER transitions directly into a different state
without passing review again. Every transition files a hedge ticket
(doctrine rail 3). `hazard-imminent` interrupts ANY state and has the
FIRST priority ticket queue (farmer protection outranks book pips).

## 2. State × permitted instrument families

| State | Permitted families (own book) | Rails required | Licences needed (grants/ feeds) | Governing compliance rail |
| --- | --- | --- | --- | --- |
| confident-loss | `short-cbot-soybean-futures`; `bought-puts` | R1 clause, R3 ticket, R5 truthfulness | market-data grants on every market-decisive feed; own-capital + FCM account (no licence: own account); the farmer CONTRACT carries the §4.1 clause | memo §3.2 bona fide hedge; memo §3.3 federal limits table; conduct attestations §5 |
| confident-gain | `forward-physical-commitment`; `input-supplier-investment` | R2 upside-share, R3 ticket, R5 truthfulness | buyer/seller-side consents for any farmer-sourced data; grant validity on the feeds that drove confidence | record memo: anticipation fits 17 CFR 150.1 "(ii)…or anticipates owning/producing/merchandising" leverage CAPS template §4.1 below |
| uncertain | `cost-capped-straddle`; `put-spread-collar` | R3 ticket + PREMIUM BUDGET, R5 truthfulness | options-advisory content NOT shipable to investors without registration (stay own-book); feeds grants as R5 | premium budget: cap% per quarter set by human; writeoff if cap breached (rails rejects); no directional posture |
| hazard-imminent | `reduce-open-risk` | R5 truthfulness (+emergency SOP refs) | emergency-preparedness validations same as others; farmer SOP takes the alert channel | anti-manipulation screens always on; liquidity blackout till expiry-adjacent windows |

Families not in this table do not exist; adding one = doctrine change =
Lead-approved commit (doctrine §8).

## 3. The analyst hand-off (what the dashboard emits, what the human does)

Dashboard per `shock_watch.ShockFlag`: rule id, fired-at, evidence
fact_time, observed value/text. It STOPS THERE. The human analyst reads
flags against the state machine, picks a state, and only THEN does a
PlaybookArtefact get built — which rails.py refuses unless every rail
for that state holds (fail closed on ANY grant expiry in the window:
R5 blocks all own-book reasoning the moment a market-decisive feed's
grant dies).

## 4. Cap tables (TEMPLATES — numbers set quarterly by the risk owner, human)

### 4.1 Bull-path input-pre-investment leverage CAPS

| Row | Cap name | Formula placeholder | Set by | Reviewed |
| --- | --- | --- | --- | --- |
| L1 | max notional per parcel-backed commitment | `<X% of expected harvest revenue>` | risk owner | quarterly |
| L2 | total open forward-physical exposure | `<X% of book equity>` | risk owner | quarterly |
| L3 | input-supplier financing drawn vs. buffer | `<X% of seasonal operating cash>` | risk owner + CFO when incorporated | quarterly |
| L4 | farmer upside-share floor (doctrine R2) | `≥ <neg>%` of realized gain | negotiated per contract | per contract |
| L5 | concurrent-book separation check | CONFIRMED per artefact | risk owner | per artefact |

### 4.2 Bear-path hedge-size guardrails

| Row | Cap name | Formula placeholder | Set by |
| --- | --- | --- | --- |
| H1 | max futures-equivalent per month vs physical anchored | `<X lots per <N> t physical>` | risk owner |
| H2 | all-months combined federal + exchange limit headroom | `<Y% of published Appendix E level>` | risk owner, printed per-cycle |
| H3 | put premium as % of hedged notional | `<Z%>` | risk owner |
| H4 | liquidity blackout window | `no orders within <N> business days of first notice / expiry` | standing |
| H5 | stress-margin buffer | `<M months of worst-case margin>` | risk owner |

### 4.3 Uncertainty-path premium budget

| Row | Cap name | Formula placeholder | Set by |
| --- | --- | --- | --- |
| P1 | seasonal premium budget | `<X% of hedged notional, per quarter>` | risk owner (human; agent may NOT set — rails enforces) |
| P2 | single-strategy premium sub-allocation | `<≤ X2% of P1>` | risk owner |
| P3 | collar skew tolerance | `<max cost debit as % of P1>` | risk owner |

No populated number ships until the WS6 feeds unlock AND the risk
owner signs a quarterly sheet filling these placeholders.

## 5. Licence + consent prerequisites per artefact kind

| Artefact kind | Grants/ consents required before production |
| --- | --- |
| Internal analyst memo | market-decisive feeds carry VALID grants (R5); no farmer-level data without written consent (R4) |
| Farmer-facing decision-support report | R1 verbatim clause in the text; consent grant for ANY farmer-level input; upside-share terms only on bull path |
| Trade-intent pack (hand-off to execution) | R1+R2(if bull)+R3 tickets complete; R5 grant-checks PASS at as_of; conduct attestations all TRUE |
| Public commentary | R5 only; market-decisive citations carry licence/support/error triples |

The forward-looking WS7.4 hedge-decision pack (roadmap) inherits THIS
table — it is blocked on WS6 unlocks by design (roadmap phasing: P3,
2027-01).

## 6. What this document deliberately does NOT contain

- Any price level, trigger threshold, or % move.
- Any position size, ratio, or calendar.
- Any strategy narrative for a named counterparty.
- Anything resembling personalised advice to investors (memorialised in
  `regulatory-perimeter.md` §2.2/§3.1).

Those populate AFTER: (1) WS6 unlock ledger shows `permits_financial_use
true` on the market-decisive feeds with unexpired grants, (2) the
Founder/risk-owner signs the regulatory memo, (3) the quarterly cap
sheet is filled and hashed into the trade ledger seed.
