"""
Project ORION - EPIC-011: Institutional AI Strategy Research & Optimization Platform.

A production-grade institutional AI research platform to discover, evaluate, compare,
optimize, and rank trading strategies using the historical research framework from
EPIC-010 (Institutional Backtesting & Quantitative Research Laboratory).

Architecture Layers:
    Foundation Layer     — Models, Interfaces, Exceptions, Context
    Feature Layer        — Feature Engineering, Dataset Builder
    Strategy Layer       — Strategy Repository, Evaluator, Ranker
    Optimization Layer   — Parameter Space, Grid Search, Random Search
    Validation Layer     — Walk Forward, Cross Validation, Robustness, Overfitting
    Analysis Layer       — Fitness Engine, Parameter Stability
    Recommender Layer    — Recommendation Engine
    Persistence Layer    — Experiment Database, Version Manager
    Orchestration Layer  — Engine, Manager, Experiment Tracker

Dependency Inversion:
    All external dependencies injected through Protocol ports (interfaces.py).
    No concrete implementations of external services.
    All models are @dataclass(frozen=True, slots=True).
    No UI code. No hardcoded datasets.

Execution Pipeline:
    AI Recommendation -> Strategy Validation -> Risk Engine -> Execution Engine -> Broker Layer
    (This module produces recommendations/rankings only - does NOT execute trades)
"""

from __future__ import annotations

# ─── Foundation Layer ───────────────────────────────────────
from libraries.domain.ai_research.context import AIResearchContext, ResearchContext

# ─── Validation Layer ───────────────────────────────────────
from libraries.domain.ai_research.cross_validation import CrossValidator

# ─── Feature Layer ──────────────────────────────────────────
from libraries.domain.ai_research.dataset_builder import ResearchDatasetBuilder

# ─── Orchestration Layer ────────────────────────────────────
from libraries.domain.ai_research.engine import AIResearchEngine
from libraries.domain.ai_research.exceptions import (
    AIResearchError,
    ConfigurationError,
    CrossValidationError,
    DatasetError,
    ExperimentDatabaseError,
    ExperimentError,
    FeatureEngineeringError,
    FitnessError,
    OptimizationError,
    OverfittingError,
    ParallelExecutionError,
    ParameterSpaceError,
    ParameterStabilityError,
    RankingError,
    RecommendationError,
    RepositoryError,
    RobustnessError,
    StrategyError,
    ValidationError,
    VersionError,
    WalkForwardError,
)

# ─── Persistence Layer ──────────────────────────────────────
from libraries.domain.ai_research.experiment_database import ExperimentDatabase
from libraries.domain.ai_research.experiment_tracker import (
    ExperimentTracker,
    InMemoryExperimentTracker,
)
from libraries.domain.ai_research.feature_engineering import (
    FeatureEngineer,
    ResearchFeatureEngineer,
)

# ─── Analysis Layer ─────────────────────────────────────────
from libraries.domain.ai_research.fitness_engine import FitnessEngine

# ─── Optimization Layer ─────────────────────────────────────
from libraries.domain.ai_research.grid_search import GridSearchOptimizer
from libraries.domain.ai_research.interfaces import (
    DatasetProvider,
    MarketDataProvider,
    MarketRegimeDetector,
    ModelPersistencePort,
    OptimizationEngine,
    OptimizationHook,
    PortfolioSimulatorPort,
    RecommendationEngine,
    ResearchEngine,
    ResearchRepositoryPort,
    RiskAssessorPort,
    StrategyPersistencePort,
)
from libraries.domain.ai_research.interfaces import StrategyRepository as StrategyRepositoryProtocol
from libraries.domain.ai_research.interfaces import (
    ValidationEngine,
)

# ─── Leaderboard ────────────────────────────────────────────
from libraries.domain.ai_research.leaderboard import Leaderboard
from libraries.domain.ai_research.liquidity_classifier import LiquidityClassifier
from libraries.domain.ai_research.manager import AIResearchManager
from libraries.domain.ai_research.market_classifier import MarketClassifier

# ─── Market Intelligence Layer ──────────────────────────────
from libraries.domain.ai_research.market_regime_detector import MarketRegimeDetector
from libraries.domain.ai_research.models import (
    CrossValidationFold,
    CrossValidationResult,
    Experiment,
    ExperimentQuery,
    ExperimentRecord,
    ExperimentResult,
    ExperimentStatus,
    FeatureDefinition,
    FeatureVector,
    FitnessResult,
    FitnessWeights,
    LeaderboardEntry,
    MarketRegime,
    OptimizationResult,
    OptimizationState,
    OverfittingReport,
    ParameterConstraint,
    ParameterDefinition,
    ParameterSpace,
    ParameterStabilityReport,
    ParameterType,
    PlatformState,
    ProgressReport,
    Recommendation,
    RecommendationAction,
    ResearchDataset,
    ResearchPlatformConfig,
    ResearchResult,
    RobustnessResult,
    StrategyCandidate,
    StrategyEvaluation,
    TaskResult,
    ValidationResult,
    VersionRecord,
    WalkForwardResult,
    WalkForwardWindow,
)
from libraries.domain.ai_research.overfitting_detector import OverfittingDetector

