"""Tests for PortfolioAnalyticsEngine — performance and risk metrics.

Covers:
- Win/Loss rate, Profit factor
- Sharpe/Sortino ratios (placeholder)
- Recovery factor, Consecutive wins/losses
- Drawdown tracking
"""

from __future__ import annotations

import math

import pytest

from libraries.domain.portfolio.analytics import PortfolioAnalytics, PortfolioAnalyticsEngine


@pytest.fixture
async def engine() -> PortfolioAnalyticsEngine:
    """Create a clean analytics engine for each test."""
    e = PortfolioAnalyticsEngine()
    yield e
    await e.clear()


class TestInitialState:
    """Initial state scenarios."""

    async def test_empty_analytics(self, engine: PortfolioAnalyticsEngine):
        analytics = await engine.calculate()
        assert analytics.total_trades == 0
        assert analytics.win_rate == 0.0
        assert analytics.profit_factor == 0.0
        assert analytics.sharpe_ratio == 0.0
        assert analytics.sortino_ratio == 0.0
        assert analytics.recovery_factor == 0.0

    async def test_all_fields_present(self, engine: PortfolioAnalyticsEngine):
        analytics = await engine.calculate()
        assert hasattr(analytics, "total_trades")
        assert hasattr(analytics, "winning_trades")
        assert hasattr(analytics, "losing_trades")
        assert hasattr(analytics, "win_rate")
        assert hasattr(analytics, "profit_factor")
        assert hasattr(analytics, "sharpe_ratio")
        assert hasattr(analytics, "sortino_ratio")
        assert hasattr(analytics, "calmar_ratio")
        assert hasattr(analytics, "average_win")
        assert hasattr(analytics, "average_loss")
        assert hasattr(analytics, "largest_win")
        assert hasattr(analytics, "largest_loss")
        assert hasattr(analytics, "expected_value")
        assert hasattr(analytics, "recovery_factor")
        assert hasattr(analytics, "portfolio_heat")
        assert hasattr(analytics, "max_consecutive_wins")
        assert hasattr(analytics, "max_consecutive_losses")


class TestWinRate:
    """Win rate scenarios."""

    async def test_all_wins(self, engine: PortfolioAnalyticsEngine):
        for _ in range(10):
            await engine.record_trade(pnl=100.0, is_win=True, is_loss=False)
        analytics = await engine.calculate()
        assert analytics.win_rate == 1.0
        assert analytics.winning_trades == 10

    async def test_all_losses(self, engine: PortfolioAnalyticsEngine):
        for _ in range(10):
            await engine.record_trade(pnl=-50.0, is_win=False, is_loss=True)
        analytics = await engine.calculate()
        assert analytics.win_rate == 0.0
        assert analytics.losing_trades == 10

    async def test_mixed_results(self, engine: PortfolioAnalyticsEngine):
        for _ in range(7):
            await engine.record_trade(pnl=100.0, is_win=True, is_loss=False)
        for _ in range(3):
            await engine.record_trade(pnl=-50.0, is_win=False, is_loss=True)
        analytics = await engine.calculate()
        assert analytics.total_trades == 10
        assert analytics.win_rate == 0.7
        assert analytics.winning_trades == 7
        assert analytics.losing_trades == 3

    async def test_breakeven_trades(self, engine: PortfolioAnalyticsEngine):
        await engine.record_trade(pnl=0.0, is_win=False, is_loss=False)
        analytics = await engine.calculate()
        assert analytics.total_trades == 1
        assert analytics.win_rate == 0.0


class TestProfitFactor:
    """Profit factor scenarios."""

    async def test_profit_factor_basic(self, engine: PortfolioAnalyticsEngine):
        await engine.record_trade(pnl=200.0, is_win=True, is_loss=False)
        await engine.record_trade(pnl=-100.0, is_win=False, is_loss=True)
        analytics = await engine.calculate()
        assert analytics.profit_factor == 2.0  # 200/100

    async def test_profit_factor_no_losses(self, engine: PortfolioAnalyticsEngine):
        await engine.record_trade(pnl=100.0, is_win=True, is_loss=False)
        await engine.record_trade(pnl=50.0, is_win=True, is_loss=False)
        analytics = await engine.calculate()
        assert analytics.profit_factor == float("inf")

    async def test_profit_factor_no_wins(self, engine: PortfolioAnalyticsEngine):
        await engine.record_trade(pnl=-50.0, is_win=False, is_loss=True)
        analytics = await engine.calculate()
        assert analytics.profit_factor == 0.0


