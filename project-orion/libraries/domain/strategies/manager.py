"""Strategy Manager - orchestrates strategy lifecycle and execution."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from libraries.domain.strategies.composite import CompositeStrategy
from libraries.domain.strategies.context import StrategyContext
from libraries.domain.strategies.exceptions import (
    StrategyError,
    StrategyNotFoundError,
)
from libraries.domain.strategies.interfaces import Strategy
from libraries.domain.strategies.lifecycle import LifecycleState, StrategyLifecycle
from libraries.domain.strategies.loader import StrategyLoader
from libraries.domain.strategies.models import StrategyConfig, StrategyPriority, StrategyStatus
from libraries.domain.strategies.registry import StrategyRegistry
from libraries.domain.strategies.statistics import (
    StrategyExecutionOutcome,
    StrategyStatistics,
)
from libraries.domain.strategies.strategy import StrategyResult
from libraries.domain.strategies.voting import VotingMethod


@dataclass(frozen=True, slots=True)
class StrategyManagerConfig:
    """Configuration for the strategy manager."""

    default_voting_method: VotingMethod = VotingMethod.CONFIDENCE_WEIGHTED
    health_check_interval_seconds: float = 60.0
    max_execution_latency_ms: float = 5000.0
    track_statistics: bool = True


class StrategyManager:
    """Orchestrates strategy lifecycle, execution, and monitoring.

    Responsible for:
    - Loading strategies via the loader
    - Starting/stopping strategies
    - Enabling/disabling strategies
    - Prioritization
    - Health monitoring
    """

    def __init__(
        self,
        registry: StrategyRegistry | None = None,
        loader: StrategyLoader | None = None,
        composite: CompositeStrategy | None = None,
        config: StrategyManagerConfig | None = None,
    ) -> None:
        self._registry = registry or StrategyRegistry()
        self._loader = loader or StrategyLoader(self._registry)
        self._composite = composite or CompositeStrategy()
        self._config = config or StrategyManagerConfig()
        self._lifecycles: dict[str, StrategyLifecycle] = {}
        self._statistics: dict[str, StrategyStatistics] = {}
        self._priorities: dict[str, int] = {}
        self._lock = asyncio.Lock()
        self._health_task: asyncio.Task[None] | None = None
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    @property
    def registry(self) -> StrategyRegistry:
        return self._registry

    @property
    def loader(self) -> StrategyLoader:
        return self._loader

    @property
    def composite(self) -> CompositeStrategy:
        return self._composite

    # ─── Lifecycle ────────────────────────────────────────────

    async def start(self) -> None:
        """Start the strategy manager."""
        async with self._lock:
            if self._running:
                return
            self._running = True

    async def stop(self) -> None:
        """Stop the strategy manager and all strategies."""
        async with self._lock:
            if not self._running:
                return
            self._running = False

        # Stop all strategies
        for strategy_id in list(self._lifecycles.keys()):
            await self._shutdown_strategy(strategy_id)

        if self._health_task is not None:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
            self._health_task = None

    # ─── Strategy Registration ────────────────────────────────

    async def register_strategy(
        self,
        strategy: Strategy,
        config: StrategyConfig | None = None,
        priority: StrategyPriority = StrategyPriority.NORMAL,
    ) -> str:
        """Register and initialize a strategy.

        Args:
            strategy: Strategy instance.
            config: Optional configuration overrides.
            priority: Execution priority.

        Returns:
            The strategy ID.

        Raises:
            StrategyError: If registration fails.
        """
        # Initialize lifecycle
        lifecycle = StrategyLifecycle()
        lifecycle.transition_to(LifecycleState.INITIALIZED)

        # Initialize statistics
        stats = StrategyStatistics()

        lifecycle.transition_to(LifecycleState.STARTED)

        async with self._lock:
            self._lifecycles[strategy.id] = lifecycle
            self._statistics[strategy.id] = stats
            self._priorities[strategy.id] = priority.numeric

        # Register in registry
        await self._loader.load(strategy)

        # Add to composite
        self._composite.add_strategy(strategy)

        return strategy.id

    async def unregister_strategy(self, strategy_id: str) -> None:
        """Unregister and dispose a strategy.

        Args:
            strategy_id: Strategy ID to remove.
        """
        await self._shutdown_strategy(strategy_id)
        await self._loader.unload(strategy_id)
        self._composite.remove_strategy(strategy_id)
        async with self._lock:
            self._lifecycles.pop(strategy_id, None)
            self._statistics.pop(strategy_id, None)
            self._priorities.pop(strategy_id, None)

    # ─── Lifecycle Control ────────────────────────────────────

    async def enable_strategy(self, strategy_id: str) -> None:
        """Enable a strategy."""
        async with self._lock:
            lifecycle = self._lifecycles.get(strategy_id)
            if lifecycle is None:
                raise StrategyNotFoundError(f"Strategy '{strategy_id}' not found")
            if lifecycle.can_transition_to(LifecycleState.RESUMED):
                lifecycle.transition_to(LifecycleState.RESUMED)
            elif lifecycle.can_transition_to(LifecycleState.STARTED):
                lifecycle.transition_to(LifecycleState.STARTED)

    async def disable_strategy(self, strategy_id: str) -> None:
        """Disable a strategy."""
        async with self._lock:
            lifecycle = self._lifecycles.get(strategy_id)
            if lifecycle is None:
                raise StrategyNotFoundError(f"Strategy '{strategy_id}' not found")
            if lifecycle.can_transition_to(LifecycleState.PAUSED):
                lifecycle.transition_to(LifecycleState.PAUSED)
            elif lifecycle.can_transition_to(LifecycleState.STOPPED):
                lifecycle.transition_to(LifecycleState.STOPPED)

    async def pause_strategy(self, strategy_id: str) -> None:
        """Pause a strategy."""
        async with self._lock:
            lifecycle = self._lifecycles.get(strategy_id)
            if lifecycle is None:
                raise StrategyNotFoundError(f"Strategy '{strategy_id}' not found")
            lifecycle.transition_to(LifecycleState.PAUSED)

    async def resume_strategy(self, strategy_id: str) -> None:
        """Resume a paused strategy."""
        async with self._lock:
            lifecycle = self._lifecycles.get(strategy_id)
            if lifecycle is None:
                raise StrategyNotFoundError(f"Strategy '{strategy_id}' not found")
            lifecycle.transition_to(LifecycleState.RESUMED)

    async def shutdown_strategy(self, strategy_id: str) -> None:
        """Shutdown a strategy completely."""
        await self._shutdown_strategy(strategy_id)

    async def _shutdown_strategy(self, strategy_id: str) -> None:
        """Internal: shutdown a strategy."""
        async with self._lock:
            lifecycle = self._lifecycles.get(strategy_id)
            if lifecycle is None:
                return
            try:
                lifecycle.transition_to(LifecycleState.SHUTDOWN)
            except ValueError:
                pass

    # ─── Execution ───────────────────────────────────────────

    async def evaluate(
        self,
        symbol: str,
        context: StrategyContext,
    ) -> list[StrategyResult]:
        """Evaluate all active strategies.

        Args:
            symbol: Trading symbol.
            context: Market context.

        Returns:
            List of strategy results (None results filtered out).
        """
        if not self._running:
            return []

        start_time = time.monotonic()
        results: list[StrategyResult] = []

        # Get active strategies
        active_strategies: list[Strategy] = []
        async with self._lock:
            for strategy_id, lifecycle in self._lifecycles.items():
                if lifecycle.is_active():
                    try:
                        strategy = await self._registry.get(strategy_id)
                        active_strategies.append(strategy)
                    except StrategyNotFoundError:
                        continue

        # Evaluate each strategy
        for strategy in active_strategies:
            try:
                result = await strategy.evaluate(symbol, context)
                if result is not None:
                    results.append(result)
                    if self._config.track_statistics:
                        stats = self._statistics.get(strategy.id)
                        if stats:
                            elapsed = (time.monotonic() - start_time) * 1000
                            await stats.record_execution(
                                outcome=StrategyExecutionOutcome.WIN,
                                confidence=result.confidence,
                                latency_ms=elapsed,
                            )
            except Exception:
                if self._config.track_statistics:
                    stats = self._statistics.get(strategy.id)
                    if stats:
                        await stats.record_execution(
                            outcome=StrategyExecutionOutcome.ERROR,
                        )

        return results

    # ─── Priority ────────────────────────────────────────────

    async def set_priority(
        self,
        strategy_id: str,
        priority: StrategyPriority,
    ) -> None:
        """Set the execution priority for a strategy.

        Args:
            strategy_id: Strategy ID.
            priority: New priority level.
        """
        async with self._lock:
            if strategy_id not in self._lifecycles:
                raise StrategyNotFoundError(f"Strategy '{strategy_id}' not found")
            self._priorities[strategy_id] = priority.numeric

    async def get_priority(self, strategy_id: str) -> int:
        """Get the numeric priority for a strategy.

        Args:
            strategy_id: Strategy ID.

        Returns:
            Numeric priority value.
        """
        async with self._lock:
            return self._priorities.get(strategy_id, StrategyPriority.NORMAL.numeric)

    # ─── Statistics ──────────────────────────────────────────

    async def get_statistics(
        self,
        strategy_id: str,
    ) -> StrategyStatistics | None:
        """Get statistics for a strategy.

        Args:
            strategy_id: Strategy ID.

        Returns:
            StrategyStatistics instance if found.
        """
        async with self._lock:
            return self._statistics.get(strategy_id)

    async def reset_statistics(self, strategy_id: str) -> None:
        """Reset statistics for a strategy."""
        async with self._lock:
            stats = self._statistics.get(strategy_id)
            if stats:
                await stats.reset()

    # ─── Health ──────────────────────────────────────────────

    async def health_check(self) -> dict[str, Any]:
        """Perform a health check on the strategy manager.

        Returns:
            Dictionary with health status information.
        """
        async with self._lock:
            strategy_statuses: dict[str, str] = {}
            for strategy_id, lifecycle in self._lifecycles.items():
                strategy_statuses[strategy_id] = lifecycle.state.value

            return {
                "running": self._running,
                "total_strategies": len(self._lifecycles),
                "active_strategies": sum(1 for l in self._lifecycles.values() if l.is_active()),
                "strategies": strategy_statuses,
            }
