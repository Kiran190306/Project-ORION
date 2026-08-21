"""ExecutionContext - aggregates all inputs for the Execution Engine.

Provides a single context object with market data, account info,
broker availability, and risk assessment for order execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any


class ExecutionMode(StrEnum):
    """Execution mode for the execution engine."""

    LIVE = "live"
    PAPER = "paper"
    SANDBOX = "sandbox"
    SIMULATION = "simulation"


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Aggregates all inputs for the Execution Engine.

    Provides a single context object with market data, account info,
    broker availability, and risk assessment for order execution.
    """

    mode: ExecutionMode = ExecutionMode.LIVE
    symbol: str = ""
    volume: Decimal = Decimal(0)
    max_slippage_bps: float = 10.0
    allow_partial_fills: bool = True
    execution_timeout_seconds: float = 30.0
    use_circuit_breaker: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Order overrides
    order_type_override: str | None = None
    time_in_force_override: str | None = None
    price_override: Decimal | None = None
    broker_symbol_override: str | None = None

    # Market / broker state
    market_open: bool = True
    broker_available: bool = True
    tick_size: Decimal | None = None
    lot_size: Decimal | None = None
    current_spread: float | None = None