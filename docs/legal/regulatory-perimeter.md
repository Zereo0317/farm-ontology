# Regulatory perimeter — markets (WS7), concluding the operating model

Written 2026-11-17 by the markets workstream (task-7). Owner: Founder /
company legal contact. Binding for `farm_ontology/markets/`, the WS6
contract pack, and any execution ledger. Related: `docs/alpha-fairness-doctrine.md`
(the doctrine this memo implements legally), `docs/decision-infra-roadmap.md` WS7,
licences teammate's `grants/` punchlist (referenced, not reimplemented here).

Status of this document: it is engineering-adjacent legal REASONING, not
legal advice, and items marked **VERIFY** were reasoned from the statutes
named below without a lawyer's confirmation in the room. The verified
primary-source quotes in §3 were pulled from the eCFR API and the Federal
Register API on 2026-11-17 (links at §7). Japan statute internals in §2
carry the traditional citation form and **VERIFY** tags.

---

## 1. The concluded operating model (the sentence that governs)

**We sell decision-support to agricultural operators and run proprietary
hedging on our own book. We do not provide personalised investment
advice to investors, and we will not, until and unless a registration
analyzed below is actually obtained and signed off by counsel.**

Three concentric consequences:

1. **The product lane** (analytics, advisories panels, supply-shock
   flags, agronomy advice) speaks to the operator ABOUT THE OPERATOR'S
   FIELD and the operator's own physical production/handling decisions.
   It never recommends the purchase or sale of a listed instrument for
   the reader's account, and it carries "not investment advice" stamps
   wherever a number meets a price outlook.
2. **The book lane** trades listed instruments only for the company's
   own account, own risk capital, own sizing. Doctrine §3 governs the
   rationales; this memo governs the legality posture.
3. **The line between the lanes** is the whole compliance problem. The
   clauses in §6 and the rails in `farm_ontology/markets/rails.py` are
   the engineering guardposts on that line.

Until an affirmative step registers us in a given regime, the default
in EVERY lane is: describe, measure, prepare — then a human signs.
No automated order, no discretionary trading for others, no advice.

---

## 2. Japan — the FIEA 投資助言業 boundary (where we stop)

### 2.1 The test we designed the product against

金融商品取引法 (FIEA, Act No. 25 of 1948, as amended) — **VERIFY all
article cites below with 弁護士 before any filing**:

- FIEA defines 投資助言業 inside 投資助言・代理業 (FIEA art. 28(2)): a
  business that, **for remuneration and under a contract**, gives
  advice on the **investment judgment** of another person concerning
  the value of 有価証券 or related derivatives, their interest rates,
  currency prices, or market conditions, and does so continuously as
  a business. Conducting it requires registration (FIEA art. 29(1)).
- Three cumulative ingredients trigger it: (a) consideration,
  (b) a contracting arrangement, (c) advice on investment judgment
  over securities/related derivatives. Cooking advice, agronomy, and
  "your field" physics fail (c) even when priced.

### 2.2 Why the current product stays outside

| Product element | Sits inside or outside the test | Reason |
| --- | --- | --- |
| Agronomy advisories (irrigation, spray windows, phenology) | outside | advice on farming, not on instruments; ingredient (c) absent |
| Harvest-timing and selling-window commentary over PHYSICAL crop | outside | judgment on the farmer's own physical commercial activity; no securities/derivative subject matter |
| Supply-shock dashboard (this repo) | outside | publication of recorded-fact states; no addressee's account, no personalised call |
| Proprietary hedging on CBOT from OUR data | outside 投資助言業 | own account, no advice given to anyone; risk logic is ours |
| "Buy/sell these futures for you" newsletters sold to investors | **INSIDE — do not ship** | consideration + investment-judgment advice, personalised |
| Paid personalised portfolio calls for investors | **INSIDE — do not ship** | same, plus discretion risk |

The working rule encoded in `rails.py` (R5/conduct attestation
`conduct/advice-gate-off`): no artefact routes a personalised trade
call to an investor.

### 2.3 The registered routes (only if the line is crossed deliberately)

If any product element crosses §2.2's boundary, registration happens
BEFORE shipping, via one of (**VERIFY route mechanics**):

- **第一種金融商品取引業** — Cabinet-Office licence through the finance
  bureau (免許 route); needed for first-class instruments.
- **第二種金融商品取引業 / 投資助言業登録** — registration route: register
  via an association (協会, practically 日本証券業協会 (JSAA)) or
  directly with the Prime Minister's office where no covering
  association route applies (FIEA art. 29; association-registration
  mechanism in the cabinet ordinance on 関係内閣府令); the 二種 route
  is the realistic one for a pure 投資助言業 shop.
