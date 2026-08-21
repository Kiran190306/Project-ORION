"""Execution statistics tracking.

Tracks execution metrics including order counts, fill rates,
latency, slippage, and broker performance.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum


class ExecutionOutcome(StrEnum):
    """Outcome of an order execution."""

    FILLED = "filled"
    PARTIAL_FILL = "partial_fill"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    TIMEOUT = "timeout"


@dataclass(frozen=True, slots=True)
class ExecutionStats:
    """Snapshot of execution statistics."""

    total_orders: int = 0
    filled_orders: int = 0
    partial_fills: int = 0
    rejected_orders: int = 0
    cancelled_orders: int = 0
    expired_orders: int = 0
    fill_rate: float = 0.0
    average_latency_ms: float = 0.0
    average_slippage_pips: float = 0.0
    total_volume: Decimal = Decimal(0)
    total_commission: Decimal = Decimal(0)
    broker_breakdown: dict[str, int] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionStatistics:
    """Tracks execution performance metrics.

    Thread-safe via asyncio.Lock.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._total_orders: int = 0
        self._outcomes: dict[ExecutionOutcome, int] = {}
        self._latencies: list[float] = []
        self._slippages: list[float] = []
        self._total_volume: Decimal = Decimal(0)
        self._total_commission: Decimal = Decimal(0)
        self._broker_counts: dict[str, int] = {}
        self._max_history: int = 10000

    async def record_execution(
        self,
        outcome: ExecutionOutcome,
        broker_id: str = "",
        latency_ms: float = 0.0,
        slippage_pips: float = 0.0,
        volume: Decimal = Decimal(0),
        commission: Decimal = Decimal(0),
    ) -> None:
        """Record an execution outcome.

        Args:
            outcome: Execution outcome.
            broker_id: Broker that handled the execution.
            latency_ms: Execution latency in milliseconds.
            slippage_pips: Slippage in pips.
            volume: Executed volume.
            commission: Commission charged.
        """
        async with self._lock:
            self._total_orders += 1
            self._outcomes[outcome] = self._outcomes.get(outcome, 0) + 1
            self._latencies.append(latency_ms)
            self._slippages.append(slippage_pips)
            self._total_volume += volume
            self._total_commission += commission

            if broker_id:
                self._broker_counts[broker_id] = self._broker_counts.get(broker_id, 0) + 1

            # Enforce history limit
            if len(self._latencies) > self._max_history:
                self._latencies = self._latencies[-self._max_history :]
                self._slippages = self._slippages[-self._max_history :]

    async def get_stats(self) -> ExecutionStats:
        """Compute current execution statistics.

        Returns:
            ExecutionStats snapshot.
        """
        async with self._lock:
            total = self._total_orders
            filled = self._outcomes.get(ExecutionOutcome.FILLED, 0)
            partial = self._outcomes.get(ExecutionOutcome.PARTIAL_FILL, 0)
            rejected = self._outcomes.get(ExecutionOutcome.REJECTED, 0)
            cancelled = self._outcomes.get(ExecutionOutcome.CANCELLED, 0)
            expired = self._outcomes.get(ExecutionOutcome.EXPIRED, 0)

            fill_rate = (filled + partial) / total if total > 0 else 0.0
            avg_latency = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
            avg_slippage = sum(self._slippages) / len(self._slippages) if self._slippages else 0.0

            return ExecutionStats(
                total_orders=total,
                filled_orders=filled,
                partial_fills=partial,
                rejected_orders=rejected,
                cancelled_orders=cancelled,
                expired_orders=expired,
                fill_rate=round(fill_rate, 4),
                average_latency_ms=round(avg_latency, 2),
                average_slippage_pips=round(avg_slippage, 4),
                total_volume=self._total_volume,
                total_commission=self._total_commission,
                broker_breakdown=dict(self._broker_counts),
            )

    async def reset(self) -> None:
        """Reset all statistics."""
        async with self._lock:
            self._total_orders = 0
            self._outcomes.clear()
            self._latencies.clear()
            self._slippages.clear()
            self._total_volume = Decimal(0)
            self._total_commission = Decimal(0)
            self._broker_counts.clear()
