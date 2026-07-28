"""Tests for EPIC-011 AI Research engine orchestration."""

from __future__ import annotations

import pytest

from libraries.domain.ai_research.context import ResearchContext
from libraries.domain.ai_research.engine import AIResearchEngine
from libraries.domain.ai_research.models import (
    ExperimentStatus,
    FeatureDefinition,
    LeaderboardEntry,
    ResearchDataset,
    ResearchPlatformConfig,
    ResearchResult,
    StrategyCandidate,
    StrategyEvaluation,
    ValidationResult,
)


class TestAIResearchEngineInitialization:
    """Test engine initialization."""

    def test_default_init(self):
        engine = AIResearchEngine()
        assert engine.feature_engineer is None
        assert engine.strategy_evaluator is None
        assert engine.strategy_ranker is None
        assert engine.validation_engine is None
        assert engine.experiment_tracker is None
        assert engine.strategy_repository is None
        assert engine.dataset_builder is None

    def test_init_with_dependencies(self):
        class FakeEvaluator:
            async def evaluate(self, strategy, dataset):
                return StrategyEvaluation(
                    strategy_id=strategy.strategy_id,
                    dataset_id=dataset.dataset_id,
                    metrics={"sharpe": 1.0},
                )

        class FakeRanker:
            async def rank(self, evaluations):
                return tuple(
                    LeaderboardEntry(rank=i + 1, eval=e, composite_score=1.0)
                    for i, e in enumerate(evaluations)
                )

        engine = AIResearchEngine(
            strategy_evaluator=FakeEvaluator(),
            strategy_ranker=FakeRanker(),
        )
        assert engine.strategy_evaluator is not None
        assert engine.strategy_ranker is not None

    def test_properties_return_injected_values(self):
        class FakeRepo:
            async def get_by_id(self, strategy_id):
                return None

        engine = AIResearchEngine(strategy_repository=FakeRepo())
        assert engine.strategy_repository is not None


