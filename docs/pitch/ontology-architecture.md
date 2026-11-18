# How the farm becomes a record, and the record becomes a decision

> Content pack for the pitch pages (consumer: the page builder, task-20).
> The audience has farmed, invested, or both — not studied knowledge
> graphs. Every technical idea below is paired with one concrete farm
> example, and every claim is checkable in the repository (class names are
> the real ones in `farm_ontology/model.py` and the agronomy/actuation
> packages). Verified 2026-11-18 against `main` @ `9fba9a8`.

The one-sentence version: **farm-ontology is a record system first, and a
recommendation system second — in that order, on purpose.** Hardware can be
bought at any time; an honest record that compounds daily cannot. This page
explains what we record, how strongly each statement is allowed to be
believed, and the exact path a piece of data travels from sensor to signed,
auditable field command.

---

## 1. The record model — four families of honest facts

### Observation — *what happened*

A measurement that never travels alone. Alongside the value itself it
carries: **how** it was measured (method and version), **where** it is true
(support — see the ladder in §2), **how wrong it might plausibly be**
(error statement), and **what may legally be done with it** (licence
stamps born native, not pasted on later).

*Farm example:* "Air temperature 18.4 °C at Biratori" is not one fact but
one *bundle*: the value; support = a 5 km national weather grid (so it
describes the belt, not the plant row); error = ±0.8 °C; licence = fine to
advise with, not yet permitted in money settlement. Downstream, no clever
combination may quietly launder this reading into something it never was.

### BoundaryVersion — *where we operate*

Farmland geometry is versioned. A parcel polygon, once surveyed (RTK-walked
boundary, recorded accuracy in metres), becomes a numbered version — and a
re-walk that shifts the line creates version *two*; nothing is ever edited
in place.

*Farm example:* the north paddock's boundary becomes
`bv-2027-001`; the irrigation recommendation, the TaskSet file handed to
the tractor, and the ledger's command record all cite that exact version.
When the fence line changes next spring (`bv-2027-002`), yesterday's
documents still refer, truthfully, to the geometry they were built on.

### LicenceGrant — *what data may do*

Permissions are written records with an issuer, a scope, a set of uses, and
an expiry — plus a "specimen" flag distinguishing practice documents from
signed ones. The grant engine enforces them by arithmetic: an expired grant
demotes its uses automatically at the next tick; no human remembering is
involved anywhere.

*Farm example:* a signed grant lets market-price data flow into a
settlement calculation. The day it expires, the financial class of every
dependent answer drops, on its own, to "not permitted" — the system never
lies even when nobody is watching the calendar.

### Refusal — *the honest no* (with ErrorStatement and MethodVersion as neighbours)

"When we don't know, we don't round." A refusal is a first-class record
that names the missing input and the remedy, instead of a confident answer
built on silence. Uncertainty is recorded as a declarable ErrorStatement;
measurement methods carry versions.

*Farm example:* asked for a parcel-level irrigation number when the only
soil data is a public grid, the system answers with a refusal naming its
cause — "sensor has not declared covered hectares" — plus the weaker,
truthful grid-level statement it *can* make. A refusal you can read is a
fact you can plan around; a guessed number is a liability wearing a coat.

*(Builder note: the pitch card originally named a "ValidationRow" family
here. That class does not exist in the code; the fourth pillar is
`Refusal` — kept, because teaching the real names is the point.)*

## 2. The honest-claims ladder — how strong is this number?

Spatial support climbs exactly three rungs, and a claim inherits the
**weakest** rung of anything it used:

```
grid-support   (native N×N km — public gridded data)
  → probe-support   (instrument-point — the sensor's own footprint)
    → parcel-support (only when a sensor itself reports an area)
```

*Farm example:* two soil probes say "wet at their tips", so a probe-support
claim is "those spots are wet". The 9 km grid says the belt dried over ten
days — a grid-support claim. But "this whole 2.1 ha parcel needs 12 mm"
becomes speakable **only** when a sensor reports the area it actually
covers. Nothing declares itself parcel-level by enthusiasm.

