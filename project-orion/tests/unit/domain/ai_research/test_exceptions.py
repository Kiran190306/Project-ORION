"""Tests for EPIC-011 AI Research exception hierarchy."""

from __future__ import annotations

import pytest

from libraries.domain.ai_research.exceptions import (
    AIResearchError,
    ConfigurationError,
    DatasetError,
    ExperimentError,
    FeatureEngineeringError,
    OptimizationError,
    RankingError,
    RepositoryError,
    StrategyError,
    ValidationError,
)


class TestExceptionHierarchy:
    """Test the exception hierarchy structure."""

    def test_ai_research_error_base(self):
        assert issubclass(AIResearchError, Exception)
        err = AIResearchError("test error")
        assert str(err) == "test error"

    def test_configuration_error_hierarchy(self):
        assert issubclass(ConfigurationError, AIResearchError)

    def test_dataset_error_hierarchy(self):
        assert issubclass(DatasetError, AIResearchError)

    def test_feature_engineering_error_hierarchy(self):
        assert issubclass(FeatureEngineeringError, AIResearchError)

    def test_validation_error_hierarchy(self):
        assert issubclass(ValidationError, AIResearchError)

    def test_strategy_error_hierarchy(self):
        assert issubclass(StrategyError, AIResearchError)

    def test_optimization_error_hierarchy(self):
        assert issubclass(OptimizationError, AIResearchError)

    def test_experiment_error_hierarchy(self):
        assert issubclass(ExperimentError, AIResearchError)

    def test_repository_error_hierarchy(self):
        assert issubclass(RepositoryError, AIResearchError)

    def test_ranking_error_hierarchy(self):
        assert issubclass(RankingError, AIResearchError)

    def test_all_exceptions_catchable_by_base(self):
        exceptions = [
            AIResearchError(),
            ConfigurationError(),
            DatasetError(),
            FeatureEngineeringError(),
            ValidationError(),
            StrategyError(),
            OptimizationError(),
            ExperimentError(),
            RepositoryError(),
            RankingError(),
        ]
        for exc in exceptions:
            assert isinstance(exc, AIResearchError)
            assert isinstance(exc, Exception)

    def test_exception_message_preserved(self):
        msg = "specific error message"
        err = AIResearchError(msg)
        assert str(err) == msg
        assert repr(msg) in repr(err)

    def test_exception_without_message(self):
        err = AIResearchError()
        assert str(err) == ""

    def test_error_raise_and_catch_base(self):
        with pytest.raises(AIResearchError):
            raise ConfigurationError("invalid config")

        with pytest.raises(AIResearchError):
            raise DatasetError("missing data")

        with pytest.raises(AIResearchError):
            raise FeatureEngineeringError("feature failed")

    def test_error_raise_and_catch_specific(self):
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("bad config")

        with pytest.raises(StrategyError):
            raise StrategyError("bad strategy")

    def test_configuration_error_message(self):
        err = ConfigurationError("random seed must be integer")
        assert "random seed" in str(err)

    def test_repository_error_message(self):
        err = RepositoryError("strategy already registered")
        assert "already registered" in str(err)
