# Actuation interface spec — WS5 (spec-first, no live machine control)

Status: **implemented as code, unproven against machines**. Author: agent
`actuation`, 2026-11-17, worktree branch `ws/actuation/spec`. Governing
documents: `decision-infra-roadmap.md` WS5 (deliverables 5.1–5.4) and
`alpha-fairness-doctrine.md` §4 (fairness rails) + §6 (execution plumbing).
Everything below describes code that exists in
`farm_ontology/actuation/` on this branch; nothing here touches a real
machine, and no module in the package opens a network connection.

**Rev 2 — fix sprint `ws/fix/actuation-ledger` (2026-11-18):** D9 BLOCKER
fixed — `verify_chain()` had consulted `_TRANSITION_FROM["void"]` (KeyError)
before the void special-case; replay now dispatches void first, refuses
void-of-unproposed-command, and survives a full lifecycle containing a
mid-HALT void (disk roundtrip proven). D8 rough seam closed — drone packet
emission now requires a human signoff release or an explicit recorded
operator override (§5).

---

## 0. Standing rules inherited from the record

Every module in this package obeys the four record principles (roadmap §1):

1. **Refuse when an input is missing** — a gap is published, never guessed.
   All packages raise `ActuationGap` / `ActuationRefusal` with a named
   gap/refusal code, a human detail string, and a remediation hint.
2. **Native support travels with every value** — prescriptions carry a
   non-empty `native_support` stamp; drone packets carry the weather data's
   support stamp too. Stamps ride along opaquely and are never rewritten.
3. **`permits_financial_use` flips only on a written grant** — the drone
   packet builder takes the flag as an explicit boolean and refuses to
   derive, coerce (`"true"` strings, `1`) or default it.
4. **Injected time, nowhere `now()`** — every ledger event, advisory
   reference and weather window carries a caller-supplied timezone-aware
   timestamp. Replay determinism is test-proven.

---

## 1. Component map

| Deliverable | Module | Public surface | Role |
| --- | --- | --- | --- |
| WS5.3 command ledger | `farm_ontology/actuation/command_ledger.py` | `CommandLedger` (`propose/approve/dispatch/acknowledge/void/halt/lift_halt/state_of/events_of/snapshot/verify_chain/save/from_path`), `command_id_for`, `canonical_json` | hash-chained lifecycle record for every field command |
| WS5.1 TaskSet export | `farm_ontology/actuation/taskset_export.py` (+ packaged `TaskData.xsd`) | `build_taskset_zip`, `validate_taskset_zip`, `build_grid_binary`, `KNOWN_OPERATIONS` | ISO 11783-10-shaped ZIP for tractor terminals (offline) |
| WS5.2 drone packet | `farm_ontology/actuation/drone_packet.py` | `build_drone_packet`, `AdvisoryRef`, `weather_window_gaps` | paperwork the human drone operator flies with |
| WS5.4 Phase-4 gate | `farm_ontology/actuation/gate.py` | `GateCheck` (`eligible_for_live_commands`, `assessment`, `gaps`, `refusal_summary`), `GATE_FACT_NAMES`, `GATE_FACT_MEANINGS`, `SATISFYING_EVIDENCE` | the clerk that says NO until six facts are evidenced |

Error vocabulary (§6 below) is defined once in `command_ledger` and imported
everywhere — there is exactly one gap/refusal alphabet in the package.

## 2. Data flow (all human-gated)

```
agronomy engine (WS3, Phase P1)          ← does not exist yet; fixtures only
  │ RecommendationRecord (WS3.5 contract)
  ▼
propose() ────────────────► CommandLedger state: proposed
  │                          (command carries: prescription + native_support +
  │                           use_class stamps, polygon_ref | None, actor)
  ▼
human approve (≠ proposer) ► approved
  │
  ├──► build_taskset_zip(...)  → TaskSet ZIP (tractor: human carries/copies it)
  └──► build_drone_packet(...) → KML packet   (human operator: flies with it)
       │
       ▼ receipts come back (transport blob, controller ack)
dispatch(receipt) ────────► dispatched
  ▼
acknowledge(receipt) ─────► acknowledged          …or void(reason) from anywhere
```

