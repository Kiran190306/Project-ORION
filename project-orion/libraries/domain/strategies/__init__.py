"""
Project ORION - Strategy Framework (EPIC-006 Sprint-2).

A fully modular strategy framework that allows strategies to be
plugged into ORION without changing the core trading engine.

Provides:
- Core interfaces (Strategy, StrategyContext, StrategyResult)
- Strategy Registry with duplicate protection & version compatibility
- Strategy Manager for lifecycle orchestration
- Plugin Loader for extensibility
- Voting Engine (majority, weighted, confidence-weighted, consensus)
- Conflict Resolution (BUY/SELL/HOLD/EXIT)
- Composite Strategy execution
- Lifecycle management (init, start, pause, resume, stop, shutdown)
- Strategy Statistics tracking
"""

from __future__ import annotations

from libraries.domain.strategies.composite import CompositeStrategy
from libraries.domain.strategies.conflict_resolver import (
    ConflictResolutionStrategy,
    ConflictResolver,
    ConflictResult,
)
from libraries.domain.strategies.context import StrategyContext
from libraries.domain.strategies.exceptions import (
    StrategyError,
    StrategyExecutionError,
    StrategyNotFoundError,
    StrategyRegistrationError,
    StrategyValidationError,
)
from libraries.domain.strategies.interfaces import (
    Strategy,
    StrategyCapabilities,
    StrategyMetadata,
)
from libraries.domain.strategies.lifecycle import (
    LifecycleState,
    StrategyLifecycle,
)
from libraries.domain.strategies.loader import StrategyLoader
from libraries.domain.strategies.manager import StrategyManager, StrategyManagerConfig
from libraries.domain.strategies.metadata import (
    IndicatorRequirement,
    MarketRequirement,
    StrategyMetadataImpl,
    TimeframeRequirement,
)
from libraries.domain.strategies.models import (
    StrategyConfig,
    StrategyPriority,
    StrategyStatus,
)
from libraries.domain.strategies.registry import StrategyRegistry
from libraries.domain.strategies.statistics import (
    StrategyExecutionOutcome,
    StrategyStatistics,
    StrategyStats,
)
from libraries.domain.strategies.strategy import (
    BaseStrategy,
    BreakoutStrategy,
    EmaCrossStrategy,
    RsiStrategy,
)
from libraries.domain.strategies.voting import (
    VotingEngine,
    VotingMethod,
    VotingResult,
)

__all__ = [
    "BaseStrategy",
    "BreakoutStrategy",
    "CompositeStrategy",
    "ConflictResolutionStrategy",
    "ConflictResolver",
    "ConflictResult",
    "EmaCrossStrategy",
    "IndicatorRequirement",
    "LifecycleState",
    "MarketRequirement",
    "RsiStrategy",
    "Strategy",
    "StrategyCapabilities",
    "StrategyConfig",
    "StrategyContext",
    "StrategyError",
    "StrategyExecutionError",
    "StrategyLifecycle",
    "StrategyLoader",
    "StrategyManager",
    "StrategyManagerConfig",
    "StrategyMetadata",
    "StrategyMetadataImpl",
    "StrategyNotFoundError",
    "StrategyPriority",
    "StrategyRegistrationError",
    "StrategyStats",
    "StrategyStatistics",
    "StrategyStatus",
    "StrategyValidationError",
    "StrategyExecutionOutcome",
    "TimeframeRequirement",
    "VotingEngine",
    "VotingMethod",
    "VotingResult",
]