- **商品先物取引法 side-note**: bespoke advice to Japanese clients on
  COMMODITY derivatives (e.g., 商品先物) historically lives under the
  commodity-derivatives regime (商品投資顧問業 registration, 農林水産省 /
  経済産業省), not FIEA. Our CBOT hedges are the company's OWN
  positions, so no Japanese licence attaches to them as such; the
  moment we replicate them "for" a client, that analogue regime
  becomes the relevant check. **VERIFY** which registration the first
  marketed product actually needs, before marketing it.

Bottom line: **we default to the unregistered posture. Any change
requires counsel sign-off + a licence-state flip in the grants/ ledger,
never a doc tweak.**

### 2.4 前払式料販 (prepaid payment instruments) — residual risk assessed NIL

資金決済法 (Payment Services Act) regulates issuers of 前払式支払手段
(prepaid instruments) usable repeatedly for payment for services: when
we COLLECT money in advance and leave a stored value standing against
future service delivery, issuance notices, deposit duties, 半額返還
rules, and 基準日残高 publicity can bite.

The operating model collects **after** performance (invoice-in-arrears
subscription). Standing constraints, which keep the residual risk at
NIL and live as a punch-list line (WS6 §6.3 analogue):

> We never (i) issue a stored-value certificate redeemable against
> our services, (ii) collect more than two months of subscription in
> advance, or (iii) resell transferable prepaid instruments. Breaking
> any of the three switches the prepaid question back ON and requires
> 資金決済法 analysis with counsel before invoicing changes.

**VERIFY** (with counsel, once any prepayment plan exists): the
remaining-term refund rules and the 基準日残高 thresholds for our
sales channels.

### 2.5 保険募集 note (founder-boundary watchpoint, not our product)

We do not solicit insurance. If advisory conversations ever drift into
insurance products, the 小口募集/代理店 licence question opens and this
memo must be revisited. Out of scope until then.

---

## 3. United States — CFTC / NFA posture for own-account ag hedging

Verified sources: eCFR API fetches of 17 CFR 150.1 and 150.2 and the
86 FR 3465 / Doc 2020-25332 final rule text (URLs in §7). This is the
best-verified section of the memo.

### 3.1 Own-account hedging: no CPO/CTA registration

Under the CEA and 17 CFR 1.3, a **commodity trading advisor** is a
person who, for compensation or profit, advises OTHERS as to the value
of or advisability of trading in commodity futures/options/swaps, or
regularly issues analyses of the same as a business. A **commodity
pool operator** pools others' funds. The company hedging its own
physical and book exposure with a futures commission merchant is
neither: no customer money, no third-party advice. NFA membership
obligations arrive with CTA/CPO status — which we intentionally do not
hold. **Therefore: publishing ANY subscribers' advisory sheet about
futures trading flips us toward CTA territory — the same line as §2.2's
"do not ship" rows, mirrored on the US side.**

Algorithmic assistance in placing our OWN orders is not a registration
matter (no customer); the compliance-relevant screens are conduct
screens (anti-manipulation, CFTC rule on improper practices,
spoofing prohibition in CEA §4c(a)(5)) — enforced, per doctrine §5,
by the attestation `conduct/no-manipulation` before any playbook fires.

### 3.2 Bona fide hedging — the exemption our physical book rides on

17 CFR 150.1 (verbatim, fetched 2026-11-17):

> "**Bona fide hedging transaction or position** means a transaction or
> position in commodity derivative contracts in a physical commodity,
> where: (1) Such transaction or position: (i) Represents a substitute
> for transactions made or to be made, or positions taken or to be
> taken, at a later time in a physical marketing channel; (ii) Is
> economically appropriate to the reduction of price risks in the
> conduct and management of a commercial enterprise; and (iii) Arises
> from the potential change in the value of—(A) Assets which a person
> owns, produces, manufactures, processes, or merchandises or
> anticipates owning, producing, manufacturing, processing, or
> merchandising; (B) Liabilities which a person owes or anticipates
> incurring; or (C) Services that a person provides or purchases, or
> anticipates providing or purchasing…"

Practice notes the rule-writing adds: **enumerated bona fide hedges**
(Appendix A to part 150) are self-effectuating; non-enumerated ones
ride the §150.3 / §150.9 recognition process through a DCM; and the
anticipatory (forward-physical) case our bull playbook relies on is
expressly contemplated by "positions taken or to be taken" +
"anticipates owning, producing … or merchandising". Every hedge ticket
in `rails.py` therefore records its physical-anchor statement —
which physical exposure the derivative substitutes for — BEFORE firing.

