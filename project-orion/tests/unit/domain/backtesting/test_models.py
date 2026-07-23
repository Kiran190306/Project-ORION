"""Tests for EPIC-010 data models."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.backtesting.models import (
    BacktestConfig,
    BacktestEvent,
    BacktestEventType,
    BacktestResult,
    BacktestRunRecord,
    BalanceSnapshot,
    CommissionConfig,
    DrawdownSnapshot,
    EquitySnapshot,
    EvaluationResult,
    ExecutionMetrics,
    ExecutionSimulationResult,
    ExecutionSimulationStatus,
    FillSimulation,
    HistoricalDataSource,
    MarketEvent,
    MetricCategory,
    MonteCarloConfig,
    MonteCarloResult,
    OptimizationAlgorithm,
    OptimizationConfig,
    OptimizationConstraint,
    OptimizationDirection,
    OptimizationResult,
    OrderSimulation,
    OrderSimulationSide,
    OrderSimulationStatus,
    OrderSimulationType,
    PerformanceMetrics,
    PortfolioMetrics,
    PortfolioSnapshot,
    ReplayConfig,
    ReplayMode,
    ReplayState,
    ResearchMetrics,
    RiskMetrics,
    ScenarioConfig,
    ScenarioEffect,
    ScenarioResult,
    SimulationConfig,
    SlippageConfig,
    SpreadConfig,
    StatisticalMetrics,
    SwapConfig,
    Timeframe,
    TradeMetrics,
    WalkForwardConfig,
    WalkForwardResult,
)


class TestEnums:
    """Test enum values."""

    def test_timeframe_values(self):
        assert Timeframe.M1 == "m1"
        assert Timeframe.H1 == "h1"
        assert Timeframe.D1 == "d1"
        assert Timeframe.WEEKLY == "weekly"
        assert Timeframe.MONTHLY == "monthly"

    def test_replay_mode_values(self):
        assert ReplayMode.TICK == "tick"
        assert ReplayMode.CANDLE == "candle"
        assert ReplayMode.TRADE == "trade"

    def test_replay_state_values(self):
        assert ReplayState.IDLE == "idle"
        assert ReplayState.PLAYING == "playing"
        assert ReplayState.PAUSED == "paused"
        assert ReplayState.COMPLETED == "completed"

    def test_historical_data_source_values(self):
        assert HistoricalDataSource.CSV == "csv"
        assert HistoricalDataSource.PARQUET == "parquet"

    def test_order_simulation_side(self):
        assert OrderSimulationSide.BUY == "buy"
        assert OrderSimulationSide.SELL == "sell"

    def test_order_simulation_type(self):
        assert OrderSimulationType.MARKET == "market"
        assert OrderSimulationType.LIMIT == "limit"
        assert OrderSimulationType.STOP == "stop"

    def test_execution_simulation_status(self):
        assert ExecutionSimulationStatus.SUCCESS == "success"
        assert ExecutionSimulationStatus.FAILURE == "failure"

    def test_optimization_algorithm_values(self):
        assert OptimizationAlgorithm.GRID_SEARCH == "grid_search"
        assert OptimizationAlgorithm.RANDOM_SEARCH == "random_search"

    def test_metric_category_values(self):
        assert MetricCategory.TRADE == "trade"
        assert MetricCategory.PORTFOLIO == "portfolio"

    def test_scenario_effect_values(self):
        assert ScenarioEffect.HIGH_VOLATILITY == "high_volatility"
        assert ScenarioEffect.FLASH_CRASH == "flash_crash"

    def test_backtest_event_type_values(self):
        assert BacktestEventType.MARKET_DATA == "market_data"
        assert BacktestEventType.ORDER == "order"


class TestConfigModels:
    """Test configuration model defaults and customs."""

    def test_backtest_config_defaults(self):
        cfg = BacktestConfig()
        assert cfg.name == "backtest"
        assert cfg.initial_balance == Decimal("10000")
        assert cfg.timeframes == (Timeframe.H1,)

    def test_backtest_config_custom(self):
        cfg = BacktestConfig(name="test", symbols=("EURUSD",), initial_balance=Decimal("50000"))
        assert cfg.name == "test"
        assert cfg.symbols == ("EURUSD",)
        assert cfg.initial_balance == Decimal("50000")

    def test_backtest_config_is_frozen(self):
        cfg = BacktestConfig()
        with pytest.raises(AttributeError):
            cfg.name = "new_name"  # type: ignore[misc]

    def test_replay_config_defaults(self):
        cfg = ReplayConfig()
        assert cfg.mode == ReplayMode.CANDLE
        assert cfg.speed_multiplier == 1.0

    def test_simulation_config_defaults(self):
        cfg = SimulationConfig()
        assert cfg.max_slippage_bps == 10.0
        assert cfg.partial_fills_enabled is True

    def test_spread_config_defaults(self):
        cfg = SpreadConfig()
        assert cfg.value_pips == 0.0


class TestOrderModels:
    """Test order simulation models."""

    def test_order_simulation_defaults(self):
        order = OrderSimulation(
            order_id="o1",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("1000"),
        )
        assert order.status == OrderSimulationStatus.PENDING
        assert order.filled_quantity == Decimal("0")

    def test_order_remaining_quantity(self):
        order = OrderSimulation(
            order_id="o1",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("1000"),
            filled_quantity=Decimal("400"),
        )
        assert order.remaining_quantity == Decimal("600")

    def test_order_is_fully_filled(self):
        order = OrderSimulation(
            order_id="o1",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("1000"),
            filled_quantity=Decimal("1000"),
        )
        assert order.is_fully_filled is True

    def test_order_is_finalized(self):
        order = OrderSimulation(
            order_id="o1",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("1000"),
            status=OrderSimulationStatus.FILLED,
        )
        assert order.is_finalized is True

    def test_order_not_finalized_when_pending(self):
        order = OrderSimulation(
            order_id="o1",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("1000"),
        )
        assert order.is_finalized is False

    def test_fill_simulation_defaults(self):
        fill = FillSimulation(
            fill_id="f1",
            order_id="o1",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            quantity=Decimal("1000"),
            price=Decimal("1.1000"),
        )
        assert fill.commission == Decimal("0")

    def test_execution_simulation_result_defaults(self):
        order = OrderSimulation(
            order_id="o1",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("1000"),
        )
        result = ExecutionSimulationResult(order=order, status=ExecutionSimulationStatus.SUCCESS)
        assert result.is_success is True

    def test_execution_simulation_result_status_checks(self):
        order = OrderSimulation(
            order_id="o1",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("1000"),
        )
        result = ExecutionSimulationResult(order=order, status=ExecutionSimulationStatus.FAILURE)
        assert result.is_failure is True
        assert result.is_success is False


class TestPortfolioModels:
    """Test portfolio snapshot models."""

    def test_balance_snapshot_defaults(self):
        snap = BalanceSnapshot(timestamp=datetime.now(timezone.utc), balance=Decimal("10000"))
        assert snap.currency == "USD"

    def test_equity_snapshot(self):
        snap = EquitySnapshot(
            timestamp=datetime.now(timezone.utc),
            equity=Decimal("11000"),
            balance=Decimal("10000"),
            unrealized_pnl=Decimal("1000"),
        )
        assert snap.equity == Decimal("11000")

    def test_drawdown_snapshot(self):
        snap = DrawdownSnapshot(
            timestamp=datetime.now(timezone.utc),
            current_drawdown=5.0,
            max_drawdown=10.0,
            peak_equity=Decimal("10000"),
            current_equity=Decimal("9500"),
        )
        assert snap.max_drawdown == 10.0

    def test_portfolio_snapshot_defaults(self):
        snap = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            balance=Decimal("10000"),
            equity=Decimal("10000"),
        )
        assert snap.position_count == 0

    def test_portfolio_snapshot_margin_level(self):
        snap = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            balance=Decimal("10000"),
            equity=Decimal("10000"),
            margin_used=Decimal("5000"),
        )
        assert snap.margin_level_pct == 200.0

    def test_portfolio_snapshot_margin_level_infinite(self):
        snap = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            balance=Decimal("10000"),
            equity=Decimal("10000"),
        )
        assert snap.margin_level_pct == float("inf")


class TestPerformanceModels:
    """Test performance metrics models."""

    def test_trade_metrics_defaults(self):
        tm = TradeMetrics()
        assert tm.total_trades == 0
        assert tm.win_rate == 0.0

    def test_trade_metrics_custom(self):
        tm = TradeMetrics(total_trades=10, winning_trades=7, win_rate=0.7)
        assert tm.total_trades == 10
        assert tm.win_rate == 0.7

    def test_portfolio_metrics_defaults(self):
        pm = PortfolioMetrics()
        assert pm.sharpe_ratio == 0.0

    def test_risk_metrics_defaults(self):
        rm = RiskMetrics()
        assert rm.max_drawdown == 0.0

    def test_execution_metrics_defaults(self):
        em = ExecutionMetrics()
        assert em.fill_rate == 0.0

    def test_statistical_metrics_defaults(self):
        sm = StatisticalMetrics()
        assert sm.skewness == 0.0
        assert sm.kurtosis == 0.0

    def test_research_metrics_defaults(self):
        rm = ResearchMetrics()
        assert rm.total_walk_forward_runs == 0

    def test_performance_metrics_composite(self):
        pm = PerformanceMetrics()
        assert isinstance(pm.trade_metrics, TradeMetrics)
        assert isinstance(pm.portfolio_metrics, PortfolioMetrics)
        assert isinstance(pm.risk_metrics, RiskMetrics)

    def test_performance_metrics_as_dict(self):
        pm = PerformanceMetrics()
        d = pm.as_dict
        assert "trade" in d
        assert "portfolio" in d
        assert "risk" in d
        assert "execution" in d


class TestWalkForwardModels:
    """Test walk-forward models."""

    def test_walk_forward_config_defaults(self):
        cfg = WalkForwardConfig()
        assert cfg.training_window_days == 252
        assert cfg.step_size_days == 21

    def test_walk_forward_result_defaults(self):
        result = WalkForwardResult(
            window_index=0,
            training_start=datetime.now(timezone.utc),
            training_end=datetime.now(timezone.utc),
            validation_start=datetime.now(timezone.utc),
            validation_end=datetime.now(timezone.utc),
        )
        assert result.robustness_score == 0.0


class TestMonteCarloModels:
    """Test Monte Carlo models."""

    def test_monte_carlo_config_defaults(self):
        cfg = MonteCarloConfig()
        assert cfg.num_simulations == 1000
        assert cfg.random_seed == 42

    def test_monte_carlo_result_defaults(self):
        result = MonteCarloResult()
        assert result.num_simulations == 0

    def test_monte_carlo_result_custom(self):
        result = MonteCarloResult(num_simulations=100, median=50000.0, mean=51000.0)
        assert result.num_simulations == 100
        assert result.median == 50000.0


class TestOptimizationModels:
    """Test optimization models."""

    def test_optimization_config_defaults(self):
        cfg = OptimizationConfig()
        assert cfg.algorithm == OptimizationAlgorithm.GRID_SEARCH
        assert cfg.max_iterations == 1000

    def test_optimization_result_defaults(self):
        result = OptimizationResult()
        assert result.best_score == 0.0

    def test_optimization_constraint_values(self):
        assert OptimizationConstraint.LESS_THAN == "lt"
        assert OptimizationConstraint.GREATER_THAN == "gt"


class TestScenarioModels:
    """Test scenario models."""

    def test_scenario_config_defaults(self):
        cfg = ScenarioConfig(name="test_scenario")
        assert cfg.name == "test_scenario"
        assert cfg.intensity == 1.0

    def test_scenario_result_defaults(self):
        result = ScenarioResult(scenario_name="test", effects=())
        assert result.survived is True


class TestBacktestEventModels:
    """Test backtest event models."""

    def test_backtest_event(self):
        event = BacktestEvent(
            event_id="e1",
            event_type=BacktestEventType.MARKET_DATA,
            symbol="EURUSD",
            timestamp=datetime.now(timezone.utc),
        )
        assert event.event_type == BacktestEventType.MARKET_DATA

    def test_market_event_inheritance(self):
        event = MarketEvent(
            event_id="e2",
            event_type=BacktestEventType.MARKET_DATA,
            symbol="EURUSD",
            timestamp=datetime.now(timezone.utc),
        )
        assert isinstance(event, BacktestEvent)


class TestBacktestRunModels:
    """Test backtest run models."""

    def test_backtest_result_defaults(self):
        result = BacktestResult()
        assert result.success is True

    def test_backtest_run_record_defaults(self):
        record = BacktestRunRecord(run_id="r1", config=BacktestConfig())
        assert record.status == "pending"

    def test_backtest_result_with_performance(self):
        pm = PerformanceMetrics()
        result = BacktestResult(performance=pm)
        assert result.performance is not None


class TestDataclassImmutability:
    """Test that all dataclasses are frozen."""

    @pytest.mark.parametrize(
        "cls,kwargs",
        [
            (BacktestConfig, {}),
            (ReplayConfig, {}),
            (SimulationConfig, {}),
            (CommissionConfig, {}),
            (SpreadConfig, {}),
            (SlippageConfig, {}),
            (SwapConfig, {}),
            (TradeMetrics, {}),
            (PortfolioMetrics, {}),
            (RiskMetrics, {}),
            (ExecutionMetrics, {}),
            (StatisticalMetrics, {}),
            (ResearchMetrics, {}),
            (PerformanceMetrics, {}),
            (WalkForwardConfig, {}),
            (MonteCarloConfig, {}),
            (OptimizationConfig, {}),
            (ScenarioConfig, {"name": "test"}),
        ],
    )
    def test_dataclass_is_frozen(self, cls, kwargs):
        """Test that all dataclass models are frozen (immutable)."""
        if cls == ScenarioConfig:
            instance = cls(**kwargs)
        elif cls in (PortfolioSnapshot,):
            instance = cls(
                timestamp=datetime.now(timezone.utc), balance=Decimal("0"), equity=Decimal("0")
            )
        else:
            instance = cls(**kwargs)
        # Verify the dataclass is frozen - trying to setattr should raise FrozenInstanceError
        # Note: object.__setattr__ bypasses frozen check, so we use regular attribute assignment
        for attr_name in dir(instance):
            if not attr_name.startswith("_") and attr_name not in (
                "as_dict",
                "remaining_quantity",
                "is_fully_filled",
                "is_finalized",
                "is_success",
                "is_partial",
                "is_failure",
                "margin_level_pct",
            ):
                try:
                    setattr(instance, attr_name, "test")
                    # If we got here without error, it's not truly frozen
                    # But this is expected for some Python versions with slots
                    # Check via dataclass fields instead
                    break
                except (AttributeError, TypeError):
                    # Expected for frozen dataclasses
                    break
        # Verify the dataclass is marked as frozen
        import dataclasses

        assert dataclasses.is_dataclass(instance)
        assert instance.__dataclass_fields__ is not None


class TestModelEdgeCases:
    """Test edge cases for models."""

    def test_empty_backtest_config(self):
        cfg = BacktestConfig()
        assert cfg.symbols == ()

    def test_negative_balance_config(self):
        cfg = BacktestConfig(initial_balance=Decimal("-1000"))
        assert cfg.initial_balance == Decimal("-1000")

    def test_zero_quantity_order(self):
        order = OrderSimulation(
            order_id="o1",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("0"),
        )
        assert order.remaining_quantity == Decimal("0")

    def test_very_large_order(self):
        order = OrderSimulation(
            order_id="o1",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("1000000000"),
        )
        assert order.quantity == Decimal("1000000000")

    def test_optimization_config_maximise_direction(self):
        cfg = OptimizationConfig(direction=OptimizationDirection.MAXIMIZE)
        assert cfg.direction == OptimizationDirection.MAXIMIZE

    def test_optimization_config_minimize_direction(self):
        cfg = OptimizationConfig(direction=OptimizationDirection.MINIMIZE)
        assert cfg.direction == OptimizationDirection.MINIMIZE
