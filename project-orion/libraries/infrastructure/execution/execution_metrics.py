"""Execution metrics tracking for the broker execution layer.

Tracks execution latency, broker latency, fill latency, retry count,
recovery count, success rate, failure rate, circuit breaker state,
and active connections.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class ExecutionMetricsSnapshot:
    """Snapshot of execution metrics."""

    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    partial_fills: int = 0
    full_fills: int = 0
    total_retries: int = 0
    total_recoveries: int = 0
    success_rate: float = 0.0
    average_execution_latency_ms: float = 0.0
    average_broker_latency_ms: float = 0.0
    average_fill_latency_ms: float = 0.0
    total_volume: Decimal = Decimal("0")
    total_commission: Decimal = Decimal("0")
    active_connections: int = 0
    circuit_breaker_open: bool = False
    broker_breakdown: dict[str, BrokerMetrics] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class BrokerMetrics:
    """Per-broker execution metrics."""

    broker_name: str
    total_orders: int = 0
    successful_orders: int = 0
    failed_orders: int = 0
    total_latency_ms: float = 0.0
    total_retries: int = 0
    total_recoveries: int = 0
    is_connected: bool = False
    circuit_breaker_state: str = "closed"
    average_latency_ms: float = 0.0
    success_rate: float = 0.0


class ExecutionMetricsCollector:
    """Collects and reports execution metrics.

    Thread-safe via asyncio.Lock. Maintains a rolling window of
    execution data for accurate metrics computation.
    """

    def __init__(self, max_history: int = 10000) -> None:
        self._lock = asyncio.Lock()
        self._max_history = max_history

        self._total_executions: int = 0
        self._successful_executions: int = 0
        self._failed_executions: int = 0
        self._partial_fills: int = 0
        self._full_fills: int = 0
        self._total_retries: int = 0
        self._total_recoveries: int = 0

        self._execution_latencies: list[float] = []
        self._broker_latencies: list[float] = []
        self._fill_latencies: list[float] = []

        self._total_volume: Decimal = Decimal("0")
        self._total_commission: Decimal = Decimal("0")
        self._active_connections: int = 0
        self._circuit_breaker_open: bool = False

        self._broker_metrics: dict[str, dict[str, Any]] = {}

    async def record_execution(
        self,
        broker_name: str,
        success: bool,
        latency_ms: float = 0.0,
        broker_latency_ms: float = 0.0,
        fill_latency_ms: float = 0.0,
        volume: Decimal = Decimal("0"),
        commission: Decimal = Decimal("0"),
        was_retry: bool = False,
        was_recovery: bool = False,
        is_partial_fill: bool = False,
    ) -> None:
        """Record an execution event.

        Args:
            broker_name: Name of the broker used.
            success: Whether the execution was successful.
            latency_ms: Total execution latency.
            broker_latency_ms: Broker-specific latency.
            fill_latency_ms: Fill confirmation latency.
            volume: Executed volume.
            commission: Commission charged.
            was_retry: Whether this was a retry attempt.
            was_recovery: Whether this was a recovery operation.
            is_partial_fill: Whether this was a partial fill.
        """
        async with self._lock:
            self._total_executions += 1

            if success:
                self._successful_executions += 1
                if is_partial_fill:
                    self._partial_fills += 1
                else:
                    self._full_fills += 1
            else:
                self._failed_executions += 1

            if was_retry:
                self._total_retries += 1
            if was_recovery:
                self._total_recoveries += 1

            self._execution_latencies.append(latency_ms)
            self._broker_latencies.append(broker_latency_ms)
            self._fill_latencies.append(fill_latency_ms)

            self._total_volume += volume
            self._total_commission += commission

            # Update broker-specific metrics
            if broker_name not in self._broker_metrics:
                self._broker_metrics[broker_name] = {
                    "total_orders": 0,
                    "successful_orders": 0,
                    "failed_orders": 0,
                    "total_latency": 0.0,
                    "total_retries": 0,
                    "total_recoveries": 0,
                }

            bm = self._broker_metrics[broker_name]
            bm["total_orders"] += 1
            if success:
                bm["successful_orders"] += 1
            else:
                bm["failed_orders"] += 1
            bm["total_latency"] += latency_ms
            if was_retry:
                bm["total_retries"] += 1
            if was_recovery:
                bm["total_recoveries"] += 1

            # Enforce history limits
            self._trim_history()

    async def set_active_connections(self, count: int) -> None:
        """Set the number of active broker connections.

        Args:
            count: Number of active connections.
        """
        async with self._lock:
            self._active_connections = count

    async def set_circuit_breaker_state(self, is_open: bool) -> None:
        """Set the circuit breaker state.

        Args:
            is_open: Whether the circuit breaker is open.
        """
        async with self._lock:
            self._circuit_breaker_open = is_open

    async def get_snapshot(self) -> ExecutionMetricsSnapshot:
        """Compute current metrics snapshot.

        Returns:
            ExecutionMetricsSnapshot with computed metrics.
        """
        async with self._lock:
            total = self._total_executions
            success_rate = (self._successful_executions / total * 100.0) if total > 0 else 0.0

            avg_exec_latency = (
                sum(self._execution_latencies) / len(self._execution_latencies)
                if self._execution_latencies
                else 0.0
            )
            avg_broker_latency = (
                sum(self._broker_latencies) / len(self._broker_latencies)
                if self._broker_latencies
                else 0.0
            )
            avg_fill_latency = (
                sum(self._fill_latencies) / len(self._fill_latencies)
                if self._fill_latencies
                else 0.0
            )

            # Compute per-broker breakdown
            broker_breakdown: dict[str, BrokerMetrics] = {}
            for name, bm in self._broker_metrics.items():
                b_total = bm["total_orders"]
                b_success_rate = (bm["successful_orders"] / b_total * 100.0) if b_total > 0 else 0.0
                b_avg_latency = (bm["total_latency"] / b_total) if b_total > 0 else 0.0
                broker_breakdown[name] = BrokerMetrics(
                    broker_name=name,
                    total_orders=bm["total_orders"],
                    successful_orders=bm["successful_orders"],
                    failed_orders=bm["failed_orders"],
                    total_latency_ms=round(bm["total_latency"], 2),
                    total_retries=bm["total_retries"],
                    total_recoveries=bm["total_recoveries"],
                    is_connected=self._active_connections > 0,
                    average_latency_ms=round(b_avg_latency, 2),
                    success_rate=round(b_success_rate, 2),
                )

            return ExecutionMetricsSnapshot(
                total_executions=total,
                successful_executions=self._successful_executions,
                failed_executions=self._failed_executions,
                partial_fills=self._partial_fills,
                full_fills=self._full_fills,
                total_retries=self._total_retries,
                total_recoveries=self._total_recoveries,
                success_rate=round(success_rate, 2),
                average_execution_latency_ms=round(avg_exec_latency, 2),
                average_broker_latency_ms=round(avg_broker_latency, 2),
                average_fill_latency_ms=round(avg_fill_latency, 2),
                total_volume=self._total_volume,
                total_commission=self._total_commission,
                active_connections=self._active_connections,
                circuit_breaker_open=self._circuit_breaker_open,
                broker_breakdown=broker_breakdown,
            )

    def _trim_history(self) -> None:
        """Trim history lists to max size."""
        if len(self._execution_latencies) > self._max_history:
            self._execution_latencies = self._execution_latencies[-self._max_history :]
        if len(self._broker_latencies) > self._max_history:
            self._broker_latencies = self._broker_latencies[-self._max_history :]
        if len(self._fill_latencies) > self._max_history:
            self._fill_latencies = self._fill_latencies[-self._max_history :]

    async def reset(self) -> None:
        """Reset all metrics."""
        async with self._lock:
            self._total_executions = 0
            self._successful_executions = 0
            self._failed_executions = 0
            self._partial_fills = 0
            self._full_fills = 0
            self._total_retries = 0
            self._total_recoveries = 0
            self._execution_latencies.clear()
            self._broker_latencies.clear()
            self._fill_latencies.clear()
            self._total_volume = Decimal("0")
            self._total_commission = Decimal("0")
            self._active_connections = 0
            self._circuit_breaker_open = False
            self._broker_metrics.clear()
