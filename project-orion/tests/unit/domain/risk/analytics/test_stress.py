"""Tests for the StressTestEngine (EPIC-014 Sprint-4)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.risk.analytics.models import (
    Scenario,
    StressTestType,
)
from libraries.domain.risk.analytics.stress import StressTestEngine
from libraries.domain.risk.analytics.validation import InvalidValueError


class TestApplyScenario:
    """Test StressTestEngine.apply_scenario."""

    async def _engine(self) -> StressTestEngine:
        return StressTestEngine()

    @pytest.mark.asyncio
    async def test_applies_shock_factors(self) -> None:
        engine = await self._engine()
        result = await engine.apply_scenario(
            returns_by_symbol={"EURUSD": [0.01], "GBPUSD": [0.02]},
            scenario=Scenario(
                name="crisis",
                shock_factors={"EURUSD": -0.15, "GBPUSD": -0.10},
            ),
            portfolio_value=Decimal("100000"),
        )
        assert result.name == "crisis"
        assert result.portfolio_value < Decimal("100000")
        assert result.portfolio_return < 0.0
        assert result.symbol_returns["EURUSD"] == -0.15
        assert result.symbol_returns["GBPUSD"] == -0.10

    @pytest.mark.asyncio
    async def test_unshocked_symbols_get_zero(self) -> None:
        engine = await self._engine()
        result = await engine.apply_scenario(
            returns_by_symbol={"EURUSD": [0.01], "USDJPY": [0.02]},
            scenario=Scenario(
                name="partial", shock_factors={"EURUSD": -0.10}
            ),
            portfolio_value=Decimal("1000"),
        )
        # USDJPY not in scenario -> shock factor 0.0
        assert result.symbol_returns["USDJPY"] == 0.0

    @pytest.mark.asyncio
    async def test_empty_scenario_raises_error(self) -> None:
        engine = await self._engine()
        with pytest.raises(InvalidValueError, match="scenario must define"):
            await engine.apply_scenario(
                returns_by_symbol={"EURUSD": [0.01]},
                scenario=Scenario(name="empty", shock_factors={}),
                portfolio_value=Decimal("1000"),
            )


class TestRunHistoricalStress:
    """Test StressTestEngine.run_historical_stress."""

    async def _engine(self) -> StressTestEngine:
        return StressTestEngine()

    @pytest.mark.asyncio
    async def test_aggregates_windows(self) -> None:
        engine = await self._engine()
        summary = await engine.run_historical_stress(
            returns_by_symbol={
                "gfc": {"EURUSD": [-0.1, -0.2, -0.05]},
                "covid": {"EURUSD": [-0.08, -0.15, -0.03]},
            },
            portfolio_weights={"EURUSD": 1.0},
            portfolio_value=Decimal("100000"),
        )
        assert summary.test_type == StressTestType.HISTORICAL
        assert summary.worst_case_return < 0.0
        assert summary.best_case_return < 0.0
        assert len(summary.results) == 2

    @pytest.mark.asyncio
    async def test_empty_returns_raises_error(self) -> None:
        engine = await self._engine()
        with pytest.raises(InvalidValueError, match="returns_by_symbol must not be empty"):
            await engine.run_historical_stress(
                returns_by_symbol={},
                portfolio_weights={"EURUSD": 1.0},
                portfolio_value=Decimal("1000"),
            )

    @pytest.mark.asyncio
    async def test_empty_weights_raises_error(self) -> None:
        engine = await self._engine()
        with pytest.raises(InvalidValueError, match="portfolio_weights must not be empty"):
            await engine.run_historical_stress(
                returns_by_symbol={"gfc": {"EURUSD": [-0.1]}},
                portfolio_weights={},
                portfolio_value=Decimal("1000"),
            )


class TestApplyPortfolioShock:
    """Test StressTestEngine.apply_portfolio_shock."""

    async def _engine(self) -> StressTestEngine:
        return StressTestEngine()

    @pytest.mark.asyncio
    async def test_applies_uniform_shock(self) -> None:
        engine = await self._engine()
        summary = await engine.apply_portfolio_shock(
            returns_by_symbol={"EURUSD": [0.01, -0.02, 0.015]},
            portfolio_weights={"EURUSD": 1.0},
            shock_pct=0.10,
            portfolio_value=Decimal("100000"),
        )
        assert summary.portfolio_shock_pct > 0.0
        assert len(summary.results) == 1

    @pytest.mark.asyncio
    async def test_zero_shock_pct_raises_error(self) -> None:
        engine = await self._engine()
        with pytest.raises(InvalidValueError, match="shock_pct must be positive"):
            await engine.apply_portfolio_shock(
                returns_by_symbol={"EURUSD": [0.01]},
                portfolio_weights={"EURUSD": 1.0},
                shock_pct=0.0,
                portfolio_value=Decimal("1000"),
            )


class TestSimulateMarketCrash:
    """Test StressTestEngine.simulate_market_crash."""

    async def _engine(self) -> StressTestEngine:
        return StressTestEngine()

    @pytest.mark.asyncio
    async def test_crash_reduces_portfolio_value(self) -> None:
        engine = await self._engine()
        result = await engine.simulate_market_crash(
            returns=[0.001, -0.002, 0.003],
            crash_pct=0.30,
            recovery_days=10,
            portfolio_value=Decimal("100000"),
        )
        assert result.test_type == StressTestType.MARKET_CRASH
        assert result.portfolio_return < 0.0
        assert result.portfolio_value < Decimal("100000")

    @pytest.mark.asyncio
    async def test_no_recovery_days(self) -> None:
        engine = await self._engine()
        result = await engine.simulate_market_crash(
            returns=[0.001, -0.002],
            crash_pct=0.20,
            recovery_days=0,
            portfolio_value=Decimal("100000"),
        )
        assert result.portfolio_return == -0.20

    @pytest.mark.asyncio
    async def test_invalid_recovery_days_raises_error(self) -> None:
        engine = await self._engine()
        with pytest.raises(InvalidValueError, match="recovery_days"):
            await engine.simulate_market_crash(
                returns=[0.01], crash_pct=0.10, recovery_days=-1, portfolio_value=Decimal("1000"),
            )


class TestApplyVolatilityShock:
    """Test StressTestEngine.apply_volatility_shock."""

    async def _engine(self) -> StressTestEngine:
        return StressTestEngine()

    @pytest.mark.asyncio
    async def test_higher_multiplier_more_loss(self) -> None:
        engine = await self._engine()
        result_1x = await engine.apply_volatility_shock(
            returns=[0.001, -0.002, 0.0015],
            volatility_multiplier=1.0,
            portfolio_value=Decimal("100000"),
        )
        result_3x = await engine.apply_volatility_shock(
            returns=[0.001, -0.002, 0.0015],
            volatility_multiplier=3.0,
            portfolio_value=Decimal("100000"),
        )
        assert result_1x.test_type == StressTestType.VOLATILITY_SHOCK
        # 3x multiplier should produce a more negative (or equal) return
        assert result_3x.portfolio_return <= result_1x.portfolio_return

    @pytest.mark.asyncio
    async def test_zero_multiplier_raises_error(self) -> None:
        engine = await self._engine()
        with pytest.raises(InvalidValueError, match="volatility_multiplier"):
            await engine.apply_volatility_shock(
                returns=[0.01], volatility_multiplier=0.0, portfolio_value=Decimal("1000"),
            )


class TestBuildSummary:
    """Test the internal _build_summary helper."""

    def test_single_result_summary(self) -> None:
        from libraries.domain.risk.analytics.stress import StressTestEngine
        from libraries.domain.risk.analytics.models import StressTestResult

        result = StressTestResult(
            test_type=StressTestType.SCENARIO,
            name="crisis",
            portfolio_value=Decimal("85000"),
            portfolio_return=-0.15,
        )
        summary = StressTestEngine._build_summary(
            test_type=StressTestType.SCENARIO,
            name="s",
            results=[result],
        )
        assert summary.portfolio_shock_pct == 15.0
        assert summary.worst_case_return == -0.15
        assert summary.best_case_return == -0.15
        assert summary.average_return == -0.15

    def test_empty_results_raises_error(self) -> None:
        from libraries.domain.risk.analytics.stress import StressTestEngine

        with pytest.raises(InvalidValueError, match="at least one"):
            StressTestEngine._build_summary(
                test_type=StressTestType.SCENARIO,
                name="s",
                results=[],
            )


class TestStdDev:
    """Test the internal _stddev helper."""

    def test_stddev_of_constant_series(self) -> None:
        from libraries.domain.risk.analytics.stress import StressTestEngine

        std = StressTestEngine._stddev([5.0, 5.0, 5.0])
        assert std == 0.0

    def test_stddev_of_changing_series(self) -> None:
        std = StressTestEngine._stddev([1.0, 2.0, 3.0, 4.0, 5.0])
        assert std == pytest.approx(1.41421356, rel=1e-5)

    def test_stddev_single_element(self) -> None:
        std = StressTestEngine._stddev([42.0])
        assert std == 0.0
