"""Position sizing for the Trading Decision Engine.

Supports Fixed, Risk%, ATR, Kelly Criterion, and Volatility-Based
position sizing methods.
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from libraries.domain.trading.models import (
    PositionSizingMethod,
    SizingResult,
    StrategyType,
    TradingSignal,
)
from libraries.domain.trading.signals import SignalDirection


class PositionSizer:
    """Base class for position sizing strategies."""

    def __init__(self, method: PositionSizingMethod) -> None:
        self._method = method
        self._lock = asyncio.Lock()

    @property
    def method(self) -> PositionSizingMethod:
        return self._method

    async def calculate(
        self,
        signal: TradingSignal,
        account_balance: Decimal,
        confidence: float,
        entry_price: Decimal | None = None,
        stop_loss: Decimal | None = None,
        atr: Decimal | None = None,
        volatility: float = 0.0,
    ) -> SizingResult:
        """Calculate position size. Override in subclasses."""
        raise NotImplementedError


class FixedPositionSizer(PositionSizer):
    """Fixed position sizing - always trades a fixed notional amount."""

    def __init__(self, fixed_notional: Decimal = Decimal("1000")) -> None:
        super().__init__(PositionSizingMethod.FIXED)
        if fixed_notional <= Decimal("0"):
            raise ValueError("fixed_notional must be positive")
        self._fixed_notional = fixed_notional

    @property
    def fixed_notional(self) -> Decimal:
        return self._fixed_notional

    async def calculate(
        self,
        signal: TradingSignal,
        account_balance: Decimal,
        confidence: float,
        entry_price: Decimal | None = None,
        stop_loss: Decimal | None = None,
        atr: Decimal | None = None,
        volatility: float = 0.0,
    ) -> SizingResult:
        async with self._lock:
            confidence_adjustment = max(0.5, confidence / 100.0)
            adjusted_notional = self._fixed_notional * Decimal(str(confidence_adjustment))
            units = adjusted_notional / (entry_price or Decimal("1"))
            risk_amount = adjusted_notional * Decimal("0.02")  # 2% risk
            account_risk_pct = (
                float(risk_amount / account_balance * 100) if account_balance > 0 else 0.0
            )

            return SizingResult(
                method=self._method,
                units=units.quantize(Decimal("0.0001")),
                notional_value=adjusted_notional.quantize(Decimal("0.01")),
                risk_amount=risk_amount.quantize(Decimal("0.01")),
                account_risk_pct=round(account_risk_pct, 4),
            )


class RiskPercentPositionSizer(PositionSizer):
    """Risk percentage position sizing - risk a fixed % of account per trade."""

    def __init__(self, risk_percent: float = 1.0) -> None:
        super().__init__(PositionSizingMethod.RISK_PERCENT)
        if not 0 < risk_percent <= 100:
            raise ValueError("risk_percent must be between 0 and 100")
        self._risk_percent = risk_percent

    @property
    def risk_percent(self) -> float:
        return self._risk_percent

    async def calculate(
        self,
        signal: TradingSignal,
        account_balance: Decimal,
        confidence: float,
        entry_price: Decimal | None = None,
        stop_loss: Decimal | None = None,
        atr: Decimal | None = None,
        volatility: float = 0.0,
    ) -> SizingResult:
        async with self._lock:
            risk_amount = account_balance * Decimal(str(self._risk_percent / 100.0))
            confidence_adjustment = max(0.5, confidence / 100.0)
            risk_amount = risk_amount * Decimal(str(confidence_adjustment))

            if stop_loss is not None and entry_price is not None and stop_loss != entry_price:
                risk_per_unit = abs(entry_price - stop_loss)
                units = risk_amount / risk_per_unit
            elif atr is not None and atr > 0:
                units = risk_amount / (atr * Decimal("2"))
            else:
                units = risk_amount / (entry_price or Decimal("1")) * Decimal("0.1")

            notional = units * (entry_price or Decimal("1"))
            account_risk_pct = (
                float(risk_amount / account_balance * 100) if account_balance > 0 else 0.0
            )

            return SizingResult(
                method=self._method,
                units=units.quantize(Decimal("0.0001")),
                notional_value=notional.quantize(Decimal("0.01")),
                risk_amount=risk_amount.quantize(Decimal("0.01")),
                account_risk_pct=round(account_risk_pct, 4),
            )


class ATRPositionSizer(PositionSizer):
    """ATR-based position sizing - position size based on ATR volatility."""

    def __init__(self, atr_multiplier: float = 2.0, risk_percent: float = 1.0) -> None:
        super().__init__(PositionSizingMethod.ATR)
        if atr_multiplier <= 0:
            raise ValueError("atr_multiplier must be positive")
        if not 0 < risk_percent <= 100:
            raise ValueError("risk_percent must be between 0 and 100")
        self._atr_multiplier = atr_multiplier
        self._risk_percent = risk_percent

    @property
    def atr_multiplier(self) -> float:
        return self._atr_multiplier

    @property
    def risk_percent(self) -> float:
        return self._risk_percent

    async def calculate(
        self,
        signal: TradingSignal,
        account_balance: Decimal,
        confidence: float,
        entry_price: Decimal | None = None,
        stop_loss: Decimal | None = None,
        atr: Decimal | None = None,
        volatility: float = 0.0,
    ) -> SizingResult:
        async with self._lock:
            risk_amount = account_balance * Decimal(str(self._risk_percent / 100.0))
            confidence_adjustment = max(0.5, confidence / 100.0)
            risk_amount = risk_amount * Decimal(str(confidence_adjustment))

            if atr is not None and atr > 0:
                stop_distance = atr * Decimal(str(self._atr_multiplier))
                units = risk_amount / stop_distance
            elif entry_price is not None:
                stop_distance = entry_price * Decimal(str(volatility * self._atr_multiplier))
                units = risk_amount / stop_distance if stop_distance > 0 else Decimal("0")
            else:
                units = Decimal("0")

            notional = units * (entry_price or Decimal("1"))
            account_risk_pct = (
                float(risk_amount / account_balance * 100) if account_balance > 0 else 0.0
            )

            return SizingResult(
                method=self._method,
                units=units.quantize(Decimal("0.0001")),
                notional_value=notional.quantize(Decimal("0.01")),
                risk_amount=risk_amount.quantize(Decimal("0.01")),
                account_risk_pct=round(account_risk_pct, 4),
            )


class KellyPositionSizer(PositionSizer):
    """Kelly Criterion position sizing."""

    def __init__(self, kelly_fraction: float = 0.25, max_risk_percent: float = 5.0) -> None:
        super().__init__(PositionSizingMethod.KELLY)
        if not 0 < kelly_fraction <= 1:
            raise ValueError("kelly_fraction must be between 0 and 1")
        if not 0 < max_risk_percent <= 100:
            raise ValueError("max_risk_percent must be between 0 and 100")
        self._kelly_fraction = kelly_fraction
        self._max_risk_percent = max_risk_percent

    @property
    def kelly_fraction(self) -> float:
        return self._kelly_fraction

    @property
    def max_risk_percent(self) -> float:
        return self._max_risk_percent

    async def calculate(
        self,
        signal: TradingSignal,
        account_balance: Decimal,
        confidence: float,
        entry_price: Decimal | None = None,
        stop_loss: Decimal | None = None,
        atr: Decimal | None = None,
        volatility: float = 0.0,
    ) -> SizingResult:
        async with self._lock:
            win_rate = confidence / 100.0
            risk_reward = 2.0  # Assumed 1:2 risk/reward when not specified

            if stop_loss is not None and entry_price is not None and stop_loss != entry_price:
                risk = abs(float(entry_price - stop_loss)) / float(entry_price)
                if risk > 0:
                    risk_reward = 2.0 / risk  # Simplified

            # Kelly % = win_rate - (1 - win_rate) / risk_reward
            kelly_pct = win_rate - (1.0 - win_rate) / risk_reward
            kelly_pct = max(0.0, min(kelly_pct, self._max_risk_percent / 100.0))
            kelly_pct *= self._kelly_fraction

            risk_amount = account_balance * Decimal(str(kelly_pct))
            if stop_loss is not None and entry_price is not None and stop_loss != entry_price:
                risk_per_unit = abs(entry_price - stop_loss)
                units = risk_amount / risk_per_unit
            else:
                units = risk_amount / (entry_price or Decimal("1"))

            notional = units * (entry_price or Decimal("1"))
            account_risk_pct = float(kelly_pct * 100)

            return SizingResult(
                method=self._method,
                units=units.quantize(Decimal("0.0001")),
                notional_value=notional.quantize(Decimal("0.01")),
                risk_amount=risk_amount.quantize(Decimal("0.01")),
                account_risk_pct=round(account_risk_pct, 4),
            )


class VolatilityBasedPositionSizer(PositionSizer):
    """Volatility-based position sizing - smaller positions in high volatility."""

    def __init__(
        self,
        base_notional: Decimal = Decimal("1000"),
        max_volatility: float = 1.0,
    ) -> None:
        super().__init__(PositionSizingMethod.VOLATILITY_BASED)
        if base_notional <= Decimal("0"):
            raise ValueError("base_notional must be positive")
        if max_volatility <= 0:
            raise ValueError("max_volatility must be positive")
        self._base_notional = base_notional
        self._max_volatility = max_volatility

    @property
    def base_notional(self) -> Decimal:
        return self._base_notional

    @property
    def max_volatility(self) -> float:
        return self._max_volatility

    async def calculate(
        self,
        signal: TradingSignal,
        account_balance: Decimal,
        confidence: float,
        entry_price: Decimal | None = None,
        stop_loss: Decimal | None = None,
        atr: Decimal | None = None,
        volatility: float = 0.0,
    ) -> SizingResult:
        async with self._lock:
            confidence_factor = max(0.5, confidence / 100.0)
            vol_factor = max(0.1, 1.0 - (volatility / self._max_volatility))

            adjusted_notional = self._base_notional * Decimal(str(confidence_factor * vol_factor))
            units = adjusted_notional / (entry_price or Decimal("1"))
            risk_amount = adjusted_notional * Decimal("0.02")
            account_risk_pct = (
                float(risk_amount / account_balance * 100) if account_balance > 0 else 0.0
            )

            return SizingResult(
                method=self._method,
                units=units.quantize(Decimal("0.0001")),
                notional_value=adjusted_notional.quantize(Decimal("0.01")),
                risk_amount=risk_amount.quantize(Decimal("0.01")),
                account_risk_pct=round(account_risk_pct, 4),
            )