class TestAverageWinLoss:
    """Average win/loss scenarios."""

    async def test_average_win(self, engine: PortfolioAnalyticsEngine):
        await engine.record_trade(pnl=100.0, is_win=True, is_loss=False)
        await engine.record_trade(pnl=200.0, is_win=True, is_loss=False)
        analytics = await engine.calculate()
        assert analytics.average_win == 150.0

    async def test_average_loss(self, engine: PortfolioAnalyticsEngine):
        await engine.record_trade(pnl=-50.0, is_win=False, is_loss=True)
        await engine.record_trade(pnl=-150.0, is_win=False, is_loss=True)
        analytics = await engine.calculate()
        assert analytics.average_loss == -100.0

    async def test_largest_win(self, engine: PortfolioAnalyticsEngine):
        await engine.record_trade(pnl=100.0, is_win=True, is_loss=False)
        await engine.record_trade(pnl=300.0, is_win=True, is_loss=False)
        await engine.record_trade(pnl=200.0, is_win=True, is_loss=False)
        analytics = await engine.calculate()
        assert analytics.largest_win == 300.0

    async def test_largest_loss(self, engine: PortfolioAnalyticsEngine):
        await engine.record_trade(pnl=-50.0, is_win=False, is_loss=True)
        await engine.record_trade(pnl=-200.0, is_win=False, is_loss=True)
        await engine.record_trade(pnl=-100.0, is_win=False, is_loss=True)
        analytics = await engine.calculate()
        assert analytics.largest_loss == -200.0


class TestExpectedValue:
    """Expected value scenarios."""

    async def test_positive_expected_value(self, engine: PortfolioAnalyticsEngine):
        for _ in range(6):
            await engine.record_trade(pnl=100.0, is_win=True, is_loss=False)
        for _ in range(4):
            await engine.record_trade(pnl=-50.0, is_win=False, is_loss=True)
        analytics = await engine.calculate()
        # ev = 0.6*100 - 0.4*50 = 60 - 20 = 40
        assert analytics.expected_value == 40.0


class TestSharpeRatio:
    """Sharpe ratio scenarios."""

    async def test_sharpe_ratio_positive(self, engine: PortfolioAnalyticsEngine):
        # Use varied PnL values so variance > 0
        pnls = [100.0, 110.0, 90.0, 105.0, 95.0, 115.0, 85.0, 108.0, 92.0, 103.0]
        for pnl in pnls:
            await engine.record_trade(pnl=pnl, is_win=True, is_loss=False)
        analytics = await engine.calculate()
        assert analytics.sharpe_ratio > 0

    async def test_sharpe_ratio_single_trade(self, engine: PortfolioAnalyticsEngine):
        await engine.record_trade(pnl=100.0, is_win=True, is_loss=False)
        analytics = await engine.calculate()
        assert analytics.sharpe_ratio == 0.0  # not enough data

    async def test_sharpe_ratio_negative(self, engine: PortfolioAnalyticsEngine):
        # Use varied PnL values so variance > 0
        pnls = [-50.0, -55.0, -45.0, -52.0, -48.0, -60.0, -40.0, -53.0, -47.0, -51.0]
        for pnl in pnls:
            await engine.record_trade(pnl=pnl, is_win=False, is_loss=True)
        analytics = await engine.calculate()
        assert analytics.sharpe_ratio < 0


class TestSortinoRatio:
    """Sortino ratio scenarios."""

    async def test_sortino_ratio_positive(self, engine: PortfolioAnalyticsEngine):
        for _ in range(10):
            await engine.record_trade(pnl=100.0, is_win=True, is_loss=False)
        analytics = await engine.calculate()
        assert analytics.sortino_ratio >= 0

    async def test_sortino_no_negative_returns(self, engine: PortfolioAnalyticsEngine):
        await engine.record_trade(pnl=100.0, is_win=True, is_loss=False)
        analytics = await engine.calculate()
        assert analytics.sortino_ratio == 0.0