Why an investor should care: support labels are what make the numbers
*priceable*. A buyer of advice can see, per number, what backs it — the
difference between buying measured ground truth and buying an atlas is
visible on every line, and our system never confuses the two.

## 3. The decision flow — sense → rule → gap → recommendation → signoff → command → ledger → ack

Every farm decision walks one road, and no step can be skipped — each step
may only answer "yes, with stamps" or "no, with a name":

1. **Sense** — devices and data services land as Observations through one
   front door (the sensor ingest path), already stamped with support,
   error, and licence.
2. **Rule** — deterministic agronomy computations (heat sums, water
   balances, spray physics) run over the records. Software proposes;
   arithmetic never winks.
3. **Gap / refuse** — anything missing is published as a named gap with a
   remedy. This is a *step*, not a failure state.
4. **Recommendation** — the survivors become first-class records with a
   content-derived identity (a truncated SHA-256 of their own canonical
   form — any changed byte yields a different id), an expiry, and a
   human-signoff requirement by default.
5. **Signoff** — a named human releases the recommendation for field use
   (or overtly records an operator override with the justification carried
   into the packet itself).
6. **Command** — the released decision becomes the machine artefacts: an
   ISO 11783 TaskSet file for a tractor terminal, or a geofenced dosage
   packet for a human-flown drone. Files for hands, never wireless
   whispers.
7. **Ledger** — the whole journey is appended, event by event, to a
   hash-chained command ledger: `proposed → approved (four-eyes: the
   approver must be human and not the proposer) → dispatched (with the
   handover receipt) → acknowledged (with the machine/operator receipt)`;
   emergencies write a signed HALT record that freezes the pipeline; a
   verify routine recomputes the entire chain — tampering with any byte of
   history is detectable, forever.
8. **Ack** — the closing receipt lands on the chain, and an auditor can
   replay the whole story from records alone.

*Biratori example of the whole road:* a soil probe reads dry → the water
balance says the parcel's crops drank more than the sky gave → the system
refuses the parcel-strong claim (grid weakness inherited), offers the
grid-labelled deficit instead → the recommendation record is minted, id
`rec:<32 hex>`, "irrigate 12.5 mm, expires Friday, human signoff
required" → the farm manager signs → a TaskSet ZIP is exported for the
tractor's terminal → the ledger shows proposed → approved → dispatched →
acknowledged, each with its receipt → months later, an auditor re-hashes
the chain and replays every step without asking us for anything.

## 4. The algorithms, in plain words

Each algorithm below runs on records and outputs records; each carries its
declared limits into the field.

### 4.1 Growing-degree-days (phenology)

**Does:** translates a season of daily heat into the crop's visible stage.
**How:** each day contributes its average temperature minus a 10 °C base
(nothing accumulates below growth temperature); the running sum crosses
variety-specific thresholds for each developmental stage.
*Biratori example:* during the recorded 2026 season the accumulated sum
reached 1,116.8 — crossing the profile's full-maturity threshold (R8 =
1,050 GDD for the Hokkaido short-season cultivar class), landing the anchor
farm at mature-within-window. The five-site verification graded the chain
clean-to-minor across Hokkaido belts (mismatch bands published:
+6.7…+16.8 % surplus, −14.3 % miss).
*Limits, declared:* linear in heat — no day-length (photoperiod) term, so
warm-climate seasons compress; thresholds calibrated to published Japanese
variety anchors plus the recorded season; national-trial parameters await
licensed PDF ingestion.

### 4.2 Water balance (FAO-56 dual-Kc irrigation)

