"""Deterministic Strategy Registry and Catalogue for Quantitative Research.

Provides central discovery, schema inspection, parameter validation,
and factory instantiation of registered trading strategies without arbitrary
code execution.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, ClassVar

from libraries.domain.strategy.base import BaseStrategy
from libraries.domain.strategy.models import StrategyMetadata
from libraries.domain.strategy.strategies import (
    BreakoutStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    TrendFollowingStrategy,
)


class UnknownStrategyError(ValueError):
    """Raised when an requested strategy ID is not in the registry."""


class InvalidStrategyParameterError(ValueError):
    """Raised when a strategy parameter fails schema validation."""


@dataclass(frozen=True, slots=True)
class ParameterDefinition:
    """Schema definition for a strategy parameter."""

    name: str
    param_type: str  # "integer", "float", "string", "boolean"
    default: Any
    min_value: float | int | None = None
    max_value: float | int | None = None
    options: tuple[str, ...] | None = None
    description: str = ""


@dataclass(frozen=True, slots=True)
class StrategyCatalogueEntry:
    """Metadata and schema specification for a registered strategy."""

    strategy_id: str
    name: str
    description: str
    category: str
    strategy_class: type[BaseStrategy]
    version: str = "1.0.0"
    is_deterministic: bool = True
    supported_instruments: tuple[str, ...] = (
        "EUR/USD",
        "GBP/USD",
        "USD/JPY",
        "AUD/USD",
        "USD/CHF",
        "EUR/GBP",
    )
    supported_timeframes: tuple[str, ...] = ("M1", "M5", "M15", "H1", "H4", "D1")
    parameters: tuple[ParameterDefinition, ...] = field(default_factory=tuple)


class StrategyRegistry:
    """Registry managing available strategies, parameter schemas, and factories."""

    _entries: ClassVar[dict[str, StrategyCatalogueEntry]] = {}

    @classmethod
    def register(cls, entry: StrategyCatalogueEntry) -> None:
        """Register a new strategy catalogue entry."""
        cls._entries[entry.strategy_id] = entry

    @classmethod
    def get(cls, strategy_id: str) -> StrategyCatalogueEntry:
        """Retrieve catalogue entry by strategy ID."""
        if strategy_id not in cls._entries:
            raise UnknownStrategyError(f"Strategy '{strategy_id}' is not registered in StrategyRegistry")
        return cls._entries[strategy_id]

    @classmethod
    def list_strategies(cls) -> list[StrategyCatalogueEntry]:
        """List all registered strategy entries."""
        return list(cls._entries.values())

    @classmethod
    def validate_parameters(
        cls,
        strategy_id: str,
        parameters: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Validate and sanitize parameters against the strategy's schema.

        Rejects unknown parameters, NaN, Infinity, and out-of-bounds values.
        Applies schema defaults for missing parameters.
        """
        entry = cls.get(strategy_id)
        input_params = dict(parameters or {})
        validated: dict[str, Any] = {}
        allowed_param_names = {p.name for p in entry.parameters}

        # Check for unknown parameters
        unknown = set(input_params.keys()) - allowed_param_names
        if unknown:
            raise InvalidStrategyParameterError(
                f"Unknown parameters for strategy '{strategy_id}': {', '.join(sorted(unknown))}"
            )

        for p in entry.parameters:
            raw_value = input_params.get(p.name, p.default)

            if p.param_type == "integer":
                if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
                    raise InvalidStrategyParameterError(
                        f"Parameter '{p.name}' must be an integer, got {type(raw_value).__name__}"
                    )
                if isinstance(raw_value, float) and not raw_value.is_integer():
                    raise InvalidStrategyParameterError(
                        f"Parameter '{p.name}' must be an integer, got non-integral float {raw_value}"
                    )
                val_int = int(raw_value)
                if p.min_value is not None and val_int < p.min_value:
                    raise InvalidStrategyParameterError(
                        f"Parameter '{p.name}' ({val_int}) cannot be less than minimum {p.min_value}"
                    )
                if p.max_value is not None and val_int > p.max_value:
                    raise InvalidStrategyParameterError(
                        f"Parameter '{p.name}' ({val_int}) cannot exceed maximum {p.max_value}"
                    )
                validated[p.name] = val_int

            elif p.param_type == "float":
                if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
                    raise InvalidStrategyParameterError(
                        f"Parameter '{p.name}' must be a number, got {type(raw_value).__name__}"
                    )
                val_float = float(raw_value)
                if math.isnan(val_float) or math.isinf(val_float):
                    raise InvalidStrategyParameterError(
                        f"Parameter '{p.name}' cannot be NaN or Infinity"
                    )
                if p.min_value is not None and val_float < p.min_value:
                    raise InvalidStrategyParameterError(
                        f"Parameter '{p.name}' ({val_float}) cannot be less than minimum {p.min_value}"
                    )
                if p.max_value is not None and val_float > p.max_value:
                    raise InvalidStrategyParameterError(
                        f"Parameter '{p.name}' ({val_float}) cannot exceed maximum {p.max_value}"
                    )
                validated[p.name] = val_float

            elif p.param_type == "string":
                if not isinstance(raw_value, str):
                    raise InvalidStrategyParameterError(
                        f"Parameter '{p.name}' must be a string, got {type(raw_value).__name__}"
                    )
                if p.options is not None and raw_value not in p.options:
                    raise InvalidStrategyParameterError(
                        f"Parameter '{p.name}' value '{raw_value}' is not among allowed options: {p.options}"
                    )
                validated[p.name] = raw_value

            elif p.param_type == "boolean":
                if not isinstance(raw_value, bool):
                    raise InvalidStrategyParameterError(
                        f"Parameter '{p.name}' must be a boolean, got {type(raw_value).__name__}"
                    )
                validated[p.name] = raw_value

            else:
                validated[p.name] = raw_value

        return validated

    @classmethod
    def create_strategy(
        cls,
        strategy_id: str,
        parameters: dict[str, Any] | None = None,
        symbols: list[str] | None = None,
    ) -> BaseStrategy:
        """Create and initialize a validated strategy instance from the registry."""
        entry = cls.get(strategy_id)
        validated_params = cls.validate_parameters(strategy_id, parameters)

        active_symbols = tuple(symbols) if symbols else entry.supported_instruments

        metadata = StrategyMetadata(
            strategy_id=entry.strategy_id,
            name=entry.name,
            version=entry.version,
            author="Project ORION Quant Lab",
            description=entry.description,
            tags=list(active_symbols),
        )

        instance = entry.strategy_class(metadata, **validated_params)
        instance.initialize()
        return instance


