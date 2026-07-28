"""Tests for EPIC-011 AI Research models."""

from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite

import pytest

from libraries.domain.ai_research.models import (
    Experiment,
    ExperimentResult,
    ExperimentStatus,
    FeatureDefinition,
    FeatureVector,
    LeaderboardEntry,
    MarketRegime,
    OptimizationResult,
    PlatformState,
    Recommendation,
    ResearchDataset,
    ResearchPlatformConfig,
    ResearchResult,
    StrategyCandidate,
    StrategyEvaluation,
    ValidationResult,
)


class TestEnums:
    """Test enum values."""

    def test_market_regime_values(self):
        assert MarketRegime.TRENDING == "trending"
        assert MarketRegime.RANGING == "ranging"
        assert MarketRegime.HIGH_VOLATILITY == "high_volatility"
        assert MarketRegime.LOW_LIQUIDITY == "low_liquidity"
        assert MarketRegime.UNKNOWN == "unknown"

    def test_experiment_status_values(self):
        assert ExperimentStatus.CREATED == "created"
        assert ExperimentStatus.RUNNING == "running"
        assert ExperimentStatus.COMPLETED == "completed"
        assert ExperimentStatus.FAILED == "failed"

    def test_platform_state_values(self):
        assert PlatformState.INITIALIZING == "initializing"
        assert PlatformState.READY == "ready"
        assert PlatformState.SHUTDOWN == "shutdown"


class TestResearchPlatformConfig:
    """Test ResearchPlatformConfig model."""

    def test_default_config(self):
        cfg = ResearchPlatformConfig()
        assert cfg.name == "orion-ai-research"
        assert cfg.version == "0.11.0-alpha.1"
        assert cfg.random_seed == 42
        assert cfg.execution_mode == "research"
        assert cfg.require_validation is True

    def test_custom_config(self):
        cfg = ResearchPlatformConfig(
            name="test-platform",
            version="1.0.0",
            random_seed=123,
            execution_mode="dry_run",
        )
        assert cfg.name == "test-platform"
        assert cfg.random_seed == 123
        assert cfg.execution_mode == "dry_run"

    def test_config_frozen(self):
        cfg = ResearchPlatformConfig()
        with pytest.raises(AttributeError):
            cfg.name = "new-name"

    def test_invalid_name_raises_error(self):
        with pytest.raises(ValueError, match="non-empty string"):
            ResearchPlatformConfig(name="")

    def test_invalid_execution_mode_raises_error(self):
        with pytest.raises(ValueError, match="execution_mode"):
            ResearchPlatformConfig(execution_mode="invalid")

    def test_invalid_random_seed_raises_error(self):
        with pytest.raises(ValueError, match="random_seed"):
            ResearchPlatformConfig(random_seed="42")  # type: ignore[arg-type]

    def test_metadata_defaults_to_empty(self):
        cfg = ResearchPlatformConfig()
        assert dict(cfg.metadata) == {}


