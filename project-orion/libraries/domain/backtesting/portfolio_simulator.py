"""Portfolio simulator for backtesting.

Simulates portfolio state evolution including balance, equity, margin,
exposure, portfolio heat, PnL, drawdown, and risk metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.backtesting.models import (
    DrawdownSnapshot,
    ExecutionSimulationResult,
    PortfolioSnapshot,
)


@dataclass(frozen=True, slots=True)
class PortfolioSimulationConfig:
    """Configuration for the portfolio simulator."""

    initial_balance: Decimal = Decimal("10000")
    base_currency: str = "USD"
    leverage: Decimal = Decimal("100")
    margin_call_level: float = 100.0
    stop_out_level: float = 50.0
    max_open_positions: int = 50
    max_portfolio_heat: float = 80.0
    metadata: dict[str, Any] = field(default_factory=dict)


class PortfolioSimulator:
    """Simulates portfolio state during backtesting.

    Tracks balance, equity, margin, exposure, drawdown, and PnL.
    """

    def __init__(self, config: PortfolioSimulationConfig | None = None) -> None:
        """Initialize portfolio simulator.

        Args:
            config: Portfolio simulation configuration.
        """
        cfg = config or PortfolioSimulationConfig()
        self._config = cfg
        self._balance = cfg.initial_balance
        self._equity = cfg.initial_balance
        self._used_margin = Decimal("0")
        self._free_margin = cfg.initial_balance
        self._margin_level = float("inf")
        self._realized_pnl = Decimal("0")
        self._unrealized_pnl = Decimal("0")
        self._total_commission = Decimal("0")
        self._total_swap = Decimal("0")
        self._peak_equity = cfg.initial_balance
        self._current_drawdown = Decimal("0")
        self._max_drawdown = Decimal("0")
        self._open_positions: dict[str, dict[str, Any]] = {}
        self._trade_history: list[dict[str, Any]] = []
        self._is_stop_out: bool = False

    @property
    def config(self) -> PortfolioSimulationConfig:
        return self._config

    @property
    def balance(self) -> Decimal:
        return self._balance

    @property
    def equity(self) -> Decimal:
        return self._equity

    @property
    def used_margin(self) -> Decimal:
        return self._used_margin

    @property
    def free_margin(self) -> Decimal:
        return self._free_margin

    @property
    def margin_level(self) -> float:
        return self._margin_level

    @property
    def realized_pnl(self) -> Decimal:
        return self._realized_pnl

    @property
    def unrealized_pnl(self) -> Decimal:
        return self._unrealized_pnl

    @property
    def is_stop_out(self) -> bool:
        return self._is_stop_out

    async def apply_fill(
        self,
        result: ExecutionSimulationResult,
        current_price: Decimal | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        """Apply an execution fill to portfolio state.

        Args:
            result: Execution simulation result.
            current_price: Current market price.
            timestamp: Current timestamp.
        """
        if self._is_stop_out:
            return

        price = result.average_price or current_price or Decimal("0")
        quantity = result.total_quantity
        notional = quantity * price
        if self._config.leverage > 0:
            margin_needed = notional / self._config.leverage
        else:
            margin_needed = notional
        commission = result.total_commission

        # Update balance after commission
        self._balance -= commission
        self._total_commission += commission
        self._used_margin += margin_needed

        # Track PnL from the fill
        side_multiplier = 1 if result.order.side.value == "buy" else -1
        fill_pnl = quantity * price * Decimal(str(side_multiplier))
        self._realized_pnl += fill_pnl

        self._update_equity(current_price)
        self._update_drawdown()

    async def update_market_price(
        self,
        symbol: str,
        price: Decimal,
        timestamp: datetime | None = None,
    ) -> None:
        """Update portfolio with new market prices.

        Args:
            symbol: Trading symbol.
            price: Current market price.
            timestamp: Current timestamp.
        """
        self._update_equity(price)
        self._update_drawdown()

    async def get_snapshot(self) -> PortfolioSnapshot:
        """Get current portfolio snapshot.

        Returns:
            Current portfolio snapshot.
        """
        return PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            balance=self._balance,
            equity=self._equity,
            margin_used=self._used_margin,
            free_margin=self._free_margin,
            realized_pnl=self._realized_pnl,
            unrealized_pnl=self._unrealized_pnl,
            total_commission=self._total_commission,
            total_swap=self._total_swap,
            position_count=len(self._open_positions),
            drawdown=DrawdownSnapshot(
                timestamp=datetime.now(timezone.utc),
                current_drawdown=float(self._current_drawdown),
                max_drawdown=float(self._max_drawdown),
                peak_equity=self._peak_equity,
                current_equity=self._equity,
            ),
        )

    def _update_equity(self, current_price: Decimal | None) -> None:
        """Update equity and margin calculations.

        Args:
            current_price: Current market price.
        """
        if current_price is not None:
            self._equity = self._balance + self._unrealized_pnl - self._total_commission

        if self._used_margin > Decimal("0"):
            self._free_margin = self._equity - self._used_margin
            self._margin_level = float(self._equity / self._used_margin * 100)
        else:
            self._free_margin = self._equity
            self._margin_level = float("inf")

        # Check stop out
        cfg = self._config
        if self._margin_level < cfg.stop_out_level:
            self._is_stop_out = True

    def _update_drawdown(self) -> None:
        """Update drawdown tracking."""
        if self._equity > self._peak_equity:
            self._peak_equity = self._equity

        self._current_drawdown = self._peak_equity - self._equity
        if self._current_drawdown > self._max_drawdown:
            self._max_drawdown = self._current_drawdown

    async def reset(self) -> None:
        """Reset portfolio to initial state."""
        self._balance = self._config.initial_balance
        self._equity = self._config.initial_balance
        self._used_margin = Decimal("0")
        self._free_margin = self._config.initial_balance
        self._margin_level = float("inf")
        self._realized_pnl = Decimal("0")
        self._unrealized_pnl = Decimal("0")
        self._total_commission = Decimal("0")
        self._total_swap = Decimal("0")
        self._peak_equity = self._config.initial_balance
        self._current_drawdown = Decimal("0")
        self._max_drawdown = Decimal("0")
        self._open_positions.clear()
        self._trade_history.clear()
        self._is_stop_out = False
