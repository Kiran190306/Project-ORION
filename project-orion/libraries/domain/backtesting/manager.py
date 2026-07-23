"""Backtest manager — lifecycle management for EPIC-010.

Provides start/stop/health check lifecycle management for the
backtesting engine and its components.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from libraries.domain.backtesting.engine import BacktestEngine, BacktestEngineResult
from libraries.domain.backtesting.exceptions import BacktestError
from libraries.domain.backtesting.models import BacktestConfig


@dataclass(frozen=True, slots=True)
class BacktestManagerConfig:
    """Configuration for the backtest manager."""

    max_concurrent_backtests: int = 1
    shutdown_timeout_seconds: float = 30.0
    health_check_interval_seconds: float = 60.0
    metadata: dict[str, Any] = field(default_factory=dict)


class BacktestManager:
    """Lifecycle manager for the backtesting engine.

    Manages engine initialization, execution, health monitoring,
    and graceful shutdown.
    """

    def __init__(
        self,
        config: BacktestManagerConfig | None = None,
        engine: BacktestEngine | None = None,
    ) -> None:
        """Initialize backtest manager.

        Args:
            config: Manager configuration.
            engine: Backtest engine instance.
        """
        self._config = config or BacktestManagerConfig()
        self._engine = engine
        self._running = False
        self._started_at: datetime | None = None
        self._results: list[BacktestEngineResult] = []
        self._health = True
        self._error: str | None = None

    @property
    def config(self) -> BacktestManagerConfig:
        return self._config

    @property
    def engine(self) -> BacktestEngine | None:
        return self._engine

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def started_at(self) -> datetime | None:
        return self._started_at

    @property
    def uptime_seconds(self) -> float:
        if self._started_at is None:
            return 0.0
        return (datetime.now(timezone.utc) - self._started_at).total_seconds()

    async def start(self, engine: BacktestEngine | None = None) -> None:
        """Start the backtest manager.

        Args:
            engine: Optional engine to set.
        """
        if self._running:
            raise BacktestError("Backtest manager is already running")

        if engine is not None:
            self._engine = engine

        if self._engine is None:
            raise BacktestError("No backtest engine configured")

        self._running = True
        self._started_at = datetime.now(timezone.utc)
        self._health = True
        self._error = None

    async def stop(self) -> None:
        """Stop the backtest manager gracefully."""
        if not self._running:
            return

        self._running = False
        if self._engine:
            await self._engine.reset()

    async def run_backtest(
        self,
        config: BacktestConfig | None = None,
        **kwargs: Any,
    ) -> BacktestEngineResult:
        """Execute a backtest.

        Args:
            config: Backtest configuration (overrides engine config).
            **kwargs: Additional arguments passed to engine.run().

        Returns:
            Backtest engine result.
        """
        if not self._running:
            raise BacktestError("Backtest manager is not running. Call start() first.")

        if not self._engine:
            raise BacktestError("No backtest engine configured")

        try:
            result = await self._engine.run(**kwargs)
            self._results.append(result)
            return result
        except Exception as e:
            self._health = False
            self._error = str(e)
            raise

    async def health_check(self) -> dict[str, Any]:
        """Return health status of the backtest manager.

        Returns:
            Dict with health status information.
        """
        return {
            "running": self._running,
            "healthy": self._health,
            "engine_configured": self._engine is not None,
            "uptime_seconds": self.uptime_seconds,
            "backtests_executed": len(self._results),
            "error": self._error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def get_results(self) -> list[BacktestEngineResult]:
        """Return all backtest results.

        Returns:
            List of backtest results.
        """
        return list(self._results)

    async def clear_results(self) -> None:
        """Clear all backtest results."""
        self._results.clear()

    async def reset(self) -> None:
        """Reset the manager to initial state."""
        await self.stop()
        self._started_at = None
        self._results.clear()
        self._health = True
        self._error = None

    async def get_stats(self) -> dict[str, Any]:
        """Return manager statistics.

        Returns:
            Dict with manager statistics.
        """
        total = len(self._results)
        passed = sum(1 for r in self._results if r.success)
        failed = total - passed
        avg_time = (
            sum(r.execution_time_seconds for r in self._results) / total if total > 0 else 0.0
        )

        return {
            "total_backtests": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / total, 4) if total > 0 else 0.0,
            "average_execution_time_seconds": round(avg_time, 2),
            "uptime_seconds": self.uptime_seconds,
        }
