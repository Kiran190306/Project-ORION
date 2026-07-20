"""Execution filter for the Trading Decision Engine.

Validates whether a trade can be executed under current market conditions
including spread, liquidity, volatility, and market hours.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from libraries.domain.trading.market_state import MarketState, MarketStateType
from libraries.domain.trading.models import TradingSignal


@dataclass(frozen=True, slots=True)
class ExecutionFilterResult:
    """Result of execution filter evaluation."""

    allowed: bool
    reason: str = ""
    spread_ok: bool = True
    liquidity_ok: bool = True
    volatility_ok: bool = True
    market_hours_ok: bool = True
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_allowed(self) -> bool:
        return self.allowed


class ExecutionFilter:
    """Filters trades based on execution feasibility.

    Thread-safe via asyncio.Lock. Checks spread, liquidity, volatility,
    and market hours before allowing execution.
    """

    def __init__(
        self,
        max_spread_pips: float = 5.0,
        min_liquidity: float = 0.2,
        max_volatility: float = 0.9,
        check_market_hours: bool = True,
    ) -> None:
        if max_spread_pips <= 0:
            raise ValueError("max_spread_pips must be positive")
        if not 0 <= min_liquidity <= 1:
            raise ValueError("min_liquidity must be between 0 and 1")
        if not 0 <= max_volatility <= 1:
            raise ValueError("max_volatility must be between 0 and 1")

        self._max_spread_pips = max_spread_pips
        self._min_liquidity = min_liquidity
        self._max_volatility = max_volatility
        self._check_market_hours = check_market_hours
        self._lock = asyncio.Lock()

    @property
    def max_spread_pips(self) -> float:
        return self._max_spread_pips

    @property
    def min_liquidity(self) -> float:
        return self._min_liquidity

    @property
    def max_volatility(self) -> float:
        return self._max_volatility

    async def check(
        self,
        signal: TradingSignal,
        market_state: MarketState,
        spread_pips: float = 0.0,
        liquidity_score: float = 0.5,
        volatility_score: float = 0.5,
        market_hours_active: bool = True,
    ) -> ExecutionFilterResult:
        """Check if a trade can be executed.

        Args:
            signal: The trading signal.
            market_state: Current market state.
            spread_pips: Current spread in pips.
            liquidity_score: 0.0-1.0 liquidity score.
            volatility_score: 0.0-1.0 volatility score.
            market_hours_active: Whether market is currently open.

        Returns:
            ExecutionFilterResult indicating if execution is feasible.
        """
        async with self._lock:
            spread_ok = spread_pips <= self._max_spread_pips
            liquidity_ok = liquidity_score >= self._min_liquidity
            volatility_ok = volatility_score <= self._max_volatility
            market_hours_ok = not self._check_market_hours or market_hours_active

            # Check if market state explicitly blocks execution
            if market_state.state_type == MarketStateType.NEWS_MODE:
                return ExecutionFilterResult(
                    allowed=False,
                    reason="News mode active - execution blocked",
                    spread_ok=spread_ok,
                    liquidity_ok=liquidity_ok,
                    volatility_ok=volatility_ok,
                    market_hours_ok=market_hours_ok,
                )

            reasons = []
            if not spread_ok:
                reasons.append(f"Spread {spread_pips:.1f}pips exceeds max {self._max_spread_pips}pips")
            if not liquidity_ok:
                reasons.append(f"Liquidity {liquidity_score:.2f} below min {self._min_liquidity:.2f}")
            if not volatility_ok:
                reasons.append(f"Volatility {volatility_score:.2f} exceeds max {self._max_volatility:.2f}")
            if not market_hours_ok:
                reasons.append("Market is closed")

            return ExecutionFilterResult(
                allowed=not bool(reasons),
                reason="; ".join(reasons) if reasons else "All execution checks passed",
                spread_ok=spread_ok,
                liquidity_ok=liquidity_ok,
                volatility_ok=volatility_ok,
                market_hours_ok=market_hours_ok,
            )
