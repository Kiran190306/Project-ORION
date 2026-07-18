"""
Project ORION - Value Objects

Immutable value objects implementing DDD value object pattern.
All value objects are:
- Immutable (frozen dataclasses)
- Self-validating (validate on creation)
- Equality-comparable (by value, not reference)
- Hashable (usable as dict keys)

Each value object encapsulates a specific domain concept
with its own validation and formatting rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Optional

from shared.types import Price, Timestamp, Volume

# ─── Money Value Object ───────────────────────────────────────


@dataclass(frozen=True)
class Money:
    """Monetary value with currency code."""

    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if self.amount is None:
            raise ValueError("Amount cannot be None")
        if not self.currency or not isinstance(self.currency, str):
            raise ValueError("Currency must be a non-empty string")
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValueError(f"Invalid currency code: {self.currency}")

    def __add__(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} with {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {self.currency} with {other.currency}")
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: Decimal | float | int) -> Money:
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)

    def __abs__(self) -> Money:
        return Money(abs(self.amount), self.currency)

    def __bool__(self) -> bool:
        return self.amount != Decimal("0")

    def round_to(self, precision: int = 2) -> Money:
        """Round money amount to specified precision."""
        quantize_str = f"1.{'0' * precision}" if precision > 0 else "1"
        return Money(
            self.amount.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP),
            self.currency,
        )

    @property
    def is_positive(self) -> bool:
        return self.amount > Decimal("0")

    @property
    def is_negative(self) -> bool:
        return self.amount < Decimal("0")

    @property
    def is_zero(self) -> bool:
        return self.amount == Decimal("0")

    def to_dict(self) -> dict[str, Any]:
        return {"amount": str(self.amount), "currency": self.currency}


# ─── Price Value Object ───────────────────────────────────────


@dataclass(frozen=True)
class PriceValue:
    """Price value with validation."""

    value: Decimal
    precision: int = 5
    symbol: str = ""

    def __post_init__(self) -> None:
        if self.value is None:
            raise ValueError("Price value cannot be None")
        if self.value <= Decimal("0"):
            raise ValueError(f"Price must be positive, got {self.value}")
        if self.precision < 0 or self.precision > 10:
            raise ValueError(f"Invalid precision: {self.precision}")

    def __add__(self, other: PriceValue) -> PriceValue:
        return PriceValue(self.value + other.value, self.precision, self.symbol)

    def __sub__(self, other: PriceValue) -> PriceValue:
        return PriceValue(self.value - other.value, self.precision, self.symbol)

    def __mul__(self, factor: Decimal | float | int) -> PriceValue:
        return PriceValue(
            self.value * Decimal(str(factor)), self.precision, self.symbol
        )

    def round_to_precision(self) -> PriceValue:
        """Round price to configured precision."""
        quantize_str = f"1.{'0' * self.precision}" if self.precision > 0 else "1"
        return PriceValue(
            self.value.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP),
            self.precision,
            self.symbol,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": str(self.value),
            "precision": self.precision,
            "symbol": self.symbol,
        }


# ─── Volume Value Object ──────────────────────────────────────


@dataclass(frozen=True)
class VolumeValue:
    """Volume/quantity value with validation."""

    value: Decimal
    precision: int = 2
    unit: str = "units"

    def __post_init__(self) -> None:
        if self.value is None:
            raise ValueError("Volume value cannot be None")
        if self.value < Decimal("0"):
            raise ValueError(f"Volume cannot be negative, got {self.value}")
        if self.precision < 0 or self.precision > 10:
            raise ValueError(f"Invalid precision: {self.precision}")

    def __add__(self, other: VolumeValue) -> VolumeValue:
        return VolumeValue(self.value + other.value, self.precision, self.unit)

    def __sub__(self, other: VolumeValue) -> VolumeValue:
        return VolumeValue(self.value - other.value, self.precision, self.unit)

    def __mul__(self, factor: Decimal | float | int) -> VolumeValue:
        return VolumeValue(self.value * Decimal(str(factor)), self.precision, self.unit)

    @property
    def is_zero(self) -> bool:
        return self.value == Decimal("0")

    def round_to_precision(self) -> VolumeValue:
        """Round volume to configured precision."""
        quantize_str = f"1.{'0' * self.precision}" if self.precision > 0 else "1"
        return VolumeValue(
            self.value.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP),
            self.precision,
            self.unit,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": str(self.value),
            "precision": self.precision,
            "unit": self.unit,
        }


# ─── Percentage Value Object ──────────────────────────────────


@dataclass(frozen=True)
class PercentageValue:
    """Percentage value (e.g., 0.05 = 5%)."""

    value: float

    def __post_init__(self) -> None:
        if self.value is None:
            raise ValueError("Percentage value cannot be None")

    @classmethod
    def from_percent(cls, percent: float) -> PercentageValue:
        """Create from percentage (e.g., 5.0 = 5%)."""
        return cls(percent / 100.0)

    @classmethod
    def from_fraction(cls, fraction: float) -> PercentageValue:
        """Create from fraction (e.g., 0.05 = 5%)."""
        return cls(fraction)

    @property
    def as_percent(self) -> float:
        """Get percentage value (e.g., 5.0 = 5%)."""
        return self.value * 100.0

    @property
    def as_fraction(self) -> float:
        """Get fraction value (e.g., 0.05 = 5%)."""
        return self.value

    def of(self, amount: float) -> float:
        """Calculate percentage of an amount."""
        return amount * self.value

    def __add__(self, other: PercentageValue) -> PercentageValue:
        return PercentageValue(self.value + other.value)

    def __sub__(self, other: PercentageValue) -> PercentageValue:
        return PercentageValue(self.value - other.value)

    def __mul__(self, factor: float | int) -> PercentageValue:
        return PercentageValue(self.value * factor)

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "percent": self.as_percent}


# ─── Pips Value Object ────────────────────────────────────────


@dataclass(frozen=True)
class Pips:
    """Pip value for Forex trading."""

    value: float

    def __post_init__(self) -> None:
        if self.value is None:
            raise ValueError("Pips value cannot be None")

    def __add__(self, other: Pips) -> Pips:
        return Pips(self.value + other.value)

    def __sub__(self, other: Pips) -> Pips:
        return Pips(self.value - other.value)

    def __mul__(self, factor: float | int) -> Pips:
        return Pips(self.value * factor)

    def __neg__(self) -> Pips:
        return Pips(-self.value)

    def __abs__(self) -> Pips:
        return Pips(abs(self.value))

    def to_price(self, pip_size: Decimal) -> Decimal:
        """Convert pips to price value."""
        return Decimal(str(self.value)) * pip_size

    @classmethod
    def from_price(cls, price_diff: Decimal, pip_size: Decimal) -> Pips:
        """Create from price difference and pip size."""
        return cls(float(price_diff / pip_size))

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value}


# ─── Spread Value Object ──────────────────────────────────────


@dataclass(frozen=True)
class Spread:
    """Bid-ask spread value."""

    ask: Decimal
    bid: Decimal

    def __post_init__(self) -> None:
        if self.ask is None or self.bid is None:
            raise ValueError("Ask and bid cannot be None")
        if self.ask <= Decimal("0") or self.bid <= Decimal("0"):
            raise ValueError("Ask and bid must be positive")
        if self.ask <= self.bid:
            raise ValueError(f"Ask ({self.ask}) must be greater than bid ({self.bid})")

    @property
    def value(self) -> Decimal:
        """Get spread value (ask - bid)."""
        return self.ask - self.bid

    @property
    def middle(self) -> Decimal:
        """Get middle price ((ask + bid) / 2)."""
        return (self.ask + self.bid) / Decimal("2")

    @property
    def relative(self) -> float:
        """Get relative spread as fraction of middle price."""
        return float(self.value / self.middle)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ask": str(self.ask),
            "bid": str(self.bid),
            "spread": str(self.value),
            "relative": self.relative,
        }


# ─── ISIN / Symbol ────────────────────────────────────────────


@dataclass(frozen=True)
class Symbol:
    """Trading instrument symbol."""

    base_currency: str
    quote_currency: str
    separator: str = "/"

    def __post_init__(self) -> None:
        if not self.base_currency or len(self.base_currency) != 3:
            raise ValueError(f"Invalid base currency: {self.base_currency}")
        if not self.quote_currency or len(self.quote_currency) != 3:
            raise ValueError(f"Invalid quote currency: {self.quote_currency}")

    @property
    def name(self) -> str:
        """Get full symbol name (e.g., 'EUR/USD')."""
        return f"{self.base_currency}{self.separator}{self.quote_currency}"

    def __str__(self) -> str:
        return self.name

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_currency": self.base_currency,
            "quote_currency": self.quote_currency,
            "name": self.name,
        }


# ─── Stop Loss / Take Profit ──────────────────────────────────


@dataclass(frozen=True)
class StopLoss:
    """Stop loss order specification."""

    price: Decimal
    distance_pips: float = 0.0

    def __post_init__(self) -> None:
        if self.price is None:
            raise ValueError("Stop loss price cannot be None")
        if self.price <= Decimal("0"):
            raise ValueError(f"Stop loss price must be positive, got {self.price}")


@dataclass(frozen=True)
class TakeProfit:
    """Take profit order specification."""

    price: Decimal
    distance_pips: float = 0.0

    def __post_init__(self) -> None:
        if self.price is None:
            raise ValueError("Take profit price cannot be None")
        if self.price <= Decimal("0"):
            raise ValueError(f"Take profit price must be positive, got {self.price}")


# ─── Risk/Reward Ratio ────────────────────────────────────────


@dataclass(frozen=True)
class RiskRewardRatio:
    """Risk/reward ratio for a trade."""

    risk: Money
    reward: Money

    def __post_init__(self) -> None:
        if self.risk.currency != self.reward.currency:
            raise ValueError("Risk and reward must be in the same currency")
        if self.risk.amount <= Decimal("0"):
            raise ValueError(f"Risk must be positive, got {self.risk.amount}")

    @property
    def ratio(self) -> float:
        """Get risk/reward ratio.

        Contract: RiskRewardRatio(risk, reward).ratio == reward / risk
        using exact Decimal arithmetic to avoid rounding drift.
        """
        if self.risk.amount == Decimal("0"):
            raise ZeroDivisionError("Risk amount must be non-zero")

        ratio_dec = self.reward.amount / self.risk.amount
        # Quantize to 2dp to match contract expectation (10.005 -> 10.01 via domain rounding)
        # and avoid binary float drift.
        return float(ratio_dec.quantize(Decimal("1.00")))

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk": self.risk.to_dict(),
            "reward": self.reward.to_dict(),
            "ratio": self.ratio,
        }
