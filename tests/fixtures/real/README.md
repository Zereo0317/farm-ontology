# Real-price fixture provenance

- File: `zs_daily_captured_2026-11-20.json` — CBOT soybean futures (ZS=F)
  daily closes, 2021-01-04 .. 2025-12-31, 1,256 trading rows, captured from
  the public Yahoo Finance chart endpoint on 2026-11-20 (session tooling).
  Byte-identical to the workspace `.tmp/zs_rows.json` capture the ad-hoc
  2026-11-22 study ran on (SHA-256 checked 2026-11-26).
- Redistribution status: **research use internally; NOT verified for
  commercial redistribution.** The upstream ToS question is open
  (`docs/legal/commercial-punchlist.md`); do not serve this file to
  customers without a rights pass.
- Load gate: tests exercise this frame only when `FARM_REAL_FIXTURES=1`
  (same opt-in discipline as `FARM_ONLINE_TESTS`); the always-on suite
  uses the explicitly-labelled stand-in frame. The gate protects the
  controlled asset from casual consumption — the suite never fetches the
  network either way.
- Consumer: `farm_ontology/markets/real_backtest.py` (the audit-gap-G4
  harness); `load_default_fixture_frame()` is the sanctioned loader.

## Clearance paths for commercial redistribution (licences workstream, WS6)

1. Preferred: re-capture from a source with explicit open terms (an
   authorised redistribution channel or an exchange-affiliated free tier)
   and record the licence verbatim in a capture manifest
   (`farm_ontology/markets/research_capture.py` shape).
2. Alternative: verify Yahoo's current terms permit caching a research
   snapshot beyond internal use — "works today" is not a licence.
3. Cheapest evidenced route: exchange-settlement data the farm stack
   already receives under an agreed licence, when one exists.

Any commit here that embeds recorded third-party quotes is a licence
DECISION: made by a human, with the licence line recorded in this README.

## What a committed fixture here must carry

A `meta` envelope with symbol, interval, source, captured_at, unit_note,
citation_url — and a licence line stating WHAT was checked and WHEN.
(The 2026-11-20 fixture predates this harness and ships as a bare
`[["date", close], ...]` array; `load_recorded_frame` supplies the
declared provenance keywords for exactly that shape.)

## Loader contract

`farm_ontology.markets.real_backtest.load_recorded_frame` consumes:

```json
{
  "meta": {
    "symbol": "ZS=F",
    "interval": "1d",
    "source": "yahoo",
    "citation_url": "https://finance.yahoo.com/quote/ZS=F/history",
    "unit_note": "US cents per bushel as printed by the Yahoo chart API",
    "captured_at": "2026-11-20T00:00:00+00:00",
    "captured_by": "<who ran the capture>"
  },
  "rows": [["2021-01-04", 1316.5]]
}
```

(`rows` also accepts `{"date": ..., "close": ..., "source": ..., "note": ...}`
objects; a bare `[["date", close], ...]` list is accepted with the
keyword-argument provenance. Recognised `unit_note` scales are closed-set
in `real_backtest.USD_PER_BU_SCALE` — anything else is refused, never
guessed. Declared harvest days with no recorded session (weekends:
2024-10-05, 2025-10-05) get honest `calendar-carry` rows inserted by the
loader, repeating the last session close.)
