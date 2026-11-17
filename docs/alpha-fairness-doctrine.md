# Alpha and fairness doctrine — information-advantage arbitrage on top of an honest record

Doctrine owner: Lead. Written 2026-11-17. Bindng for every agent touching
`farm_ontology/markets/`, `farm_ontology/licences/`, or any execution ledger.
Related: `decision-infra-roadmap.md` (build plan), markets'
`docs/legal/regulatory-perimeter.md` (registration boundary), licences'
`grants/punchlist.yaml` (unlock state).

## 1. The mandate, translated

Founder's directive: exploit our information advantage when we know a crop
will suffer or thrive; when outcomes are 50/50, play risk-hedging instead;
profiting when the farmer would lose is acceptable only if the farmer's loss
is not worsened by our conduct — and the system must remain lawful and
truthful throughout.

This doctrine converts that into engineering rails.

## 2. Where the advantage actually comes from

| Advantage type | Mechanism in THIS system | Why it persists |
| --- | --- | --- |
| Lead time | Multi-feed convergence recorded early (hazard watchers + Sentinel-2/VHI + WASDE cycles) | Feed recording starts at publication, not when traders read newsletters |
| Granularity | Parcel/sensor truths vs public county-level numbers | The record preserves native support — we can distinguish field truth from public proxy |
| Provability | `factsAt` point-in-time semantics + hash-chained ledgers | An auditor can replay every decision — this is the moat competitors' notebooks cannot show |

Advantage decays with every unlicensed shortcut; therefore the grants engine
(GS6) gates ALL market data reuse. No grant ⇒ no derivative-market use of the
signal. Fail closed, always.

## 3. Scenario playbooks (permitted instrument families)

| Signal state | For OUR OWN book | For the FARMER relationship |
| --- | --- | --- |
| Confident yield LOSS (hazard or sub-standard vegetative trajectory, multi-feed confirmed) | Hedge own physical exposure: short CBOT soybean futures / bought puts, sized to physical contract quantities | Deliver decision-support that LIMITS the loss (spray windows, drainage, harvest timing); disclose our hedge per §4; contract PRE-agrees our disclosure duty — never silently positioned against the grower |
| Confident yield GAIN (trajectory ahead of baseline + good finishing weather) | Pre-commit forward physical purchase; input-supplier investments (lease/financing) priced from OUR certainty | Offer the farmer the gain: input financing against contracted tons, revenue share; our leverage funds THEIR upside — alignment by design |
| UNCERTAIN (≈50/50, wide bands) | Volatility stance, NOT direction: cost-capped straddles or put-spread collars with written premium budgets (< X% of notional per season; X set quarterly by human) | Sell nothing; provide the probability map and both branches' preparations |
| Hazard imminent (typhoon/frost/heavy rain flags) | Reduce open risk in exposed instruments ahead of public panic liquidity — with strict anti-manipulation limits (§5) | Trigger the emergency SOP (actuation spec, WS5); Farmer protection outranks book pips in every tie |

Leverage and sizing obey: per-book VaR cap, stress-margin buffer, position
limits (CFTC federal speculative limits for soybean futures; exchange-level
limits), and a hard 'liquidity blackout' rule: no order flow into thin books
within N days of settlement maturity.

## 4. The fairness rails (CI-enforceable invariants)

1. **Concurrent-position disclosure**: any contract sold to a farmer must
   carry this clause verbatim: *"The Company maintains proprietary positions
   in agricultural commodities. When its data indicates materially adverse or
   favourable conditions for Your fields, the Company shall disclose the
   existence — never the size — of related positions in its periodic
   decision-support report, before the affected transaction dates."*
2. **Upside sharing on winning-knowlege plays**: when OUR confidence funds
   input investment (bull path), ≥ negotiated share of realised upside accrues
   to the farmer — the doctrine rejects pure asymmetry.
3. **No worsening conduct**: every playbook action must answer YES to "would
   the farmer still sign if they saw this hedge ticket?" — the ticket MUST be
   filed in the trade ledger regardless of signing (audit > convenience).
4. **Consent-first upward flow**: farmer-level data reaching any market-facing
   artefact requires the farmer's written grant (grants/ v2 object), with
   purpose, scope, expiry. No grant ⇒ aggregation stays anonymised.
5. **Truthfulness gates**: memo/publication tests (existing) must include the
   new rail: an artefact citing a market-decisive signal MUST ALSO cite the
   source observations' licences/support/errors, and MUST FAIL CLOSED if any
   contributing feed lost its grant.

## 5. Lawful conduct boundaries (verified perimeter lives in markets' memo)

- Proprietary trading on own account with own risk capital: generally outside
  FIEA investment-advice licensing in Japan; the moment we ADVISE (personalized,
  for reward) — license or stop. The product therefore ships
  decision-support TO OPERATORS, never personalised trade calls to investors.
- Manipulation prohibitions bind always: no spoofing, wash trading, squeezes,
  or trading to create artificial price. 'Reduce ahead of disaster' is lawful
  information reaction, not channel checks or inducing counterparties.
- Insider/embargoed regimes do not apply to public-data syntheses — but DO
  apply to anything sourced from privileged government pre-release windows;
  embargo clocks are recorded facts here, so honour them mechanically.

## 6. Execution plumbing (which subsystem actually presses buttons)

| Concern | Mechanism | Ledger |
| --- | --- | --- |
| Book decisions | human-signed order intents → broker API (Phase 3+) | Trade ledger (hash-chained; pattern reused from ontolaw DecisionLedger) |
| Farm-side actions | recommendation → human approve → ISO11783 TaskSet / drone packet | Command ledger (proposed→approved→dispatched→acked) |
| Kill switch | both ledgers recognise an emergency HALT record written by the risk owner | propagated by the runtime watchdog (WS5 gate) |

No autonomous market order execution before Phase 4 of the roadmap AND a
successful quarter of human-signed operation.

## 7. What this changes for tasks on the board

- markets (task-7): encode rails §3–§5 as executable validation functions in
  `farm_ontology/markets/rails.py` with tests: every playbook artefact must
  carry disclosure footer, premium-budget check, licence-state check; producer
  tests prove FAIL-CLOSED on grant expiry.
- licences (task-6): include the §4.1 clause in the punch-list contract pack
  as ready-to-sign text.
- infra (task-1): reserve alert channels for 'HALT raised' events.

## 8. Review cadence

Human risk-owner reviews the rails quarterly and after ANY regulatory shift in
Japan/US commodity rules. Doctrine edits require a Lead-approved commit
referencing a dated rationale in the commit message.
