# Real-price fixture provenance

- File: `zs_daily_captured_2026-11-20.json` — CBOT soybean futures (ZS=F)
  daily OHLC, 2021-01-04 .. 2025-10-06, 1256 trading rows, captured from
  the public Yahoo Finance chart endpoint on 2026-11-20 (session tooling).
- Redistribution status: **research use internally; NOT verified for
  commercial redistribution.** The upstream ToS question is open
  (`docs/legal/commercial-punchlist.md`); do not serve this file to
  customers without a rights pass.
- Load gate: tests exercise this frame only when `FARM_REAL_FIXTURES=1`
  (same opt-in discipline as `FARM_ONLINE_TESTS`); the always-on suite
  uses the explicitly-labelled stand-in frame.
