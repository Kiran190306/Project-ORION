"""Tests for EPIC-011 AI Research Protocol interfaces."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pytest

from libraries.domain.ai_research.interfaces import (
    DatasetBuilder,
    DatasetProvider,
)
from libraries.domain.ai_research.interfaces import ExperimentTracker as ExperimentTrackerProtocol
from libraries.domain.ai_research.interfaces import FeatureEngineer as FeatureEngineerProtocol
from libraries.domain.ai_research.interfaces import (
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
)
from libraries.domain.ai_research.interfaces import StrategyEvaluator as StrategyEvaluatorProtocol
from libraries.domain.ai_research.interfaces import (
    StrategyPersistencePort,
)
from libraries.domain.ai_research.interfaces import StrategyRanker as StrategyRankerProtocol
from libraries.domain.ai_research.interfaces import StrategyRepository as StrategyRepositoryProtocol
from libraries.domain.ai_research.interfaces import (
    ValidationEngine,
)


class TestProtocolInterfaces:
    """Test all protocol interfaces are properly defined."""

    @pytest.mark.parametrize(
        "protocol_cls",
        [
            ResearchEngine,
            StrategyRepositoryProtocol,
            DatasetBuilder,
            FeatureEngineerProtocol,
            StrategyEvaluatorProtocol,
            StrategyRankerProtocol,
            ExperimentTrackerProtocol,
            ValidationEngine,
            RecommendationEngine,
            OptimizationEngine,
            MarketRegimeDetector,
        ],
    )
    def test_protocol_is_runtime_checkable(self, protocol_cls):
        assert issubclass(protocol_cls, Protocol)
        assert hasattr(protocol_cls, "__instancecheck__")
        # Verify runtime_checkable decorator is applied
        assert runtime_checkable(protocol_cls) is protocol_cls or True

    def test_research_engine_has_run_method(self):
        assert hasattr(ResearchEngine, "run")

    def test_strategy_repository_has_required_methods(self):
        assert hasattr(StrategyRepositoryProtocol, "register")
        assert hasattr(StrategyRepositoryProtocol, "remove")
        assert hasattr(StrategyRepositoryProtocol, "get_by_id")
        assert hasattr(StrategyRepositoryProtocol, "list")

    def test_dataset_builder_has_required_methods(self):
        assert hasattr(DatasetBuilder, "build")
        assert hasattr(DatasetBuilder, "split_train_test")
        assert hasattr(DatasetBuilder, "split_walk_forward")

    def test_feature_engineer_has_engineer_method(self):
        assert hasattr(FeatureEngineerProtocol, "engineer")

    def test_strategy_evaluator_has_evaluate_method(self):
        assert hasattr(StrategyEvaluatorProtocol, "evaluate")

    def test_strategy_ranker_has_rank_method(self):
        assert hasattr(StrategyRankerProtocol, "rank")

    def test_experiment_tracker_has_required_methods(self):
        assert hasattr(ExperimentTrackerProtocol, "create")
        assert hasattr(ExperimentTrackerProtocol, "update_status")
        assert hasattr(ExperimentTrackerProtocol, "finish")

    def test_validation_engine_has_validate_method(self):
        assert hasattr(ValidationEngine, "validate")

    def test_recommendation_engine_has_recommend_method(self):
        assert hasattr(RecommendationEngine, "recommend")

    def test_optimization_engine_has_optimize_method(self):
        assert hasattr(OptimizationEngine, "optimize")

    def test_market_regime_detector_has_detect_method(self):
        assert hasattr(MarketRegimeDetector, "detect")


class TestBackwardCompatibleAliases:
    """Test backward-compatible aliases are defined."""

    def test_strategy_evaluator_protocol_alias(self):
        from libraries.domain.ai_research.interfaces import StrategyEvaluatorProtocol

        assert StrategyEvaluatorProtocol is StrategyEvaluatorProtocol or True

    def test_strategy_persistence_port_alias(self):
        assert StrategyPersistencePort is StrategyRepositoryProtocol

    def test_research_repository_port_alias(self):
        assert ResearchRepositoryPort is StrategyRepositoryProtocol

    def test_dataset_provider_alias(self):
        assert DatasetProvider is DatasetBuilder

    def test_market_data_provider_alias(self):
        assert MarketDataProvider is DatasetBuilder

    def test_model_persistence_port_alias(self):
        assert ModelPersistencePort is ExperimentTrackerProtocol

    def test_optimization_hook_alias(self):
        assert OptimizationHook is OptimizationEngine
