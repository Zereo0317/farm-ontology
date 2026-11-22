"""In-memory, research-only fully funded commodity paper accounting.

This is a toy cash purchase/sale model for USD-per-bushel fills. It does not
model futures, margin, taxes, FX, financing, settlement delays, permissions,
brokers, persistence or actual executions. Inputs are hypothetical fills; no
external orders or money movements exist. Results are not validated P&L.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from enum import Enum
from typing import Mapping


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


class FillUnit(str, Enum):
    USD_PER_BUSHEL = "USD/bu"


def _decimal(value: Decimal, name: str, *, positive: bool = False,
             nonnegative: bool = False, max_scale: int = 6,
             max_abs: Decimal = Decimal('1000000000000')) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{name} must be a finite Decimal")
    # Bound precision and scale so input amounts are explicit and calculations
    # fit within the 50-digit local accounting context.
    if value.copy_abs() > max_abs or value.as_tuple().exponent < -max_scale:
        raise ValueError(f"{name} exceeds supported magnitude or precision")
    if positive and value <= 0:
        raise ValueError(f"{name} must be positive")
    if nonnegative and value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("fill time must be timezone-aware")
    return value.astimezone(timezone.utc)


def _instrument(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError("instrument must be a nonempty unpadded identifier")
    return value


@dataclass(frozen=True)
class PaperFill:
    fill_id: str
    instrument: str
    side: Side
    quantity_bushels: Decimal
    price: Decimal
    price_unit: FillUnit
    fee_usd: Decimal
    filled_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.fill_id, str) or not self.fill_id.strip() or self.fill_id != self.fill_id.strip():
            raise ValueError("fill_id must be nonempty and unpadded")
        _instrument(self.instrument)
        if not isinstance(self.side, Side) or not isinstance(self.price_unit, FillUnit):
            raise ValueError("side and price_unit must be explicit enums")
        _decimal(self.quantity_bushels, "quantity_bushels", positive=True)
        _decimal(self.price, "price", positive=True)
        _decimal(self.fee_usd, "fee_usd", nonnegative=True)
        _utc(self.filled_at)


@dataclass(frozen=True)
class PaperSnapshot:
    cash_usd: Decimal
    positions_bushels: tuple[tuple[str, Decimal], ...]
    fill_count: int


@dataclass(frozen=True)
class Reconciliation:
    cash_difference_usd: Decimal
    position_differences_bushels: tuple[tuple[str, Decimal], ...]

    @property
    def matches(self) -> bool:
        return self.cash_difference_usd == 0 and not self.position_differences_bushels


class PaperLedger:
    """Cash and inventory ledger. Negative cash and short inventory are refused."""
    def __init__(self, opening_cash_usd: Decimal) -> None:
        self._cash = _decimal(opening_cash_usd, "opening_cash_usd", nonnegative=True)
        self._positions: dict[str, Decimal] = {}
        self._fills: list[PaperFill] = []
        self._ids: set[str] = set()

    def record_fill(self, fill: PaperFill) -> PaperSnapshot:
        if not isinstance(fill, PaperFill):
            raise ValueError("a PaperFill is required")
        if fill.fill_id in self._ids:
            raise ValueError("duplicate fill_id")
        moment = _utc(fill.filled_at)
        if self._fills and moment < _utc(self._fills[-1].filled_at):
            raise ValueError("fills must be recorded in time order")
        with localcontext() as ctx:
            ctx.prec = 50
            old_position = self._positions.get(fill.instrument, Decimal(0))
            consideration = fill.quantity_bushels * fill.price
            if fill.side is Side.BUY:
                new_cash = self._cash - consideration - fill.fee_usd
                new_position = old_position + fill.quantity_bushels
            else:
                new_cash = self._cash + consideration - fill.fee_usd
                new_position = old_position - fill.quantity_bushels
            if new_cash < 0:
                raise ValueError("paper fill would create negative cash")
            if new_position < 0:
                raise ValueError("paper fill would create a short position")
            if new_cash > Decimal('1000000000000000000000000') or new_position > Decimal('1000000000000'):
                raise ValueError("paper balance exceeds supported magnitude")
            # Only mutate after every validation passes.
            self._cash = new_cash
            if new_position:
                self._positions[fill.instrument] = new_position
            else:
                self._positions.pop(fill.instrument, None)
            self._fills.append(fill)
            self._ids.add(fill.fill_id)
        return self.snapshot()

    def snapshot(self) -> PaperSnapshot:
        return PaperSnapshot(self._cash, tuple(sorted(self._positions.items())), len(self._fills))

    def reconcile(self, *, cash_usd: Decimal,
                  positions_bushels: Mapping[str, Decimal]) -> Reconciliation:
        """Compare a caller-provided paper statement with this ledger.

        Differences are statement minus ledger. A match does not verify the
        independence or authenticity of the supplied statement.
        """
        _decimal(cash_usd, "cash_usd", max_scale=12,
                 max_abs=Decimal('1000000000000000000000000'))
        if not isinstance(positions_bushels, Mapping):
            raise ValueError("positions_bushels must be a mapping")
        for instrument, quantity in positions_bushels.items():
            _instrument(instrument)
            _decimal(quantity, "statement position")
        with localcontext() as ctx:
            ctx.prec = 50
            diffs = tuple(
                (instrument, positions_bushels.get(instrument, Decimal(0)) -
                 self._positions.get(instrument, Decimal(0)))
                for instrument in sorted(set(positions_bushels) | set(self._positions))
                if positions_bushels.get(instrument, Decimal(0)) != self._positions.get(instrument, Decimal(0))
            )
            return Reconciliation(cash_usd - self._cash, diffs)
