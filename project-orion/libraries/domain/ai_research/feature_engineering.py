"""Modular, deterministic feature engineering with no infrastructure dependency."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from math import sqrt
from typing import Any

from libraries.domain.ai_research.exceptions import FeatureEngineeringError
from libraries.domain.ai_research.models import FeatureDefinition, FeatureVector, ResearchDataset

CustomFeature = Callable[[ResearchDataset, FeatureDefinition], Sequence[float]]


class ResearchFeatureEngineer:
    """Computes declared features; custom implementations are registered by callers."""

    def __init__(self) -> None:
        self._custom_features: dict[str, CustomFeature] = {}

    def register_custom(self, name: str, implementation: CustomFeature) -> None:
        if not name or not callable(implementation):
            raise FeatureEngineeringError("custom feature needs a name and callable implementation")
        self._custom_features[name] = implementation

    async def engineer(
        self, dataset: ResearchDataset, definitions: Sequence[FeatureDefinition]
    ) -> tuple[FeatureVector, ...]:
        if not definitions:
            return ()
        series: dict[str, Sequence[float]] = {}
        for definition in definitions:
            missing = set(definition.required_columns).difference(dataset.schema)
            if missing:
                raise FeatureEngineeringError(
                    f"feature '{definition.name}' is missing columns: {sorted(missing)}"
                )
            values = self._compute(dataset, definition)
            if len(values) != dataset.row_count:
                raise FeatureEngineeringError(
                    f"feature '{definition.name}' returned an invalid length"
                )
            series[definition.name] = values
        return tuple(
            FeatureVector(
                values={name: float(values[index]) for name, values in series.items()},
                timestamp=self._timestamp(row),
            )
            for index, row in enumerate(dataset.rows)
        )

    def _compute(self, dataset: ResearchDataset, definition: FeatureDefinition) -> Sequence[float]:
        if definition.category == "custom":
            implementation = self._custom_features.get(definition.name)
            if implementation is None:
                raise FeatureEngineeringError(
                    f"no implementation registered for custom feature '{definition.name}'"
                )
            return implementation(dataset, definition)
        close = self._numbers(dataset, "close")
        period = int(definition.parameters.get("period", 14))
        if period < 1:
            raise FeatureEngineeringError("period must be positive")
        name = definition.name.lower()
        if name == "sma":
            return self._sma(close, period)
        if name == "ema":
            return self._ema(close, period)
        if name == "rsi":
            return self._rsi(close, period)
        if name == "macd":
            return self._macd(
                close,
                int(definition.parameters.get("fast", 12)),
                int(definition.parameters.get("slow", 26)),
            )
        if name == "atr":
            return self._atr(dataset, period)
        if name in {"bollinger", "bollinger_width"}:
            return self._bollinger_width(
                close, period, float(definition.parameters.get("stddev", 2.0))
            )
        if definition.category == "price_action":
            return self._price_action(dataset, name)
        if definition.category == "candlestick":
            return self._candlestick(dataset, name)
        if definition.category == "liquidity":
            return self._numbers(dataset, "volume")
        if definition.category == "session":
            return [self._session_value(row) for row in dataset.rows]
        if definition.category == "time":
            return [self._time_value(row, name) for row in dataset.rows]
        if definition.category == "volume":
            return self._volume_change(self._numbers(dataset, "volume"))
        if definition.category == "trend":
            return self._sma(close, period)
        if definition.category == "momentum":
            return self._momentum(close, period)
        if definition.category == "volatility":
            return self._volatility(close, period)
        raise FeatureEngineeringError(f"unsupported feature '{definition.name}'")

    @staticmethod
    def _numbers(dataset: ResearchDataset, column: str) -> list[float]:
        try:
            return [float(row[column]) for row in dataset.rows]
        except (KeyError, TypeError, ValueError) as exc:
            raise FeatureEngineeringError(f"column '{column}' must contain numeric values") from exc

    @staticmethod
    def _sma(values: Sequence[float], period: int) -> list[float]:
        return [
            sum(values[max(0, index - period + 1) : index + 1]) / min(index + 1, period)
            for index in range(len(values))
        ]

    @staticmethod
    def _ema(values: Sequence[float], period: int) -> list[float]:
        result: list[float] = []
        multiplier = 2.0 / (period + 1)
        for value in values:
            result.append(
                value if not result else (value * multiplier) + (result[-1] * (1 - multiplier))
            )
        return result

    def _rsi(self, values: Sequence[float], period: int) -> list[float]:
        result = [50.0]
        for index in range(1, len(values)):
            changes = [
                values[item] - values[item - 1]
                for item in range(max(1, index - period + 1), index + 1)
            ]
            gains = [change for change in changes if change > 0]
            losses = [-change for change in changes if change < 0]
            average_gain = sum(gains) / period
            average_loss = sum(losses) / period
            result.append(
                100.0
                if average_loss == 0
                else 100.0 - (100.0 / (1.0 + average_gain / average_loss))
            )
        return result

    def _macd(self, values: Sequence[float], fast: int, slow: int) -> list[float]:
        if fast < 1 or slow < 1:
            raise FeatureEngineeringError("MACD periods must be positive")
        fast_values, slow_values = self._ema(values, fast), self._ema(values, slow)
        return [fast_value - slow_value for fast_value, slow_value in zip(fast_values, slow_values)]

    def _atr(self, dataset: ResearchDataset, period: int) -> list[float]:
        high, low, close = (self._numbers(dataset, field) for field in ("high", "low", "close"))
        true_ranges = [high[0] - low[0]] + [
            max(
                high[index] - low[index],
                abs(high[index] - close[index - 1]),
                abs(low[index] - close[index - 1]),
            )
            for index in range(1, len(close))
        ]
        return self._sma(true_ranges, period)

    def _bollinger_width(self, values: Sequence[float], period: int, stddev: float) -> list[float]:
        result = []
        for index in range(len(values)):
            window = values[max(0, index - period + 1) : index + 1]
            mean = sum(window) / len(window)
            deviation = sqrt(sum((value - mean) ** 2 for value in window) / len(window))
            result.append(0.0 if mean == 0 else (2 * stddev * deviation) / mean)
        return result

    def _price_action(self, dataset: ResearchDataset, name: str) -> list[float]:
        close = self._numbers(dataset, "close")
        if name in {"return", "price_change"}:
            return [0.0] + [close[index] - close[index - 1] for index in range(1, len(close))]
        high, low = self._numbers(dataset, "high"), self._numbers(dataset, "low")
        return [
            (
                0.0
                if high[index] == low[index]
                else (close[index] - low[index]) / (high[index] - low[index])
            )
            for index in range(len(close))
        ]

    def _candlestick(self, dataset: ResearchDataset, name: str) -> list[float]:
        open_, close = self._numbers(dataset, "open"), self._numbers(dataset, "close")
        if name == "body":
            return [close[index] - open_[index] for index in range(len(close))]
        high, low = self._numbers(dataset, "high"), self._numbers(dataset, "low")
        return [high[index] - low[index] for index in range(len(close))]

    @staticmethod
    def _volume_change(values: Sequence[float]) -> list[float]:
        return [0.0] + [values[index] - values[index - 1] for index in range(1, len(values))]

    @staticmethod
    def _momentum(values: Sequence[float], period: int) -> list[float]:
        return [
            0.0 if index < period else values[index] - values[index - period]
            for index in range(len(values))
        ]

    @staticmethod
    def _volatility(values: Sequence[float], period: int) -> list[float]:
        result = []
        for index in range(len(values)):
            window = values[max(0, index - period + 1) : index + 1]
            mean = sum(window) / len(window)
            result.append(sqrt(sum((value - mean) ** 2 for value in window) / len(window)))
        return result

    @staticmethod
    def _timestamp(row: dict[str, Any]) -> datetime | None:
        value = row.get("timestamp")
        return value if isinstance(value, datetime) else None

    @staticmethod
    def _time_value(row: dict[str, Any], name: str) -> float:
        timestamp = ResearchFeatureEngineer._timestamp(row)
        if timestamp is None:
            raise FeatureEngineeringError("time features require datetime 'timestamp' values")
        return float(timestamp.hour if name == "hour" else timestamp.weekday())

    @staticmethod
    def _session_value(row: dict[str, Any]) -> float:
        timestamp = ResearchFeatureEngineer._timestamp(row)
        if timestamp is None:
            raise FeatureEngineeringError("session features require datetime 'timestamp' values")
        return float(timestamp.hour // 8)


FeatureEngineer = ResearchFeatureEngineer
