"""Context objects for the Portfolio & Position Management Engine.

Provides input aggregation for portfolio operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class PortfolioContext:
    """Complete context for portfolio operations.

    Aggregates all inputs for a portfolio operation (open, close, etc.).
    Prepared for multi-currency support.
    """

    account_id: str = "default"
    base_currency: str = "USD"
    timestamps: dict[str, datetime] = field(default_factory=dict)
    prices: dict[str, Decimal] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class FillUpdate:
    """Payload for a fill update from the Execution Engine."""

    execution_id: str
    decision_id: str
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    commission: Decimal = Decimal(0)
    swap: Decimal = Decimal(0)
    fees: Decimal = Decimal(0)
    strategy: str = ""
    broker: str = ""
    currency: str = "USD"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PriceUpdate:
    """Payload for market price updates affecting position valuations."""

    symbol: str
    price: Decimal
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