class TestAIResearchEngineRun:
    """Test the main run method."""

    @pytest.mark.asyncio
    async def test_run_with_minimal_deps(self):
        """Engine should run with only evaluator and ranker."""

        class FakeEvaluator:
            async def evaluate(self, strategy, dataset):
                return StrategyEvaluation(
                    strategy_id=strategy.strategy_id,
                    dataset_id=dataset.dataset_id,
                    metrics={"sharpe": 1.5, "win_rate": 0.6},
                )

        class FakeRanker:
            async def rank(self, evaluations):
                entries = []
                for i, e in enumerate(evaluations):
                    entries.append(
                        LeaderboardEntry(
                            rank=i + 1,
                            evaluation=e,
                            composite_score=0.85,
                        )
                    )
                return tuple(entries)

        ds = ResearchDataset(
            dataset_id="ds1",
            schema=("close",),
            rows=({"close": 1.0}, {"close": 2.0}),
        )
        config = ResearchPlatformConfig()
        strategy = StrategyCandidate(strategy_id="s1", name="EMA Crossover")
        ctx = ResearchContext(
            dataset=ds,
            configuration=config,
            strategies=(strategy,),
        )

        engine = AIResearchEngine(
            strategy_evaluator=FakeEvaluator(),
            strategy_ranker=FakeRanker(),
        )
        result = await engine.run(ctx)
        assert isinstance(result, ResearchResult)
        assert result.dataset_id == "ds1"
        assert len(result.evaluations) == 1
        assert len(result.leaderboard) == 1
        assert result.leaderboard[0].rank == 1

    @pytest.mark.asyncio
    async def test_run_with_feature_engineering(self):
        """Engine should invoke feature engineering when provided."""

        class FakeEngineer:
            async def engineer(self, dataset, definitions):
                return ()

        class FakeEvaluator:
            async def evaluate(self, strategy, dataset):
                return StrategyEvaluation(
                    strategy_id=strategy.strategy_id,
                    dataset_id=dataset.dataset_id,
                    metrics={"sharpe": 1.0},
                )

        class FakeRanker:
            async def rank(self, evaluations):
                return tuple(
                    LeaderboardEntry(rank=i + 1, evaluation=e, composite_score=1.0)
                    for i, e in enumerate(evaluations)
                )

        ds = ResearchDataset(
            dataset_id="ds1",
            schema=("close",),
            rows=({"close": 1.0},),
        )
        strategy = StrategyCandidate(strategy_id="s1", name="test")
        fd = FeatureDefinition(name="sma", category="trend")
        ctx = ResearchContext(
            dataset=ds,
            configuration=ResearchPlatformConfig(),
            strategies=(strategy,),
            feature_definitions=(fd,),
        )

        engine = AIResearchEngine(
            feature_engineer=FakeEngineer(),
            strategy_evaluator=FakeEvaluator(),
            strategy_ranker=FakeRanker(),
        )
        result = await engine.run(ctx)
        assert len(result.evaluations) == 1

    @pytest.mark.asyncio
    async def test_run_with_validation(self):
        """Engine should invoke validation when validation engine is provided."""

        class FakeEvaluator:
            async def evaluate(self, strategy, dataset):
                return StrategyEvaluation(
                    strategy_id=strategy.strategy_id,
                    dataset_id=dataset.dataset_id,
                    metrics={"sharpe": 1.0},
                )

        class FakeRanker:
            async def rank(self, evaluations):
                return tuple(
                    LeaderboardEntry(rank=i + 1, evaluation=e, composite_score=1.0)
                    for i, e in enumerate(evaluations)
                )

        class FakeValidator:
            async def validate(self, strategy, evaluation):
                return ValidationResult(
                    strategy_id=strategy.strategy_id,
                    is_valid=True,
                )

        class FakeRepo:
            async def get_by_id(self, strategy_id):
                return StrategyCandidate(strategy_id=strategy_id, name="test")

        ds = ResearchDataset(
            dataset_id="ds1",
            schema=("close",),
            rows=({"close": 1.0},),
        )
        strategy = StrategyCandidate(strategy_id="s1", name="test")
        ctx = ResearchContext(
            dataset=ds,
            configuration=ResearchPlatformConfig(),
            strategies=(strategy,),
        )

        engine = AIResearchEngine(
            strategy_evaluator=FakeEvaluator(),
            strategy_ranker=FakeRanker(),
            validation_engine=FakeValidator(),
            strategy_repository=FakeRepo(),
        )
        result = await engine.run(ctx)
        assert len(result.evaluations) == 1

    @pytest.mark.asyncio
    async def test_run_with_experiment_tracker(self):
        """Engine should track experiment when tracker is provided."""
        calls = []

        class FakeEvaluator:
            async def evaluate(self, strategy, dataset):
                return StrategyEvaluation(
                    strategy_id=strategy.strategy_id,
                    dataset_id=dataset.dataset_id,
                    metrics={"sharpe": 1.0},
                )

        class FakeRanker:
            async def rank(self, evaluations):
                return tuple(
                    LeaderboardEntry(rank=i + 1, evaluation=e, composite_score=1.0)
                    for i, e in enumerate(evaluations)
                )

        class FakeTracker:
            async def create(self, experiment):
                calls.append(("create", experiment.experiment_id))

            async def update_status(self, experiment_id, status):
                calls.append(("update_status", experiment_id, status))

            async def finish(self, result):
                calls.append(("finish", result.experiment_id))

        ds = ResearchDataset(
            dataset_id="ds1",
            schema=("close",),
            rows=({"close": 1.0},),
        )
        strategy = StrategyCandidate(strategy_id="s1", name="test")
        ctx = ResearchContext(
            dataset=ds,
            configuration=ResearchPlatformConfig(),
            strategies=(strategy,),
        )

        engine = AIResearchEngine(
            strategy_evaluator=FakeEvaluator(),
            strategy_ranker=FakeRanker(),
            experiment_tracker=FakeTracker(),
        )
        result = await engine.run(ctx)
        assert result.experiment is not None
        assert len(calls) >= 2  # create + finish

    @pytest.mark.asyncio
    async def test_run_single_strategy(self):
        """Engine should evaluate a single strategy by ID."""

        class FakeEvaluator:
            async def evaluate(self, strategy, dataset):
                return StrategyEvaluation(
                    strategy_id=strategy.strategy_id,
                    dataset_id=dataset.dataset_id,
                    metrics={"sharpe": 1.0},
                )

        ds = ResearchDataset(
            dataset_id="ds1",
            schema=("close",),
            rows=({"close": 1.0},),
        )
        strategy = StrategyCandidate(strategy_id="s1", name="test")
        ctx = ResearchContext(
            dataset=ds,
            configuration=ResearchPlatformConfig(),
            strategies=(strategy,),
        )

        engine = AIResearchEngine(strategy_evaluator=FakeEvaluator())
        result = await engine.run_single(ctx, "s1")
        assert result is not None
        assert result.strategy_id == "s1"

    @pytest.mark.asyncio
    async def test_run_single_strategy_not_found(self):
        """Engine should return None for unknown strategy ID."""

        class FakeEvaluator:
            async def evaluate(self, strategy, dataset):
                return StrategyEvaluation(
                    strategy_id=strategy.strategy_id,
                    dataset_id=dataset.dataset_id,
                    metrics={"sharpe": 1.0},
                )

        ds = ResearchDataset(
            dataset_id="ds1",
            schema=("close",),
            rows=({"close": 1.0},),
        )
        strategy = StrategyCandidate(strategy_id="s1", name="test")
        ctx = ResearchContext(
            dataset=ds,
            configuration=ResearchPlatformConfig(),
            strategies=(strategy,),
        )

        engine = AIResearchEngine(strategy_evaluator=FakeEvaluator())
        result = await engine.run_single(ctx, "nonexistent")
        assert result is None


class TestAIResearchEngineEdgeCases:
    """Test edge cases for the engine."""

    @pytest.mark.asyncio
    async def test_run_with_multiple_strategies(self):
        """Engine should handle multiple strategies correctly."""

        class FakeEvaluator:
            async def evaluate(self, strategy, dataset):
                return StrategyEvaluation(
                    strategy_id=strategy.strategy_id,
                    dataset_id=dataset.dataset_id,
                    metrics={"sharpe": 1.0},
                )

        class FakeRanker:
            async def rank(self, evaluations):
                return tuple(
                    LeaderboardEntry(rank=i + 1, evaluation=e, composite_score=1.0)
                    for i, e in enumerate(evaluations)
                )

        ds = ResearchDataset(
            dataset_id="ds1",
            schema=("close",),
            rows=({"close": 1.0},),
        )
        s1 = StrategyCandidate(strategy_id="s1", name="Alpha")
        s2 = StrategyCandidate(strategy_id="s2", name="Beta")
        ctx = ResearchContext(
            dataset=ds,
            configuration=ResearchPlatformConfig(),
            strategies=(s1, s2),
        )

        engine = AIResearchEngine(
            strategy_evaluator=FakeEvaluator(),
            strategy_ranker=FakeRanker(),
        )
        result = await engine.run(ctx)
        assert len(result.evaluations) == 2
        assert len(result.leaderboard) == 2
