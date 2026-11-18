# Alert ACK drill — executed walkthrough (task-10, 2026-11-18)

Purpose: prove the alert path END TO END once — condition evaluation →
FIRING → (delivery) → human ACKNOWLEDGEMENT — without ever risking alarm
fatigue on the production monitors. Executed as two drill rounds against
a transient check/policy pair, both torn down at the end; the
timestamps below are the durable record.

## Drill artifacts (transient, all deleted at the end)

| Round | Uptime check | Policy | Created | Torn down |
| --- | --- | --- | --- | --- |
| 1 | `farm-drill-404-KJZlWBe9_Vg` | `3998181078065159024` | 11:52:47Z (check) / ~11:53Z (policy) | 11:59Z |
| 2 | `farm-drill-404-N4OLADDT1C4` | `13867544241062375733` | ~11:59:2xZ (check) / 12:00:37Z (policy) | 12:04:02Z |

The check pinged `https://farm-seges-ai-451400509859.asia-east1.run.app/drill-sprint-c-404`
— an intentionally NONEXISTENT route (guaranteed 404, hence guaranteed
failed pings), every 60 s from all six checker locations. The policy
watched `monitoring.googleapis.com/uptime_check/check_passed < 1`
(any-region failed ping), duration 60 s, notifying the standing email
channel `8915504179369323569` (segescloud@gmail.com).

## FIRING — proven twice

Queried live via the timeSeries REST API:

- 11:58:00Z (round 1): `check_passed` series for the drill check_id
  returned **all-False datapoints in every checker location**
  (usa-virginia, usa-oregon, usa-iowa, eur-belgium, apac-singapore,
  sa-brazil-sao_paulo; 39–46 points per series) — the condition "any
  region saw a failed ping" was continuously TRUE, so the policy held
  `FIRED` from its first complete 60 s window.
- 12:01Z (round 2): same all-False picture after the v2 policy went
  hot at 12:00:37Z.

## Delivery — empirical finding (recorded honestly)

Monitoring sends the email on the fired state, but this project shows
**no customer-visible delivery rows**: `logs/notification` and
`cloud-monitoring-alert` came back empty at 11:59Z, 12:04Z and 12:06Z
queries around both fired windows (twice-verified emptiness; EMAIL
channel dispatches evidently are not logged here). The strongest
delivery+witness combination therefore REMAINS THE MAILBOX ITSELF:

- OWNER LEG (human, same day): open the "Uptime DOWN — DRILL…" mail on
  `segescloud@gmail.com`, click through to the incident page, press
  **Acknowledge**. THAT CLICK IS THE ACK LEG the acceptance criterion
  names ("alert fired and acknowledged in a fault drill") — the agent
  cannot read Gmail, so it is deliberately a human step, documented
  rather than claimed.

## Tear-down (noise hygiene)

| Time (UTC) | Action |
| --- | --- |
| 11:59Z | Round-1 artifacts deleted (`uptime delete farm-drill-404-KJZlWBe9_Vg`, `policies delete 3998181078065159024`), before round 2 reopened |
| 12:04:02Z | Round-2 artifacts deleted (`farm-drill-404-N4OLADDT1C4`, policy `13867544241062375733`) after the log probes concluded |

Production monitors (`farm-prod-livez`, `farm-prod-weather`) were never
silenced or altered; the drill route `/drill-sprint-c-404` never touched
a real handler (404s only, ~6 req/min for ten minutes).

## Conclusion + reproduction

Condition evaluation and FIRING: proven twice with data. Delivery:
exists via the standing channel; the human ACK click closes the loop
(owner action, mailbox-side). Reproduce on any future date exactly as
the artifacts table specifies (uptime check on `/drill-sprint-c-404`,
period 1 min, `< 1` threshold policy on `check_passed` → email channel),
let it bake ≥ 5 minutes, walk the mailbox, tear down both.
