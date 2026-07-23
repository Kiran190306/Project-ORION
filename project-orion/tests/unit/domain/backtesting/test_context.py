"""Tests for EPIC-010 BacktestContext."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.backtesting.context import BacktestContext
from libraries.domain.backtesting.models import BacktestConfig, ReplayConfig, SimulationConfig


class TestBacktestContext:
    """Test BacktestContext frozen dataclass."""

    def test_default_context(self):
        ctx = BacktestContext()
        assert isinstance(ctx.backtest_config, BacktestConfig)
        assert isinstance(ctx.replay_config, ReplayConfig)
        assert isinstance(ctx.simulation_config, SimulationConfig)

    def test_custom_context(self):
        cfg = BacktestConfig(name="test_backtest", initial_balance=Decimal("50000"))
        rcfg = ReplayConfig(speed_multiplier=2.0)
        scfg = SimulationConfig(max_slippage_bps=5.0)
        ctx = BacktestContext(backtest_config=cfg, replay_config=rcfg, simulation_config=scfg)
        assert ctx.backtest_config.name == "test_backtest"
        assert ctx.replay_config.speed_multiplier == 2.0
        assert ctx.simulation_config.max_slippage_bps == 5.0
        assert ctx.mid_price == Decimal("0")

    def test_context_is_frozen(self):
        ctx = BacktestContext()
        with pytest.raises(AttributeError):
            ctx.backtest_config = BacktestConfig()  # type: ignore[misc]

    def test_mid_price(self):
        ctx = BacktestContext(current_bid=Decimal("1.0990"), current_ask=Decimal("1.1000"))
        assert ctx.mid_price == Decimal("1.0995")

    def test_is_market_open(self):
        from libraries.domain.backtesting.models import ReplayState

        ctx = BacktestContext()
        assert ctx.is_market_open is False
        ctx2 = BacktestContext(replay_state=ReplayState.PLAYING)
        assert ctx2.is_market_open is True

    def test_elapsed_bars(self):
        ctx = BacktestContext(processed_bars=50)
        assert ctx.elapsed_bars == 50

    def test_remaining_bars(self):
        ctx = BacktestContext(total_bars=100, processed_bars=30)
        assert ctx.remaining_bars == 70

    def test_check_summary(self):
        ctx = BacktestContext()
        summary = ctx.check_summary
        assert "bar_index" in summary
        assert "timestamp" in summary
        assert "replay_state" in summary