Until Phase 4, nothing after `approve` connects to a machine: "dispatch"
means handing a file to a human, and the receipt is that handover's evidence
(file sha256 for a TaskSet, operator sheet signature for a packet).

## 3. Command state machine (normative)

States: `proposed → approved → dispatched → acknowledged`, plus terminal
`voided` (reachable from every non-voided state).

```
            propose              approve                dispatch              acknowledge
  (start) ───────────► proposed ──────────► approved ──────────► dispatched ──────────► acknowledged
                          │  │                 │  │                 │  │                    │
                          └──┴─────────────────┴──┴─────────────────┴──┴────────────────────┘
                                             void(reason) from any state above → voided
                                             (terminal; history is never erased)
```

| Transition | Guard (raises otherwise) | Refusal codes |
| --- | --- | --- |
| `start → proposed` | prescription dict with **both stamps** present; valid actor; polygon_ref string-or-None; no active HALT; identical content = same command_id (duplicate propose → refusal) | `prescription_missing`, `native_support_missing`, `use_class_missing`, `actor_*`, `polygon_ref_ill_formed`, `naive_timestamp`, `timestamp_regression` |
| `proposed → approved` | approver is **human** and **≠ proposer** (four-eyes) | `approver_must_be_human`, `approver_equals_proposer`, `illegal_transition` |
| `approved → dispatched` | non-empty receipt blob (string or JSON) | `dispatch_receipt_missing`, `illegal_transition` |
| `dispatched → acknowledged` | non-empty receipt blob | `ack_receipt_missing`, `illegal_transition` |
| `any → voided` | reason mandatory | `void_reason_missing`, `illegal_transition` (voiding `voided`) |

Extras:

- **Command identity**: `command_id = sha256(canonical_json({kind,
  prescription, polygon_ref, proposer}))[:32]`. Timestamps are *excluded* —
  replaying the same proposal yields the same id; two identical proposals are
  one command, not two. Sequence-of-authority ambiguity is thereby impossible.
- **Timestamp monotonicity**: each command's events are non-decreasing in
  injected time (`timestamp_regression` gap otherwise).
- **Refused transitions leave no trace** on the chain (tested); the ledger
  records history, never intentions-that-failed.

### Chain mechanics (mirrors `ontolaw/src/ontolaw/ledger.py`)

```
record = {seq, type, ts, prev, event, hash}
hash   = sha256(prev.encode("ascii") + canonical_json({type, ts, event}))
genesis prev = "0" * 64
```

- `canonical_json`: sorted keys, `ensure_ascii=False`, `separators=(",", ":")`
  — byte-stable across processes.
- Record types: `command_event` (lifecycle) and `halt` (emergency HALT).
- `verify_chain()` walks the whole chain checking seq continuity, prev-link
  equality, recomputed entry hashes, structural validity of every event, and
  **replays the state machine over the history** — so a forger who deletes
  or reorders records and re-forges hashes consistently is still caught by
  replay (test-proven).
- Persistence: `save()` writes JSONL; `from_path()`/`from_jsonl_text()`
  **verify before trusting** and refuse a tampered file
  (`ledger_verify_failed`).

### Emergency HALT (doctrine §6: the kill switch, on both ledgers)

An emergency HALT is a *record on the chain* written by the **human risk
owner** (`halt(reason, actor=human)`, reason mandatory). While active it
freezes `propose/approve/dispatch/acknowledge`; **voiding stays legal during
a HALT** because cancelling commands only reduces risk. Lifting requires a
second human-authored record (`lift_halt(reason)`). Actions attempted during
a HALT raise refusal `halted` with the lift remedy in the message. The gate's
`watchdog_defined` fact is precisely: some runtime component polls the
ledgers and propagates this freeze to command intake within its poll
interval.

## 4. ISO 11783-10 TaskSet export (WS5.1)

`build_taskset_zip(polygon_ring, prescription, operation, partfield_id,
task_id, designator="")` → `(zip_bytes, report)`.

- Inputs: open WGS84 ring (≥3 (lat, lon) points, closure added by the
  builder), prescription `{"zone_table": {zone: {product, dose, unit}},
  "native_support": …, "use_class": …, "grid": optional}`, operation ∈
  `KNOWN_OPERATIONS` (`IRRIG` — WATER only; `SPRAY` — any product).
