"""Backtesting engine — main orchestrator for EPIC-010.

Coordinates the full backtesting pipeline:
1. Historical data loading
2. Replay (tick/candle/order/trade/market)
3. Execution simulation (with slippage, spread, commission, etc.)
4. Portfolio simulation (balance, equity, margin, PnL, drawdown)
5. Performance calculation
6. Reporting
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Callable

from libraries.domain.backtesting.execution_simulator import (
    ExecutionSimulationConfig,
    ExecutionSimulator,
)
from libraries.domain.backtesting.historical_data import HistoricalDataProvider
from libraries.domain.backtesting.models import (
    BacktestConfig,
    BacktestResult,
    ReplayMode,
    Timeframe,
)
from libraries.domain.backtesting.performance import PerformanceEngine
from libraries.domain.backtesting.portfolio_simulator import (
    PortfolioSimulationConfig,
    PortfolioSimulator,
)
from libraries.domain.backtesting.replay_engine import (
    ReplayEngine,
    ReplayEngineConfig,
    ReplayEventHandler,
)
from libraries.domain.backtesting.reporting import ReportManager
from libraries.domain.backtesting.statistics import (
    ExecutionStatistics,
    PortfolioStatistics,
    TradeStatistics,
)


@dataclass(frozen=True, slots=True)
class BacktestEngineResult:
    """Result produced by the backtest engine."""

    success: bool
    result: BacktestResult | None = None
    error: str = ""
    execution_time_seconds: float = 0.0


class BacktestEngine(ReplayEventHandler):
    """Main orchestrator for backtesting.

    Coordinates data loading, replay, execution simulation,
    portfolio tracking, performance calculation, and reporting.
    """

    def __init__(
        self,
        config: BacktestConfig | None = None,
        data_provider: HistoricalDataProvider | None = None,
        execution_config: ExecutionSimulationConfig | None = None,
        portfolio_config: PortfolioSimulationConfig | None = None,
    ) -> None:
        """Initialize backtest engine.

        Args:
            config: Backtest configuration.
            data_provider: Historical data provider.
            execution_config: Execution simulation configuration.
            portfolio_config: Portfolio simulation configuration.
        """
        cfg = config or BacktestConfig()
        self._config = cfg

        first_symbol = cfg.symbols[0] if cfg.symbols else "EURUSD"
        first_tf = cfg.timeframes[0] if cfg.timeframes else Timeframe.H1
        self._replay = ReplayEngine(
            ReplayEngineConfig(
                replay_mode=ReplayMode.CANDLE,
                timeframe=first_tf,
                speed_multiplier=1.0,
                symbols=(first_symbol,),
            ),
            data_provider,
        )
        self._replay.add_handler(self)

        self._execution = ExecutionSimulator(execution_config)
        self._portfolio = PortfolioSimulator(portfolio_config)

        self._performance = PerformanceEngine()
        self._reporting = ReportManager()

        self._trade_stats = TradeStatistics()
        self._execution_stats = ExecutionStatistics()
        self._portfolio_stats = PortfolioStatistics()

        self._trades: list[dict[str, Any]] = []
        self._equity_curve: list[float] = []
        self._current_bid: Decimal = Decimal("0")
        self._current_ask: Decimal = Decimal("0")
        self._current_volatility: float = 0.0
        self._current_liquidity: float = 0.8

    @property
    def config(self) -> BacktestConfig:
        return self._config

    @property
    def portfolio(self) -> PortfolioSimulator:
        return self._portfolio

    @property
    def replay(self) -> ReplayEngine:
        return self._replay

    @property
    def execution(self) -> ExecutionSimulator:
        return self._execution

    async def run(
        self,
        symbol: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        strategy_func: Callable[[dict[str, Any]], Any] | None = None,
    ) -> BacktestEngineResult:
        """Run a backtest.

        Args:
            symbol: Trading symbol (overrides config).
            start_date: Start date (overrides config).
            end_date: End date (overrides config).
            strategy_func: Optional strategy callback.

        Returns:
            Backtest engine result.
        """
        import time

        start = time.time()

        try:
            # Resolve symbol from args or config
            sym = symbol
            if not sym:
                sym = self._config.symbols[0] if self._config.symbols else "EURUSD"

            # Resolve start/end dates (config uses datetime, args use date)
            sd: datetime | None = None
            if start_date:
                sd = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
            elif self._config.start_date:
                sd = self._config.start_date

            ed: datetime | None = None
            if end_date:
                ed = datetime.combine(end_date, datetime.min.time(), tzinfo=timezone.utc)
            elif self._config.end_date:
                ed = self._config.end_date

            # Resolve timeframe from config
            tf = self._config.timeframes[0] if self._config.timeframes else Timeframe.H1

            await self._replay.load_data(sym, sd, ed)
            await self._replay.play()

            performance = await self._performance.calculate(
                self._trades,
                self._equity_curve,
                self._config.initial_balance,
            )

            elapsed = time.time() - start

            bt_result = BacktestResult(
                symbol=sym,
                timeframe=tf,
                start_date=(sd or datetime.now(timezone.utc)).date(),
                end_date=(ed or datetime.now(timezone.utc)).date(),
                initial_balance=self._config.initial_balance,
                final_balance=self._portfolio.balance,
                net_profit=self._portfolio.balance - self._config.initial_balance,
                total_trades=len(self._trades),
                winning_trades=sum(1 for t in self._trades if t.get("pnl", 0) > 0),
                losing_trades=sum(1 for t in self._trades if t.get("pnl", 0) < 0),
                performance=performance,
                equity_curve=list(self._equity_curve),
            )

            return BacktestEngineResult(
                success=True,
                result=bt_result,
                execution_time_seconds=round(elapsed, 2),
            )

        except Exception as e:
            import traceback

            return BacktestEngineResult(
                success=False,
                error=f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
            )

    async def on_candle(
        self,
        symbol: str,
        timestamp: datetime,
        open_price: Decimal,
        high: Decimal,
        low: Decimal,
        close: Decimal,
        volume: Decimal,
    ) -> None:
        """Handle candle data from replay."""
        self._current_bid = close - Decimal("0.0001")
        self._current_ask = close
        self._current_liquidity = 0.8

        equity = self._portfolio.equity
        self._equity_curve.append(float(equity))

    async def on_tick(
        self,
        symbol: str,
        timestamp: datetime,
        bid: Decimal,
        ask: Decimal,
    ) -> None:
        """Handle tick data from replay."""
        self._current_bid = bid
        self._current_ask = ask
        self._current_liquidity = 0.9

        equity = self._portfolio.equity
        self._equity_curve.append(float(equity))

    async def on_event(self, event: Any) -> None:
        """Handle scheduled events from replay."""
        pass

    async def reset(self) -> None:
        """Reset backtest engine to initial state."""
        await self._replay.reset()
        await self._portfolio.reset()
        self._trades.clear()
        self._equity_curve.clear()
        self._trade_stats = TradeStatistics()
        self._execution_stats = ExecutionStatistics()
        self._portfolio_stats = PortfolioStatistics()
