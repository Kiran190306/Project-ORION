"""Tests for trading data models."""

from __future__ import annotations

from decimal import Decimal

from libraries.domain.trading.models import (
    PositionSizingMethod,
    SizingResult,
    StrategyType,
    TradeSignal,
    TradingSignal,
)
from libraries.domain.trading.signals import SignalDirection, SignalStrength


class TestStrategyType:
    def test_enum_values(self) -> None:
        assert StrategyType.SCALPING == "scalping"
        assert StrategyType.SWING == "swing"
        assert StrategyType.TREND_FOLLOWING == "trend_following"
        assert StrategyType.MEAN_REVERSION == "mean_reversion"
        assert StrategyType.BREAKOUT == "breakout"
        assert StrategyType.NEWS == "news"

    def test_all_strategies_covered(self) -> None:
        assert len(StrategyType) == 6


class TestPositionSizingMethod:
    def test_enum_values(self) -> None:
        assert PositionSizingMethod.FIXED == "fixed"
        assert PositionSizingMethod.RISK_PERCENT == "risk_percent"
        assert PositionSizingMethod.ATR == "atr"
        assert PositionSizingMethod.KELLY == "kelly"
        assert PositionSizingMethod.VOLATILITY_BASED == "volatility_based"

    def test_all_methods_covered(self) -> None:
        assert len(PositionSizingMethod) == 5


class TestTradingSignal:
    def test_creates_with_defaults(self) -> None:
        signal = TradingSignal(
            direction=SignalDirection.BUY,
            strength=SignalStrength.STRONG,
            strategy=StrategyType.SWING,
            symbol="EUR/USD",
        )
        assert signal.direction == SignalDirection.BUY
        assert signal.strength == SignalStrength.STRONG
        assert signal.strategy == StrategyType.SWING
        assert signal.symbol == "EUR/USD"
        assert signal.confidence_score == 0.0
        assert signal.metadata == {}

    def test_creates_with_confidence(self) -> None:
        signal = TradingSignal(
            direction=SignalDirection.SELL,
            strength=SignalStrength.MODERATE,
            strategy=StrategyType.TREND_FOLLOWING,
            symbol="GBP/USD",
            confidence_score=75.0,
        )
        assert signal.confidence_score == 75.0

    def test_creates_with_metadata(self) -> None:
        signal = TradingSignal(
            direction=SignalDirection.BUY,
            strength=SignalStrength.WEAK,
            strategy=StrategyType.SCALPING,
            symbol="EUR/JPY",
            metadata={"rsi": 30},
        )
        assert signal.metadata["rsi"] == 30


class TestTradeSignal:
    def test_creates_with_defaults(self) -> None:
        ts = TradeSignal(
            direction=SignalDirection.BUY,
            symbol="EUR/USD",
        )
        assert ts.direction == SignalDirection.BUY
        assert ts.symbol == "EUR/USD"
        assert ts.entry_price is None
        assert ts.confidence == 0.0

    def test_creates_with_prices(self) -> None:
        ts = TradeSignal(
            direction=SignalDirection.SELL,
            symbol="GBP/USD",
            entry_price=Decimal("1.2500"),
            stop_loss=Decimal("1.2550"),
            take_profit=Decimal("1.2400"),
            confidence=80.0,
        )
        assert ts.entry_price == Decimal("1.2500")
        assert ts.stop_loss == Decimal("1.2550")
        assert ts.take_profit == Decimal("1.2400")
        assert ts.confidence == 80.0


class TestSizingResult:
    def test_creates_with_values(self) -> None:
        result = SizingResult(
            method=PositionSizingMethod.FIXED,
            units=Decimal("1000"),
            notional_value=Decimal("10000"),
            risk_amount=Decimal("100"),
            account_risk_pct=1.0,
        )
        assert result.method == PositionSizingMethod.FIXED
        assert result.units == Decimal("1000")
        assert result.notional_value == Decimal("10000")
        assert result.risk_amount == Decimal("100")
        assert result.account_risk_pct == 1.0

    def test_creates_with_max_units(self) -> None:
        result = SizingResult(
            method=PositionSizingMethod.ATR,
            units=Decimal("500"),
            notional_value=Decimal("5000"),
            risk_amount=Decimal("50"),
            account_risk_pct=0.5,
            max_units=Decimal("1000"),
        )
        assert result.max_units == Decimal("1000")