### 3.3 Speculative position limits — CBOT soybeans, the table we obey

- The operative regulation is **17 CFR 150.2** with levels in
  **Appendix E to part 150**; the levels were reset by the final rule
  "Position Limits for Derivatives", **86 FR 3465 (Jan. 14, 2021)**.
- Mechanism (verbatim from the final rule): *"Federal spot month
  position limit levels are set at or below 25 percent of estimated
  deliverable supply, whereas Federal non-spot month limit levels are
  set at 10% of open interest for the first 50,000 contracts of open
  interest, with an incremental increase of 2.5% of open interest
  thereafter."*
- The regulatory table of levels: the CFTC publishes the mirrored
  "Position Limits" table under Industry Oversight, Trading
  Organizations (https://www.cftc.gov/IndustryOversight/TradingOrganizations/index.htm —
  its server refused automated access from this build environment, so
  the URL is cited without numbers); the authoritative machine-readable
  current text of the SAME table is
  <https://www.ecfr.gov/current/title-17/part-150/appendix-Appendix%20E%20to%20Part%20150>.
- **Desk rule:** before the first soybean futures order, the risk owner
  prints the current CBOT soybean federal spot / single-month /
  all-months figures from that table into the execution plan, together
  with the exchange-level limits CME imposes (exchange limits cap at or
  below the federal levels for the legacy agricultural contracts), and
  the hedge ticket records them. rails.py does NOT hardcode the
  numbers — limits drift with deliverable supply and open interest, and
  a hardcoded number would be a lie in a year.

