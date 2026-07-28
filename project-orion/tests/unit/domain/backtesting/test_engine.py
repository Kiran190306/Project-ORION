"""Tests for EPIC-010 BacktestEngine — main orchestrator."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from libraries.domain.backtesting.engine import BacktestEngine, BacktestEngineResult
from libraries.domain.backtesting.models import (
    BacktestConfig,
    BacktestResult,
    EquitySnapshot,
    ExecutionSimulationResult,
    ExecutionSimulationStatus,
    OrderSimulation,
    OrderSimulationSide,
    OrderSimulationType,
    PerformanceMetrics,
    ReplayMode,
    Timeframe,
)
from libraries.domain.backtesting.portfolio_simulator import PortfolioSimulationConfig


class TestBacktestEngineInitialization:
    """Test engine initialization with various configurations."""

    def test_default_initialization(self):
        engine = BacktestEngine()
        assert engine.config is not None
        assert engine.config.name == "backtest"
        assert engine.config.initial_balance == Decimal("10000")
        assert engine.portfolio is not None
        assert engine.replay is not None
        assert engine.execution is not None

    def test_custom_config(self):
        cfg = BacktestConfig(
            name="custom_test",
            symbols=("GBPUSD", "EURJPY"),
            timeframes=(Timeframe.M15, Timeframe.H1),
            initial_balance=Decimal("50000"),
        )
        engine = BacktestEngine(config=cfg)
        assert engine.config.name == "custom_test"
        assert engine.config.initial_balance == Decimal("50000")

    def test_custom_portfolio_config(self):
        pcfg = PortfolioSimulationConfig(initial_balance=Decimal("100000"))
        engine = BacktestEngine(portfolio_config=pcfg)
        assert engine.portfolio.config.initial_balance == Decimal("100000")

    @pytest.mark.asyncio
    async def test_engine_properties(self):
        engine = BacktestEngine()
        assert hasattr(engine, "config")
        assert hasattr(engine, "portfolio")
        assert hasattr(engine, "replay")
        assert hasattr(engine, "execution")
        # Properties should return the correct types
        from libraries.domain.backtesting.execution_simulator import ExecutionSimulator
        from libraries.domain.backtesting.portfolio_simulator import PortfolioSimulator
        from libraries.domain.backtesting.replay_engine import ReplayEngine

        assert isinstance(engine.portfolio, PortfolioSimulator)
        assert isinstance(engine.replay, ReplayEngine)
        assert isinstance(engine.execution, ExecutionSimulator)

    def test_empty_symbols_config(self):
        cfg = BacktestConfig(symbols=())
        engine = BacktestEngine(config=cfg)
        assert engine.config.symbols == ()

    def test_backtest_engine_result_defaults(self):
        result = BacktestEngineResult(success=False, error="failed")
        assert result.success is False
        assert result.error == "failed"
        assert result.execution_time_seconds == 0.0
        assert result.result is None

    def test_backtest_engine_result_success(self):
        bt_result = BacktestResult()
        result = BacktestEngineResult(
            success=True,
            result=bt_result,
            execution_time_seconds=1.5,
        )
        assert result.success is True
        assert result.result is bt_result
        assert result.execution_time_seconds == 1.5


class TestBacktestEngineCandleHandling:
    """Test candle event handling."""

    @pytest.mark.asyncio
    async def test_on_candle_updates_market_state(self):
        engine = BacktestEngine()
        ts = datetime.now(timezone.utc)
        await engine.on_candle(
            symbol="EURUSD",
            timestamp=ts,
            open_price=Decimal("1.1000"),
            high=Decimal("1.1050"),
            low=Decimal("1.0950"),
            close=Decimal("1.1020"),
            volume=Decimal("1000"),
        )
        # Equity curve should have been updated
        assert len(engine._equity_curve) == 1
        assert engine._current_bid > Decimal("0")
        assert engine._current_ask > Decimal("0")

    @pytest.mark.asyncio
    async def test_on_candle_with_different_symbols(self):
        engine = BacktestEngine()
        ts = datetime.now(timezone.utc)
        await engine.on_candle(
            symbol="GBPUSD",
            timestamp=ts,
            open_price=Decimal("1.3000"),
            high=Decimal("1.3100"),
            low=Decimal("1.2900"),
            close=Decimal("1.3050"),
            volume=Decimal("500"),
        )
        assert len(engine._equity_curve) == 1

    @pytest.mark.asyncio
    async def test_on_candle_zero_volume(self):
        engine = BacktestEngine()
        ts = datetime.now(timezone.utc)
        await engine.on_candle(
            symbol="EURUSD",
            timestamp=ts,
            open_price=Decimal("1.1000"),
            high=Decimal("1.1050"),
            low=Decimal("1.0950"),
            close=Decimal("1.1020"),
            volume=Decimal("0"),
        )
        assert len(engine._equity_curve) == 1

    @pytest.mark.asyncio
    async def test_on_candle_prices_preserved(self):
        engine = BacktestEngine()
        ts = datetime.now(timezone.utc)
        close_price = Decimal("1.1020")
        await engine.on_candle(
            symbol="EURUSD",
            timestamp=ts,
            open_price=Decimal("1.1000"),
            high=Decimal("1.1050"),
            low=Decimal("1.0950"),
            close=close_price,
            volume=Decimal("1000"),
        )
        assert engine._current_ask == close_price
        assert engine._current_bid == close_price - Decimal("0.0001")

    @pytest.mark.asyncio
    async def test_multiple_candles_appended(self):
        engine = BacktestEngine()
        ts = datetime.now(timezone.utc)
        for i in range(5):
            await engine.on_candle(
                symbol="EURUSD",
                timestamp=ts,
                open_price=Decimal("1.1000"),
                high=Decimal("1.1050"),
                low=Decimal("1.0950"),
                close=Decimal("1.1020") + Decimal(i) * Decimal("0.001"),
                volume=Decimal("1000"),
            )
        assert len(engine._equity_curve) == 5


class TestBacktestEngineTickHandling:
    """Test tick event handling."""

    @pytest.mark.asyncio
    async def test_on_tick_updates_state(self):
        engine = BacktestEngine()
        ts = datetime.now(timezone.utc)
        await engine.on_tick(
            symbol="EURUSD",
            timestamp=ts,
            bid=Decimal("1.0990"),
            ask=Decimal("1.1000"),
        )
        assert engine._current_bid == Decimal("1.0990")
        assert engine._current_ask == Decimal("1.1000")
        assert len(engine._equity_curve) == 1

    @pytest.mark.asyncio
    async def test_on_tick_liquidity(self):
        engine = BacktestEngine()
        ts = datetime.now(timezone.utc)
        await engine.on_tick(
            symbol="EURUSD",
            timestamp=ts,
            bid=Decimal("1.0990"),
            ask=Decimal("1.1000"),
        )
        assert engine._current_liquidity == 0.9

    @pytest.mark.asyncio
    async def test_multiple_ticks(self):
        engine = BacktestEngine()
        ts = datetime.now(timezone.utc)
        for i in range(10):
            await engine.on_tick(
                symbol="EURUSD",
                timestamp=ts,
                bid=Decimal("1.0990") + Decimal(i) * Decimal("0.0001"),
                ask=Decimal("1.1000") + Decimal(i) * Decimal("0.0001"),
            )
        assert len(engine._equity_curve) == 10


class TestBacktestEngineEventHandling:
    """Test event handling."""

    @pytest.mark.asyncio
    async def test_on_event_noop(self):
        engine = BacktestEngine()
        await engine.on_event({"type": "test", "data": "value"})
        # Should not raise and state should remain unchanged
        assert engine._equity_curve == []


class TestBacktestEngineReset:
    """Test reset functionality."""

    @pytest.mark.asyncio
    async def test_reset_clears_state(self):
        engine = BacktestEngine()
        # Add some state
        ts = datetime.now(timezone.utc)
        await engine.on_candle(
            symbol="EURUSD",
            timestamp=ts,
            open_price=Decimal("1.1000"),
            high=Decimal("1.1050"),
            low=Decimal("1.0950"),
            close=Decimal("1.1020"),
            volume=Decimal("1000"),
        )
        await engine.on_tick(
            symbol="EURUSD",
            timestamp=ts,
            bid=Decimal("1.0990"),
            ask=Decimal("1.1000"),
        )
        assert len(engine._equity_curve) == 2
        engine._trades.append({"pnl": 100})

        await engine.reset()
        assert len(engine._equity_curve) == 0
        assert len(engine._trades) == 0
        assert engine._portfolio.balance == engine._portfolio.config.initial_balance

    @pytest.mark.asyncio
    async def test_reset_multiple_times(self):
        engine = BacktestEngine()
        await engine.reset()
        await engine.reset()
        await engine.reset()
        # Should not raise errors
        assert engine._portfolio.balance == Decimal("10000")


class TestBacktestEngineRun:
    """Test backtest execution."""

    @pytest.mark.asyncio
    async def test_run_with_no_data_provider_returns_error(self):
        engine = BacktestEngine()
        result = await engine.run(symbol="EURUSD")
        assert result.success is False
        assert "ReplayError" in result.error or "Error" in result.error

    @pytest.mark.asyncio
    async def test_run_with_custom_dates(self):
        engine = BacktestEngine()
        result = await engine.run(
            symbol="EURUSD",
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
        )
        # Will fail because no data provider, but should not crash
        assert result.success is False

    @pytest.mark.asyncio
    async def test_run_returns_engine_result_type(self):
        engine = BacktestEngine()
        result = await engine.run()
        assert isinstance(result, BacktestEngineResult)

    @pytest.mark.asyncio
    async def test_run_with_strategy_func_does_not_crash(self):
        engine = BacktestEngine()

        async def strategy(data):
            return {"signal": "buy"}

        result = await engine.run(strategy_func=strategy)
        assert isinstance(result, BacktestEngineResult)


class TestBacktestEngineRunErrorScenarios:
    """Test error handling during backtest runs."""

    @pytest.mark.asyncio
    async def test_run_with_invalid_symbol_still_returns_result(self):
        engine = BacktestEngine()
        result = await engine.run(symbol="")
        assert isinstance(result, BacktestEngineResult)

    @pytest.mark.asyncio
    async def test_run_recovers_gracefully(self):
        engine = BacktestEngine()
        result = await engine.run()
        # After failure, engine should still be usable
        assert isinstance(result, BacktestEngineResult)


class TestBacktestEngineBacktestEngineResult:
    """Test the BacktestEngineResult dataclass."""

    def test_result_immutability(self):
        result = BacktestEngineResult(success=True)
        with pytest.raises(AttributeError):
            result.success = False  # type: ignore[misc]

    def test_result_with_all_fields(self):
        bt_result = BacktestResult(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            initial_balance=Decimal("10000"),
            final_balance=Decimal("11000"),
            net_profit=Decimal("1000"),
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
        )
        result = BacktestEngineResult(
            success=True,
            result=bt_result,
            execution_time_seconds=2.5,
        )
        assert result.result.total_trades == 10
        assert result.result.net_profit == Decimal("1000")
        assert result.execution_time_seconds == 2.5


class TestBacktestEngineEquityCurve:
    """Test equity curve tracking."""

    @pytest.mark.asyncio
    async def test_equity_curve_grows_with_events(self):
        engine = BacktestEngine()
        ts = datetime.now(timezone.utc)
        for i in range(100):
            await engine.on_tick(
                symbol="EURUSD",
                timestamp=ts,
                bid=Decimal("1.0990"),
                ask=Decimal("1.1000"),
            )
        assert len(engine._equity_curve) == 100

    @pytest.mark.asyncio
    async def test_equity_curve_cleared_on_reset(self):
        engine = BacktestEngine()
        ts = datetime.now(timezone.utc)
        for i in range(10):
            await engine.on_tick(
                symbol="EURUSD",
                timestamp=ts,
                bid=Decimal("1.0990"),
                ask=Decimal("1.1000"),
            )
        assert len(engine._equity_curve) == 10
        await engine.reset()
        assert len(engine._equity_curve) == 0


class TestBacktestEngineReplayIntegration:
    """Test integration with replay engine."""

    def test_replay_engine_created(self):
        engine = BacktestEngine()
        assert engine.replay is not None
        assert hasattr(engine.replay, "state")

    def test_engine_is_registered_as_handler(self):
        engine = BacktestEngine()
        # The engine should be in the replay handlers list
        assert engine in engine.replay._handlers