**Does:** keeps the field's chequebook of water.
**How:** the atmosphere's demand (reference evapotranspiration) is scaled
by two crop coefficients — the crop's own thirst plus bare-soil
evaporation — and debited against effective rainfall and stored soil
moisture; the running balance, in millimetres, is the deficit.
*Nemuro example (the honest highlight):* the coastal site showed a
season-long structural shortfall — 40–56 % of it rebuilt by conservative
supplemental watering, totalling **78.8 mm** of honest advice, the only
site in the matrix that needed any.
*Limits:* parcel-strong claims require sensor-declared coverage; the
grid-labelled answer is labelled forever until a sensor earns it.

### 4.3 The 48-hour spray-window scan

**Does:** finds the safe hours to spray, this week, in physics.
**How:** slides an hourly lens across the next two days of forecast; a
window GOes only if wind stays under the cap, no rain arrives inside it,
temperatures sit in the product's band, and enough drying hours follow.
Otherwise NO-GO, with the reason attached.
*Worked example (illustrative arithmetic on the Biratori profile):*
afternoon forecast 2.6 m/s southerly breeze, first rain eleven hours out,
12–26 °C → GO 13:00–16:00, stamped "rain-free 9 h after window";
next morning's gusts at 7 m/s → NO-GO, reason: wind.
*Limits:* coastal gust quirks are a known measurement squint (documented
finding from the fieldtest round); thresholds travel with the product and
the label.

### 4.4 Staged-selling evaluation (the first honest backtest)

**Does:** asks whether drip-releasing harvested lots beats selling all at
once.
**How (the rule):** sell 40 % at harvest, 30 % more if price breaks
$11.40, the last 30 % after the December WASDE report — evaluated across
five prior seasons with declared data shapes, point-in-time safe.
*Result, published even though it lost:* staged selling averaged
**−$29 per hectare** versus all-at-once (−2.4 % against a $1,221/ha mean),
winning 1 of 5 seasons, worst year −$60, best +$55
(`reports/backtest-t3-REPORT.md`).
*Why we show a losing rule:* because the same rig would have published a
winner with equal enthusiasm, and because it demonstrates the finance lane
executes truthfully *before* any live money is permitted — activation
still stands behind signed human cards by design.

### 4.5 Provenance fingerprints (tamper-evidence as a habit)

**Does:** makes every durable object able to vouch for itself.
**How:** the object's canonical form (keys sorted, one serialization) is
hashed with SHA-256; recommendation ids are that hash, truncated; grants
carry fingerprints the registry must recognise before believing them; the
command ledger chains `hash(previous + this event)` from genesis onward.
*Biratori example:* the recommendation `rec:c1abaed375cf…` cited in §3 —
change a single digit of its dose and re-hash, and the id no longer
matches; an auditor's script catches the substitution without trusting a
word we say. The same replay machinery survived a deliberately recycled
container during the chaos drill: the restored chain re-verified, byte for
byte.

## 5. What this system does *not* do yet

Stated as prominently as the features: machine actuation is specification
and offline file export, behind a six-fact safety gate — no field command
has reached a real machine. Money execution does not exist; every
finance artefact is decision-support requiring human signature. All
quantitative claims inherit the season and geography of their calibration.
The honesty infrastructure exists precisely so that, when these doors
open, each opening is recorded, attributable, and reversible.

## 6. Glossary (for the page builder and translators)

| Term | Plain meaning |
| --- | --- |
| support | the geographic area a fact is truly about (grid / probe / parcel) |
| `factsAt` | the instant a fact was true-as-known — enabling exact replay of the past |
| gap | a published "we don't know", naming what's missing and what would fix it |
| grant | a written, expiring permission that says what data may be used for |
| specimen | practice/sample document — visibly not a signed grant |
| four-eyes | the rule that the human approving a command is never the one proposing it |
| HALT | a signed emergency-stop record; freezing is also on the ledger |
| hash chain | tamper-evidence: each record seals the previous one cryptographically |
| p95 | the response-time moment below which 95 % of requests finish — latency's honest middle-upper bound |
| SLO | the reliability target we publish and police (availability 99.5 %/month) |
