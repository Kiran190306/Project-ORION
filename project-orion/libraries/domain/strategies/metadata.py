"""Strategy metadata models for market and indicator requirements."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, FrozenSet

from libraries.domain.strategies.interfaces import (
    StrategyCapabilities,
    StrategyMetadata,
)


@dataclass(frozen=True, slots=True)
class MarketRequirement:
    """Requirement for a supported market type."""

    market: str
    required: bool = True


@dataclass(frozen=True, slots=True)
class TimeframeRequirement:
    """Requirement for a supported timeframe."""

    timeframe: str
    required: bool = False


@dataclass(frozen=True, slots=True)
class IndicatorRequirement:
    """Requirement for a technical indicator."""

    indicator: str
    required: bool = True
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StrategyMetadataImpl:
    """Concrete implementation of strategy metadata with requirements."""

    metadata: StrategyMetadata
    capabilities: StrategyCapabilities
    market_requirements: frozenset[MarketRequirement] = frozenset()
    timeframe_requirements: frozenset[TimeframeRequirement] = frozenset()
    indicator_requirements: frozenset[IndicatorRequirement] = frozenset()
