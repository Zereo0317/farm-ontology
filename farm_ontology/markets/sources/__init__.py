"""Pluggable intraday/daily price-series sources (task-14, Sprint-D).

ONE seam, many adapters: anything that can produce
:class:`PriceSeriesFrame` rows — ``{date, time, close, open, high, low,
volume, source, symbol}`` — plugs in behind :class:`PriceSourceAdapter`.
The first adapter is a stooq.com-style CSV reader (daily and intraday
layouts), shipped FREE-SOURCE-FIRST per the card, with the live fetch
reachable only behind the ``FARM_ONLINE_TESTS`` gate
(:mod:`farm_ontology.testing`).

House rules, inherited and restated:

- Offline by default. A CSV path the repo already carries (or a caller
 -supplied path) needs no network; the only network call in this
  package sits behind :func:`stooq_csv.capture_online` and the env gate.
- No source page opens twice on the same day in tests; recordings land
  as fixtures with ``captured_live``/``fetched_at`` provenance, exactly
  like the fieldtest harness does.
- Series metadata (source URL, symbol, units, licence posture) travels
  on the frame; the backtest refuses frames whose provenance is blank.

The adapters DESCRIBE market data; none of them execute, subscribe, or
advise. Permit state stays False until the grants ledger says otherwise.
"""

from __future__ import annotations

from farm_ontology.markets.sources.stooq_csv import (
    SOURCE_FACTS,
    SYMBOL_ZS_F,
    SYMBOL_CL_F,
    PriceSeriesFrame,
    PriceSourceAdapter,
    StooqCsvSeriesLoader,
    capture_online,
    parse_stooq_csv,
)

__all__ = [
    "SOURCE_FACTS",
    "SYMBOL_ZS_F",
    "SYMBOL_CL_F",
    "PriceSeriesFrame",
    "PriceSourceAdapter",
    "StooqCsvSeriesLoader",
    "capture_online",
    "parse_stooq_csv",
]
