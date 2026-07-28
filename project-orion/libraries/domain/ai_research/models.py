"""Validated, immutable domain models for the AI research foundation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping


def _frozen_mapping(values: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(values or {}))


def _required(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _finite(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be finite")


class MarketRegime(StrEnum):
    """A deterministic classification supplied by a regime detector port."""

    TRENDING = "trending"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_LIQUIDITY = "low_liquidity"
    UNKNOWN = "unknown"


class TrendDirection(StrEnum):
    """Direction of market trend."""

    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    UNKNOWN = "unknown"


class VolatilityLevel(StrEnum):
    """Level of market volatility."""

    HIGH = "high"
    LOW = "low"
    NORMAL = "normal"
    UNKNOWN = "unknown"


class LiquidityLevel(StrEnum):
    """Level of market liquidity."""

    HIGH = "high"
    LOW = "low"
    NORMAL = "normal"
    UNKNOWN = "unknown"


class MarketCondition(StrEnum):
    """Comprehensive market condition combining trend, volatility, and liquidity."""

    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    HIGH_LIQUIDITY = "high_liquidity"
    LOW_LIQUIDITY = "low_liquidity"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class ExperimentStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PlatformState(StrEnum):
    """Lifecycle state of the AI research platform."""

    INITIALIZING = "initializing"
    READY = "ready"
    SHUTDOWN = "shutdown"


@dataclass(frozen=True, slots=True)
class ResearchPlatformConfig:
    """Configuration owned by the research manager."""

    name: str = "orion-ai-research"
    version: str = "0.11.0-alpha.1"
    random_seed: int = 42
    execution_mode: str = "research"
    require_validation: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _required(self.name, "name")
        _required(self.version, "version")
        if not isinstance(self.random_seed, int) or isinstance(self.random_seed, bool):
            raise ValueError("random_seed must be an integer")
        if self.execution_mode not in {"research", "dry_run"}:
            raise ValueError("execution_mode must be 'research' or 'dry_run'")
        object.__setattr__(self, "metadata", _frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class ResearchDataset:
    """An in-memory, schema-validated research dataset."""

    dataset_id: str
    schema: tuple[str, ...]
    rows: tuple[Mapping[str, Any], ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _required(self.dataset_id, "dataset_id")
        if not self.schema or any(
            not isinstance(column, str) or not column for column in self.schema
        ):
            raise ValueError("schema must contain non-empty column names")
        if len(set(self.schema)) != len(self.schema):
            raise ValueError("schema column names must be unique")
        frozen_rows = tuple(MappingProxyType(dict(row)) for row in self.rows)
        required = set(self.schema)
        if any(not required.issubset(row) for row in frozen_rows):
            raise ValueError("every row must contain every schema column")
        object.__setattr__(self, "rows", frozen_rows)
        object.__setattr__(self, "metadata", _frozen_mapping(self.metadata))

    @property
    def row_count(self) -> int:
        return len(self.rows)


@dataclass(frozen=True, slots=True)
class FeatureVector:
    """One immutable, named set of values generated for an observation."""

    values: Mapping[str, float]
    timestamp: datetime | None = None

    def __post_init__(self) -> None:
        if not self.values:
            raise ValueError("values must not be empty")
        for name, value in self.values.items():
            _required(name, "feature name")
            _finite(value, f"feature '{name}'")
        object.__setattr__(self, "values", _frozen_mapping(self.values))


@dataclass(frozen=True, slots=True)
class FeatureDefinition:
    """Declarative feature specification; custom callables are injected separately."""

    name: str
    category: str
    parameters: Mapping[str, Any] = field(default_factory=dict)
    required_columns: tuple[str, ...] = ("close",)

    def __post_init__(self) -> None:
        _required(self.name, "name")
        if self.category not in {
            "trend",
            "momentum",
            "volatility",
            "price_action",
            "candlestick",
            "liquidity",
            "session",
            "time",
            "volume",
            "custom",
        }:
            raise ValueError("unsupported feature category")
        if not self.required_columns or any(not item for item in self.required_columns):
            raise ValueError("required_columns must not be empty")
        object.__setattr__(self, "parameters", _frozen_mapping(self.parameters))


@dataclass(frozen=True, slots=True)
class StrategyCandidate:
    strategy_id: str
    name: str
    version: str = "1.0.0"
    tags: frozenset[str] = field(default_factory=frozenset)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _required(self.strategy_id, "strategy_id")
        _required(self.name, "name")
        _required(self.version, "version")
        if any(not isinstance(tag, str) or not tag for tag in self.tags):
            raise ValueError("tags must contain non-empty strings")
        object.__setattr__(self, "tags", frozenset(self.tags))
        object.__setattr__(self, "metadata", _frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class StrategyEvaluation:
    strategy_id: str
    metrics: Mapping[str, float]
    dataset_id: str
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        _required(self.strategy_id, "strategy_id")
        _required(self.dataset_id, "dataset_id")
        if not self.metrics:
            raise ValueError("metrics must not be empty")
        for name, value in self.metrics.items():
            _required(name, "metric name")
            _finite(value, f"metric '{name}'")
        object.__setattr__(self, "metrics", _frozen_mapping(self.metrics))


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    """A transport model reserved for a future OptimizationEngine implementation."""

    strategy_id: str
    best_parameters: Mapping[str, Any]
    score: float

    def __post_init__(self) -> None:
        _required(self.strategy_id, "strategy_id")
        _finite(self.score, "score")
        object.__setattr__(self, "best_parameters", _frozen_mapping(self.best_parameters))


@dataclass(frozen=True, slots=True)
class Experiment:
    experiment_id: str
    name: str
    version: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        _required(self.experiment_id, "experiment_id")
        _required(self.name, "name")
        _required(self.version, "version")
        object.__setattr__(self, "metadata", _frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class ExperimentResult:
    experiment_id: str
    status: ExperimentStatus
    metrics: Mapping[str, float] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _required(self.experiment_id, "experiment_id")
        for name, value in self.metrics.items():
            _finite(value, f"metric '{name}'")
        object.__setattr__(self, "metrics", _frozen_mapping(self.metrics))
        object.__setattr__(self, "metadata", _frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class LeaderboardEntry:
    rank: int
    evaluation: StrategyEvaluation
    composite_score: float

    def __post_init__(self) -> None:
        if self.rank < 1:
            raise ValueError("rank must be positive")
        _finite(self.composite_score, "composite_score")


@dataclass(frozen=True, slots=True)
class ValidationResult:
    strategy_id: str
    is_valid: bool
    reasons: tuple[str, ...] = ()
    metrics: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _required(self.strategy_id, "strategy_id")
        if any(not reason for reason in self.reasons):
            raise ValueError("reasons must contain non-empty strings")
        for name, value in self.metrics.items():
            _finite(value, f"metric '{name}'")
        object.__setattr__(self, "metrics", _frozen_mapping(self.metrics))


class RecommendationAction(StrEnum):
    """Action recommended by the recommendation engine."""

    ACCEPT = "accept"
    REJECT = "reject"
    NEEDS_MORE_DATA = "needs_more_data"
    OVERFIT_RISK = "overfit_risk"
    PROMISING = "promising"
    HIGH_CONFIDENCE = "high_confidence"
    LOW_CONFIDENCE = "low_confidence"
    INSUFFICIENT_SAMPLE = "insufficient_sample"


@dataclass(frozen=True, slots=True)
class Recommendation:
    strategy_id: str
    rationale: str
    confidence: float
    regime: MarketRegime = MarketRegime.UNKNOWN
    action: RecommendationAction = RecommendationAction.LOW_CONFIDENCE
    reason_codes: tuple[str, ...] = ()
    supporting_metrics: Mapping[str, float] = field(default_factory=dict)
    validation_summary: str = ""

    def __post_init__(self) -> None:
        _required(self.strategy_id, "strategy_id")
        _required(self.rationale, "rationale")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if any(not code for code in self.reason_codes):
            raise ValueError("reason_codes must contain non-empty strings")
        for name, value in self.supporting_metrics.items():
            _finite(value, f"supporting_metric '{name}'")
        object.__setattr__(self, "supporting_metrics", _frozen_mapping(self.supporting_metrics))


@dataclass(frozen=True, slots=True)
class ResearchResult:
    dataset_id: str
    evaluations: tuple[StrategyEvaluation, ...]
    leaderboard: tuple[LeaderboardEntry, ...]
    experiment: ExperimentResult | None = None

    def __post_init__(self) -> None:
        _required(self.dataset_id, "dataset_id")
        evaluated_ids = {item.strategy_id for item in self.evaluations}
        if any(entry.evaluation.strategy_id not in evaluated_ids for entry in self.leaderboard):
            raise ValueError("leaderboard entries must reference an evaluation")


# ═══════════════════════════════════════════════════════════════════════
# Sprint-3 — Market Intelligence, Recommendation & Leaderboard
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class TrendClassificationResult:
    """Result of trend classification on a dataset."""

    direction: TrendDirection
    strength: float  # 0.0 to 1.0
    slope: float = 0.0
    details: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError("strength must be between 0 and 1")
        for name, value in self.details.items():
            _finite(value, f"detail '{name}'")
        object.__setattr__(self, "details", _frozen_mapping(self.details))


@dataclass(frozen=True, slots=True)
class VolatilityClassificationResult:
    """Result of volatility classification on a dataset."""

    level: VolatilityLevel
    percentile: float  # 0.0 to 1.0, current volatility percentile
    atr_value: float = 0.0
    details: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.percentile <= 1.0:
            raise ValueError("percentile must be between 0 and 1")
        for name, value in self.details.items():
            _finite(value, f"detail '{name}'")
        object.__setattr__(self, "details", _frozen_mapping(self.details))


@dataclass(frozen=True, slots=True)
class LiquidityClassificationResult:
    """Result of liquidity classification on a dataset."""

    level: LiquidityLevel
    score: float  # 0.0 to 1.0 liquidity score
    avg_volume: float = 0.0
    details: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0 and 1")
        for name, value in self.details.items():
            _finite(value, f"detail '{name}'")
        object.__setattr__(self, "details", _frozen_mapping(self.details))


@dataclass(frozen=True, slots=True)
class MarketClassificationResult:
    """Comprehensive market classification combining all classifiers."""

    condition: MarketCondition
    regime: MarketRegime
    trend: TrendClassificationResult
    volatility: VolatilityClassificationResult
    liquidity: LiquidityClassificationResult
    confidence: float = 1.0
    details: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        for name, value in self.details.items():
            _finite(value, f"detail '{name}'")
        object.__setattr__(self, "details", _frozen_mapping(self.details))


@dataclass(frozen=True, slots=True)
class LeaderboardFilter:
    """Filter criteria for querying the leaderboard."""

    tags: frozenset[str] = field(default_factory=frozenset)
    min_score: float = 0.0
    max_score: float = float("inf")
    version: str | None = None
    top_n: int | None = None
    sort_by: str = "composite_score"
    sort_ascending: bool = False

    def __post_init__(self) -> None:
        if self.top_n is not None and self.top_n < 1:
            raise ValueError("top_n must be positive")
        if self.min_score < 0.0:
            raise ValueError("min_score must be non-negative")
        object.__setattr__(self, "tags", frozenset(self.tags))


@dataclass(frozen=True, slots=True)
class LeaderboardComparison:
    """Comparison between two leaderboard snapshots."""

    strategy_id: str
    rank_change: int
    score_change: float
    previous_rank: int
    current_rank: int
    previous_score: float
    current_score: float


# ═══════════════════════════════════════════════════════════════════════
# Sprint-2 — Optimization & Validation Framework
# ═══════════════════════════════════════════════════════════════════════


class ParameterType(StrEnum):
    """Supported parameter types for search spaces."""

    INT = "int"
    FLOAT = "float"
    DECIMAL = "decimal"
    BOOL = "bool"
    CATEGORICAL = "categorical"
    ENUM = "enum"


class OptimizationState(StrEnum):
    """State of an optimization run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


