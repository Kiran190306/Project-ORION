"""Tests for EPIC-010 MonteCarloSimulator."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.backtesting.models import MonteCarloConfig, MonteCarloResult
from libraries.domain.backtesting.monte_carlo import MonteCarloSimulator


class TestMonteCarloSimulatorInitialization:
    """Test Monte Carlo simulator creation."""

    def test_default_config(self):
        sim = MonteCarloSimulator()
        assert sim.config.num_simulations == 1000
        assert sim.config.random_seed == 42

    def test_custom_config(self):
        config = MonteCarloConfig(num_simulations=500, random_seed=123)
        sim = MonteCarloSimulator(config)
        assert sim.config.num_simulations == 500
        assert sim.config.random_seed == 123


class TestMonteCarloTradeOrdering:
    """Test trade reordering simulation."""

    @pytest.mark.asyncio
    async def test_empty_trades(self):
        sim = MonteCarloSimulator()
        result = await sim.simulate_trade_ordering([], num_simulations=10)
        assert result.simulation_type == "trade_ordering"
        assert result.num_simulations == 10
        assert result.mean == 0.0

    @pytest.mark.asyncio
    async def test_single_trade(self):
        sim = MonteCarloSimulator()
        trades = [{"pnl": 100.0}]
        result = await sim.simulate_trade_ordering(trades, num_simulations=10)
        assert result.mean == 100.0  # Only one trade, always same
        assert result.pct_positive > 0

    @pytest.mark.asyncio
    async def test_multiple_trades(self):
        sim = MonteCarloSimulator()
        trades = [{"pnl": 100.0}, {"pnl": -50.0}]
        result = await sim.simulate_trade_ordering(trades, num_simulations=100)
        assert result.mean == 50.0  # Always 100 - 50 = 50 regardless of order
        assert result.num_simulations == 100

    @pytest.mark.asyncio
    async def test_deterministic_seed(self):
        sim1 = MonteCarloSimulator(MonteCarloConfig(random_seed=42))
        sim2 = MonteCarloSimulator(MonteCarloConfig(random_seed=42))
        trades = [{"pnl": 100.0}, {"pnl": 200.0}, {"pnl": -50.0}, {"pnl": -30.0}]
        r1 = await sim1.simulate_trade_ordering(trades, num_simulations=50)
        r2 = await sim2.simulate_trade_ordering(trades, num_simulations=50)
        assert r1.mean == r2.mean

    @pytest.mark.asyncio
    async def test_large_number_of_trades(self):
        sim = MonteCarloSimulator()
        trades = [{"pnl": float(i)} for i in range(100)]
        result = await sim.simulate_trade_ordering(trades, num_simulations=20)
        assert result.num_simulations == 20


class TestMonteCarloTradeRemoval:
    """Test trade removal simulation."""

    @pytest.mark.asyncio
    async def test_empty_trades(self):
        sim = MonteCarloSimulator()
        result = await sim.simulate_trade_removal([], num_simulations=10)
        assert result.mean == 0.0

    @pytest.mark.asyncio
    async def test_no_removal(self):
        sim = MonteCarloSimulator()
        trades = [{"pnl": 100.0}, {"pnl": 200.0}]
        result = await sim.simulate_trade_removal(trades, removal_fraction=0.0, num_simulations=10)
        assert result.mean == 300.0  # All trades kept

    @pytest.mark.asyncio
    async def test_full_removal(self):
        sim = MonteCarloSimulator()
        trades = [{"pnl": 100.0}]
        result = await sim.simulate_trade_removal(trades, removal_fraction=1.0, num_simulations=10)
        assert result.mean == 0.0  # All trades removed

    @pytest.mark.asyncio
    async def test_partial_removal(self):
        sim = MonteCarloSimulator()
        trades = [{"pnl": 100.0}, {"pnl": 100.0}, {"pnl": 100.0}, {"pnl": 100.0}, {"pnl": 100.0}]
        result = await sim.simulate_trade_removal(trades, removal_fraction=1.0, num_simulations=10)
        assert result.mean == 0.0  # All trades removed


class TestMonteCarloSpreadVariation:
    """Test spread variation simulation."""

    @pytest.mark.asyncio
    async def test_base_pnl(self):
        sim = MonteCarloSimulator()
        result = await sim.simulate_spread_variation(
            base_pnl=1000.0,
            spread_cost_per_trade=0.0,
            num_simulations=10,
        )
        # With no spread cost, PnL should always be 1000
        assert abs(result.mean - 1000.0) < 0.01

    @pytest.mark.asyncio
    async def test_spread_reduces_pnl(self):
        sim = MonteCarloSimulator()
        result = await sim.simulate_spread_variation(
            base_pnl=1000.0,
            spread_cost_per_trade=100.0,
            num_simulations=100,
        )
        # With spread cost, PnL should be reduced
        assert result.mean < 1000.0


class TestMonteCarloSlippageVariation:
    """Test slippage variation simulation."""

    @pytest.mark.asyncio
    async def test_no_slippage_cost(self):
        sim = MonteCarloSimulator()
        result = await sim.simulate_slippage_variation(
            base_pnl=1000.0,
            slippage_cost_per_trade=0.0,
            num_simulations=10,
        )
        assert abs(result.mean - 1000.0) < 0.01

    @pytest.mark.asyncio
    async def test_slippage_reduces_pnl(self):
        sim = MonteCarloSimulator()
        result = await sim.simulate_slippage_variation(
            base_pnl=1000.0,
            slippage_cost_per_trade=50.0,
            num_simulations=100,
        )
        assert result.mean < 1000.0


class TestMonteCarloExecutionDelay:
    """Test execution delay simulation."""

    @pytest.mark.asyncio
    async def test_empty_trades(self):
        sim = MonteCarloSimulator()
        result = await sim.simulate_execution_delay([], num_simulations=10)
        assert result.mean == 0.0

    @pytest.mark.asyncio
    async def test_single_trade_no_impact(self):
        sim = MonteCarloSimulator()
        trades = [{"pnl": 100.0, "price": 1.1000}]
        result = await sim.simulate_execution_delay(
            trades, price_impact_per_bar=0.0, num_simulations=10
        )
        # With no price impact, PnL should be unchanged
        assert abs(result.mean - 100.0) < 1.0

    @pytest.mark.asyncio
    async def test_execution_delay_impact(self):
        sim = MonteCarloSimulator()
        trades = [{"pnl": 100.0, "price": 1.1000}]
        result = await sim.simulate_execution_delay(
            trades, price_impact_per_bar=0.1, num_simulations=100
        )
        # With high price impact, PnL should be reduced on average
        assert result.mean < 100.0


class TestMonteCarloRunAll:
    """Test running all simulations."""

    @pytest.mark.asyncio
    async def test_run_all_empty_trades(self):
        sim = MonteCarloSimulator(MonteCarloConfig(num_simulations=10))
        results = await sim.run_all([])
        assert len(results) == 5
        assert "trade_ordering" in results
        assert "trade_removal" in results
        assert "spread_variation" in results
        assert "slippage_variation" in results
        assert "execution_delay" in results

    @pytest.mark.asyncio
    async def test_run_all_with_trades(self):
        sim = MonteCarloSimulator(MonteCarloConfig(num_simulations=10))
        trades = [{"pnl": 100.0, "price": 1.1000}, {"pnl": -50.0, "price": 1.2000}]
        results = await sim.run_all(trades, spread_cost_per_trade=5.0, slippage_cost_per_trade=3.0)
        assert len(results) == 5
        for name, result in results.items():
            assert isinstance(result, MonteCarloResult)
            assert result.num_simulations == 10

    @pytest.mark.asyncio
    async def test_run_all_deterministic(self):
        sim1 = MonteCarloSimulator(MonteCarloConfig(num_simulations=10, random_seed=42))
        sim2 = MonteCarloSimulator(MonteCarloConfig(num_simulations=10, random_seed=42))
        trades = [{"pnl": 100.0}]
        r1 = await sim1.run_all(trades)
        r2 = await sim2.run_all(trades)
        for name in r1:
            assert r1[name].mean == r2[name].mean


class TestMonteCarloResult:
    """Test MonteCarloResult model."""

    def test_result_defaults(self):
        result = MonteCarloResult()
        assert result.num_simulations == 0
        assert result.median == 0.0
        assert result.mean == 0.0

    def test_result_custom(self):
        result = MonteCarloResult(
            simulation_type="trade_ordering",
            num_simulations=100,
            median=50000.0,
            mean=51000.0,
            std=10000.0,
            min_val=10000.0,
            max_val=90000.0,
            percentile_5=20000.0,
            percentile_25=40000.0,
            percentile_75=60000.0,
            percentile_95=80000.0,
            pct_positive=0.85,
            prob_profit=0.85,
            prob_ruin=0.15,
            ci_lower_95=30000.0,
            ci_upper_95=70000.0,
        )
        assert result.num_simulations == 100
        assert result.median == 50000.0
        assert result.mean == 51000.0
        assert result.pct_positive == 0.85

    def test_percentiles(self):
        result = MonteCarloResult(
            num_simulations=1000,
            percentile_5=-5000.0,
            percentile_25=1000.0,
            percentile_75=15000.0,
            percentile_95=25000.0,
        )
        assert result.percentile_5 == -5000.0
        assert result.percentile_95 == 25000.0

    def test_standard_monte_carlo_config_defaults(self):
        config = MonteCarloConfig()
        assert config.num_simulations == 1000
        assert config.random_seed == 42
