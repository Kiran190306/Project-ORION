"""Core interfaces for the Indicator Engine.

Defines the Indicator protocol and IndicatorConfig that all indicators
must implement. Completely independent from Strategy Framework.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from libraries.domain.indicators.models import (
    Bar,
    IndicatorMetadata,
    IndicatorResult,
    IndicatorType,
)


@dataclass(frozen=True, slots=True)
class IndicatorConfig:
    """Base configuration for all indicators."""

    period: int = 14
    symbol: str = ""
    timeframe: str = ""
    params: dict[str, Any] | None = None

    def get(self, key: str, default: Any = None) -> Any:
        if self.params:
            return self.params.get(key, default)
        return default


@runtime_checkable
class Indicator(Protocol):
    """Protocol that all indicators must implement.

    Indicators are completely independent from strategies.
    Strategies consume indicators - indicators never know about strategies.
    """

    metadata: IndicatorMetadata

    async def initialize(self, config: IndicatorConfig) -> None:
        """Initialize the indicator with configuration."""
        ...

    async def warmup(self, bars: list[Bar]) -> None:
        """Warm up the indicator with historical data."""
        ...

    async def update(self, bar: Bar) -> IndicatorResult:
        """Update the indicator with a new bar and return the result."""
        ...

    async def batch_calculate(self, bars: list[Bar]) -> list[IndicatorResult]:
        """Calculate the indicator for a batch of bars."""
        ...

    async def reset(self) -> None:
        """Reset the indicator to its initial state."""
        ...

    def is_warmed_up(self) -> bool:
        """Return whether the indicator has completed warmup."""
        ...

    def required_period(self) -> int:
        """Return the number of bars required for warmup."""
        ...


class BaseIndicatorABC(ABC):
    """Abstract base class for indicators.

    Provides the standard lifecycle that all indicators follow.
    """

    @abstractmethod
    async def initialize(self, config: IndicatorConfig) -> None: ...

    @abstractmethod
    async def warmup(self, bars: list[Bar]) -> None: ...

    @abstractmethod
    async def update(self, bar: Bar) -> IndicatorResult: ...

    @abstractmethod
    async def batch_calculate(self, bars: list[Bar]) -> list[IndicatorResult]: ...

    @abstractmethod
    async def reset(self) -> None: ...

    @abstractmethod
    def is_warmed_up(self) -> bool: ...

    @abstractmethod
    def required_period(self) -> int: ...

    @abstractmethod
    async def serialize(self) -> dict[str, Any]:
        """Serialize the indicator state."""
        ...

    @classmethod
    @abstractmethod
    async def deserialize(cls, data: dict[str, Any]) -> BaseIndicatorABC:
        """Deserialize and create an indicator from state."""
        ...