Legitimate-activity reminder (also in the table's neighbourhood):
federal limits apply absent the bona fide hedge exemption or a granted
exemption; our qualifying hedges are exempt from the SPECULATIVE limits
by §3.2's door, but exchange-level/accountability terms still apply to
how and when they are worked (see 17 CFR 150.5 for exchange-set limit
framework). **Verify** each trading-day morning, not annually.

### 3.4 Bonus CEA mentions that shaped the doctrine

- Anti-evasion: 17 CFR 150.2(i) — structuring a position set to skirt
  limits voids the exemptions; hence rails.py's ticket granularity.
- Manipulation/spoofing: CEA §4c(a)(5)(C), §180.1 — mapped to the
  doctrine's `conduct/no-manipulation` attestation.
- Embargo/pre-release: CEA does not govern government statistics; but
  WASDE embargo is enforced administratively by USDA rules for
  credentialed attendees — we only ever ingest PUBLIC releases at
  public availability times, so §5's `conduct/public-synthesis-only`
  attestation covers the edge case forever: no credentialed attendance,
  no pre-release windows, no Waiver.

---

## 4. European Union — MiFID II activates only with EU clients

Directives/existence anchors: Directive 2014/65/EU (MiFID II),
Regulation (EU) 600/2014. Commodity derivatives sit inside MiFID II's
financial-instruments list (Annex I Section C items 4-10), subject to
carve-outs for persons dealing on own account in physically-settled
commodity derivatives for their own operational needs (MiFID II
art. 2(1)(g), (i) — **VERIFY** the current post-MiFIR review text with
EU counsel when an EU client becomes plausible).

Operating conclusions:

1. A Japanese company providing decision-support TO JAPANESE and
   US-linked operators triggers no MiFID II obligations. Serving an EU
   customer is the TRIGGER EVENT for a full EU analysis.
2. Cross-border provision of investment services into the EU from
   third countries needs EU authorisation (MiFID II art. 42(2) for
   services into retail and professional markets); "reverse
   solicitation" exceptions are narrow and anti-abuse-tested — we do
   not build products on them.
3. Until trigger: EU-facing artefacts limited to public informational
   publications (no targeted solicitation, no账户 targeting), which
   are marketing-neutral in almost every EU member state but STILL
   deserve a one-glance legal check when any EU traction appears.
4. EUDR (deforestation regulation) intersects our soybean records but
   is a compliance-question for the EUDR lanes, not the markets lane —
   referenced here only so nobody thinks the markets perimeter is the
   whole perimeter.

---

## 5. Residual open items feeding the WS6 punchlist (as data)

| # | Item | Regime | When it bites | Gate |
| --- | --- | --- | --- | --- |
| 1 | Confirm FIEA article numbers & route mechanics with 弁護士 | JP | before ANY paid advice pilot | counsel sign-off |
| 2 | 商品投資顧問業 registration need decision | JP | if commodity-derivative advice ships | counsel sign-off |
| 3 | Prepaid instruments posture stays NIL | JP | any prepaid plan, or >2-month advance collection | counsel sign-off |
| 4 | Print current federal CBOT soybean limits from Appendix E table | US | first soybean futures order + each delivery-cycle morning | risk-owner signature |
| 5 | Confirm enumeration path: self-effectuating Appendix A hedge vs §150.3/150.9 recognition | US | before the first non-generic hedge shape | FCM compliance desk written confirmation |
| 6 | MiFID II trigger analysis | EU | first EU client contact | EU counsel |
| 7 | Licence-grant expiry alarm firing for market-facing feeds | ALL | WS6 6.2 deadline set | WS6 unlock ledger |

These items are already reflected as attestations/grant-states in
`farm_ontology/markets/rails.py`; nothing in the deliverables depends
on an unverified cite.

---

## 6. The Founder-mandated integrity clause (for the WS6 contract pack)

The Founder's operating doctrine: **when our data advantage implies a
farmer-side loss, we hedge OUR book, we MAY trade around the public
markets lawfully — and farmer contracts MUST disclose concurrent
proprietary positioning.** The following clause is VERBATIM as provided
by the Lead and is to be inserted into the WS6 contract pack unchanged
(English authoritative; the punchlist owns translations and localisations):

> "The Company maintains proprietary positions in agricultural
> commodities. When its data indicates materially adverse or favourable
> conditions for Your fields, the Company shall disclose the existence
> — never the size — of related positions in its periodic
> decision-support report, before the affected transaction dates."

rails.py pins this string (`DISCLOSURE_CLAUSE`); an artefact failing to
carry it verbatim FAILS rail 1 — mechanical enforcement, not drafting
suggestions. Two companion duties close the loop:

1. **Farmer-consent for upward data flow.** Any product that SHARES
   farmer-level data upward to markets MUST be covered by the farmer's
   WRITTEN consent grant, with purpose, scope, and expiry, using the
   grants/ v2 object the licences teammate specifies (see
   `docs/alpha-fairness-doctrine.md` §4 rail 4 and the grants spec on
   shared-board task-6). No written grant ⇒ the aggregation stays
   ANONYMISED rail. rails.py encodes this as R4; the consent OBJECT
   itself stays the licences workstream's to define — referenced, not
   reimplemented here.
2. **Trade-around lawfulness.** "Trading around public markets" never
   means: spoofing, wash trades, squeeze tactics, or order flow into
   thin books close to settlement expiry (doctrine §3's liquidity
   blackout). Those are enforced as the §5 conduct attestations.

---

## 7. Sources consulted (fetched 2026-11-17, build environment time Asia/Tokyo)

- 17 CFR 150.1 (definitions incl. bona fide hedging), fetched via the
  eCFR versioner API:
  <https://www.ecfr.gov/api/versioner/v1/full/2026-10-01/title-17.xml?part=150&section=150.1>
  (human-readable: <https://www.ecfr.gov/current/title-17/part-150>)
- 17 CFR 150.2 (federal speculative position limits):
  <https://www.ecfr.gov/api/versioner/v1/full/2026-10-01/title-17.xml?part=150&section=150.2>
- Appendix E to part 150 (levels; rendered as images on eCFR; current
  human-readable table):
  <https://www.ecfr.gov/current/title-17/part-150/appendix-Appendix%20E%20to%20Part%20150>
- Final rule "Position Limits for Derivatives", 86 FR 3465, Doc
  2020-25332 (mechanism quote in §3.3; enumerated-hedge/150.9 process):
  <https://www.federalregister.gov/documents/full_text/text/2021/01/14/2020-25332.txt>
- CFTC landing page for the limit table (server rejected automated
  fetch from this environment; cited per task instruction; numbers
  verified from the FR/eCFR mirror instead):
  <https://www.cftc.gov/IndustryOversight/TradingOrganizations/index.htm>
- FIEA text (金融商品取引法) — reasoned from the statute's standing
  structure; article-level citations **VERIFY** with counsel; e-Gov
  法令検索: <https://elaws.e-gov.go.jp/document?lawid=140AC0000000025>
- 資金決済法 (Payment Services Act, prepaid instruments):
  <https://elaws.e-gov.go.jp/document?lawid=421AC0000000059>
- MiFID II: Directive 2014/65/EU consolidated:
  <https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02014L0065-20240328>

*(e-Gov and EUR-Lex URLs were not fetched in this build session; they
are the canonical document homes, marked VERIFY like the articles they
carry.)*
