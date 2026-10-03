"""Exception hierarchy for the Institutional Backtesting & Quantitative Research Laboratory.

All exceptions raised by the backtesting domain library inherit from BacktestError,
enabling clean catch-and-handle patterns without exposing internals.
"""

from __future__ import annotations

from typing import Any


class BacktestError(Exception):
    """Base exception for all backtesting errors."""


# ─── Replay Errors ────────────────────────────────────────────────────────


class ReplayError(BacktestError):
    """Raised when the replay engine encounters an error."""


class ReplayStateError(ReplayError):
    """Raised when a replay operation is invalid for the current state."""


class ReplayDataError(ReplayError):
    """Raised when replay data is missing or malformed."""


class ReplaySeekError(ReplayError):
    """Raised when a seek operation fails."""


# ─── Historical Data Errors ───────────────────────────────────────────────


class HistoricalDataError(BacktestError):
    """Raised when historical data operations fail."""


class HistoricalDataUnavailableError(HistoricalDataError):
    """Raised when external historical data is requested but unavailable.

    Guarantees that backtests fail explicitly without silent fallback to synthetic data.
    """

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        start: Any,
        end: Any,
        provider: str | None = None,
        reason: str | None = None,
        status_code: int | None = None,
        cause: Exception | None = None,
    ) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.start = start
        self.end = end
        self.provider = provider
        self.reason = reason
        self.status_code = status_code
        self.cause = cause

        msg = (
            f"Historical data unavailable for symbol='{symbol}', timeframe='{timeframe}', "
            f"range=[{start} -> {end}] from provider='{provider or 'external'}': {reason or 'no data returned'}. "
            f"Silent fallback to synthetic data is prohibited."
        )
        super().__init__(msg)


class DataFormatError(HistoricalDataError):
    """Raised when data format is unsupported or malformed."""


class DataNotFoundError(HistoricalDataError):
    """Raised when requested data is not found."""


class DataCorruptionError(HistoricalDataError):
    """Raised when data integrity checks fail."""


# ─── Simulation Errors ────────────────────────────────────────────────────


class SimulationError(BacktestError):
    """Raised when simulation encounters an error."""


class PortfolioSimulationError(SimulationError):
    """Raised during portfolio simulation failures."""


class ExecutionSimulationError(SimulationError):
    """Raised during execution simulation failures."""


class MarketSimulationError(SimulationError):
    """Raised when market simulation encounters an error."""


# ─── Parameter & Optimization Errors ──────────────────────────────────────


class ParameterError(BacktestError):
    """Raised when parameter operations fail."""


class OptimizationError(ParameterError):
    """Raised when parameter optimization fails."""


class ScenarioError(ParameterError):
    """Raised when scenario operations fail."""


# ─── Statistics & Reporting Errors ────────────────────────────────────────


class StatisticsError(BacktestError):
    """Raised when statistics calculation encounters an error."""


class ReportingError(BacktestError):
    """Raised when report generation fails."""


# ─── Engine Errors ────────────────────────────────────────────────────────


class EngineNotReadyError(BacktestError):
    """Raised when the engine is invoked before being fully initialized."""


class EngineShutdownError(BacktestError):
    """Raised when the engine is used after shutdown."""


# ─── Randomizer State (for deterministic replay) ──────────────────────────


class RandomizerState(BacktestError):
    """Raised when randomizer state operations fail."""
