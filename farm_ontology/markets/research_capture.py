"""Conservative, research-only capture manifest for historical price rows.

The CSV bytes are hashed and parsed together; a caller cannot validate one
file and accidentally use another. Quote units are explicit. Availability is
never earlier than *this capture*, even when a CSV claims an older publish or
observation time. Timestamps and rights metadata remain caller declarations,
not independent proof of origin, a commercial licence, or execution authority.
No API in this module authorizes financial use or routes an order.
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from urllib.parse import urlparse


class QuoteUnit(str, Enum):
    USD_PER_BUSHEL = "USD/bu"
    USD_CENTS_PER_BUSHEL = "US cents/bu"


def _instant(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _parse_instant(value: str, name: str) -> datetime:
    try:
        return _instant(datetime.fromisoformat(value.replace("Z", "+00:00")), name)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError(f"{name} must be a timezone-aware ISO-8601 instant") from exc


@dataclass(frozen=True)
class CaptureManifest:
    source_url: str
    instrument: str
    quote_unit: QuoteUnit
    captured_at: datetime
    sha256: str

    def __post_init__(self) -> None:
        parsed = urlparse(self.source_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("source_url must be an HTTP(S) URL")
        if not isinstance(self.instrument, str) or not self.instrument.strip():
            raise ValueError("instrument must be nonempty")
        if not isinstance(self.quote_unit, QuoteUnit):
            raise ValueError("quote_unit must be an explicit QuoteUnit")
        _instant(self.captured_at, "captured_at")
        if not isinstance(self.sha256, str) or len(self.sha256) != 64 or any(c not in "0123456789abcdef" for c in self.sha256):
            raise ValueError("sha256 must be lowercase hex")


@dataclass(frozen=True)
class ResearchPrice:
    session_date: date
    close_usd_per_bushel: Decimal
    source_published_at: datetime
    available_at: datetime


@dataclass(frozen=True)
class ResearchCapture:
    manifest: CaptureManifest
    rows: tuple[ResearchPrice, ...]

    def known_at(self, instant: datetime) -> tuple[ResearchPrice, ...]:
        at = _instant(instant, "instant")
        return tuple(row for row in self.rows if row.available_at <= at)

    @property
    def permits_financial_use(self) -> bool:
        # A capture hash is integrity evidence, not an entitlement.
        return False


def read_capture(manifest: CaptureManifest, content: bytes) -> ResearchCapture:
    """Validate a hashed UTF-8 CSV and return normalized research-only rows.

    Required exact header: session_date, close, source_published_at. No row is
    considered available before both its publication and capture instants.
    These dates do not validate the provider's timestamps or licence rights.
    """
    if not isinstance(manifest, CaptureManifest) or not isinstance(content, bytes):
        raise ValueError("a CaptureManifest and its captured bytes are required")
    if not hmac.compare_digest(hashlib.sha256(content).hexdigest(), manifest.sha256):
        raise ValueError("capture hash mismatch")
    try:
        text = content.decode("utf-8-sig", errors="strict")
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        if reader.fieldnames != ["session_date", "close", "source_published_at"]:
            raise ValueError("CSV requires session_date,close,source_published_at")
        rows = []
        seen = set()
        captured_at = _instant(manifest.captured_at, "captured_at")
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError("CSV row has missing or extra columns")
            day = date.fromisoformat(row["session_date"])
            if day in seen:
                raise ValueError("duplicate session date")
            seen.add(day)
            price = Decimal(row["close"])
            if not price.is_finite() or price <= 0:
                raise ValueError("close must be finite and positive")
            published = _parse_instant(row["source_published_at"], "source_published_at")
            if published > captured_at:
                raise ValueError("publication cannot follow capture")
            if published.date() < day:
                raise ValueError("publication cannot precede its session date")
            if manifest.quote_unit is QuoteUnit.USD_CENTS_PER_BUSHEL:
                price /= Decimal(100)
            rows.append(ResearchPrice(day, price, published, captured_at))
    except (UnicodeDecodeError, csv.Error, InvalidOperation, TypeError) as exc:
        raise ValueError("invalid capture CSV") from exc
    if not rows:
        raise ValueError("empty capture")
    rows.sort(key=lambda row: row.session_date)
    return ResearchCapture(manifest, tuple(rows))
