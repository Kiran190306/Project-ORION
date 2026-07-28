"""Dependency-inversion ports for the AI research domain."""

from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from libraries.domain.ai_research.context import ResearchContext
from libraries.domain.ai_research.models import (
    Experiment,
    ExperimentResult,
    FeatureDefinition,
    FeatureVector,
    LeaderboardEntry,
    MarketRegime,
    OptimizationResult,
    Recommendation,
    ResearchDataset,
    ResearchResult,
    StrategyCandidate,
    StrategyEvaluation,
    ValidationResult,
)


@runtime_checkable
class ResearchEngine(Protocol):
    """Protocol for the research engine orchestrator."""

    async def run(self, context: ResearchContext) -> ResearchResult: ...


@runtime_checkable
class StrategyRepository(Protocol):
    """Protocol for strategy metadata persistence."""

    async def register(self, strategy: StrategyCandidate) -> None: ...
    async def remove(self, strategy_id: str) -> bool: ...
    async def get_by_id(self, strategy_id: str) -> StrategyCandidate | None: ...
    async def list(self, tags: frozenset[str] | None = None) -> tuple[StrategyCandidate, ...]: ...


@runtime_checkable
class DatasetBuilder(Protocol):
    """Protocol for constructing validated datasets."""

    async def build(
        self, dataset_id: str, rows: Sequence[Mapping[str, Any]]
    ) -> ResearchDataset: ...
    def split_train_test(
        self, dataset: ResearchDataset, train_fraction: float = 0.8
    ) -> tuple[ResearchDataset, ResearchDataset]: ...
    def split_walk_forward(
        self, dataset: ResearchDataset, train_size: int, test_size: int
    ) -> tuple[tuple[ResearchDataset, ResearchDataset], ...]: ...


@runtime_checkable
class FeatureEngineer(Protocol):
    """Protocol for computing feature vectors from datasets."""

    async def engineer(
        self, dataset: ResearchDataset, definitions: Sequence[FeatureDefinition]
    ) -> tuple[FeatureVector, ...]: ...


@runtime_checkable
class StrategyEvaluator(Protocol):
    """Protocol for evaluating a single strategy against a dataset."""

    async def evaluate(
        self, strategy: StrategyCandidate, dataset: ResearchDataset
    ) -> StrategyEvaluation: ...


@runtime_checkable
class StrategyRanker(Protocol):
    """Protocol for ranking evaluated strategies."""

    async def rank(
        self, evaluations: Sequence[StrategyEvaluation]
    ) -> tuple[LeaderboardEntry, ...]: ...


@runtime_checkable
class ExperimentTracker(Protocol):
    """Protocol for tracking experiment lifecycle."""

    async def create(self, experiment: Experiment) -> None: ...
    async def update_status(self, experiment_id: str, status: str) -> None: ...
    async def finish(self, result: ExperimentResult) -> None: ...


@runtime_checkable
class ValidationEngine(Protocol):
    """Protocol for strategy validation."""

    async def validate(
        self, strategy: StrategyCandidate, evaluation: StrategyEvaluation
    ) -> ValidationResult: ...


@runtime_checkable
class RecommendationEngine(Protocol):
    """Protocol for generating strategy recommendations."""

    async def recommend(self, entry: LeaderboardEntry, regime: MarketRegime) -> Recommendation: ...


@runtime_checkable
class OptimizationEngine(Protocol):
    """Protocol reserved for future optimization implementations."""

    async def optimize(
        self, strategy: StrategyCandidate, dataset: ResearchDataset
    ) -> OptimizationResult: ...


@runtime_checkable
class MarketRegimeDetector(Protocol):
    """Protocol for detecting market regimes from datasets."""

    async def detect(self, dataset: ResearchDataset) -> MarketRegime: ...


# ─── Backward-compatible aliases ─────────────────────────────────────────
StrategyEvaluatorProtocol = StrategyEvaluator
FeatureEngineerProtocol = FeatureEngineer
StrategyPersistencePort = StrategyRepository
ResearchRepositoryPort = StrategyRepository
DatasetProvider = DatasetBuilder
MarketDataProvider = DatasetBuilder
RiskAssessorPort = ValidationEngine
PortfolioSimulatorPort = ValidationEngine
ModelPersistencePort = ExperimentTracker
OptimizationHook = OptimizationEngine
