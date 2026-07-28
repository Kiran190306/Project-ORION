"""Tests for EPIC-011 MetadataStrategyEvaluator."""

from __future__ import annotations

import pytest

from libraries.domain.ai_research.exceptions import StrategyError
from libraries.domain.ai_research.models import ResearchDataset, StrategyCandidate
from libraries.domain.ai_research.strategy_evaluator import MetadataStrategyEvaluator


class TestMetadataStrategyEvaluator:
    """Test MetadataStrategyEvaluator."""

    @pytest.fixture
    def evaluator(self):
        return MetadataStrategyEvaluator()

    @pytest.fixture
    def sample_dataset(self):
        return ResearchDataset(
            dataset_id="ds1",
            schema=("close",),
            rows=({"close": 1.0},),
        )

    @pytest.mark.asyncio
    async def test_evaluate_with_metrics_in_metadata(self, evaluator, sample_dataset):
        strategy = StrategyCandidate(
            strategy_id="s1",
            name="Test",
            metadata={"metrics": {"sharpe": 1.5, "win_rate": 0.6}},
        )
        result = await evaluator.evaluate(strategy, sample_dataset)
        assert result.strategy_id == "s1"
        assert result.dataset_id == "ds1"
        assert result.metrics["sharpe"] == 1.5
        assert result.metrics["win_rate"] == 0.6

    @pytest.mark.asyncio
    async def test_evaluate_missing_metrics_in_metadata(self, evaluator, sample_dataset):
        strategy = StrategyCandidate(strategy_id="s1", name="Test")
        with pytest.raises(StrategyError, match="metrics"):
            await evaluator.evaluate(strategy, sample_dataset)

    @pytest.mark.asyncio
    async def test_evaluate_wrong_metrics_type(self, evaluator, sample_dataset):
        strategy = StrategyCandidate(
            strategy_id="s1",
            name="Test",
            metadata={"metrics": "not_a_dict"},
        )
        with pytest.raises(StrategyError, match="metrics"):
            await evaluator.evaluate(strategy, sample_dataset)

    @pytest.mark.asyncio
    async def test_evaluate_empty_metrics(self, evaluator, sample_dataset):
        strategy = StrategyCandidate(
            strategy_id="s1",
            name="Test",
            metadata={"metrics": {}},
        )
        with pytest.raises(StrategyError):
            await evaluator.evaluate(strategy, sample_dataset)

    @pytest.mark.asyncio
    async def test_evaluate_with_custom_metric_provider(self, sample_dataset):
        def custom_provider(strategy, dataset):
            return {"sharpe": 2.0, "profit_factor": 1.5}

        evaluator = MetadataStrategyEvaluator(metric_provider=custom_provider)
        strategy = StrategyCandidate(strategy_id="s1", name="Test")
        result = await evaluator.evaluate(strategy, sample_dataset)
        assert result.metrics["sharpe"] == 2.0
        assert result.metrics["profit_factor"] == 1.5

    @pytest.mark.asyncio
    async def test_evaluate_with_custom_provider_returning_empty(self, sample_dataset):
        def empty_provider(strategy, dataset):
            return {}

        evaluator = MetadataStrategyEvaluator(metric_provider=empty_provider)
        strategy = StrategyCandidate(strategy_id="s1", name="Test")
        with pytest.raises(StrategyError):
            await evaluator.evaluate(strategy, sample_dataset)