class TestRecoveryFactor:
    """Recovery factor scenarios."""

    async def test_recovery_factor_basic(self, engine: PortfolioAnalyticsEngine):
        await engine.record_equity(10000.0)
        await engine.record_equity(8000.0)  # drawdown
        await engine.record_trade(pnl=200.0, is_win=True, is_loss=False)
        analytics = await engine.calculate()
        # recovery = total_pnl / max_dd = 200 / 2000 = 0.1
        assert analytics.recovery_factor > 0

    async def test_recovery_factor_no_drawdown(self, engine: PortfolioAnalyticsEngine):
        await engine.record_trade(pnl=100.0, is_win=True, is_loss=False)
        analytics = await engine.calculate()
        assert analytics.recovery_factor == 0.0

    async def test_get_max_drawdown(self, engine: PortfolioAnalyticsEngine):
        await engine.record_equity(10000.0)
        await engine.record_equity(9000.0)
        await engine.record_equity(8000.0)
        await engine.record_equity(8500.0)
        max_dd = await engine.get_max_drawdown()
        assert max_dd == 2000.0  # 10000 - 8000

    async def test_get_current_drawdown(self, engine: PortfolioAnalyticsEngine):
        await engine.record_equity(10000.0)
        await engine.record_equity(8500.0)
        current_dd = await engine.get_current_drawdown()
        assert current_dd == 1500.0


class TestConsecutiveWinsLosses:
    """Consecutive wins/losses scenarios."""

    async def test_consecutive_wins(self, engine: PortfolioAnalyticsEngine):
        outcomes = [(100, True, False)] * 5 + [(-50, False, True)] * 2 + [(100, True, False)] * 3
        for pnl, win, loss in outcomes:
            await engine.record_trade(pnl=pnl, is_win=win, is_loss=loss)
        analytics = await engine.calculate()
        assert analytics.max_consecutive_wins == 5

    async def test_consecutive_losses(self, engine: PortfolioAnalyticsEngine):
        outcomes = [(100, True, False)] * 2 + [(-50, False, True)] * 4 + [(100, True, False)] * 1
        for pnl, win, loss in outcomes:
            await engine.record_trade(pnl=pnl, is_win=win, is_loss=loss)
        analytics = await engine.calculate()
        assert analytics.max_consecutive_losses == 4

    async def test_consecutive_with_breakeven(self, engine: PortfolioAnalyticsEngine):
        await engine.record_trade(pnl=100.0, is_win=True, is_loss=False)
        await engine.record_trade(pnl=100.0, is_win=True, is_loss=False)
        await engine.record_trade(pnl=0.0, is_win=False, is_loss=False)  # breaks streak
        await engine.record_trade(pnl=100.0, is_win=True, is_loss=False)
        analytics = await engine.calculate()
        assert analytics.max_consecutive_wins == 2


class TestPortfolioHeat:
    """Portfolio heat scenarios."""

    async def test_portfolio_heat_in_analytics(self, engine: PortfolioAnalyticsEngine):
        analytics = await engine.calculate(portfolio_heat=75.5)
        assert analytics.portfolio_heat == 75.5

    async def test_set_portfolio_heat(self, engine: PortfolioAnalyticsEngine):
        await engine.set_portfolio_heat(50.0)
        analytics = await engine.calculate()
        # portfolio_heat from calculate arg defaults to 0 if not passed
        assert analytics.portfolio_heat == 0.0


class TestClear:
    """Clear scenarios."""

    async def test_clear_engine(self, engine: PortfolioAnalyticsEngine):
        await engine.record_trade(pnl=100.0, is_win=True, is_loss=False)
        await engine.record_equity(10000.0)
        await engine.clear()
        analytics = await engine.calculate()
        assert analytics.total_trades == 0
        max_dd = await engine.get_max_drawdown()
        assert max_dd == 0.0
