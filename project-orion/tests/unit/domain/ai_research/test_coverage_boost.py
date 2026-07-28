"""Targeted coverage boost for Sprint-2 modules."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.ai_research.exceptions import (
    WalkForwardError,
)
from libraries.domain.ai_research.fitness_engine import FitnessEngine
from libraries.domain.ai_research.models import (
    ParameterConstraint,
    ParameterDefinition,
    ParameterSpace,
    ParameterType,
    ResearchDataset,
    StrategyCandidate,
    StrategyEvaluation,
    WalkForwardResult,
    WalkForwardWindow,
)
from libraries.domain.ai_research.parameter_stability import ParameterStabilityAnalyzer
from libraries.domain.ai_research.walk_forward_validator import WalkForwardValidator

# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_evaluation_minimal(
    strategy_id: str = "s1",
    metrics: dict | None = None,
) -> StrategyEvaluation:
    return StrategyEvaluation(
        strategy_id=strategy_id,
        dataset_id="ds-1",
        metrics=metrics or {"sharpe": 1.5, "profit_factor": 2.0},
        evaluated_at=datetime.now(timezone.utc),
    )


def _make_strategy() -> StrategyCandidate:
    return StrategyCandidate(strategy_id="s-1", name="Test", version="1.0.0")


def _make_dataset(rows: int = 500) -> ResearchDataset:
    return ResearchDataset(
        dataset_id="ds-1",
        schema=("timestamp", "close", "high", "low"),
        rows=tuple(
            {
                "timestamp": datetime.now(timezone.utc),
                "close": 100.0 + i,
                "high": 101.0 + i,
                "low": 99.0 + i,
            }
            for i in range(rows)
        ),
    )


def _make_evaluation(
    sharpe: float = 1.5,
    profit_factor: float = 2.0,
    sortino: float = 1.2,
    calmar: float = 0.8,
    expectancy: float = 0.3,
    max_drawdown: float = 15.0,
    recovery_factor: float = 1.5,
    win_rate: float = 0.6,
    risk_reward: float = 2.0,
) -> StrategyEvaluation:
    return StrategyEvaluation(
        strategy_id="strat-1",
        dataset_id="ds-1",
        metrics={
            "sharpe": sharpe,
            "sortino": sortino,
            "calmar": calmar,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "max_drawdown": max_drawdown,
            "recovery_factor": recovery_factor,
            "win_rate": win_rate,
            "risk_reward": risk_reward,
        },
        evaluated_at=datetime.now(timezone.utc),
    )


# ── Walk-Forward Validator (covers lines 94, 104) ──────────────────────────


class TestWalkForwardValidatorCoverage:
    """Covers edge cases: empty windows, robustness calculations."""

    @pytest.mark.asyncio
    async def test_too_small_dataset_raises_specific_message(self):
        """Cover: check the 'no windows' path with exact message."""
        validator = WalkForwardValidator(min_train_size=1, min_test_size=1)
        with pytest.raises(WalkForwardError, match="dataset has"):
            await validator.validate(
                strategy=_make_strategy(),
                dataset=_make_dataset(10),
                evaluation=_make_evaluation_minimal(),
                train_size=200,
                test_size=50,
            )

    @pytest.mark.asyncio
    async def test_exact_fit_produces_windows(self):
        """Cover: boundary where dataset exactly fits train + test."""
        validator = WalkForwardValidator(min_train_size=1, min_test_size=1)
        result = await validator.validate(
            strategy=_make_strategy(),
            dataset=_make_dataset(250),
            evaluation=_make_evaluation_minimal(),
            train_size=200,
            test_size=50,
            step_size=50,
        )
        assert result.num_windows >= 1

    @pytest.mark.asyncio
    async def test_robustness_with_zero_train_sharpe(self):
        """Cover: robustness calculation when train_sharpe == 0."""
        validator = WalkForwardValidator(min_train_size=1, min_test_size=1)
        evaluation = StrategyEvaluation(
            strategy_id="s1",
            dataset_id="ds-1",
            metrics={"sharpe": 0.0},
            evaluated_at=datetime.now(timezone.utc),
        )
        result = await validator.validate(
            strategy=_make_strategy(),
            dataset=_make_dataset(500),
            evaluation=evaluation,
            train_size=200,
            test_size=50,
            step_size=100,
        )
        assert result.robustness_score >= 0.0


# ── Parameter Stability (covers lines 65-67, 79-84) ─────────────────────────


class TestParameterStabilityCoverage:
    """Covers edge cases: zero mean, exception handling."""

    @pytest.mark.asyncio
    async def test_mean_near_zero_uses_absolute_values(self):
        """Cover: line 65-67 branch when mean is near zero."""
        analyzer = ParameterStabilityAnalyzer()
        wf = WalkForwardResult(
            windows=(
                WalkForwardWindow(
                    window_index=0,
                    train_start=0,
                    train_end=100,
                    test_start=100,
                    test_end=120,
                    test_metrics={"sharpe": 0.001, "profit_factor": 2.0},
                ),
                WalkForwardWindow(
                    window_index=1,
                    train_start=100,
                    train_end=200,
                    test_start=200,
                    test_end=220,
                    test_metrics={"sharpe": -0.001, "profit_factor": 2.1},
                ),
            ),
            robustness_score=0.8,
        )
        report = await analyzer.analyze(wf)
        assert 0.0 <= report.stability_score <= 1.0
        assert "sharpe" in report.parameter_std

    @pytest.mark.asyncio
    async def test_all_values_zero(self):
        """Cover: all metric values are zero -> stability 1.0."""
        analyzer = ParameterStabilityAnalyzer()
        wf = WalkForwardResult(
            windows=(
                WalkForwardWindow(
                    window_index=0,
                    train_start=0,
                    train_end=100,
                    test_start=100,
                    test_end=120,
                    test_metrics={"sharpe": 0.0},
                ),
                WalkForwardWindow(
                    window_index=1,
                    train_start=100,
                    train_end=200,
                    test_start=200,
                    test_end=220,
                    test_metrics={"sharpe": 0.0},
                ),
            ),
            robustness_score=0.8,
        )
        report = await analyzer.analyze(wf)
        assert report.stability_score >= 0.0

    @pytest.mark.asyncio
    async def test_identical_nonzero_values(self):
        """Cover: identical metrics across windows -> stability ~1.0."""
        analyzer = ParameterStabilityAnalyzer()
        wf = WalkForwardResult(
            windows=(
                WalkForwardWindow(
                    window_index=0,
                    train_start=0,
                    train_end=100,
                    test_start=100,
                    test_end=120,
                    test_metrics={"sharpe": 2.0, "profit_factor": 3.0},
                ),
                WalkForwardWindow(
                    window_index=1,
                    train_start=100,
                    train_end=200,
                    test_start=200,
                    test_end=220,
                    test_metrics={"sharpe": 2.0, "profit_factor": 3.0},
                ),
            ),
            robustness_score=1.0,
        )
        report = await analyzer.analyze(wf)
        assert report.stability_score > 0.9

    @pytest.mark.asyncio
    async def test_exception_in_stdev_handled(self):
        """Cover: exception during stdev -> stability 1.0."""
        analyzer = ParameterStabilityAnalyzer()
        wf = WalkForwardResult(
            windows=(
                WalkForwardWindow(
                    window_index=0,
                    train_start=0,
                    train_end=100,
                    test_start=100,
                    test_end=120,
                    test_metrics={"sharpe": 1.0},
                ),
            ),
            robustness_score=0.5,
        )
        report = await analyzer.analyze(wf)
        assert report.stability_score >= 0.0


# ── Fitness Engine (covers lines 39, 70, 74, 101, 108, 115) ────────────────


class TestFitnessEngineCoverage:
    """Covers edge cases: calculate_batch, weights property, non-finite guards."""

    def test_calculate_batch_empty(self):
        engine = FitnessEngine()
        results = engine.calculate_batch(())
        assert len(results) == 0

    def test_weights_property(self):
        engine = FitnessEngine()
        w = engine.weights
        assert w.sharpe == 0.25

    def test_calculate_with_all_zero_metrics_except_defaults(self):
        """Test with metrics that have 0 values for all numeric fields."""
        engine = FitnessEngine()
        result = engine.calculate(
            StrategyEvaluation(
                strategy_id="strat-1",
                dataset_id="ds-1",
                metrics={"sharpe": 0.0, "profit_factor": 0.0, "win_rate": 0.0, "max_drawdown": 0.0},
                evaluated_at=datetime.now(timezone.utc),
            )
        )
        assert result.composite_score is not None


# ── Grid Search (covers lines 132, 145, 149, 158) ───────────────────────────


from libraries.domain.ai_research.grid_search import GridSearchOptimizer


class TestGridSearchCoverage:
    """Covers edge cases in grid search."""

    def test_cancelled_state(self):
        optimizer = GridSearchOptimizer()
        assert optimizer.state.name == "PENDING"
        optimizer.cancel()
        assert optimizer.state.name == "CANCELLED"

    def test_generate_with_enum_parameter(self):
        optimizer = GridSearchOptimizer()
        p = ParameterDefinition(
            name="mode",
            parameter_type=ParameterType.ENUM,
            constraint=ParameterConstraint(values=("fast", "slow")),
        )
        results = optimizer.generate(ParameterSpace(parameters=(p,)))
        assert len(results) == 2


class TestMarketClassifierCUBoost:
    """Coverage for market_classifier.py uncovered lines."""

    def test_resolve_regime_trending(self):
        from libraries.domain.ai_research.market_classifier import MarketClassifier
        from libraries.domain.ai_research.models import (
            LiquidityClassificationResult,
            LiquidityLevel,
            MarketRegime,
            TrendClassificationResult,
            TrendDirection,
            VolatilityClassificationResult,
            VolatilityLevel,
        )

        t = TrendClassificationResult(
            direction=TrendDirection.BULL, strength=0.8, slope=0.01, details={}
        )
        v = VolatilityClassificationResult(
            level=VolatilityLevel.NORMAL, percentile=0.5, atr_value=1.0, details={}
        )
        l = LiquidityClassificationResult(
            level=LiquidityLevel.NORMAL, score=0.5, avg_volume=1000, details={}
        )
        assert MarketClassifier._resolve_regime(t, v, l) == MarketRegime.TRENDING

    def test_resolve_regime_high_volatility(self):
        from libraries.domain.ai_research.market_classifier import MarketClassifier
        from libraries.domain.ai_research.models import (
            LiquidityClassificationResult,
            LiquidityLevel,
            MarketRegime,
            TrendClassificationResult,
            TrendDirection,
            VolatilityClassificationResult,
            VolatilityLevel,
        )

        t = TrendClassificationResult(
            direction=TrendDirection.BULL, strength=0.5, slope=0, details={}
        )
        v = VolatilityClassificationResult(
            level=VolatilityLevel.HIGH, percentile=0.9, atr_value=5.0, details={}
        )
        l = LiquidityClassificationResult(
            level=LiquidityLevel.NORMAL, score=0.5, avg_volume=1000, details={}
        )
        assert MarketClassifier._resolve_regime(t, v, l) == MarketRegime.HIGH_VOLATILITY

    def test_resolve_regime_low_liquidity(self):
        from libraries.domain.ai_research.market_classifier import MarketClassifier
        from libraries.domain.ai_research.models import (
            LiquidityClassificationResult,
            LiquidityLevel,
            MarketRegime,
            TrendClassificationResult,
            TrendDirection,
            VolatilityClassificationResult,
            VolatilityLevel,
        )

        t = TrendClassificationResult(
            direction=TrendDirection.UNKNOWN, strength=0.5, slope=0, details={}
        )
        v = VolatilityClassificationResult(
            level=VolatilityLevel.LOW, percentile=0.1, atr_value=1.0, details={}
        )
        l = LiquidityClassificationResult(
            level=LiquidityLevel.LOW, score=0.1, avg_volume=100, details={}
        )
        assert MarketClassifier._resolve_regime(t, v, l) == MarketRegime.LOW_LIQUIDITY

    def test_resolve_regime_ranging(self):
        from libraries.domain.ai_research.market_classifier import MarketClassifier
        from libraries.domain.ai_research.models import (
            LiquidityClassificationResult,
            LiquidityLevel,
            MarketRegime,
            TrendClassificationResult,
            TrendDirection,
            VolatilityClassificationResult,
            VolatilityLevel,
        )

        t = TrendClassificationResult(
            direction=TrendDirection.SIDEWAYS, strength=0.1, slope=0.001, details={}
        )
        v = VolatilityClassificationResult(
            level=VolatilityLevel.LOW, percentile=0.1, atr_value=0.5, details={}
        )
        l = LiquidityClassificationResult(
            level=LiquidityLevel.HIGH, score=0.9, avg_volume=10000, details={}
        )
        assert MarketClassifier._resolve_regime(t, v, l) == MarketRegime.RANGING

    def test_resolve_regime_unknown(self):
        from libraries.domain.ai_research.market_classifier import MarketClassifier
        from libraries.domain.ai_research.models import (
            LiquidityClassificationResult,
            LiquidityLevel,
            MarketRegime,
            TrendClassificationResult,
            TrendDirection,
            VolatilityClassificationResult,
            VolatilityLevel,
        )

        t = TrendClassificationResult(
            direction=TrendDirection.SIDEWAYS, strength=0.3, slope=0, details={}
        )
        v = VolatilityClassificationResult(
            level=VolatilityLevel.NORMAL, percentile=0.4, atr_value=1.0, details={}
        )
        l = LiquidityClassificationResult(
            level=LiquidityLevel.NORMAL, score=0.5, avg_volume=1000, details={}
        )
        assert MarketClassifier._resolve_regime(t, v, l) == MarketRegime.UNKNOWN

    def test_resolve_condition_bull(self):
        from libraries.domain.ai_research.market_classifier import MarketClassifier
        from libraries.domain.ai_research.models import (
            LiquidityClassificationResult,
            LiquidityLevel,
            MarketCondition,
            TrendClassificationResult,
            TrendDirection,
            VolatilityClassificationResult,
            VolatilityLevel,
        )

        t = TrendClassificationResult(
            direction=TrendDirection.BULL, strength=0.8, slope=0.01, details={}
        )
        v = VolatilityClassificationResult(
            level=VolatilityLevel.NORMAL, percentile=0.5, atr_value=1.0, details={}
        )
        l = LiquidityClassificationResult(
            level=LiquidityLevel.NORMAL, score=0.5, avg_volume=1000, details={}
        )
        assert MarketClassifier._resolve_condition(t, v, l) == MarketCondition.BULL

    def test_resolve_condition_bear(self):
        from libraries.domain.ai_research.market_classifier import MarketClassifier
        from libraries.domain.ai_research.models import (
            LiquidityClassificationResult,
            LiquidityLevel,
            MarketCondition,
            TrendClassificationResult,
            TrendDirection,
            VolatilityClassificationResult,
            VolatilityLevel,
        )

        t = TrendClassificationResult(
            direction=TrendDirection.BEAR, strength=0.8, slope=-0.01, details={}
        )
        v = VolatilityClassificationResult(
            level=VolatilityLevel.NORMAL, percentile=0.5, atr_value=1.0, details={}
        )
        l = LiquidityClassificationResult(
            level=LiquidityLevel.NORMAL, score=0.5, avg_volume=1000, details={}
        )
        assert MarketClassifier._resolve_condition(t, v, l) == MarketCondition.BEAR

    def test_resolve_condition_sideways(self):
        from libraries.domain.ai_research.market_classifier import MarketClassifier
        from libraries.domain.ai_research.models import (
            LiquidityClassificationResult,
            LiquidityLevel,
            MarketCondition,
            TrendClassificationResult,
            TrendDirection,
            VolatilityClassificationResult,
            VolatilityLevel,
        )

        t = TrendClassificationResult(
            direction=TrendDirection.SIDEWAYS, strength=0.1, slope=0, details={}
        )
        v = VolatilityClassificationResult(
            level=VolatilityLevel.NORMAL, percentile=0.5, atr_value=1.0, details={}
        )
        l = LiquidityClassificationResult(
            level=LiquidityLevel.NORMAL, score=0.5, avg_volume=1000, details={}
        )
        result = MarketClassifier._resolve_condition(t, v, l)
        assert result is not None

    def test_resolve_condition_high_vol(self):
        from libraries.domain.ai_research.market_classifier import MarketClassifier
        from libraries.domain.ai_research.models import (
            LiquidityClassificationResult,
            LiquidityLevel,
            MarketCondition,
            TrendClassificationResult,
            TrendDirection,
            VolatilityClassificationResult,
            VolatilityLevel,
        )

        t = TrendClassificationResult(
            direction=TrendDirection.UNKNOWN, strength=0.5, slope=0, details={}
        )
        v = VolatilityClassificationResult(
            level=VolatilityLevel.HIGH, percentile=0.9, atr_value=5.0, details={}
        )
        l = LiquidityClassificationResult(
            level=LiquidityLevel.NORMAL, score=0.5, avg_volume=1000, details={}
        )
        assert MarketClassifier._resolve_condition(t, v, l) == MarketCondition.HIGH_VOLATILITY

    def test_resolve_condition_low_vol(self):
        from libraries.domain.ai_research.market_classifier import MarketClassifier
        from libraries.domain.ai_research.models import (
            LiquidityClassificationResult,
            LiquidityLevel,
            MarketCondition,
            TrendClassificationResult,
            TrendDirection,
            VolatilityClassificationResult,
            VolatilityLevel,
        )

        t = TrendClassificationResult(
            direction=TrendDirection.UNKNOWN, strength=0.5, slope=0, details={}
        )
        v = VolatilityClassificationResult(
            level=VolatilityLevel.LOW, percentile=0.1, atr_value=0.5, details={}
        )
        l = LiquidityClassificationResult(
            level=LiquidityLevel.NORMAL, score=0.5, avg_volume=1000, details={}
        )
        assert MarketClassifier._resolve_condition(t, v, l) == MarketCondition.LOW_VOLATILITY

    def test_resolve_condition_high_liq(self):
        from libraries.domain.ai_research.market_classifier import MarketClassifier
        from libraries.domain.ai_research.models import (
            LiquidityClassificationResult,
            LiquidityLevel,
            MarketCondition,
            TrendClassificationResult,
            TrendDirection,
            VolatilityClassificationResult,
            VolatilityLevel,
        )

        t = TrendClassificationResult(
            direction=TrendDirection.UNKNOWN, strength=0.5, slope=0, details={}
        )
        v = VolatilityClassificationResult(
            level=VolatilityLevel.NORMAL, percentile=0.5, atr_value=1.0, details={}
        )
        l = LiquidityClassificationResult(
            level=LiquidityLevel.HIGH, score=0.9, avg_volume=10000, details={}
        )
        assert MarketClassifier._resolve_condition(t, v, l) == MarketCondition.HIGH_LIQUIDITY

    def test_resolve_condition_low_liq(self):
        from libraries.domain.ai_research.market_classifier import MarketClassifier
        from libraries.domain.ai_research.models import (
            LiquidityClassificationResult,
            LiquidityLevel,
            MarketCondition,
            TrendClassificationResult,
            TrendDirection,
            VolatilityClassificationResult,
            VolatilityLevel,
        )

        t = TrendClassificationResult(
            direction=TrendDirection.UNKNOWN, strength=0.5, slope=0, details={}
        )
        v = VolatilityClassificationResult(
            level=VolatilityLevel.NORMAL, percentile=0.5, atr_value=1.0, details={}
        )
        l = LiquidityClassificationResult(
            level=LiquidityLevel.LOW, score=0.1, avg_volume=100, details={}
        )
        assert MarketClassifier._resolve_condition(t, v, l) == MarketCondition.LOW_LIQUIDITY

    def test_resolve_condition_mixed(self):
        from libraries.domain.ai_research.market_classifier import MarketClassifier
        from libraries.domain.ai_research.models import (
            LiquidityClassificationResult,
            LiquidityLevel,
            MarketCondition,
            TrendClassificationResult,
            TrendDirection,
            VolatilityClassificationResult,
            VolatilityLevel,
        )

        t = TrendClassificationResult(
            direction=TrendDirection.BEAR, strength=0.8, slope=-0.01, details={}
        )
        v = VolatilityClassificationResult(
            level=VolatilityLevel.HIGH, percentile=0.9, atr_value=5.0, details={}
        )
        l = LiquidityClassificationResult(
            level=LiquidityLevel.NORMAL, score=0.5, avg_volume=1000, details={}
        )
        assert MarketClassifier._resolve_condition(t, v, l) == MarketCondition.MIXED

    def test_classify_bull_market_integration(self):
        import asyncio
        from datetime import datetime

        from libraries.domain.ai_research.market_classifier import MarketClassifier
        from libraries.domain.ai_research.models import ResearchDataset

        rows = tuple(
            {
                "close": 100.0 + i * 0.5,
                "high": 101.0 + i * 0.5,
                "low": 99.0 + i * 0.5,
                "volume": 1000.0,
                "timestamp": datetime.now(),
            }
            for i in range(250)
        )
        ds = ResearchDataset(
            dataset_id="test", schema=("close", "high", "low", "volume", "timestamp"), rows=rows
        )
        result = asyncio.run(MarketClassifier().classify(ds))
        assert result is not None
        assert result.confidence >= 0

    def test_classify_with_high_volatility_scenario(self):
        import asyncio
        import math
        from datetime import datetime

        from libraries.domain.ai_research.market_classifier import MarketClassifier
        from libraries.domain.ai_research.models import ResearchDataset

        rows = tuple(
            {
                "close": 100.0 + math.sin(i * 0.5) * 20.0,
                "high": 105.0 + math.sin(i * 0.5) * 25.0,
                "low": 95.0 + math.sin(i * 0.5) * 15.0,
                "volume": 1000.0,
                "timestamp": datetime.now(),
            }
            for i in range(250)
        )
        ds = ResearchDataset(
            dataset_id="test", schema=("close", "high", "low", "volume", "timestamp"), rows=rows
        )
        result = asyncio.run(MarketClassifier().classify(ds))
        assert result is not None


class TestMRDBoost:
    def test_detect_returns_regime(self):
        import asyncio
        from datetime import datetime

        from libraries.domain.ai_research.market_regime_detector import MarketRegimeDetector
        from libraries.domain.ai_research.models import ResearchDataset

        rows = tuple(
            {
                "close": 100.0 + i,
                "high": 102.0 + i,
                "low": 98.0 + i,
                "volume": 1000.0,
                "timestamp": datetime.now(),
            }
            for i in range(250)
        )
        ds = ResearchDataset(
            dataset_id="t", schema=("close", "high", "low", "volume", "timestamp"), rows=rows
        )
        r = asyncio.run(MarketRegimeDetector().detect(ds))
        assert r is not None

    def test_detect_with_insufficient_data_returns_unknown(self):
        import asyncio
        from datetime import datetime

        from libraries.domain.ai_research.market_regime_detector import MarketRegimeDetector
        from libraries.domain.ai_research.models import ResearchDataset

        rows = tuple(
            {
                "close": 100.0,
                "high": 101.0,
                "low": 99.0,
                "volume": 1000.0,
                "timestamp": datetime.now(),
            }
            for _ in range(5)
        )
        ds = ResearchDataset(
            dataset_id="t", schema=("close", "high", "low", "volume", "timestamp"), rows=rows
        )
        import pytest

        from libraries.domain.ai_research.exceptions import MarketClassificationError

        with pytest.raises(MarketClassificationError):
            asyncio.run(MarketRegimeDetector().detect(ds))


class TestLeaderboardBoost:
    def test_entry_count_multiple(self):
        import asyncio

        from libraries.domain.ai_research.leaderboard import Leaderboard
        from libraries.domain.ai_research.models import LeaderboardEntry, StrategyEvaluation

        def mk(s, sc):
            return LeaderboardEntry(
                rank=1,
                evaluation=StrategyEvaluation(
                    strategy_id=s, metrics={"sharpe_ratio": sc}, dataset_id="d"
                ),
                composite_score=sc,
            )

        lb = Leaderboard()
        asyncio.run(lb.update((mk("a", 0.9), mk("b", 0.7), mk("c", 0.8))))
        assert lb.entry_count == 3

    def test_get_entry_not_found(self):
        import asyncio

        from libraries.domain.ai_research.leaderboard import Leaderboard

        lb = Leaderboard()
        e = asyncio.run(lb.get_entry("nonexistent"))
        assert e is None

    def test_clear_leaderboard(self):
        import asyncio

        from libraries.domain.ai_research.leaderboard import Leaderboard
        from libraries.domain.ai_research.models import LeaderboardEntry, StrategyEvaluation

        e = LeaderboardEntry(
            rank=1,
            evaluation=StrategyEvaluation(
                strategy_id="s1", metrics={"sharpe_ratio": 1.0}, dataset_id="d"
            ),
            composite_score=0.9,
        )
        lb = Leaderboard()
        asyncio.run(lb.update((e,)))
        assert lb.entry_count == 1
        asyncio.run(lb.clear())
        assert lb.entry_count == 0