# ─── Parameter Space Models ──────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ParameterConstraint:
    """Constraint on a single parameter within a search space."""

    min_value: float | Decimal | None = None
    max_value: float | Decimal | None = None
    step: float | Decimal | None = None
    values: tuple[Any, ...] = ()

    def __post_init__(self) -> None:
        if self.min_value is not None and self.max_value is not None:
            if self.min_value > self.max_value:
                raise ValueError("min_value must not exceed max_value")
        if self.step is not None and self.step <= 0:
            raise ValueError("step must be positive")
        if not self.values and self.min_value is None and self.max_value is None:
            pass  # unconstrained is valid


@dataclass(frozen=True, slots=True)
class ParameterDefinition:
    """Definition of a single parameter in a search space."""

    name: str
    parameter_type: ParameterType
    default: Any = None
    constraint: ParameterConstraint = field(default_factory=ParameterConstraint)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _required(self.name, "name")
        object.__setattr__(self, "metadata", _frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class ParameterSpace:
    """A complete search space composed of parameter definitions."""

    parameters: tuple[ParameterDefinition, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        names = [p.name for p in self.parameters]
        if len(names) != len(set(names)):
            raise ValueError("parameter names must be unique")
        object.__setattr__(self, "metadata", _frozen_mapping(self.metadata))

    @property
    def size(self) -> int:
        """Return the number of parameters."""
        return len(self.parameters)


# ─── Fitness Models ──────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class FitnessWeights:
    """Configurable weights for composite fitness scoring."""

    sharpe: float = 0.25
    sortino: float = 0.15
    calmar: float = 0.10
    profit_factor: float = 0.15
    expectancy: float = 0.10
    max_drawdown: float = -0.10
    recovery_factor: float = 0.10
    win_rate: float = 0.05
    risk_reward: float = 0.10

    def __post_init__(self) -> None:
        for name, value in [
            ("sharpe", self.sharpe),
            ("sortino", self.sortino),
            ("calmar", self.calmar),
            ("profit_factor", self.profit_factor),
            ("expectancy", self.expectancy),
            ("max_drawdown", self.max_drawdown),
            ("recovery_factor", self.recovery_factor),
            ("win_rate", self.win_rate),
            ("risk_reward", self.risk_reward),
        ]:
            _finite(value, name)


@dataclass(frozen=True, slots=True)
class FitnessResult:
    """Result of a composite fitness calculation."""

    strategy_id: str
    composite_score: float
    component_scores: dict[str, float]

    def __post_init__(self) -> None:
        _required(self.strategy_id, "strategy_id")
        _finite(self.composite_score, "composite_score")
        for name, value in self.component_scores.items():
            _finite(value, f"component '{name}'")


# ─── Validation Models ───────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class WalkForwardWindow:
    """Metadata for a single walk-forward window."""

    window_index: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    train_metrics: Mapping[str, float] = field(default_factory=dict)
    test_metrics: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.window_index < 0:
            raise ValueError("window_index must be non-negative")
        for name, value in self.train_metrics.items():
            _finite(value, f"train_metrics.{name}")
        for name, value in self.test_metrics.items():
            _finite(value, f"test_metrics.{name}")
        object.__setattr__(self, "train_metrics", _frozen_mapping(self.train_metrics))
        object.__setattr__(self, "test_metrics", _frozen_mapping(self.test_metrics))


@dataclass(frozen=True, slots=True)
class WalkForwardResult:
    """Aggregated walk-forward validation result."""

    windows: tuple[WalkForwardWindow, ...]
    robustness_score: float = 0.0

    def __post_init__(self) -> None:
        _finite(self.robustness_score, "robustness_score")

    @property
    def num_windows(self) -> int:
        return len(self.windows)


@dataclass(frozen=True, slots=True)
class CrossValidationFold:
    """Metadata for a single cross-validation fold."""

    fold_index: int
    train_indices: tuple[int, ...]
    test_indices: tuple[int, ...]
    score: float = 0.0

    def __post_init__(self) -> None:
        if self.fold_index < 0:
            raise ValueError("fold_index must be non-negative")
        if not self.train_indices:
            raise ValueError("train_indices must not be empty")
        if not self.test_indices:
            raise ValueError("test_indices must not be empty")
        _finite(self.score, "score")


@dataclass(frozen=True, slots=True)
class CrossValidationResult:
    """Aggregated cross-validation result."""

    folds: tuple[CrossValidationFold, ...]
    mean_score: float = 0.0
    std_score: float = 0.0

    def __post_init__(self) -> None:
        _finite(self.mean_score, "mean_score")
        _finite(self.std_score, "std_score")

    @property
    def num_folds(self) -> int:
        return len(self.folds)


@dataclass(frozen=True, slots=True)
class RobustnessResult:
    """Result of a robustness analysis."""

    strategy_id: str
    score: float
    details: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _required(self.strategy_id, "strategy_id")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("robustness score must be between 0 and 1")
        for name, value in self.details.items():
            _finite(value, f"detail '{name}'")
        object.__setattr__(self, "details", _frozen_mapping(self.details))


@dataclass(frozen=True, slots=True)
class OverfittingReport:
    """Report on potential overfitting indicators."""

    strategy_id: str
    is_overfit: bool
    indicators: Mapping[str, float] = field(default_factory=dict)
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _required(self.strategy_id, "strategy_id")
        for name, value in self.indicators.items():
            _finite(value, f"indicator '{name}'")
        if any(not reason for reason in self.reasons):
            raise ValueError("reasons must contain non-empty strings")
        object.__setattr__(self, "indicators", _frozen_mapping(self.indicators))


@dataclass(frozen=True, slots=True)
class ParameterStabilityReport:
    """Report on parameter stability across walk-forward windows."""

    strategy_id: str
    stability_score: float
    parameter_std: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _required(self.strategy_id, "strategy_id")
        if not 0.0 <= self.stability_score <= 1.0:
            raise ValueError("stability_score must be between 0 and 1")
        for name, value in self.parameter_std.items():
            _finite(value, f"parameter_std '{name}'")
        object.__setattr__(self, "parameter_std", _frozen_mapping(self.parameter_std))


# ─── Experiment Database Models ──────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ExperimentRecord:
    """Persistent record of an experiment."""

    experiment_id: str
    name: str
    status: ExperimentStatus
    version: str
    tags: frozenset[str] = field(default_factory=frozenset)
    metrics: Mapping[str, float] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        _required(self.experiment_id, "experiment_id")
        _required(self.name, "name")
        _required(self.version, "version")
        object.__setattr__(self, "tags", frozenset(self.tags))
        object.__setattr__(self, "metrics", _frozen_mapping(self.metrics))
        object.__setattr__(self, "metadata", _frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class ExperimentQuery:
    """Filters for querying experiments."""

    status: ExperimentStatus | None = None
    tags: frozenset[str] | None = None
    name_pattern: str | None = None
    limit: int = 100
    offset: int = 0

    def __post_init__(self) -> None:
        if self.limit < 1:
            raise ValueError("limit must be positive")
        if self.offset < 0:
            raise ValueError("offset must be non-negative")
        if self.tags is not None:
            object.__setattr__(self, "tags", frozenset(self.tags))


# ─── Version Models ──────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class VersionRecord:
    """Record of a versioned entity."""

    entity_type: str
    entity_id: str
    version: str
    previous_version: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        _required(self.entity_type, "entity_type")
        _required(self.entity_id, "entity_id")
        _required(self.version, "version")
        object.__setattr__(self, "metadata", _frozen_mapping(self.metadata))


# ─── Parallel Execution Models ───────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TaskResult:
    """Result of a single parallel task execution."""

    task_id: str
    success: bool
    result: Any = None
    error: str | None = None

    def __post_init__(self) -> None:
        _required(self.task_id, "task_id")


@dataclass(frozen=True, slots=True)
class ProgressReport:
    """Progress report for long-running operations."""

    completed: int
    total: int
    errors: int = 0
    message: str = ""

    def __post_init__(self) -> None:
        if self.completed < 0:
            raise ValueError("completed must be non-negative")
        if self.total < 0:
            raise ValueError("total must be non-negative")
        if self.errors < 0:
            raise ValueError("errors must be non-negative")

    @property
    def progress_pct(self) -> float:
        return (self.completed / self.total * 100) if self.total > 0 else 100.0
