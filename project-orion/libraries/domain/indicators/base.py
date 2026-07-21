"""Base indicator implementation providing the standard lifecycle.

All concrete indicators extend BaseIndicator.
"""

from __future__ import annotations

import math
from abc import abstractmethod
from typing import Any

from libraries.domain.indicators.exceptions import (
    IndicatorCalculationError,
    IndicatorInitializationError,
    WarmupError,
)
from libraries.domain.indicators.interfaces import BaseIndicatorABC, IndicatorConfig
from libraries.domain.indicators.models import (
    Bar,
    IndicatorMetadata,
    IndicatorResult,
    IndicatorType,
)


class BaseIndicator(BaseIndicatorABC):
    """Abstract base for all indicators.

    Provides:
    - initialize/warmup/update/batch_calculate/reset lifecycle
    - Warmup state tracking
    - Serialization support
    - Rolling window management
    """

    def __init__(self, metadata: IndicatorMetadata) -> None:
        self._metadata = metadata
        self._config: IndicatorConfig | None = None
        self._warmed_up = False
        self._initialized = False
        self._values: list[float] = []
        self._timestamps: list[Any] = []
        self._rolling_window: list[Bar] = []

    @property
    def metadata(self) -> IndicatorMetadata:
        return self._metadata

    @property
    def config(self) -> IndicatorConfig | None:
        return self._config

    @property
    def values(self) -> list[float]:
        return list(self._values)

    async def initialize(self, config: IndicatorConfig) -> None:
        """Initialize the indicator with configuration.

        Args:
            config: Indicator configuration.

        Raises:
            IndicatorInitializationError: If initialization fails.
        """
        try:
            self._config = config
            self._values.clear()
            self._timestamps.clear()
            self._rolling_window.clear()
            self._warmed_up = False
            self._initialized = True
            await self._on_initialize(config)
        except Exception as exc:
            raise IndicatorInitializationError(
                f"Failed to initialize {self._metadata.name}: {exc}"
            ) from exc

    async def warmup(self, bars: list[Bar]) -> None:
        """Warm up the indicator with historical data.

        Args:
            bars: Historical bars for warmup.

        Raises:
            IndicatorInitializationError: If not initialized.
        """
        if not self._initialized:
            raise IndicatorInitializationError(
                f"{self._metadata.name} must be initialized before warmup"
            )
        if not bars:
            self._warmed_up = True
            return

        period = self.required_period()
        max_window = period * 4
        self._rolling_window = list(bars[-max_window:]) if len(bars) > max_window else list(bars)
        await self._on_warmup(bars)
        self._warmed_up = True

    async def update(self, bar: Bar) -> IndicatorResult:
        """Update the indicator with a new bar.

        Args:
            bar: New bar data.

        Returns:
            IndicatorResult with computed values.

        Raises:
            WarmupError: If warmup has not been completed.
        """
        if not self._warmed_up:
            raise WarmupError(
                f"{self._metadata.name} has not completed warmup "
                f"(required: {self.required_period()} bars)"
            )

        self._rolling_window.append(bar)
        period = self.required_period()
        max_window = period * 4
        if len(self._rolling_window) > max_window:
            self._rolling_window.pop(0)

        result = await self._on_update(bar)
        if result.value is not None:
            self._values.append(result.value)
            self._timestamps.append(bar.timestamp)

        return result

    async def batch_calculate(self, bars: list[Bar]) -> list[IndicatorResult]:
        """Calculate the indicator for a batch of bars.

        Args:
            bars: Batch of bars to calculate.

        Returns:
            List of indicator results.
        """
        if not bars:
            return []

        if not self._initialized:
            period = self._metadata.min_period if self._metadata else 14
            await self.initialize(self._config or IndicatorConfig(period=period))

        required = self.required_period()
        warmup_count = min(required, len(bars))
        if warmup_count > 0:
            await self.warmup(bars[:warmup_count])

        results: list[IndicatorResult] = []
        for bar in bars[warmup_count:]:
            result = await self._on_update(bar)
            if result.value is not None:
                self._values.append(result.value)
                self._timestamps.append(bar.timestamp)
            results.append(result)

        # If no bars remain after warmup, compute result for the last bar
        if not results and bars:
            last_bar = bars[-1]
            result = await self._on_update(last_bar)
            if result.value is not None:
                self._values.append(result.value)
                self._timestamps.append(last_bar.timestamp)
            results.append(result)

        return results

    async def reset(self) -> None:
        """Reset the indicator to its initial state."""
        self._values.clear()
        self._timestamps.clear()
        self._rolling_window.clear()
        self._warmed_up = False
        self._initialized = False
        self._config = None

    def is_warmed_up(self) -> bool:
        """Return whether the indicator has completed warmup."""
        return self._warmed_up

    def required_period(self) -> int:
        """Return the number of bars required for warmup."""
        return self._metadata.min_period

    def get_rolling_window(self, size: int | None = None) -> list[Bar]:
        """Get the current rolling window of bars."""
        if size is not None:
            return self._rolling_window[-size:]
        return list(self._rolling_window)

    def get_recent_values(self, count: int = 5) -> list[float]:
        """Get the most recent computed values."""
        return self._values[-count:]

    async def serialize(self) -> dict[str, Any]:
        """Serialize the indicator state."""
        return {
            "metadata": {
                "name": self._metadata.name,
                "indicator_type": self._metadata.indicator_type.value,
                "version": self._metadata.version,
            },
            "config": {
                "period": self._config.period if self._config else 0,
                "symbol": self._config.symbol if self._config else "",
                "timeframe": self._config.timeframe if self._config else "",
            },
            "state": {
                "warmed_up": self._warmed_up,
                "initialized": self._initialized,
                "values": list(self._values),
                "value_count": len(self._values),
            },
        }

    @classmethod
    async def deserialize(cls, data: dict[str, Any]) -> BaseIndicator:
        """Deserialize and create an indicator from state.

        Args:
            data: Serialized indicator state.

        Returns:
            Reconstructed indicator instance.
        """
        instance = cls.__new__(cls)
        metadata_data = data.get("metadata", {})
        instance._metadata = IndicatorMetadata(
            name=metadata_data.get("name", "unknown"),
            indicator_type=IndicatorType(metadata_data.get("indicator_type", "trend")),
            display_name=metadata_data.get("name", "unknown"),
            version=metadata_data.get("version", "1.0.0"),
        )
        config_data = data.get("config", {})
        instance._config = IndicatorConfig(
            period=config_data.get("period", 14),
            symbol=config_data.get("symbol", ""),
            timeframe=config_data.get("timeframe", ""),
        )
        state = data.get("state", {})
        instance._warmed_up = state.get("warmed_up", False)
        instance._initialized = state.get("initialized", False)
        instance._values = list(state.get("values", []))
        instance._timestamps = []
        instance._rolling_window = []
        return instance

    # ─── Abstract methods ────────────────────────────────────

    @abstractmethod
    async def _on_initialize(self, config: IndicatorConfig) -> None:
        """Perform indicator-specific initialization."""

    @abstractmethod
    async def _on_warmup(self, bars: list[Bar]) -> None:
        """Perform indicator-specific warmup."""

    @abstractmethod
    async def _on_update(self, bar: Bar) -> IndicatorResult:
        """Perform indicator-specific update calculation."""

    # ─── Math utilities ──────────────────────────────────────

    @staticmethod
    def _sma(values: list[float], period: int) -> float:
        """Compute Simple Moving Average."""
        if not values or period <= 0:
            return 0.0
        return sum(values[-period:]) / min(period, len(values))

    @staticmethod
    def _ema(previous_ema: float, value: float, period: int) -> float:
        """Compute Exponential Moving Average."""
        multiplier = 2.0 / (period + 1)
        return (value - previous_ema) * multiplier + previous_ema

    @staticmethod
    def _wma(values: list[float], period: int) -> float:
        """Compute Weighted Moving Average."""
        if not values or period <= 0:
            return 0.0
        recent = values[-period:]
        weight_sum = sum(i + 1 for i in range(len(recent)))
        weighted = sum((i + 1) * v for i, v in enumerate(recent))
        return weighted / weight_sum

    @staticmethod
    def _stddev(values: list[float], period: int) -> float:
        """Compute Standard Deviation."""
        if len(values) < 2:
            return 0.0
        recent = values[-period:]
        mean = sum(recent) / len(recent)
        variance = sum((x - mean) ** 2 for x in recent) / len(recent)
        return math.sqrt(variance)

    @staticmethod
    def _tr(bar: Bar) -> float:
        """Compute True Range for a single bar."""
        high_low = bar.high - bar.low
        return high_low

    @staticmethod
    def _round(value: float, decimals: int = 8) -> float:
        """Round a value to specified decimal places."""
        return round(value, decimals)

    @staticmethod
    def _safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
        """Safe division returning default on zero division."""
        if denominator == 0:
            return default
        return numerator / denominator

    def _create_result(
        self,
        bar: Bar,
        value: float | None = None,
        values: dict[str, float | None] | None = None,
        quality: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> IndicatorResult:
        """Helper to create an IndicatorResult."""
        return IndicatorResult(
            indicator_name=self._metadata.name,
            timestamp=bar.timestamp,
            value=value,
            values=values or {},
            quality=quality,
            metadata=metadata or {},
        )
