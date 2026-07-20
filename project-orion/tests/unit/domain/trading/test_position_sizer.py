"""Tests for position sizers."""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from libraries.domain.trading.models import (
    PositionSizingMethod,
    StrategyType,
    TradingSignal,
)
from libraries.domain.trading.position_sizer import (
    ATRPositionSizer,
    FixedPositionSizer,
    KellyPositionSizer,
    RiskPercentPositionSizer,
    VolatilityBasedPositionSizer,
)
from libraries.domain.trading.signals import SignalDirection, SignalStrength


def make_signal() -> TradingSignal:
    return TradingSignal(
        direction=SignalDirection.BUY,
        strength=SignalStrength.STRONG,
        strategy=StrategyType.SWING,
        symbol="EUR/USD",
    )


class TestFixedPositionSizer:
    def test_initialization(self) -> None:
        sizer = FixedPositionSizer(fixed_notional=Decimal("1000"))
        assert sizer.method == PositionSizingMethod.FIXED
        assert sizer.fixed_notional == Decimal("1000")

    def test_invalid_notional(self) -> None:
        with pytest.raises(ValueError):
            FixedPositionSizer(fixed_notional=Decimal("0"))
        with pytest.raises(ValueError):
            FixedPositionSizer(fixed_notional=Decimal("-100"))

    def test_calculates_position(self) -> None:
        async def exercise() -> None:
            sizer = FixedPositionSizer(fixed_notional=Decimal("1000"))
            result = await sizer.calculate(
                signal=make_signal(),
                account_balance=Decimal("10000"),
                confidence=80.0,
                entry_price=Decimal("1.1000"),
            )
            assert result.method == PositionSizingMethod.FIXED
            assert result.units > 0
            assert result.notional_value > 0

        asyncio.run(exercise())

    def test_confidence_adjusts_size(self) -> None:
        async def exercise() -> None:
            sizer = FixedPositionSizer(fixed_notional=Decimal("1000"))
            high_conf = await sizer.calculate(
                signal=make_signal(),
                account_balance=Decimal("10000"),
                confidence=100.0,
                entry_price=Decimal("1.1000"),
            )
            low_conf = await sizer.calculate(
                signal=make_signal(),
                account_balance=Decimal("10000"),
                confidence=50.0,
                entry_price=Decimal("1.1000"),
            )
            assert high_conf.units >= low_conf.units

        asyncio.run(exercise())


class TestRiskPercentPositionSizer:
    def test_initialization(self) -> None:
        sizer = RiskPercentPositionSizer(risk_percent=2.0)
        assert sizer.method == PositionSizingMethod.RISK_PERCENT
        assert sizer.risk_percent == 2.0

    def test_invalid_risk_percent(self) -> None:
        with pytest.raises(ValueError):
            RiskPercentPositionSizer(risk_percent=0)
        with pytest.raises(ValueError):
            RiskPercentPositionSizer(risk_percent=101)

    def test_calculates_with_stop_loss(self) -> None:
        async def exercise() -> None:
            sizer = RiskPercentPositionSizer(risk_percent=1.0)
            result = await sizer.calculate(
                signal=make_signal(),
                account_balance=Decimal("10000"),
                confidence=100.0,
                entry_price=Decimal("1.1000"),
                stop_loss=Decimal("1.0900"),
            )
            assert result.units > 0
            assert result.account_risk_pct <= 1.0

        asyncio.run(exercise())


class TestATRPositionSizer:
    def test_initialization(self) -> None:
        sizer = ATRPositionSizer(atr_multiplier=2.0, risk_percent=1.0)
        assert sizer.method == PositionSizingMethod.ATR
        assert sizer.atr_multiplier == 2.0

    def test_invalid_params(self) -> None:
        with pytest.raises(ValueError):
            ATRPositionSizer(atr_multiplier=0)
        with pytest.raises(ValueError):
            ATRPositionSizer(risk_percent=0)

    def test_calculates_with_atr(self) -> None:
        async def exercise() -> None:
            sizer = ATRPositionSizer(atr_multiplier=2.0, risk_percent=1.0)
            result = await sizer.calculate(
                signal=make_signal(),
                account_balance=Decimal("10000"),
                confidence=100.0,
                entry_price=Decimal("1.1000"),
                atr=Decimal("0.0050"),
            )
            assert result.units > 0
            assert result.method == PositionSizingMethod.ATR

        asyncio.run(exercise())


class TestKellyPositionSizer:
    def test_initialization(self) -> None:
        sizer = KellyPositionSizer(kelly_fraction=0.25, max_risk_percent=5.0)
        assert sizer.method == PositionSizingMethod.KELLY
        assert sizer.kelly_fraction == 0.25

    def test_invalid_params(self) -> None:
        with pytest.raises(ValueError):
            KellyPositionSizer(kelly_fraction=0)
        with pytest.raises(ValueError):
            KellyPositionSizer(kelly_fraction=1.5)
        with pytest.raises(ValueError):
            KellyPositionSizer(max_risk_percent=0)

    def test_calculates_kelly_size(self) -> None:
        async def exercise() -> None:
            sizer = KellyPositionSizer(kelly_fraction=0.25, max_risk_percent=5.0)
            result = await sizer.calculate(
                signal=make_signal(),
                account_balance=Decimal("10000"),
                confidence=80.0,
                entry_price=Decimal("1.1000"),
                stop_loss=Decimal("1.0900"),
            )
            assert result.units >= 0
            assert result.method == PositionSizingMethod.KELLY

        asyncio.run(exercise())


class TestVolatilityBasedPositionSizer:
    def test_initialization(self) -> None:
        sizer = VolatilityBasedPositionSizer(
            base_notional=Decimal("1000"), max_volatility=1.0
        )
        assert sizer.method == PositionSizingMethod.VOLATILITY_BASED
        assert sizer.base_notional == Decimal("1000")

    def test_invalid_params(self) -> None:
        with pytest.raises(ValueError):
            VolatilityBasedPositionSizer(base_notional=Decimal("0"))
        with pytest.raises(ValueError):
            VolatilityBasedPositionSizer(max_volatility=0)

    def test_volatility_reduces_size(self) -> None:
        async def exercise() -> None:
            sizer = VolatilityBasedPositionSizer(
                base_notional=Decimal("1000"), max_volatility=1.0
            )
            low_vol = await sizer.calculate(
                signal=make_signal(),
                account_balance=Decimal("10000"),
                confidence=100.0,
                entry_price=Decimal("1.1000"),
                volatility=0.1,
            )
            high_vol = await sizer.calculate(
                signal=make_signal(),
                account_balance=Decimal("10000"),
                confidence=100.0,
                entry_price=Decimal("1.1000"),
                volatility=0.9,
            )
            assert low_vol.units > high_vol.units

        asyncio.run(exercise())
