"""Stooq.com-style CSV adapter — the free first source (task-14).

stooq publishes comma-separated OHLCV files; the daily layout for US
futures/indices is::

    Date,Open,High,Low,Close,Volume
    2026-10-05,1053.5,1059.0,1050.2,1055.75,38410

and the intraday layout prefixes each row with an HH:MM stamp::

    Date,Time,Open,High,Low,Close,Volume
    2026-10-05,01:00,1053.0,1054.0,1051.5,1053.25,1204

Continuous back-adjusted soybean futures trade there under ``zs`` (the
CBOT Soybeans continuous front month, US cents per bushel implied by
quote scale — quotes land in USD dollars-per-bushel numeric scale for
grains on stooq, e.g. ``1055.75`` ~ 1055.75 cents/bu... the adapter does
NOT convert: it stores the printed number and its PRINTED scale, and
``SOURCE_FACTS`` says so. Scaling for display is the consumer's declared
choice, never an adapter default.)

A crude-oil sample (``cl.f``) ships as a tiny committed fixture for
offline tests; a synthetic ``zs.f``-shaped fixture backs the backtest.
Both fixtures carry ``captured_live: false``: they are SHAPE fixtures,
not recordings (the repo's long-standing ``fixtures/dry_run`` marking,
misapplied to a single leg here for clarity).

The ONLY network body is :func:`capture_online`, guarded by
``FARM_ONLINE_TESTS`` discipline; it writes a real capture under
``fixtures/markets/`` with provenance, once, and is never exercised by
the offline suite.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from farm_ontology.testing import ONLINE_ENV

STOOQ_BASE = "https://stooq.com"
#: Continuous back-adjusted CBOT Soybeans (front) — the card's first symbol.
SYMBOL_ZS_F = "zs.f"
#: Crude oil continuous, the free sample kept tiny in fixtures.
SYMBOL_CL_F = "cl.f"

CSV_DOWNLOAD_PATH = "/q/d/l/"
PAGE_PATH = "/q/d/"

SAMPLE_FIXTURE_DAILY = (
    Path(__file__).resolve().parent / "fixtures" / "stooq-zs-daily-SAMPLE.csv"
)
SAMPLE_FIXTURE_INTRADAY = (
    Path(__file__).resolve().parent / "fixtures" / "stooq-zs-intraday-SAMPLE.csv"
)


@dataclass(frozen=True)
class SourceFacts:
    """What we can PROVE about a source, recorded like every header."""

    name: str
    base_url: str
    download_url_template: str
    page_url_template: str
    symbol_example: str
    period_note: str
    unit_note: str
    licence_note: str
    citable_url: str

    def citation_lines(self) -> tuple[str, ...]:
        return (
            f"source: {self.name}",
            f"citable URL: {self.citable_url}",
            f"download template: {self.download_url_template}",
            f"symbol example: {self.symbol_example}",
            f"period: {self.period_note}",
            f"units: {self.unit_note}",
            f"licence posture: {self.licence_note}",
        )


SOURCE_FACTS: dict[str, SourceFacts] = {
    SYMBOL_ZS_F: SourceFacts(
        name="stooq.com",
        base_url=STOOQ_BASE,
        download_url_template="https://stooq.com/q/d/l/?s=zs.f&i={interval}&d1={d1}&d2={d2}",
        page_url_template="https://stooq.com/q/d/?s=zs.f",
        symbol_example=SYMBOL_ZS_F,
        period_note=(
            "daily (i=d) and intraday intervals (i=60/30/15/5) for the "
            "continuous back-adjusted front contract; history depth seen "
            "by the recorder was not stored here and is NOT claimed"
        ),
        unit_note=(
            "stooq prints grains/futures quotes at their exchange scale; "
            "the file's numeric column is stored AS PRINTED with its "
            "print-scale noted per capture — no cents/dollars conversion "
            "is invented by this adapter"
        ),
        licence_note=(
            "free public web tables; personal/non-commercial reading is "
            "routine, but systematic redistribution/API-style harvesting "
            "needs the operator's own review — permits_financial_use is "
            "False by default and flips only via the grants ledger"
        ),
        citable_url=f"https://stooq.com/q/d/?s={SYMBOL_ZS_F}",
    ),
    SYMBOL_CL_F: SourceFacts(
        name="stooq.com",
        base_url=STOOQ_BASE,
        download_url_template="https://stooq.com/q/d/l/?s=cl.f&i={interval}&d1={d1}&d2={d2}",
        page_url_template="https://stooq.com/q/d/?s=cl.f",
        symbol_example=SYMBOL_CL_F,
        period_note="daily and intraday intervals for WTI continuous",
        unit_note="USD per barrel as printed; no conversion invented",
        licence_note=(
            "same posture as zs.f: free tables, personal-scale use; "
            "financial use flips only via the grants ledger"
        ),
        citable_url=f"https://stooq.com/q/d/?s={SYMBOL_CL_F}",
    ),
}


@dataclass(frozen=True)
class PriceSeriesFrame:
    """A parsed series with its provenance riding along."""

    source: str
    symbol: str
    interval: str  # "d" or e.g. "60"
    rows: tuple[dict, ...] = field(default_factory=tuple)
    captured_live: bool = False
    citation_url: str = ""
    unit_note: str = ""

    def __post_init__(self) -> None:
        if not self.source or not self.symbol or not self.interval:
            raise ValueError("a frame names its source, symbol, and interval")
        for row in self.rows:
            for key in ("date", "close", "source", "symbol"):
                if key not in row:
                    raise ValueError(f"frame rows carry {key!r}")

    @property
    def dates(self) -> tuple[date, ...]:
        return tuple(row["date"] for row in self.rows)

    def closes_by_date(self) -> dict[date, float]:
        """Daily close map; when intraday, the LAST close per day."""
        out: dict[date, float] = {}
        for row in self.rows:
            out[row["date"]] = row["close"]  # ordered rows: last wins
        return out

    def max_drawdown_of_closes(self) -> dict | None:
        """Peak-to-trough drawdown over the CLOSE series (helper metric)."""
        best = None
        peak = None
        peak_at = None
        trough_running = None
        for row in self.rows:
            px = row["close"]
            if peak is None or px > peak:
                peak = px
                peak_at = row
                trough_running = row
            elif px < trough_running["close"]:
                trough_running = row
            drop = peak - trough_running["close"]
            if drop > 0 and (best is None or drop > best["drawdown"]):
                best = {
                    "drawdown": drop,
                    "peak": peak,
                    "trough": trough_running["close"],
                    "peak_date": peak_at["date"],
                    "trough_date": trough_running["date"],
                }
        return best

    def repr_hint(self) -> str:
        return (
            f"<PriceSeriesFrame {self.symbol} {self.interval} rows={len(self.rows)} "
            f"captured_live={self.captured_live}>"
        )


@dataclass(frozen=True)
class PriceSourceAdapter:
    """The pluggable seam. Adapters answer ``parse``; loaders compose."""

    name: str
    parse: Callable[[Iterable[str], str, str, str], PriceSeriesFrame]

    def __call__(self, *args, **kwargs):
        return self.parse(*args, **kwargs)


def parse_stooq_csv_rows(lines: Iterable[str], symbol: str, interval: str) -> tuple[dict, ...]:
    """Parse stooq CSV lines into frame rows (layout-auto: with/without Time).

    ``#`` comment lines (the provenance preamble on captured fixtures)
    are skipped, so a capture file re-parses exactly like the raw
    download body would.
    """
    data_lines = [
        line
        for line in lines
        if line.strip() and not line.lstrip().startswith("#")
    ]
    reader = csv.DictReader(data_lines)
    if reader.fieldnames is None:
        raise ValueError("empty stooq CSV")
    lowered = [name.strip().lower() for name in reader.fieldnames]
    if lowered[:2] == ["date", "time"]:
        has_time = True
    elif lowered[:1] == ["date"]:
        has_time = False
    else:
        raise ValueError(
            f"not a recognised stooq CSV header: {reader.fieldnames!r}"
        )
    rows: list[dict] = []
    for record in reader:
        clean = {
            (key.strip().lower() if key else key): (value.strip() if isinstance(value, str) else value)
            for key, value in record.items()
        }
        day = date.fromisoformat(clean["date"])
        close = float(clean["close"])
        row = {
            "date": day,
            "close": close,
            "open": float(clean["open"]) if clean.get("open") else None,
            "high": float(clean["high"]) if clean.get("high") else None,
            "low": float(clean["low"]) if clean.get("low") else None,
            "volume": (int(clean["volume"]) if clean.get("volume") else None),
            "source": "stooq",
            "symbol": symbol,
        }
        if has_time:
            hh, mm = clean["time"].split(":")[:2]
            row["time"] = time(int(hh), int(mm))
            row["ts"] = datetime(day.year, day.month, day.day, int(hh), int(mm), tzinfo=timezone.utc)
        rows.append(row)
    rows.sort(key=lambda row: (row["date"], row.get("time") or time()))
    return tuple(rows)


def parse_stooq_csv(
    lines: Iterable[str], symbol: str, interval: str, citation_url: str
) -> PriceSeriesFrame:
    facts = SOURCE_FACTS.get(symbol)
    frame = PriceSeriesFrame(
        source="stooq",
        symbol=symbol,
        interval=interval,
        rows=parse_stooq_csv_rows(lines, symbol, interval),
        captured_live=False,
        citation_url=citation_url or (facts.citable_url if facts else ""),
        unit_note=(facts.unit_note if facts else "as printed by source"),
    )
    if not frame.rows:
        raise ValueError("stooq CSV parsed to zero rows; refusing an empty frame")
    return frame


STOOQ_ADAPTER = PriceSourceAdapter(name="stooq-csv", parse=parse_stooq_csv)


class StooqCsvSeriesLoader:
    """Loads frames from committed/sample CSV paths (offline) or online."""

    def __init__(self, adapter: PriceSourceAdapter | None = None) -> None:
        self.adapter = adapter or STOOQ_ADAPTER

    def from_path(self, path, symbol: str, interval: str = "d") -> PriceSeriesFrame:
        text = Path(path).read_text(encoding="utf-8")
        return self.adapter.parse(
            text.splitlines(),
            symbol,
            interval,
            SOURCE_FACTS[symbol].citable_url if symbol in SOURCE_FACTS else "",
        )

    def from_sample(self, symbol: str = SYMBOL_ZS_F, intraday: bool = False) -> PriceSeriesFrame:
        path = SAMPLE_FIXTURE_INTRADAY if intraday else SAMPLE_FIXTURE_DAILY
        return self.from_path(path, symbol, "60" if intraday else "d")


def _download_url(symbol: str, interval: str, d1: str, d2: str) -> str:
    facts = SOURCE_FACTS[symbol]
    return facts.download_url_template.format(interval=interval, d1=d1, d2=d2)


def fetch_history_bytes(symbol: str, interval: str, d1: str, d2: str) -> bytes:
    """THE network body of this package. Callers gate via the env flag."""
    facts = SOURCE_FACTS[symbol]
    url = _download_url(symbol, interval, d1, d2)
    request = Request(url, headers={"User-Agent": "farm-ontology markets backtest"})
    try:
        with urlopen(request, timeout=60) as response:
            body = response.read()
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise ConnectionError(f"stooq fetch failed for {symbol}: {exc}") from exc
    if not body.lstrip().startswith(b"Date"):
        raise ConnectionError("stooq responded, but not with a CSV table")
    return body


def capture_online(
    symbol: str, interval: str, d1: str, d2: str, out_dir
) -> Path:
    """Sanctioned live capture — ONLY callable when the env gate is on."""
    gate = os.environ.get(ONLINE_ENV, "").strip().lower()
    if gate not in {"1", "true", "yes", "on"}:
        raise PermissionError(
            f"live fetch is opt-in: set {ONLINE_ENV}=1 (discipline "
            "mirrors farm_ontology.testing.online_gate)"
        )
    body = fetch_history_bytes(symbol, interval, d1, d2)
    folder = Path(out_dir)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = folder / f"stooq-{symbol}-{interval}-{stamp}.csv"
    provenance = (
        f"# captured_live: true\n# fetched_at: {stamp}\n"
        f"# symbol: {symbol}\n# interval: {interval}\n"
        f"# citable_url: {SOURCE_FACTS[symbol].citable_url}\n"
    )
    path.write_text(provenance + body.decode("utf-8"), encoding="utf-8")
    return path


__all__ = [
    "SOURCE_FACTS",
    "SYMBOL_ZS_F",
    "SYMBOL_CL_F",
    "SAMPLE_FIXTURE_DAILY",
    "SAMPLE_FIXTURE_INTRADAY",
    "PriceSeriesFrame",
    "PriceSourceAdapter",
    "StooqCsvSeriesLoader",
    "STOOQ_ADAPTER",
    "parse_stooq_csv",
    "parse_stooq_csv_rows",
    "fetch_history_bytes",
    "capture_online",
]
