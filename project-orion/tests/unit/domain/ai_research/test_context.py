"""Tests for EPIC-011 AI Research context."""

from __future__ import annotations

import pytest

from libraries.domain.ai_research.context import AIResearchContext, ResearchContext
from libraries.domain.ai_research.models import (
    FeatureDefinition,
    ResearchDataset,
    ResearchPlatformConfig,
    StrategyCandidate,
)


class TestAIResearchContext:
    """Test AIResearchContext alias."""

    def test_alias_resolves(self):
        """AIResearchContext should resolve to ResearchContext string for now."""
        assert AIResearchContext == "ResearchContext"


class TestResearchContext:
    """Test ResearchContext model."""

    def test_valid_context(self):
        ds = ResearchDataset(
            dataset_id="ds1",
            schema=("close",),
            rows=({"close": 1.0},),
        )
        config = ResearchPlatformConfig()
        strategy = StrategyCandidate(strategy_id="s1", name="test")
        ctx = ResearchContext(
            dataset=ds,
            configuration=config,
            strategies=(strategy,),
            random_seed=42,
            execution_mode="research",
        )
        assert ctx.dataset.dataset_id == "ds1"
        assert ctx.random_seed == 42
        assert ctx.execution_mode == "research"
        assert len(ctx.strategies) == 1

    def test_empty_strategies_raises_error(self):
        ds = ResearchDataset(
            dataset_id="ds1",
            schema=("close",),
            rows=({"close": 1.0},),
        )
        with pytest.raises(ValueError, match="not be empty"):
            ResearchContext(
                dataset=ds,
                configuration=ResearchPlatformConfig(),
                strategies=(),
            )

    def test_duplicate_strategy_ids_raises_error(self):
        ds = ResearchDataset(
            dataset_id="ds1",
            schema=("close",),
            rows=({"close": 1.0},),
        )
        s1 = StrategyCandidate(strategy_id="s1", name="test")
        s2 = StrategyCandidate(strategy_id="s1", name="duplicate")
        with pytest.raises(ValueError, match="unique"):
            ResearchContext(
                dataset=ds,
                configuration=ResearchPlatformConfig(),
                strategies=(s1, s2),
            )

    def test_context_frozen(self):
        ds = ResearchDataset(
            dataset_id="ds1",
            schema=("close",),
            rows=({"close": 1.0},),
        )
        ctx = ResearchContext(
            dataset=ds,
            configuration=ResearchPlatformConfig(),
            strategies=(StrategyCandidate(strategy_id="s1", name="test"),),
        )
        with pytest.raises(AttributeError):
            ctx.dataset = ds

    def test_experiment_metadata_is_proxy(self):
        ds = ResearchDataset(
            dataset_id="ds1",
            schema=("close",),
            rows=({"close": 1.0},),
        )
        ctx = ResearchContext(
            dataset=ds,
            configuration=ResearchPlatformConfig(),
            strategies=(StrategyCandidate(strategy_id="s1", name="test"),),
            experiment_metadata={"key": "value"},
        )
        assert ctx.experiment_metadata["key"] == "value"
        with pytest.raises(TypeError):
            ctx.experiment_metadata["key"] = "new-value"  # type: ignore[index]

    def test_config_seed_used_when_no_seed_provided(self):
        ds = ResearchDataset(
            dataset_id="ds1",
            schema=("close",),
            rows=({"close": 1.0},),
        )
        config = ResearchPlatformConfig(random_seed=99)
        ctx = ResearchContext(
            dataset=ds,
            configuration=config,
            strategies=(StrategyCandidate(strategy_id="s1", name="test"),),
        )
        assert ctx.random_seed == 99

    def test_invalid_execution_mode_raises_error(self):
        ds = ResearchDataset(
            dataset_id="ds1",
            schema=("close",),
            rows=({"close": 1.0},),
        )
        with pytest.raises(ValueError, match="execution_mode"):
            ResearchContext(
                dataset=ds,
                configuration=ResearchPlatformConfig(),
                strategies=(StrategyCandidate(strategy_id="s1", name="test"),),
                execution_mode="production",
            )


class TestResearchContextFeatureDefinitions:
    """Test ResearchContext with feature definitions."""

    def test_with_feature_definitions(self):
        ds = ResearchDataset(
            dataset_id="ds1",
            schema=("close",),
            rows=({"close": 1.0},),
        )
        fd = FeatureDefinition(name="sma", category="trend")
        ctx = ResearchContext(
            dataset=ds,
            configuration=ResearchPlatformConfig(),
            strategies=(StrategyCandidate(strategy_id="s1", name="test"),),
            feature_definitions=(fd,),
        )
        assert len(ctx.feature_definitions) == 1
        assert ctx.feature_definitions[0].name == "sma"