# ─── Parallel Execution Layer ───────────────────────────────
from libraries.domain.ai_research.parallel_executor import ParallelExecutor
from libraries.domain.ai_research.parameter_space import ParameterSpaceBuilder
from libraries.domain.ai_research.parameter_stability import ParameterStabilityAnalyzer
from libraries.domain.ai_research.random_search import RandomSearchOptimizer

# ─── Recommender Layer ──────────────────────────────────────
from libraries.domain.ai_research.recommendation_engine import RecommendationEngine
from libraries.domain.ai_research.robustness_analyzer import RobustnessAnalyzer

# ─── Strategy Layer ─────────────────────────────────────────
from libraries.domain.ai_research.strategy_evaluator import (
    MetadataStrategyEvaluator,
    StrategyEvaluator,
)
from libraries.domain.ai_research.strategy_ranker import CompositeStrategyRanker, StrategyRanker
from libraries.domain.ai_research.strategy_repository import (
    InMemoryStrategyRepository,
    StrategyRepository,
)
from libraries.domain.ai_research.trend_classifier import TrendClassifier
from libraries.domain.ai_research.version_manager import VersionManager
from libraries.domain.ai_research.volatility_classifier import VolatilityClassifier
from libraries.domain.ai_research.walk_forward_validator import WalkForwardValidator

__all__ = [
    # ─── Exceptions ────────────────────────────────────
    "AIResearchError",
    "ConfigurationError",
    "CrossValidationError",
    "DatasetError",
    "ExperimentDatabaseError",
    "ExperimentError",
    "FeatureEngineeringError",
    "FitnessError",
    "OptimizationError",
    "OverfittingError",
    "ParallelExecutionError",
    "ParameterSpaceError",
    "ParameterStabilityError",
    "RankingError",
    "RecommendationError",
    "RepositoryError",
    "RobustnessError",
    "StrategyError",
    "ValidationError",
    "VersionError",
    "WalkForwardError",
    # ─── Models ────────────────────────────────────────
    "CrossValidationFold",
    "CrossValidationResult",
    "Experiment",
    "ExperimentQuery",
    "ExperimentRecord",
    "ExperimentResult",
    "ExperimentStatus",
    "FeatureDefinition",
    "FeatureVector",
    "FitnessResult",
    "FitnessWeights",
    "LeaderboardEntry",
    "MarketRegime",
    "OptimizationResult",
    "OptimizationState",
    "OverfittingReport",
    "ParameterConstraint",
    "ParameterDefinition",
    "ParameterSpace",
    "ParameterStabilityReport",
    "ParameterType",
    "PlatformState",
    "ProgressReport",
    "Recommendation",
    "RecommendationAction",
    "ResearchDataset",
    "ResearchPlatformConfig",
    "ResearchResult",
    "RobustnessResult",
    "StrategyCandidate",
    "StrategyEvaluation",
    "TaskResult",
    "ValidationResult",
    "VersionRecord",
    "WalkForwardResult",
    "WalkForwardWindow",
    # ─── Context ───────────────────────────────────────
    "ResearchContext",
    "AIResearchContext",
    # ─── Feature Engineering ───────────────────────────
    "FeatureEngineer",
    "ResearchFeatureEngineer",
    "ResearchDatasetBuilder",
    # ─── Strategy ──────────────────────────────────────
    "StrategyRepository",
    "InMemoryStrategyRepository",
    "StrategyEvaluator",
    "MetadataStrategyEvaluator",
    "StrategyRanker",
    "CompositeStrategyRanker",
    # ─── Interfaces ────────────────────────────────────
    "ResearchEngine",
    "StrategyRepositoryProtocol",
    "ValidationEngine",
    "RecommendationEngine",
    "OptimizationEngine",
    "MarketRegimeDetector",
    "StrategyPersistencePort",
    "ResearchRepositoryPort",
    "DatasetProvider",
    "MarketDataProvider",
    "RiskAssessorPort",
    "PortfolioSimulatorPort",
    "ModelPersistencePort",
    "OptimizationHook",
    # ─── Optimization ─────────────────────────────────
    "ParameterSpaceBuilder",
    "GridSearchOptimizer",
    "RandomSearchOptimizer",
    # ─── Analysis ─────────────────────────────────────
    "FitnessEngine",
    "ParameterStabilityAnalyzer",
    "RobustnessAnalyzer",
    # ─── Validation ───────────────────────────────────
    "WalkForwardValidator",
    "CrossValidator",
    "OverfittingDetector",
    # ─── Orchestration ─────────────────────────────────
    "AIResearchEngine",
    "AIResearchManager",
    "ExperimentTracker",
    "InMemoryExperimentTracker",
    # ─── Parallel Execution ────────────────────────────
    "ParallelExecutor",
    # ─── Persistence ───────────────────────────────────
    "ExperimentDatabase",
    "VersionManager",
    # ─── Recommender ───────────────────────────────────
    "RecommendationEngine",
]
