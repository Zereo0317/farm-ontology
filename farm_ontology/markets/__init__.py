"""Markets workstream (WS7, shared-board task-7).

Three analysts-facing modules and no execution path:

- ``pit_dataset`` builds point-in-time matrices from the recorded feed
  fixtures under ``facts_at`` semantics.
- ``shock_watch`` turns recorded series into ``ShockFlag`` records under
  declarative rules. It persists nothing.
- ``rails`` encodes the alpha-and-fairness doctrine
  (``docs/alpha-fairness-doctrine.md``, sections 3 to 5) as validators
  that fail closed.

Nothing in this package fetches, scores a market, or advises. Class C
stays closed. Persistence, scheduling, and the human gate belong to
other workstreams.
"""
