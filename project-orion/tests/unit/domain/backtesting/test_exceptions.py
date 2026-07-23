"""Tests for EPIC-010 exception hierarchy."""

from __future__ import annotations

import pytest

from libraries.domain.backtesting.exceptions import (
    BacktestError,
    DataCorruptionError,
    DataFormatError,
    DataNotFoundError,
    EngineNotReadyError,
    EngineShutdownError,
    ExecutionSimulationError,
    HistoricalDataError,
    MarketSimulationError,
    OptimizationError,
    ParameterError,
    PortfolioSimulationError,
    ReplayDataError,
    ReplayError,
    ReplaySeekError,
    ReplayStateError,
    ReportingError,
    ScenarioError,
    SimulationError,
    StatisticsError,
)


class TestExceptionHierarchy:
    """Test the exception hierarchy structure."""

    def test_backtest_error_base(self):
        assert issubclass(BacktestError, Exception)
        err = BacktestError("test error")
        assert str(err) == "test error"

    def test_replay_error_hierarchy(self):
        assert issubclass(ReplayError, BacktestError)
        assert issubclass(ReplayStateError, ReplayError)
        assert issubclass(ReplayDataError, ReplayError)
        assert issubclass(ReplaySeekError, ReplayError)

    def test_historical_data_error_hierarchy(self):
        assert issubclass(HistoricalDataError, BacktestError)
        assert issubclass(DataFormatError, HistoricalDataError)
        assert issubclass(DataNotFoundError, HistoricalDataError)
        assert issubclass(DataCorruptionError, HistoricalDataError)

    def test_simulation_error_hierarchy(self):
        assert issubclass(SimulationError, BacktestError)
        assert issubclass(PortfolioSimulationError, SimulationError)
        assert issubclass(ExecutionSimulationError, SimulationError)
        assert issubclass(MarketSimulationError, SimulationError)

    def test_parameter_error_hierarchy(self):
        assert issubclass(ParameterError, BacktestError)
        assert issubclass(OptimizationError, ParameterError)
        assert issubclass(ScenarioError, ParameterError)

    def test_standalone_exceptions(self):
        assert issubclass(StatisticsError, BacktestError)
        assert issubclass(ReportingError, BacktestError)
        assert issubclass(EngineNotReadyError, BacktestError)
        assert issubclass(EngineShutdownError, BacktestError)

    def test_all_exceptions_catchable_by_base(self):
        exceptions = [
            ReplayError(),
            ReplayStateError(),
            ReplayDataError(),
            ReplaySeekError(),
            HistoricalDataError(),
            DataFormatError(),
            DataNotFoundError(),
            DataCorruptionError(),
            SimulationError(),
            PortfolioSimulationError(),
            ExecutionSimulationError(),
            MarketSimulationError(),
            ParameterError(),
            OptimizationError(),
            ScenarioError(),
            StatisticsError(),
            ReportingError(),
            EngineNotReadyError(),
            EngineShutdownError(),
        ]
        for exc in exceptions:
            assert isinstance(exc, BacktestError)
            assert isinstance(exc, Exception)

    def test_exception_message_preserved(self):
        msg = "specific error message"
        err = BacktestError(msg)
        assert str(err) == msg
        assert repr(msg) in repr(err)

    def test_replay_state_error_message(self):
        err = ReplayStateError("cannot pause")
        assert "cannot pause" in str(err)

    def test_engine_not_ready_error(self):
        err = EngineNotReadyError("engine not initialized")
        assert "engine" in str(err)

    def test_statistics_error_standalone(self):
        err = StatisticsError("calculation error")
        assert isinstance(err, BacktestError)
        assert "calculation" in str(err)

    def test_reporting_error_standalone(self):
        err = ReportingError("report generation failed")
        assert isinstance(err, BacktestError)
        assert "report" in str(err)

    def test_exception_without_message(self):
        err = BacktestError()
        assert str(err) == ""

    def test_error_raise_and_catch(self):
        with pytest.raises(BacktestError):
            raise ReplayError("replay failed")

        with pytest.raises(SimulationError):
            raise ExecutionSimulationError("execution failed")

        with pytest.raises(HistoricalDataError):
            raise DataNotFoundError("data not found")