class TestResearchDataset:
    """Test ResearchDataset model."""

    def test_valid_dataset(self):
        ds = ResearchDataset(
            dataset_id="test-ds",
            schema=("open", "high", "low", "close"),
            rows=(
                {"open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05},
                {"open": 1.05, "high": 1.15, "low": 0.95, "close": 1.1},
            ),
        )
        assert ds.dataset_id == "test-ds"
        assert ds.row_count == 2
        assert ds.schema == ("open", "high", "low", "close")

    def test_dataset_frozen(self):
        ds = ResearchDataset(
            dataset_id="test",
            schema=("close",),
            rows=({"close": 1.0},),
        )
        with pytest.raises(AttributeError):
            ds.dataset_id = "new-id"

    def test_empty_schema_raises_error(self):
        with pytest.raises(ValueError, match="schema"):
            ResearchDataset(
                dataset_id="test",
                schema=(),
                rows=(),
            )

    def test_duplicate_columns_raises_error(self):
        with pytest.raises(ValueError, match="unique"):
            ResearchDataset(
                dataset_id="test",
                schema=("close", "close"),
                rows=({"close": 1.0},),
            )

    def test_row_missing_column_raises_error(self):
        with pytest.raises(ValueError, match="every row"):
            ResearchDataset(
                dataset_id="test",
                schema=("close", "volume"),
                rows=({"close": 1.0},),
            )

    def test_empty_dataset_id_raises_error(self):
        with pytest.raises(ValueError, match="non-empty"):
            ResearchDataset(
                dataset_id="",
                schema=("close",),
                rows=({"close": 1.0},),
            )


class TestFeatureVector:
    """Test FeatureVector model."""

    def test_valid_feature_vector(self):
        fv = FeatureVector(values={"sma": 1.5, "rsi": 70.0})
        assert fv.values["sma"] == 1.5
        assert fv.timestamp is None

    def test_empty_values_raises_error(self):
        with pytest.raises(ValueError, match="not be empty"):
            FeatureVector(values={})

    def test_nan_value_raises_error(self):
        with pytest.raises(ValueError, match="must be finite"):
            FeatureVector(values={"nan_val": float("nan")})

    def test_frozen(self):
        fv = FeatureVector(values={"sma": 1.0})
        with pytest.raises(AttributeError):
            fv.values = {}


class TestFeatureDefinition:
    """Test FeatureDefinition model."""

    def test_valid_feature_definition(self):
        fd = FeatureDefinition(name="sma", category="trend")
        assert fd.name == "sma"
        assert fd.category == "trend"
        assert fd.required_columns == ("close",)

    def test_invalid_category_raises_error(self):
        with pytest.raises(ValueError, match="unsupported"):
            FeatureDefinition(name="test", category="invalid")

    def test_empty_name_raises_error(self):
        with pytest.raises(ValueError, match="non-empty"):
            FeatureDefinition(name="", category="trend")

    def test_empty_required_columns_raises_error(self):
        with pytest.raises(ValueError, match="not be empty"):
            FeatureDefinition(name="test", category="trend", required_columns=())


class TestStrategyCandidate:
    """Test StrategyCandidate model."""

    def test_valid_strategy(self):
        s = StrategyCandidate(strategy_id="s1", name="MyStrategy")
        assert s.strategy_id == "s1"
        assert s.name == "MyStrategy"
        assert s.version == "1.0.0"
        assert isinstance(s.tags, frozenset)

    def test_empty_id_raises_error(self):
        with pytest.raises(ValueError, match="non-empty"):
            StrategyCandidate(strategy_id="", name="test")

    def test_empty_name_raises_error(self):
        with pytest.raises(ValueError, match="non-empty"):
            StrategyCandidate(strategy_id="s1", name="")

    def test_invalid_tag_raises_error(self):
        with pytest.raises(ValueError):
            StrategyCandidate(strategy_id="s1", name="test", tags={"a", ""})


class TestStrategyEvaluation:
    """Test StrategyEvaluation model."""

    def test_valid_evaluation(self):
        e = StrategyEvaluation(
            strategy_id="s1",
            dataset_id="ds1",
            metrics={"sharpe": 1.5, "win_rate": 0.6},
        )
        assert e.strategy_id == "s1"
        assert e.metrics["sharpe"] == 1.5

    def test_empty_metrics_raises_error(self):
        with pytest.raises(ValueError, match="not be empty"):
            StrategyEvaluation(
                strategy_id="s1",
                dataset_id="ds1",
                metrics={},
            )

    def test_invalid_metric_value_raises_error(self):
        with pytest.raises(ValueError, match="must be finite"):
            StrategyEvaluation(
                strategy_id="s1",
                dataset_id="ds1",
                metrics={"sharpe": float("inf")},
            )


class TestOptimizationResult:
    """Test OptimizationResult model."""

    def test_valid_result(self):
        r = OptimizationResult(
            strategy_id="s1",
            best_parameters={"lookback": 14},
            score=0.85,
        )
        assert r.strategy_id == "s1"
        assert r.best_parameters["lookback"] == 14
        assert r.score == 0.85

    def test_invalid_score_raises_error(self):
        with pytest.raises(ValueError, match="must be finite"):
            OptimizationResult(
                strategy_id="s1",
                best_parameters={},
                score=float("nan"),
            )


class TestExperimentModels:
    """Test Experiment and ExperimentResult models."""

    def test_valid_experiment(self):
        exp = Experiment(
            experiment_id="exp-1",
            name="test-exp",
            version="1.0.0",
        )
        assert exp.experiment_id == "exp-1"
        assert exp.name == "test-exp"

    def test_experiment_frozen(self):
        exp = Experiment(experiment_id="exp-1", name="test", version="1.0.0")
        with pytest.raises(AttributeError):
            exp.name = "new-name"

    def test_valid_experiment_result(self):
        result = ExperimentResult(
            experiment_id="exp-1",
            status=ExperimentStatus.COMPLETED,
            metrics={"accuracy": 0.95},
        )
        assert result.status == ExperimentStatus.COMPLETED
        assert result.metrics["accuracy"] == 0.95

    def test_experiment_result_invalid_metric(self):
        with pytest.raises(ValueError, match="must be finite"):
            ExperimentResult(
                experiment_id="exp-1",
                status=ExperimentStatus.FAILED,
                metrics={"score": float("-inf")},
            )


class TestLeaderboardEntry:
    """Test LeaderboardEntry model."""

    def test_valid_entry(self):
        evaluation = StrategyEvaluation(
            strategy_id="s1",
            dataset_id="ds1",
            metrics={"sharpe": 2.0},
        )
        entry = LeaderboardEntry(rank=1, evaluation=evaluation, composite_score=0.85)
        assert entry.rank == 1
        assert entry.composite_score == 0.85

    def test_rank_must_be_positive(self):
        evaluation = StrategyEvaluation(
            strategy_id="s1",
            dataset_id="ds1",
            metrics={"sharpe": 1.0},
        )
        with pytest.raises(ValueError, match="rank must be positive"):
            LeaderboardEntry(rank=0, evaluation=evaluation, composite_score=0.5)


class TestValidationResult:
    """Test ValidationResult model."""

    def test_valid_validation(self):
        vr = ValidationResult(strategy_id="s1", is_valid=True)
        assert vr.is_valid is True
        assert vr.reasons == ()

    def test_invalid_with_reasons(self):
        vr = ValidationResult(
            strategy_id="s1",
            is_valid=False,
            reasons=("insufficient data", "high drawdown"),
        )
        assert vr.is_valid is False
        assert len(vr.reasons) == 2

    def test_empty_reason_raises_error(self):
        with pytest.raises(ValueError, match="non-empty"):
            ValidationResult(
                strategy_id="s1",
                is_valid=False,
                reasons=("",),
            )


class TestRecommendation:
    """Test Recommendation model."""

    def test_valid_recommendation(self):
        rec = Recommendation(
            strategy_id="s1",
            rationale="high sharpe ratio",
            confidence=0.8,
        )
        assert rec.strategy_id == "s1"
        assert rec.confidence == 0.8
        assert rec.regime == MarketRegime.UNKNOWN

    def test_confidence_out_of_range_low(self):
        with pytest.raises(ValueError, match="confidence"):
            Recommendation(
                strategy_id="s1",
                rationale="test",
                confidence=-0.1,
            )

    def test_confidence_out_of_range_high(self):
        with pytest.raises(ValueError, match="confidence"):
            Recommendation(
                strategy_id="s1",
                rationale="test",
                confidence=1.5,
            )


class TestResearchResult:
    """Test ResearchResult model."""

    def test_valid_result(self):
        evaluation = StrategyEvaluation(
            strategy_id="s1",
            dataset_id="ds1",
            metrics={"sharpe": 1.5},
        )
        entry = LeaderboardEntry(rank=1, evaluation=evaluation, composite_score=0.8)
        result = ResearchResult(
            dataset_id="ds1",
            evaluations=(evaluation,),
            leaderboard=(entry,),
        )
        assert result.dataset_id == "ds1"
        assert len(result.evaluations) == 1
        assert len(result.leaderboard) == 1

    def test_leaderboard_must_reference_evaluation(self):
        evaluation = StrategyEvaluation(
            strategy_id="s1",
            dataset_id="ds1",
            metrics={"sharpe": 1.5},
        )
        other_eval = StrategyEvaluation(
            strategy_id="s2",
            dataset_id="ds1",
            metrics={"sharpe": 2.0},
        )
        entry = LeaderboardEntry(rank=1, evaluation=other_eval, composite_score=0.8)
        with pytest.raises(ValueError, match="must reference an evaluation"):
            ResearchResult(
                dataset_id="ds1",
                evaluations=(evaluation,),
                leaderboard=(entry,),
            )


class TestDataclassImmutability:
    """Test all dataclass models are frozen."""

    @pytest.mark.parametrize(
        "model_class,kwargs",
        [
            (ResearchPlatformConfig, {}),
            (
                ResearchDataset,
                {"dataset_id": "test", "schema": ("close",), "rows": ({"close": 1.0},)},
            ),
            (FeatureVector, {"values": {"sma": 1.0}}),
            (FeatureDefinition, {"name": "sma", "category": "trend"}),
            (StrategyCandidate, {"strategy_id": "s1", "name": "test"}),
            (StrategyEvaluation, {"strategy_id": "s1", "dataset_id": "ds1", "metrics": {"m": 1.0}}),
            (OptimizationResult, {"strategy_id": "s1", "best_parameters": {}, "score": 0.5}),
            (Experiment, {"experiment_id": "e1", "name": "test", "version": "1.0"}),
            (ExperimentResult, {"experiment_id": "e1", "status": ExperimentStatus.CREATED}),
            (ValidationResult, {"strategy_id": "s1", "is_valid": True}),
        ],
    )
    def test_dataclass_is_frozen(self, model_class, kwargs):
        import dataclasses

        instance = model_class(**kwargs)
        assert dataclasses.is_dataclass(instance)
        assert instance.__dataclass_params__.frozen is True
