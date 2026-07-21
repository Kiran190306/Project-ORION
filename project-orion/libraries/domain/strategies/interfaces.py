"""Core strategy interfaces for the strategy framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, FrozenSet, Protocol, runtime_checkable

from libraries.domain.strategies.models import StrategyPriority


@dataclass(frozen=True, slots=True)
class StrategyMetadata:
    """Metadata describing a strategy's identity and requirements."""

    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    website: str = ""


@dataclass(frozen=True, slots=True)
class StrategyCapabilities:
    """Declares what a strategy needs and supports."""

    supported_markets: FrozenSet[str] = frozenset()
    supported_timeframes: FrozenSet[str] = frozenset()
    required_indicators: FrozenSet[str] = frozenset()
    required_market_state: FrozenSet[str] = frozenset()
    supports_multiple_positions: bool = False
    supports_partial_exit: bool = False
    requires_real_time: bool = True


@runtime_checkable
class Strategy(Protocol):
    """Core protocol every strategy must implement."""

    @property
    def id(self) -> str: ...

    @property
    def name(self) -> str: ...

    @property
    def metadata(self) -> StrategyMetadata: ...

    @property
    def capabilities(self) -> StrategyCapabilities: ...

    async def initialize(self) -> None:
        """Initialize the strategy (load params, set up state)."""
        ...

    async def evaluate(
        self,
        symbol: str,
        context: "StrategyContext",  # noqa: F821
    ) -> "StrategyResult | None":  # noqa: F821
        """Evaluate market conditions and return a trading signal or None."""
        ...

    async def dispose(self) -> None:
        """Clean up resources when the strategy is removed."""
        ...
