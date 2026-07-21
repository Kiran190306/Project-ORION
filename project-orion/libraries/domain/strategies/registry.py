"""Strategy Registry - central registry for strategy discovery and lookup."""

from __future__ import annotations

import asyncio
from typing import Any

from packaging.version import Version

from libraries.domain.strategies.exceptions import (
    StrategyNotFoundError,
    StrategyRegistrationError,
)
from libraries.domain.strategies.interfaces import Strategy
from libraries.domain.strategies.models import StrategyStatus


class StrategyRegistry:
    """Central registry for trading strategies.

    Supports:
    - register() with duplicate protection
    - unregister() by strategy ID
    - get() by strategy ID
    - list() with optional filtering
    - discover() for scanning registered strategies
    - Version compatibility checking
    """

    def __init__(self) -> None:
        self._strategies: dict[str, Strategy] = {}
        self._lock = asyncio.Lock()

    async def register(self, strategy: Strategy) -> None:
        """Register a strategy.

        Args:
            strategy: Strategy instance to register.

        Raises:
            StrategyRegistrationError: If a strategy with the same ID
                or name already exists.
        """
        async with self._lock:
            if strategy.id in self._strategies:
                raise StrategyRegistrationError(
                    f"Strategy with id '{strategy.id}' is already registered"
                )

            # Check for duplicate name
            for existing in self._strategies.values():
                if existing.name == strategy.name:
                    raise StrategyRegistrationError(
                        f"Strategy with name '{strategy.name}' is already registered"
                    )

            self._strategies[strategy.id] = strategy

    async def unregister(self, strategy_id: str) -> None:
        """Unregister a strategy.

        Args:
            strategy_id: ID of the strategy to remove.

        Raises:
            StrategyNotFoundError: If the strategy is not registered.
        """
        async with self._lock:
            strategy = self._strategies.pop(strategy_id, None)
            if strategy is None:
                raise StrategyNotFoundError(f"Strategy with id '{strategy_id}' not found")

    async def get(self, strategy_id: str) -> Strategy:
        """Get a strategy by ID.

        Args:
            strategy_id: Strategy ID to look up.

        Returns:
            The registered strategy.

        Raises:
            StrategyNotFoundError: If not found.
        """
        async with self._lock:
            strategy = self._strategies.get(strategy_id)
            if strategy is None:
                raise StrategyNotFoundError(f"Strategy with id '{strategy_id}' not found")
            return strategy

    async def list(
        self,
        status: StrategyStatus | None = None,
        market: str | None = None,
        timeframe: str | None = None,
    ) -> list[Strategy]:
        """List registered strategies, optionally filtered.

        Args:
            status: Filter by strategy status.
            market: Filter by supported market.
            timeframe: Filter by supported timeframe.

        Returns:
            List of matching strategies.
        """
        async with self._lock:
            strategies = list(self._strategies.values())

        if status is not None:
            strategies = [s for s in strategies if hasattr(s, "status") and s.status == status]

        if market is not None:
            strategies = [s for s in strategies if market in s.capabilities.supported_markets]

        if timeframe is not None:
            strategies = [s for s in strategies if timeframe in s.capabilities.supported_timeframes]

        return strategies

    async def discover(self) -> list[Strategy]:
        """Discover all registered strategies.

        Returns:
            List of all registered strategies.
        """
        async with self._lock:
            return list(self._strategies.values())

    async def contains(self, strategy_id: str) -> bool:
        """Check if a strategy ID is registered.

        Args:
            strategy_id: Strategy ID to check.

        Returns:
            True if registered.
        """
        async with self._lock:
            return strategy_id in self._strategies

    async def count(self) -> int:
        """Return the number of registered strategies."""
        async with self._lock:
            return len(self._strategies)

    @staticmethod
    def check_version_compatibility(
        strategy_version: str,
        min_version: str,
        max_version: str | None = None,
    ) -> bool:
        """Check if a strategy version is compatible.

        Args:
            strategy_version: Version of the strategy.
            min_version: Minimum acceptable version.
            max_version: Maximum acceptable version (optional).

        Returns:
            True if compatible.
        """
        try:
            sv = Version(strategy_version)
            if sv < Version(min_version):
                return False
            if max_version is not None and sv > Version(max_version):
                return False
            return True
        except Exception:
            return False
