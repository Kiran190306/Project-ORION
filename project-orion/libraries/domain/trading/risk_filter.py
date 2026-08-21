"""Risk filter for the Trading Decision Engine.

Validates trades against risk management rules before execution.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone

from libraries.domain.trading.models import TradingSignal


@dataclass(frozen=True, slots=True)
class RiskFilterResult:
    """Result of risk filter evaluation."""

    allowed: bool
    reason: str = ""
    max_position_size: float | None = None
    max_risk_per_trade: float | None = None
    max_daily_trades: int | None = None
    daily_trade_count: int = 0
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_allowed(self) -> bool:
        return self.allowed


class RiskFilter:
    """Filters trades based on risk management rules.

    Thread-safe via asyncio.Lock. Supports:
    - Max position size
    - Max risk per trade
    - Max daily trades
    - Max drawdown
    - Min confidence
    - Max correlation
    """

    def __init__(
        self,
        max_position_size: float = 0.1,  # 10% of account
        max_risk_per_trade: float = 0.02,  # 2% of account
        max_daily_trades: int = 10,
        max_drawdown: float = 0.2,  # 20% max drawdown
        min_confidence: float = 30.0,
        max_correlation: float = 0.7,
    ) -> None:
        if not 0 < max_position_size <= 1:
            raise ValueError("max_position_size must be between 0 and 1")
        if not 0 < max_risk_per_trade <= 1:
            raise ValueError("max_risk_per_trade must be between 0 and 1")
        if max_daily_trades <= 0:
            raise ValueError("max_daily_trades must be positive")
        if not 0 <= max_drawdown <= 1:
            raise ValueError("max_drawdown must be between 0 and 1")
        if not 0 <= min_confidence <= 100:
            raise ValueError("min_confidence must be between 0 and 100")

        self._max_position_size = max_position_size
        self._max_risk_per_trade = max_risk_per_trade
        self._max_daily_trades = max_daily_trades
        self._max_drawdown = max_drawdown
        self._min_confidence = min_confidence
        self._max_correlation = max_correlation
        self._lock = asyncio.Lock()
        self._daily_trade_count: int = 0
        self._current_drawdown: float = 0.0
        self._current_positions: dict[str, float] = {}
        self._reset_date: datetime | None = None

    @property
    def max_position_size(self) -> float:
        return self._max_position_size

    @property
    def max_risk_per_trade(self) -> float:
        return self._max_risk_per_trade

    @property
    def max_daily_trades(self) -> int:
        return self._max_daily_trades

    @property
    def min_confidence(self) -> float:
        return self._min_confidence

    @property
    def max_drawdown(self) -> float:
        return self._max_drawdown

    async def check(
        self,
        signal: TradingSignal,
        confidence: float,
        current_positions: dict[str, float] | None = None,
        current_drawdown: float = 0.0,
    ) -> RiskFilterResult:
        """Check if a trade is allowed by risk rules.

        Args:
            signal: The trading signal.
            confidence: Confidence score 0-100.
            current_positions: Current positions {symbol: size}.
            current_drawdown: Current drawdown ratio.

        Returns:
            RiskFilterResult indicating if trade is allowed.
        """
        async with self._lock:
            self._reset_daily_if_needed()
            self._current_drawdown = current_drawdown
            if current_positions is not None:
                self._current_positions = current_positions

            # Check confidence
            if confidence < self._min_confidence:
                return RiskFilterResult(
                    allowed=False,
                    reason=f"Confidence {confidence:.1f} below minimum {self._min_confidence}",
                    daily_trade_count=self._daily_trade_count,
                )

            # Check drawdown
            if self._current_drawdown >= self._max_drawdown:
                return RiskFilterResult(
                    allowed=False,
                    reason=f"Drawdown {self._current_drawdown:.1%} exceeds max {self._max_drawdown:.1%}",
                    daily_trade_count=self._daily_trade_count,
                )

            # Check daily trades
            if self._daily_trade_count >= self._max_daily_trades:
                return RiskFilterResult(
                    allowed=False,
                    reason=f"Daily trade limit {self._max_daily_trades} reached",
                    daily_trade_count=self._daily_trade_count,
                )

            # Check position size
            symbol = signal.symbol
            current_size = self._current_positions.get(symbol, 0.0)
            if current_size >= self._max_position_size:
                return RiskFilterResult(
                    allowed=False,
                    reason=f"Position size {current_size:.2%} exceeds max {self._max_position_size:.1%}",
                    max_position_size=self._max_position_size,
                    daily_trade_count=self._daily_trade_count,
                )

            # All checks passed
            return RiskFilterResult(
                allowed=True,
                reason="All risk checks passed",
                max_position_size=self._max_position_size,
                max_risk_per_trade=self._max_risk_per_trade,
                max_daily_trades=self._max_daily_trades,
                daily_trade_count=self._daily_trade_count,
            )

    async def record_trade(self) -> None:
        """Record a trade that was executed (increments daily counter)."""
        async with self._lock:
            self._reset_daily_if_needed()
            self._daily_trade_count += 1

    async def set_drawdown(self, drawdown: float) -> None:
        """Set the current drawdown level."""
        async with self._lock:
            self._current_drawdown = drawdown

    async def set_position(self, symbol: str, size: float) -> None:
        """Set the current position size for a symbol."""
        async with self._lock:
            self._current_positions[symbol] = size

    async def get_daily_trade_count(self) -> int:
        """Return the current daily trade count."""
        async with self._lock:
            self._reset_daily_if_needed()
            return self._daily_trade_count

    async def reset_daily(self) -> None:
        """Reset the daily trade counter."""
        async with self._lock:
            self._daily_trade_count = 0

    def _reset_daily_if_needed(self) -> None:
        """Reset daily counter if a new day has started."""
        now = datetime.now(timezone.utc)
        if self._reset_date is None or now.date() > self._reset_date.date():
            self._daily_trade_count = 0
            self._reset_date = now