# Register Default Reference Strategies
StrategyRegistry.register(
    StrategyCatalogueEntry(
        strategy_id="trend_following",
        name="Trend Following",
        description="Dual moving average trend-following strategy with momentum filter.",
        category="trend",
        strategy_class=TrendFollowingStrategy,
        version="1.0.0",
        is_deterministic=True,
        parameters=(
            ParameterDefinition(
                name="fast_period",
                param_type="integer",
                default=10,
                min_value=2,
                max_value=100,
                description="Fast moving average period",
            ),
            ParameterDefinition(
                name="slow_period",
                param_type="integer",
                default=30,
                min_value=5,
                max_value=300,
                description="Slow moving average period",
            ),
        ),
    )
)

StrategyRegistry.register(
    StrategyCatalogueEntry(
        strategy_id="mean_reversion",
        name="Mean Reversion",
        description="Statistical mean reversion identifying price deviation from rolling mean.",
        category="reversion",
        strategy_class=MeanReversionStrategy,
        version="1.0.0",
        is_deterministic=True,
        parameters=(
            ParameterDefinition(
                name="lookback_period",
                param_type="integer",
                default=20,
                min_value=5,
                max_value=100,
                description="Rolling average lookback period",
            ),
            ParameterDefinition(
                name="entry_threshold",
                param_type="float",
                default=2.0,
                min_value=0.5,
                max_value=5.0,
                description="Z-score entry threshold multiplier",
            ),
        ),
    )
)

StrategyRegistry.register(
    StrategyCatalogueEntry(
        strategy_id="breakout",
        name="Breakout",
        description="Donchian-style channel breakout strategy capturing volatility expansions.",
        category="breakout",
        strategy_class=BreakoutStrategy,
        version="1.0.0",
        is_deterministic=True,
        parameters=(
            ParameterDefinition(
                name="channel_period",
                param_type="integer",
                default=20,
                min_value=5,
                max_value=100,
                description="High/low channel lookback period",
            ),
            ParameterDefinition(
                name="breakout_multiplier",
                param_type="float",
                default=1.0,
                min_value=0.1,
                max_value=5.0,
                description="Channel breakout buffer multiplier",
            ),
        ),
    )
)

StrategyRegistry.register(
    StrategyCatalogueEntry(
        strategy_id="momentum",
        name="Momentum",
        description="Rate of change price momentum strategy capturing directional velocity.",
        category="momentum",
        strategy_class=MomentumStrategy,
        version="1.0.0",
        is_deterministic=True,
        parameters=(
            ParameterDefinition(
                name="momentum_period",
                param_type="integer",
                default=14,
                min_value=2,
                max_value=50,
                description="Rate-of-change lookback period",
            ),
            ParameterDefinition(
                name="momentum_threshold",
                param_type="float",
                default=0.02,
                min_value=0.001,
                max_value=0.20,
                description="Minimum velocity threshold required to trigger a signal",
            ),
        ),
    )
)
