"""BacktestContext - aggregates all inputs for the Backtesting Engine.

Provides a single context object with configuration, market data,
portfolio state, and scenario information for each evaluation step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.backtesting.models import (
    BacktestConfig,
    BacktestEvent,
    PortfolioSnapshot,
    ReplayConfig,
    ReplayState,
    ScenarioConfig,
    SimulationConfig,
)


@dataclass(frozen=True, slots=True)
class BacktestContext:
    """Complete context for a backtest evaluation step.

    All fields are read-only. Constructed by the BacktestEngine before
    each evaluation step and passed to all components.
    """

    # ─── Configuration ───────────────────────────────────────
    backtest_config: BacktestConfig = field(default_factory=BacktestConfig)
    replay_config: ReplayConfig = field(default_factory=ReplayConfig)
    simulation_config: SimulationConfig = field(default_factory=SimulationConfig)

    # ─── Current State ───────────────────────────────────────
    current_bar_index: int = 0
    current_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    current_bid: Decimal = Decimal("0")
    current_ask: Decimal = Decimal("0")
    current_open: Decimal = Decimal("0")
    current_high: Decimal = Decimal("0")
    current_low: Decimal = Decimal("0")
    current_close: Decimal = Decimal("0")
    current_volume: Decimal = Decimal("0")
    current_spread_pips: float = 0.0

    # ─── Replay State ────────────────────────────────────────
    replay_state: ReplayState = ReplayState.IDLE
    replay_progress: float = 0.0  # 0.0–1.0
    replay_speed: float = 1.0
    total_bars: int = 0
    processed_bars: int = 0

    # ─── Portfolio State ─────────────────────────────────────
    portfolio_snapshot: PortfolioSnapshot | None = None

    # ─── Scenario State ──────────────────────────────────────
    active_scenarios: tuple[ScenarioConfig, ...] = ()
    is_scenario_active: bool = False
    scenario_intensity: float = 1.0

    # ─── Metadata ────────────────────────────────────────────
    metadata: dict[str, Any] = field(default_factory=dict)

    # ─── Computed Properties ─────────────────────────────────

    @property
    def is_market_open(self) -> bool:
        """Return whether the market is considered open."""
        return self.replay_state == ReplayState.PLAYING

    @property
    def mid_price(self) -> Decimal:
        """Return mid-price between bid and ask."""
        return (self.current_bid + self.current_ask) / Decimal("2")

    @property
    def elapsed_bars(self) -> int:
        """Return number of bars processed."""
        return self.processed_bars

    @property
    def remaining_bars(self) -> int:
        """Return number of bars remaining."""
        return self.total_bars - self.processed_bars

    @property
    def is_complete(self) -> bool:
        """Return whether the backtest has completed."""
        return self.replay_state == ReplayState.COMPLETED

    @property
    def is_paused(self) -> bool:
        """Return whether the backtest is paused."""
        return self.replay_state == ReplayState.PAUSED

    @property
    def check_summary(self) -> dict[str, Any]:
        """Return a summary dict of key context values."""
        return {
            "bar_index": self.current_bar_index,
            "timestamp": self.current_timestamp.isoformat(),
            "symbol": self.backtest_config.symbols[0] if self.backtest_config.symbols else "",
            "bid": float(self.current_bid),
            "ask": float(self.current_ask),
            "replay_state": self.replay_state.value,
            "replay_progress": round(self.replay_progress * 100, 2),
            "portfolio_balance": (
                float(self.portfolio_snapshot.balance) if self.portfolio_snapshot else 0.0
            ),
            "portfolio_equity": (
                float(self.portfolio_snapshot.equity) if self.portfolio_snapshot else 0.0
            ),
            "is_scenario_active": self.is_scenario_active,
        }
