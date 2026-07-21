"""Indicator Manager.

Orchestrates the full lifecycle of indicators across symbols:
- Initialization
- Warmup
- Incremental updates
- Batch calculations
- Reset

Uses dependency injection for registry, cache, and statistics.
No global state - each manager instance is independent.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from libraries.domain.indicators.base import BaseIndicator
from libraries.domain.indicators.cache import IndicatorCache, IndicatorCacheConfig
from libraries.domain.indicators.interfaces import IndicatorConfig
from libraries.domain.indicators.models import Bar, IndicatorResult
from libraries.domain.indicators.registry import IndicatorRegistry
from libraries.domain.indicators.statistics import IndicatorStatistics


@dataclass(frozen=True, slots=True)
class IndicatorManagerConfig:
    """Configuration for the IndicatorManager."""

    default_period: int = 14
    enable_cache: bool = True
    enable_statistics: bool = True
    track_latency: bool = True

    cache_config: IndicatorCacheConfig = field(default_factory=IndicatorCacheConfig)


class IndicatorManager:
    """Orchestrates indicator lifecycle management.

    Manages creation, initialization, warmup, and updates of indicators
    grouped by symbol. Each manager instance is independent with injected
    dependencies.
    """

    def __init__(
        self,
        registry: IndicatorRegistry | None = None,
        cache: IndicatorCache | None = None,
        statistics: IndicatorStatistics | None = None,
        config: IndicatorManagerConfig | None = None,
    ) -> None:
        self._registry = registry or IndicatorRegistry()
        self._cache = cache or (IndicatorCache(config.cache_config) if config and config.enable_cache else None)  # fmt: skip
        self._statistics = statistics or (IndicatorStatistics() if not config or config.enable_statistics else None)  # fmt: skip
        self._config = config or IndicatorManagerConfig()

        # Per-symbol indicator instances: {symbol: {indicator_name: BaseIndicator}}
        self._indicators: dict[str, dict[str, BaseIndicator]] = {}
        self._lock = asyncio.Lock()

    async def create_indicator(
        self,
        name: str,
        symbol: str,
        config: IndicatorConfig | None = None,
    ) -> BaseIndicator:
        """Create and initialize an indicator for a symbol.

        Args:
            name: Indicator name (must be registered).
            symbol: Trading symbol.
            config: Optional configuration override.

        Returns:
            Initialized BaseIndicator instance.

        Raises:
            ValueError: If indicator name is not registered.
        """
        indicator_class = await self._registry.get_class(name)
        if indicator_class is None:
            raise ValueError(
                f"Indicator '{name}' is not registered. " f"Call registry.register() first."
            )

        indicator = indicator_class()
        indicator_config = config or IndicatorConfig(
            period=self._config.default_period,
            symbol=symbol,
        )
        await indicator.initialize(indicator_config)

        async with self._lock:
            if symbol not in self._indicators:
                self._indicators[symbol] = {}
            self._indicators[symbol][name] = indicator

        return indicator

    async def warmup(
        self,
        symbol: str,
        bars: list[Bar],
        indicator_names: list[str] | None = None,
    ) -> None:
        """Warm up indicators with historical data.

        Args:
            symbol: Trading symbol.
            bars: Historical bars for warmup.
            indicator_names: Optional subset of indicators to warm up.
                           If None, all indicators for the symbol are warmed.
        """
        indicators = await self._get_indicators(symbol, indicator_names)
        if not indicators:
            return

        for indicator in indicators:
            start = time.monotonic()
            try:
                await indicator.warmup(bars)
                if self._statistics and self._config.enable_statistics:
                    await self._statistics.record_warmup(indicator.metadata.name)
            except Exception as exc:
                if self._statistics and self._config.enable_statistics:
                    await self._statistics.record_execution(
                        indicator.metadata.name,
                        time.monotonic() - start,
                        error=str(exc),
                    )
                raise

    async def update(
        self,
        symbol: str,
        bar: Bar,
        indicator_names: list[str] | None = None,
    ) -> dict[str, IndicatorResult]:
        """Update indicators with a new bar.

        Args:
            symbol: Trading symbol.
            bar: New bar data.
            indicator_names: Optional subset of indicators to update.
                           If None, all indicators for the symbol are updated.

        Returns:
            Dictionary mapping indicator name to result.
        """
        indicators = await self._get_indicators(symbol, indicator_names)
        results: dict[str, IndicatorResult] = {}

        for indicator in indicators:
            name = indicator.metadata.name

            # Check cache first
            if self._config.enable_cache and self._cache:
                cached = await self._cache.get(name, bar, symbol)
                if cached is not None:
                    results[name] = cached
                    if self._statistics and self._config.enable_statistics:
                        await self._statistics.record_execution(name, 0.0, cache_hit=True)
                    continue

            # Calculate
            start = time.monotonic()
            try:
                result = await indicator.update(bar)
                elapsed = time.monotonic() - start

                results[name] = result

                # Cache the result
                if self._config.enable_cache and self._cache:
                    await self._cache.set(name, bar, result, symbol)

                # Record statistics
                if self._statistics and self._config.enable_statistics:
                    await self._statistics.record_execution(name, elapsed)
            except Exception as exc:
                if self._statistics and self._config.enable_statistics:
                    await self._statistics.record_execution(
                        name,
                        time.monotonic() - start,
                        error=str(exc),
                    )
                raise

        return results

    async def batch_calculate(
        self,
        symbol: str,
        bars: list[Bar],
        indicator_names: list[str] | None = None,
    ) -> dict[str, list[IndicatorResult]]:
        """Calculate indicators for a batch of bars.

        Creates indicators on-the-fly if needed.

        Args:
            symbol: Trading symbol.
            bars: Batch of bars to calculate.
            indicator_names: Optional subset of indicators.

        Returns:
            Dictionary mapping indicator name to list of results.
        """
        indicators = await self._get_indicators(symbol, indicator_names)
        if not indicators:
            return {}

        results: dict[str, list[IndicatorResult]] = {}

        for indicator in indicators:
            name = indicator.metadata.name
            start = time.monotonic()
            try:
                indicator_results = await indicator.batch_calculate(bars)
                elapsed = time.monotonic() - start
                results[name] = indicator_results

                if self._statistics and self._config.enable_statistics:
                    await self._statistics.record_execution(name, elapsed)
            except Exception as exc:
                if self._statistics and self._config.enable_statistics:
                    await self._statistics.record_execution(
                        name,
                        time.monotonic() - start,
                        error=str(exc),
                    )
                raise

        return results

    async def reset(self, symbol: str | None = None, indicator_name: str | None = None) -> None:
        """Reset indicators.

        Args:
            symbol: Optional symbol to reset. If None, resets all.
            indicator_name: Optional indicator name to reset.
        """
        async with self._lock:
            if symbol:
                if indicator_name:
                    indicator = self._indicators.get(symbol, {}).get(indicator_name)
                    if indicator:
                        await indicator.reset()
                else:
                    for indicator in self._indicators.get(symbol, {}).values():
                        await indicator.reset()
            else:
                for sym_indicators in self._indicators.values():
                    for indicator in sym_indicators.values():
                        await indicator.reset()

    async def get_indicator(
        self,
        symbol: str,
        name: str,
    ) -> BaseIndicator | None:
        """Get a specific indicator instance.

        Args:
            symbol: Trading symbol.
            name: Indicator name.

        Returns:
            BaseIndicator if found, None otherwise.
        """
        async with self._lock:
            return self._indicators.get(symbol, {}).get(name)

    async def list_indicators(self, symbol: str | None = None) -> dict[str, list[str]]:
        """List all managed indicators.

        Args:
            symbol: Optional symbol filter.

        Returns:
            Dictionary mapping symbol to list of indicator names.
        """
        async with self._lock:
            if symbol:
                return {symbol: list(self._indicators.get(symbol, {}).keys())}

            return {sym: list(inds.keys()) for sym, inds in self._indicators.items()}

    async def remove_indicator(self, symbol: str, name: str) -> bool:
        """Remove an indicator from management.

        Args:
            symbol: Trading symbol.
            name: Indicator name.

        Returns:
            True if removed, False if not found.
        """
        async with self._lock:
            if symbol in self._indicators and name in self._indicators[symbol]:
                await self._indicators[symbol][name].reset()
                del self._indicators[symbol][name]
                return True
            return False

    async def _get_indicators(
        self,
        symbol: str,
        names: list[str] | None = None,
    ) -> list[BaseIndicator]:
        """Get indicator instances for a symbol.

        Args:
            symbol: Trading symbol.
            names: Optional list of indicator names to filter.

        Returns:
            List of BaseIndicator instances.
        """
        async with self._lock:
            indicators = self._indicators.get(symbol, {})
            if names:
                return [indicators[n] for n in names if n in indicators]
            return list(indicators.values())
