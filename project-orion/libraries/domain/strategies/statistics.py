"""Strategy statistics tracking."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class StrategyExecutionOutcome(StrEnum):
    """Outcome of a strategy execution."""

    WIN = "win"
    LOSS = "loss"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class StrategyStats:
    """Snapshot of strategy statistics."""

    strategy_id: str
    execution_count: int
    win_count: int
    loss_count: int
    error_count: int
    win_rate: float
    loss_rate: float
    avg_confidence: float
    avg_latency_ms: float
    last_execution_time: str | None
    last_outcome: StrategyExecutionOutcome | None


class StrategyStatistics:
    """Tracks execution statistics for a single strategy.

    Maintains:
    - execution count
    - win rate
    - loss rate
    - average confidence
    - average latency
    - last execution
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._execution_count: int = 0
        self._win_count: int = 0
        self._loss_count: int = 0
        self._error_count: int = 0
        self._total_confidence: float = 0.0
        self._total_latency: float = 0.0
        self._last_execution_time: datetime | None = None
        self._last_outcome: StrategyExecutionOutcome | None = None

    async def record_execution(
        self,
        outcome: StrategyExecutionOutcome,
        confidence: float = 0.0,
        latency_ms: float = 0.0,
    ) -> None:
        """Record a strategy execution.

        Args:
            outcome: Outcome of the execution.
            confidence: Confidence score (0-100).
            latency_ms: Execution latency in milliseconds.
        """
        async with self._lock:
            self._execution_count += 1
            self._total_confidence += confidence
            self._total_latency += latency_ms
            self._last_execution_time = datetime.now(timezone.utc)
            self._last_outcome = outcome

            if outcome == StrategyExecutionOutcome.WIN:
                self._win_count += 1
            elif outcome == StrategyExecutionOutcome.LOSS:
                self._loss_count += 1
            elif outcome == StrategyExecutionOutcome.ERROR:
                self._error_count += 1

    async def get_stats(self, strategy_id: str) -> StrategyStats:
        """Return a snapshot of current statistics.

        Args:
            strategy_id: Strategy identifier for the snapshot.

        Returns:
            StrategyStats snapshot.
        """
        async with self._lock:
            total = self._execution_count
            win_rate = self._win_count / total if total > 0 else 0.0
            loss_rate = self._loss_count / total if total > 0 else 0.0
            avg_confidence = self._total_confidence / total if total > 0 else 0.0
            avg_latency = self._total_latency / total if total > 0 else 0.0

            return StrategyStats(
                strategy_id=strategy_id,
                execution_count=self._execution_count,
                win_count=self._win_count,
                loss_count=self._loss_count,
                error_count=self._error_count,
                win_rate=round(win_rate, 4),
                loss_rate=round(loss_rate, 4),
                avg_confidence=round(avg_confidence, 2),
                avg_latency_ms=round(avg_latency, 2),
                last_execution_time=(
                    self._last_execution_time.isoformat() if self._last_execution_time else None
                ),
                last_outcome=self._last_outcome,
            )

    async def reset(self) -> None:
        """Reset all statistics."""
        async with self._lock:
            self._execution_count = 0
            self._win_count = 0
            self._loss_count = 0
            self._error_count = 0
            self._total_confidence = 0.0
            self._total_latency = 0.0
            self._last_execution_time = None
            self._last_outcome = None
