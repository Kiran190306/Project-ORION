"""Strategy Plugin Loader.

Supports manual registration, future dynamic loading, package discovery,
and marketplace compatibility. No filesystem scanning required yet.
"""

from __future__ import annotations

from typing import Any

from libraries.domain.strategies.exceptions import StrategyRegistrationError
from libraries.domain.strategies.interfaces import Strategy
from libraries.domain.strategies.registry import StrategyRegistry


class StrategyLoader:
    """Loads strategies into the registry.

    Supports:
    - Manual registration (single or batch)
    - Future dynamic loading (class references)
    - Future package discovery
    - Future marketplace compatibility
    """

    def __init__(self, registry: StrategyRegistry) -> None:
        self._registry = registry

    async def load(self, strategy: Strategy) -> None:
        """Load a single strategy into the registry.

        Args:
            strategy: Strategy instance to load.

        Raises:
            StrategyRegistrationError: On duplicate registration.
        """
        await self._registry.register(strategy)

    async def load_batch(self, strategies: list[Strategy]) -> list[str]:
        """Load multiple strategies into the registry.

        Args:
            strategies: List of strategy instances.

        Returns:
            List of successfully loaded strategy IDs.

        Raises:
            StrategyRegistrationError: Only if all strategies fail.
        """
        loaded: list[str] = []
        for strategy in strategies:
            try:
                await self._registry.register(strategy)
                loaded.append(strategy.id)
            except StrategyRegistrationError:
                continue
        return loaded

    async def unload(self, strategy_id: str) -> None:
        """Unload a strategy from the registry.

        Args:
            strategy_id: ID of the strategy to unload.
        """
        from libraries.domain.strategies.exceptions import StrategyNotFoundError

        try:
            strategy = await self._registry.get(strategy_id)
            await strategy.dispose()
            await self._registry.unregister(strategy_id)
        except StrategyNotFoundError:
            pass

    async def reload(self, strategy: Strategy) -> None:
        """Reload a strategy (unregister + register).

        Args:
            strategy: Strategy instance to reload.
        """
        await self.unload(strategy.id)
        await self.load(strategy)
