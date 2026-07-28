"""Tests for recommendation_engine module."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.domain.ai_research.exceptions import RecommendationError
from libraries.domain.ai_research.models import (
    LeaderboardEntry,
    MarketRegime,
    RecommendationAction,
    StrategyEvaluation,
    ValidationResult,
)
from libraries.domain.ai_research.recommendation_engine import RecommendationEngine


def _make_entry(**metrics_overrides) -> LeaderboardEntry:
    metrics = {
        "sharpe": 1.5,
        "profit_factor": 2.0,
        "win_rate": 0.6,
        "max_drawdown": 15.0,
        "expectancy": 0.3,
        "total_trades": 100,
    }
    metrics.update(metrics_overrides)
    evaluation = StrategyEvaluation(
        strategy_id="s-1",
        dataset_id="ds-1",
        metrics=metrics,
        evaluated_at=datetime.now(timezone.utc),
    )
    return LeaderboardEntry(rank=1, evaluation=evaluation, composite_score=1.5)


class TestRecommendationEngine:
    def test_high_confidence(self):
        engine = RecommendationEngine()
        import asyncio

        rec = asyncio.run(
            engine.recommend(_make_entry(sharpe=2.5, profit_factor=3.0, max_drawdown=5.0))
        )
        assert rec.confidence == 0.9

    def test_accept(self):
        engine = RecommendationEngine()
        import asyncio

        rec = asyncio.run(
            engine.recommend(_make_entry(sharpe=1.5, profit_factor=2.0, max_drawdown=15.0))
        )
        assert rec.confidence == 0.7

    def test_promising(self):
        engine = RecommendationEngine()
        import asyncio

        rec = asyncio.run(
            engine.recommend(_make_entry(sharpe=0.7, profit_factor=1.2, win_rate=0.5))
        )
        assert rec.confidence == 0.5

    def test_reject_negative_sharpe(self):
        engine = RecommendationEngine()
        import asyncio

        rec = asyncio.run(engine.recommend(_make_entry(sharpe=-0.5)))
        assert rec.confidence == 0.1

    def test_reject_high_drawdown(self):
        engine = RecommendationEngine()
        import asyncio

        rec = asyncio.run(engine.recommend(_make_entry(sharpe=1.0, max_drawdown=35.0)))
        assert rec.confidence == 0.1

    def test_overfit_risk(self):
        engine = RecommendationEngine()
        import asyncio

        rec = asyncio.run(engine.recommend(_make_entry(sharpe=2.5, max_drawdown=25.0)))
        assert rec.confidence == 0.4

    def test_low_confidence(self):
        engine = RecommendationEngine()
        import asyncio

        rec = asyncio.run(
            engine.recommend(_make_entry(sharpe=0.3, profit_factor=1.1, win_rate=0.35))
        )
        assert rec.confidence == 0.3

    def test_with_validation_failure(self):
        engine = RecommendationEngine()
        validation = ValidationResult(strategy_id="s-1", is_valid=False, reasons=("failed checks",))
        import asyncio

        rec = asyncio.run(
            engine.recommend(
                _make_entry(sharpe=2.5),
                validation_result=validation,
            )
        )
        assert rec.confidence == 0.05
        assert "failed checks" in rec.rationale

    def test_with_high_volatility_regime(self):
        engine = RecommendationEngine()
        import asyncio

        rec = asyncio.run(
            engine.recommend(
                _make_entry(sharpe=1.5, max_drawdown=20.0),
                regime=MarketRegime.HIGH_VOLATILITY,
            )
        )
        assert rec.confidence < 0.7  # penalized for high volatility

    def test_empty_metrics_raises_error(self):
        engine = RecommendationEngine()
        with pytest.raises(ValueError, match="metrics must not be empty"):
            StrategyEvaluation(
                strategy_id="s-1",
                dataset_id="ds-1",
                metrics={},
                evaluated_at=datetime.now(timezone.utc),
            )

    def test_rationale_includes_metrics(self):
        engine = RecommendationEngine()
        import asyncio

        rec = asyncio.run(
            engine.recommend(_make_entry(sharpe=2.5, profit_factor=3.0, max_drawdown=5.0))
        )
        assert "Sharpe" in rec.rationale
        assert "ProfitFactor" in rec.rationale

    def test_confidence_in_range(self):
        engine = RecommendationEngine()
        import asyncio

        rec = asyncio.run(engine.recommend(_make_entry(sharpe=2.5)))
        assert 0.0 <= rec.confidence <= 1.0

    def test_recommendation_immutable(self):
        engine = RecommendationEngine()
        import asyncio

        rec = asyncio.run(engine.recommend(_make_entry(sharpe=2.5)))
        with pytest.raises(AttributeError):
            rec.confidence = 0.5  # type: ignore[misc]

    def test_win_rate_normalized(self):
        engine = RecommendationEngine()
        import asyncio

        rec = asyncio.run(
            engine.recommend(_make_entry(sharpe=0.7, win_rate=55.0, profit_factor=1.2))
        )
        assert rec.confidence == 0.5

    def test_regime_unknown(self):
        engine = RecommendationEngine()
        import asyncio

        rec = asyncio.run(engine.recommend(_make_entry(sharpe=1.5), regime=MarketRegime.UNKNOWN))
        assert rec.regime == MarketRegime.UNKNOWN

    def test_insufficient_sample(self):
        engine = RecommendationEngine()
        import asyncio

        rec = asyncio.run(
            engine.recommend(
                _make_entry(sharpe=2.5, profit_factor=3.0, max_drawdown=5.0, total_trades=10)
            )
        )
        assert rec.action == RecommendationAction.INSUFFICIENT_SAMPLE
        assert rec.confidence == 0.2
        assert "insufficient" in rec.rationale.lower()
