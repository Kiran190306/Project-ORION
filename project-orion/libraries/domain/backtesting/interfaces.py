"""Protocol/port definitions for the Institutional Backtesting & Quantitative Research Laboratory.

Defines all protocol ports that the backtesting domain depends on.
Every external dependency is injected through these ports.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Protocol, runtime_checkable

from libraries.domain.backtesting.models import (
    BacktestConfig,
    BacktestEvent,
    BacktestEventType,
    BacktestRunRecord,
    ExecutionSimulationResult,
    MarketEvent,
    OrderSimulation,
    PerformanceMetrics,
    PortfolioSnapshot,
    ScenarioConfig,
    ScenarioResult,
)

# ─── Historical Data Provider ─────────────────────────────────────────────


@runtime_checkable
class HistoricalDataProviderPort(Protocol):
    """Port for accessing historical market data.

    Implementations can read from CSV, Parquet, DuckDB, PostgreSQL,
    compressed files, S3, or any other data source.
    """

    async def load_data(
        self,
        symbol: str,
        timeframe: str,
        start: Any,
        end: Any,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Load historical data as an async iterator of dicts.

        Args:
            symbol: Instrument symbol (e.g., EUR/USD).
            timeframe: Timeframe string (e.g., h1, d1).
            start: Start datetime.
            end: End datetime.

        Yields:
            Dict with keys like timestamp, open, high, low, close, volume.
        """
        ...  # pragma: no cover
        if False:  # pragma: no cover
            yield {}  # pragma: no cover

    async def validate_data(self, symbol: str, timeframe: str) -> bool:
        """Check if data is available and valid for the given parameters.

        Args:
            symbol: Instrument symbol.
            timeframe: Timeframe string.

        Returns:
            True if valid data is available.
        """
        ...

    async def get_available_symbols(self) -> list[str]:
        """Return list of symbols with available data."""
        ...

    async def get_available_timeframes(self, symbol: str) -> list[str]:
        """Return list of timeframes available for a symbol."""
        ...

    async def get_date_range(self, symbol: str, timeframe: str) -> tuple[Any, Any]:
        """Return (start_date, end_date) for available data."""
        ...


# ─── Replay Controller ────────────────────────────────────────────────────


@runtime_checkable
class ReplayControllerPort(Protocol):
    """Port for controlling the replay engine.

    Supports play, pause, resume, seek, reverse, and speed control.
    """

    async def play(self) -> None:
        """Start or resume replay."""
        ...

    async def pause(self) -> None:
        """Pause replay."""
        ...

    async def stop(self) -> None:
        """Stop replay and reset."""
        ...

    async def seek(self, timestamp: Any) -> bool:
        """Seek to a specific timestamp.

        Args:
            timestamp: Target timestamp.

        Returns:
            True if seek was successful.
        """
        ...

    async def set_speed(self, multiplier: float) -> None:
        """Set replay speed multiplier.

        Args:
            multiplier: Speed multiplier (1.0 = real-time).
        """
        ...

    async def get_state(self) -> str:
        """Return current replay state."""
        ...

    async def get_progress(self) -> float:
        """Return replay progress as 0.0–1.0."""
        ...


# ─── Portfolio Simulator ──────────────────────────────────────────────────


@runtime_checkable
class PortfolioSimulatorPort(Protocol):
    """Port for simulating portfolio state during backtesting.

    Tracks balance, equity, margin, exposure, PnL, drawdown.
    Supports incremental updates (no full recalc after every candle).
    """

    async def apply_fill(
        self,
        symbol: str,
        side: str,
        quantity: Any,
        price: Any,
        commission: Any,
        swap: Any,
        timestamp: Any,
    ) -> PortfolioSnapshot:
        """Apply a fill to the portfolio.

        Args:
            symbol: Instrument symbol.
            side: buy or sell.
            quantity: Fill quantity.
            price: Fill price.
            commission: Commission charged.
            swap: Swap charged.
            timestamp: Fill timestamp.

        Returns:
            Updated portfolio snapshot.
        """
        ...

    async def apply_price_update(
        self, symbol: str, price: Any, timestamp: Any
    ) -> PortfolioSnapshot:
        """Update unrealized PnL with new market price.

        Args:
            symbol: Instrument symbol.
            price: Current market price.
            timestamp: Update timestamp.

        Returns:
            Updated portfolio snapshot.
        """
        ...

    async def get_snapshot(self) -> PortfolioSnapshot:
        """Return current portfolio snapshot."""
        ...

    async def reset(self, initial_balance: Any) -> None:
        """Reset portfolio to initial state.

        Args:
            initial_balance: Starting account balance.
        """
        ...

    async def get_equity_curve(self) -> list[tuple[Any, float]]:
        """Return the full equity curve as (timestamp, equity) pairs.

        Supports incremental calculation — does not recalc from scratch.
        """
        ...

    async def get_drawdown_curve(self) -> list[tuple[Any, float]]:
        """Return the drawdown curve as (timestamp, drawdown_pct) pairs."""
        ...