- ZIP members: `taskdata.xml` (root `Iso11783TaskData`, attributes
  VersionMajor/VersionMinor/DataTransferOrigin/ManagementSoftware*/,
  TransferFileLanguage; Partfield with closed Polygon of Point
  North/East; TreatmentZone Attr pairs; Task with
  TaskTreatmentProcessCode=operation, TaskPartfieldIdRef, UseClass,
  NativeSupport), `taskdata.xsd` (the packaged profile schema, also the
  validator's shape contract), and `grid0001.bin` + `GridInfo` element when
  the prescription is gridded.
- Grid encoding (farm-ontology profile, labelled as such in code and XSD):
  uint16 little-endian treatment-zone codes, column-major BLIN order,
  first cell = (min_lat, min_lon) north-west corner; GridInfo carries the
  min corner, cell size, row/col counts and min/max zone codes computed
  from the payload — never asserted by the caller.
- **Validator**: `validate_taskset_zip` parses the archive offline with
  ElementTree and asserts: member presence, root element, mandatory
  attributes, polygon ≥3 points with coordinates, Task↔Partfield referential
  integrity, GridInfo↔ZIP-member consistency, and XSD well-formedness.
  Failures are refusals with every problem enumerated.

> **Validation boundary (honesty note)**: what ships is a *structurally
> valid, internally consistent* TaskSet profile — not a promise that any
> particular ISO 11783-10 controller accepts it. The farm-ontology
> `TaskData.xsd` is our own profile schema, not the normative ISO text
> (stdlib Python cannot do XSD validation anyway; obtaining the licensed
> normative document is a separate task). Controller-acceptance testing is
> pinned to the **Phase-4 field drill** (`gate.py`:
> `field_drill_completed`) — see module docstring and §8.

## 5. Drone spray packet (WS5.2)

`build_drone_packet(geofence_ring, dosage_table, advisory_ref,
weather_window, use_class, permits_financial_use, designator="")` →
`(kml_bytes, report)`.

- Emitted KML 2.2 (`http://www.opengis.net/kml/2.2`): Document named after
  the advisory, description block carrying BOTH stamps verbatim
  (`use_class=…`, `permits_financial_use=true|false`) plus the explicit
  notice **"HUMAN-flown packet: the operator flies, this sheet prescribes.
  No autopilot link is created by farm-ontology."**; one Placemark with the
  geofence Polygon (coordinates in KML `lon,lat,0` order — deliberately
  reversed from the module's `(lat, lon)` input order); ExtendedData with
  one JSON `dose:<zone>` entry per dosage row and `weather:*` entries per
  window field.
- **`AdvisoryRef`** (dataclass, frozen): `{reference_id, issuer,
  issued_at (aware ISO-8601), contract}`. The contract default names
  `farm_ontology.agronomy.RecommendationRecord` per roadmap **WS3.5**
  ("inputs, licences, uncertainties, expiry"). The agronomy engine does not
  exist yet (Phase P1) — refs are FIXTURES; their shape is validated, their
  agronomy is not, and every report says so.
- **Weather window** (`weather_window_gaps` is the public checker):
  `window_start_utc`/`window_end_utc` (aware, end > start), `wind_max_ms` >
  0, `rain_free_hours` ≥ 0, `temp_min_c` ≤ `temp_max_c`,
  `native_support` stamp of the weather data itself.
- **SIGNOFF GATE (D8, Rev 2)**: the packet refuses to fly on an UNSIGNED
  recommendation. `AdvisoryRef.requires_human_signoff` defaults **True**;
  while it stands, emission demands either `signoff_release` — a
  `SignoffRelease(signer, signed_at, signature, recommendation_id)` whose
  `recommendation_id` binds it to EXACTLY the cited recommendation (a
  mismatch refuses with `signoff_target_mismatch`) — or an explicit
  `operator_override="<justification>"`, which is recorded VERBATIM into the
  packet payload (`operator_override=…`, `signature=
  none-operator-override-recorded`). Neither given ⇒ refusal
  `signature_missing`. A malformed supplied release refuses loudly
  (`signoff_release_invalid`) and is not silently rescued by an override.
- **All-or-nothing refusal**: the builder collects EVERY gap across all six
  inputs and refuses with one verbose refusal (`drone_packet_inputs_incomplete`)
  enumerating them — a partially-filled packet is a field hazard, not a
  convenience.

## 6. Error catalogue (the gap/refusal vocabulary)

Raised by every public function in the package; never a fake pass.

### Gaps — `ActuationGap("[gap:<code>] detail (remedy: …)")`

| Code | Raised when |
| --- | --- |
| `prescription_missing` | payload absent/empty/non-dict (ledger, TaskSet) |
| `native_support_missing` / `use_class_missing` | stamp missing or blank (ledger propose, TaskSet, packet) |
| `polygon_ref_ill_formed` | non-None non-string polygon_ref |
| `polygon_ring_ill_formed` | ring too small / non-numeric / out-of-WGS84 / closed ring (TaskSet) |
| `zone_id_ill_formed`, `zone_spec_ill_formed`, `product_missing`, `dose_ill_formed`, `unit_missing` | zone-table malformations |
| `operation_unknown` | operation not in KNOWN_OPERATIONS |
| `partfield_id_missing`, `task_id_missing` | TaskSet identity missing |
| `grid_ill_formed`, `grid_missing_field`, `grid_cell_nonpositive`, `grid_shape_nonpositive`, `grid_origin_out_of_range`, `grid_codes_shape`, `grid_code_ill_formed` | gridded prescription malformations |
| `taskset_bytes_missing`, `taskset_zip_unreadable` | validator input unusable |
| `advisory_reference_id_missing`, `advisory_issuer_missing`, `advisory_issued_at_missing`, `advisory_issued_at_unparsable`, `advisory_issued_at_naive`, `advisory_contract_missing`, `advisory_signoff_flag_not_boolean` | AdvisoryRef malformation |
| `signoff_signer_missing`, `signoff_signature_missing`, `signoff_signed_at_missing`, `signoff_signed_at_unparsable`, `signoff_signed_at_naive`, `signoff_recommendation_id_missing` | SignoffRelease malformation (Rev 2) |
| `weather_window_missing` + per-field window gaps | weather window unusable |
| `geofence_ring` (+ indexed variants) | KML fence unusable |
| `command_id_missing`, `unknown_command` | ledger addressing errors |
| `actor_kind_invalid`, `actor_id_missing`, `<role>_missing` | actor records |
| `naive_timestamp`, `timestamp_regression` | determinism violations |
| `dispatch_receipt_missing`, `ack_receipt_missing`, `void_reason_missing`, `halt_reason_missing`, `lift_reason_missing` | transition prerequisites |
| `ledger_line_unparsable`, `ledger_read_failed`, `ledger_write_failed` | persistence IO |
| `gate_facts_ill_formed`, `gate_fact_unknown`, `gate_fact_not_boolean` | GateCheck input hygiene |

### Refusals — `ActuationRefusal("[refusal:<code>] detail (remedy: …)")`

| Code | Meaning |
| --- | --- |
| `illegal_transition` (subclass) | state machine violated; message names from→to |
| `approver_must_be_human` | approval authority is human-only (§7) |
| `approver_equals_proposer` | four-eyes violation |
| `halted` | an emergency HALT is active; lifecycle frozen |
| `halt_actor_must_be_human` | only the human risk owner wields the HALT |
| `halt_already_active` / `halt_not_active` | HALT idempotence |
| `product_wrong_for_operation` | e.g. fungicide inside IRRIG |
| `drone_packet_inputs_incomplete` | the aggregate all-gaps packet refusal |
| `signature_missing` | unsigned recommendation, no release AND no override given (Rev 2, D8) |
| `signoff_release_invalid` | a supplied SignoffRelease failed shape validation (Rev 2) |
| `signoff_target_mismatch` | release binds a different recommendation than the packet cites (Rev 2) |
| `operator_override_ill_formed` | override given but not a justification string (Rev 2) |
| `taskset_structure_invalid` (validator refusals incl. `taskset_xml_unparsable`) | offline structural validation failed; every problem enumerated |
| `ledger_verify_failed` | loaded chain failed integrity; never silently accepted |

`IllegalTransition` is `ActuationRefusal` subclassed so callers can catch
narrowly; both carry `.gap`/`.refusal`, `.detail`, `.remediation`.

## 7. Who holds approval authority

- **The human risk owner** (the operator/principal, doctrine §6 "human
  approve") holds sole approval authority for field commands. `approve()`
  refuses service actors outright, refuses the proposer approving their own
  proposal, and the gate's signed kill-switch contract names WHO may halt.
- The **engine proposes** (WS3 recommendations), the **ledger remembers**
  (this package), the **human disposes**. Doctrine §4 rails referenced by
  this spec: §4.3 (ticket filed even if unratified — the ledger is that
  filing), §4.4 (farmer-consent gating of any market-facing derivative of
  farm data), §4.5 (fail-closed truthfulness on licence loss — hence the
  packet's explicit, non-derivable `permits_financial_use`).
- Quarterly review (doctrine §8) maps to the gate's `audit_quarter_clean`
  fact — the quarter is clean only with zero unresolved ledger findings.

## 8. Kill-switch propagation contract & the Phase-4 gate (WS5.4)

**HALT semantics** (binding, mirrored in `command_ledger` and summarized in
the gate's fact meanings): the human risk owner writes `halt` on the command
ledger (and — per doctrine §6 — symmetric recognition on the trade ledger).
Propagation duties belong to the **runtime watchdog**, whose existence the
gate demands:

1. Watchdog observes the newest halt/lift record on each ledger it supervises.
2. Within one poll interval of a `halt` record: command intake freezes
   (propose/approve/dispatch refused by the ledger anyway; the watchdog
   additionally suspends intake endpoints and cancels queued transports).
3. Liveness of the watchdog itself is alerted on (doctrine §7: 'HALT raised'
   alert channel reserved by task-1's team).
4. A `lift_halt` record reopens intake; no automatic re-dispatch of anything
   frozen — resumption is fresh human action.

**The gate as code** — `GateCheck(eligibility over six facts)`:

| Fact | True means (condensed; full text in `GATE_FACT_MEANINGS`) |
| --- | --- |
| `min_instances` | command intake holds a warm instance (Cloud Run min-instances=1 or equivalent) |
| `auth_configured` | every mutating actuation endpoint demands an authorised principal |
| `watchdog_defined` | a watchdog owns HALT propagation + liveness alerting |
| `kill_switch_contract_signed` | risk owner SIGNED the kill-switch contract (who halts, ack latency, drill procedure) |
| `field_drill_completed` | successful closed-loop drill on REAL equipment: proposed→approved→dispatched→acknowledged with verify_chain() ok |
| `audit_quarter_clean` | last full quarter closed with zero unresolved ledger/audit findings |

`eligible_for_live_commands()` is `True` **iff all six facts are literally
`True`**. Facts are `bool | None` (None = not assessed); non-booleans raise
`gate_fact_not_boolean` — `"yes"`, `1`, truthy strings never count. Facts
arrive from deployment evidence; the gate inspects nothing, networks
nowhere. `gaps()` returns, per failing fact: `kind` (`missing` vs
`failed`), the fact's meaning, and the evidence that would satisfy it
(`SATISFYING_EVIDENCE`). `refusal_summary()` is the one-liner for logs.
There is **no override knob** by design: production flipping the gate to
True requires human-authored evidence covering exactly these six facts,
reviewed per the doctrine cadence.

## 9. Determinism, offline discipline, test evidence

- Tests: `tests/test_actuation_command_ledger.py` (35),
  `tests/test_actuation_taskset_export.py` (19),
  `tests/test_actuation_drone_packet.py` (17), `tests/test_actuation_gate.py`
  (9) — 80 new tests, all offline, all deterministic (injected timestamps;
  no sleeps; no sockets; no fixtures fetched).
- Tamper detection proof (selected): edited entry hash, deleted-record seq
  break, reordered prev mismatch, forged-but-impossible history caught by
  replay, tampered-file reload refused, structural garbage flagged.
- House-suite regression: 1204 pre-existing + 80 = 1284 tests green;
  `compileall` clean.

## 10. Explicit non-goals (this phase)

- No Bluetooth/CAN/serial/MQTT transports, no autopilot APIs, no live
  valves. Dispatch = human-carried files + receipts.
- No real ISO-controller validation (Phase-4 field drill).
- No agronomy judgement (`AdvisoryRef` is a pointer; fixtures until WS3).
- No decision on which machines get bought. The gate decides WHEN code may
  speak to machines; procurement is a human card away from the board.