# ─── Execution Simulator ──────────────────────────────────────────────────


@runtime_checkable
class ExecutionSimulatorPort(Protocol):
    """Port for simulating order execution during backtesting.

    Reuses the same execution interfaces used by live trading.
    The only difference is the execution adapter (simulation vs. live).
    This guarantees identical behaviour between backtest, paper, and live trading.
    """

    async def execute_market(
        self,
        symbol: str,
        side: str,
        quantity: Any,
        timestamp: Any,
        **kwargs: Any,
    ) -> ExecutionSimulationResult:
        """Execute a market order simulation.

        Args:
            symbol: Instrument symbol.
            side: buy or sell.
            quantity: Order quantity.
            timestamp: Execution timestamp.

        Returns:
            Execution simulation result.
        """
        ...

    async def execute_limit(
        self,
        symbol: str,
        side: str,
        quantity: Any,
        price: Any,
        timestamp: Any,
        **kwargs: Any,
    ) -> ExecutionSimulationResult:
        """Execute a limit order simulation."""
        ...

    async def execute_stop(
        self,
        symbol: str,
        side: str,
        quantity: Any,
        stop_price: Any,
        timestamp: Any,
        **kwargs: Any,
    ) -> ExecutionSimulationResult:
        """Execute a stop order simulation."""
        ...

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending simulated order.

        Args:
            order_id: ID of the order to cancel.

        Returns:
            True if cancellation was successful.
        """
        ...

    async def get_open_orders(self) -> list[OrderSimulation]:
        """Return all open (pending/partial) orders."""
        ...

    async def check_pending_orders(
        self,
        symbol: str,
        bid: Any,
        ask: Any,
        timestamp: Any,
    ) -> list[ExecutionSimulationResult]:
        """Check and fill pending limit/stop orders against current prices.

        Args:
            symbol: Instrument symbol.
            bid: Current bid price.
            ask: Current ask price.
            timestamp: Current timestamp.

        Returns:
            List of execution results for orders that were filled.
        """
        ...


# ─── Market Simulator ─────────────────────────────────────────────────────


@runtime_checkable
class MarketSimulatorPort(Protocol):
    """Port for simulating market conditions during backtesting.

    Applies slippage, spread, liquidity constraints, and market impact.
    All randomness uses configurable seeds for deterministic execution.
    """

    async def apply_slippage(
        self,
        symbol: str,
        price: Any,
        quantity: Any,
        side: str,
        timestamp: Any,
    ) -> tuple[Any, float]:
        """Apply slippage to an execution price.

        Args:
            symbol: Instrument symbol.
            price: Base execution price.
            quantity: Order quantity.
            side: buy or sell.
            timestamp: Execution timestamp.

        Returns:
            (executed_price, slippage_bps).
        """
        ...

    async def apply_spread(
        self,
        symbol: str,
        bid: Any,
        ask: Any,
        timestamp: Any,
    ) -> tuple[Any, Any]:
        """Apply spread model to bid/ask prices.

        Args:
            symbol: Instrument symbol.
            bid: Input bid price.
            ask: Input ask price.
            timestamp: Current timestamp.

        Returns:
            (adjusted_bid, adjusted_ask).
        """
        ...

    async def check_liquidity(
        self,
        symbol: str,
        quantity: Any,
        side: str,
        timestamp: Any,
    ) -> tuple[bool, Any]:
        """Check if sufficient liquidity exists for an order.

        Args:
            symbol: Instrument symbol.
            quantity: Order quantity.
            side: buy or sell.
            timestamp: Current timestamp.

        Returns:
            (has_liquidity, max_executable_quantity).
        """
        ...

    async def calculate_market_impact(
        self,
        symbol: str,
        quantity: Any,
        side: str,
        timestamp: Any,
    ) -> float:
        """Calculate expected market impact in bps.

        Args:
            symbol: Instrument symbol.
            quantity: Order quantity.
            side: buy or sell.
            timestamp: Current timestamp.

        Returns:
            Estimated market impact in bps.
        """
        ...

    async def apply_commission(
        self,
        symbol: str,
        quantity: Any,
        price: Any,
        timestamp: Any,
    ) -> Any:
        """Calculate commission for an execution.

        Args:
            symbol: Instrument symbol.
            quantity: Filled quantity.
            price: Fill price.
            timestamp: Fill timestamp.

        Returns:
            Commission amount.
        """
        ...

    async def apply_swap(
        self,
        symbol: str,
        quantity: Any,
        side: str,
        timestamp: Any,
    ) -> Any:
        """Calculate swap/overnight charge.

        Args:
            symbol: Instrument symbol.
            quantity: Position quantity.
            side: Position side.
            timestamp: Current timestamp.

        Returns:
            Swap amount.
        """
        ...

    async def get_latency_ms(self, timestamp: Any) -> float:
        """Get simulated broker latency in milliseconds.

        Uses configurable random seed for deterministic delay simulation.
        """
        ...


# ─── Performance Calculator ───────────────────────────────────────────────


@runtime_checkable
class PerformanceCalculatorPort(Protocol):
    """Port for calculating performance metrics.

    Supports incremental calculations for millions of ticks.
    """

    async def calculate(self, from_snapshot: PortfolioSnapshot | None = None) -> PerformanceMetrics:
        """Calculate complete performance metrics.

        Args:
            from_snapshot: Optional portfolio snapshot to include.

        Returns:
            Complete PerformanceMetrics.
        """
        ...

    async def record_trade(self, pnl: float, is_win: bool, is_loss: bool) -> None:
        """Record a trade outcome for metrics calculation.

        Args:
            pnl: Profit/loss amount.
            is_win: True if winning trade.
            is_loss: True if losing trade.
        """
        ...

    async def record_equity(self, equity: float, timestamp: Any) -> None:
        """Record an equity value for drawdown and curve calculations.

        Args:
            equity: Account equity value.
            timestamp: Equity timestamp.
        """
        ...

    async def get_sharpe_ratio(self) -> float:
        """Return current Sharpe ratio."""
        ...

    async def get_sortino_ratio(self) -> float:
        """Return current Sortino ratio."""
        ...

    async def get_max_drawdown(self) -> float:
        """Return maximum drawdown observed."""
        ...

    async def reset(self) -> None:
        """Reset all calculations."""
        ...


# ─── Reporting ────────────────────────────────────────────────────────────


@runtime_checkable
class ReportingPort(Protocol):
    """Port for generating backtest reports.

    Supports JSON, CSV, HTML, Markdown, and PDF (future).
    Reports are generated independently of simulation.
    """

    async def generate_json(
        self,
        metrics: PerformanceMetrics,
        config: Any,
        trades: list[Any],
        output_path: str = "",
    ) -> str:
        """Generate a JSON report.

        Args:
            metrics: Performance metrics to include.
            config: Backtest configuration.
            trades: List of simulated trades.
            output_path: Optional output file path.

        Returns:
            Path to the generated report.
        """
        ...

    async def generate_csv(
        self,
        trades: list[Any],
        equity_curve: list[Any],
        output_path: str = "",
    ) -> str:
        """Generate a CSV report with trade list and equity curve.

        Args:
            trades: List of simulated trades.
            equity_curve: Equity curve data points.
            output_path: Optional output file path.

        Returns:
            Path to the generated report.
        """
        ...

    async def generate_html(
        self,
        metrics: PerformanceMetrics,
        config: Any,
        trades: list[Any],
        output_path: str = "",
    ) -> str:
        """Generate an HTML report with charts and tables.

        Args:
            metrics: Performance metrics.
            config: Backtest configuration.
            trades: List of simulated trades.
            output_path: Optional output file path.

        Returns:
            Path to the generated report.
        """
        ...

    async def generate_markdown(
        self,
        metrics: PerformanceMetrics,
        config: Any,
        output_path: str = "",
    ) -> str:
        """Generate a Markdown report.

        Args:
            metrics: Performance metrics.
            config: Backtest configuration.
            output_path: Optional output file path.

        Returns:
            Path to the generated report.
        """
        ...


# ─── Scenario Provider ────────────────────────────────────────────────────


@runtime_checkable
class ScenarioProviderPort(Protocol):
    """Port for providing scenario configurations.

    Scenarios can be chained: e.g., High Volatility + Spread Spike + Broker Delay.
    """

    async def load_scenario(self, name: str) -> ScenarioConfig:
        """Load a scenario configuration by name.

        Args:
            name: Scenario name.

        Returns:
            ScenarioConfig with effects and parameters.
        """
        ...

    async def apply_scenario(
        self,
        market_simulator: MarketSimulatorPort,
        scenario: ScenarioConfig,
        current_bid: Any,
        current_ask: Any,
        bar_index: int,
        timestamp: Any,
    ) -> None:
        """Apply scenario effects to the market simulator.

        Args:
            market_simulator: The active market simulator.
            scenario: The scenario configuration.
            current_bid: Current market bid.
            current_ask: Current market ask.
            bar_index: Current bar index.
            timestamp: Current timestamp.
        """
        ...

    async def evaluate_scenario(
        self,
        scenario: ScenarioConfig,
        normal_metrics: PerformanceMetrics,
        scenario_metrics: PerformanceMetrics,
    ) -> ScenarioResult:
        """Evaluate the impact of a scenario.

        Args:
            scenario: The scenario that was applied.
            normal_metrics: Performance without scenario.
            scenario_metrics: Performance with scenario.

        Returns:
            ScenarioResult with impact analysis.
        """
        ...


# ─── Walk Forward Analysis ────────────────────────────────────────────────


@runtime_checkable
class WalkForwardPort(Protocol):
    """Port for walk-forward analysis.

    Supports training window, validation window, rolling/anchored windows.
    """

    async def generate_windows(
        self,
        start: Any,
        end: Any,
        training_days: int,
        validation_days: int,
        step_days: int,
        window_type: str,
    ) -> list[tuple[Any, Any, Any, Any]]:
        """Generate walk-forward window definitions.

        Returns:
            List of (training_start, training_end, validation_start, validation_end) tuples.
        """
        ...

    async def calculate_robustness(
        self,
        in_sample_scores: list[float],
        out_of_sample_scores: list[float],
    ) -> float:
        """Calculate walk-forward robustness score.

        Args:
            in_sample_scores: List of in-sample performance scores.
            out_of_sample_scores: List of out-of-sample performance scores.

        Returns:
            Robustness score (0.0–1.0).
        """
        ...


# ─── Backtest Event Publisher ─────────────────────────────────────────────


@runtime_checkable
class BacktestEventPublisher(Protocol):
    """Port for publishing backtest events.

    The engine is fully event-driven. Components publish events through
    this port, and consumers subscribe to specific event types.
    """

    async def publish(self, event: BacktestEvent) -> None:
        """Publish an event to all subscribers.

        Args:
            event: The event to publish.
        """
        ...

    async def subscribe(
        self,
        event_type: BacktestEventType,
        handler: "BacktestEventHandler",
    ) -> None:
        """Subscribe a handler to a specific event type.

        Args:
            event_type: Type of event to subscribe to.
            handler: Handler to call when event is published.
        """
        ...

    async def unsubscribe(
        self,
        event_type: BacktestEventType,
        handler: "BacktestEventHandler",
    ) -> None:
        """Unsubscribe a handler from an event type.

        Args:
            event_type: Event type to unsubscribe from.
            handler: Handler to remove.
        """
        ...


@runtime_checkable
class BacktestEventHandler(Protocol):
    """Protocol for handling backtest events."""

    async def handle_event(self, event: BacktestEvent) -> None:
        """Handle a backtest event.

        Args:
            event: The event to handle.
        """
        ...


# ─── Randomizer Port ──────────────────────────────────────────────────────


@runtime_checkable
class RandomizerPort(Protocol):
    """Port for deterministic random number generation.

    Supports configurable seeds for reproducible results.
    """

    @property
    def seed(self) -> int | None:
        """Return current random seed."""
        ...

    def set_seed(self, seed: int | None) -> None:
        """Set the random seed for reproducibility.

        Args:
            seed: Random seed. None for non-deterministic.
        """
        ...

    def random(self) -> float:
        """Return a random float in [0.0, 1.0).

        Same seed always produces the same sequence.
        """
        ...

    def uniform(self, low: float, high: float) -> float:
        """Return a random float in [low, high).

        Args:
            low: Lower bound.
            high: Upper bound.
        """
        ...

    def gauss(self, mu: float, sigma: float) -> float:
        """Return a Gaussian random number.

        Args:
            mu: Mean.
            sigma: Standard deviation.
        """
        ...

    def randint(self, low: int, high: int) -> int:
        """Return a random integer in [low, high].

        Args:
            low: Lower bound (inclusive).
            high: Upper bound (inclusive).
        """
        ...

    def get_state(self) -> Any:
        """Return current randomizer state for checkpointing.

        Returns:
            Opaque state object that can be passed to set_state().
        """
        ...

    def set_state(self, state: Any) -> None:
        """Restore randomizer state from a checkpoint.

        Args:
            state: State previously returned by get_state().
        """
        ...


# ─── Optimization Hook ────────────────────────────────────────────────────


@runtime_checkable
class OptimizationHook(Protocol):
    """Hook for extending the parameter optimizer.

    Implementations can provide:
    - Bayesian optimization (external library)
    - Genetic algorithms (external library)
    - Particle swarm optimization
    - Reinforcement learning-based optimization
    """

    async def suggest_parameters(
        self,
        param_space: dict[str, list[Any]],
        previous_results: list[tuple[dict[str, Any], float]],
    ) -> dict[str, Any]:
        """Suggest the next set of parameters to evaluate.

        Args:
            param_space: The parameter search space.
            previous_results: List of (params, score) from previous evaluations.

        Returns:
            Suggested parameter set.
        """
        ...

    async def on_optimization_complete(
        self,
        best_params: dict[str, Any],
        best_score: float,
        all_results: list[tuple[dict[str, Any], float]],
    ) -> None:
        """Called when optimization completes.

        Args:
            best_params: Best found parameters.
            best_score: Best score achieved.
            all_results: All (params, score) pairs evaluated.
        """
        ...


# ─── Backtest Repository ──────────────────────────────────────────────────


@runtime_checkable
class BacktestRepositoryPort(Protocol):
    """Port for persisting backtest runs, parameters, metrics, and trades.

    Designed for the Research Database.
    Supports future comparison dashboard.
    """

    async def save_run(self, run: BacktestRunRecord) -> str:
        """Save a backtest run record.

        Args:
            run: The run record to save.

        Returns:
            Run ID.
        """
        ...

    async def load_run(self, run_id: str) -> BacktestRunRecord | None:
        """Load a backtest run record by ID.

        Args:
            run_id: ID of the run to load.

        Returns:
            The run record, or None if not found.
        """
        ...

    async def list_runs(
        self,
        symbol: str | None = None,
        strategy: str | None = None,
        limit: int = 100,
    ) -> list[BacktestRunRecord]:
        """List backtest runs with optional filters.

        Args:
            symbol: Optional symbol filter.
            strategy: Optional strategy name filter.
            limit: Maximum number of runs to return.

        Returns:
            List of matching run records.
        """
        ...

    async def delete_run(self, run_id: str) -> bool:
        """Delete a backtest run record.

        Args:
            run_id: ID of the run to delete.

        Returns:
            True if deletion was successful.
        """
        ...
