"""Tests for RiskFilter."""

from __future__ import annotations

import asyncio

import pytest

from libraries.domain.trading.models import StrategyType, TradingSignal
from libraries.domain.trading.risk_filter import RiskFilter, RiskFilterResult
from libraries.domain.trading.signals import SignalDirection, SignalStrength


def make_signal(symbol: str = "EUR/USD") -> TradingSignal:
    return TradingSignal(
        direction=SignalDirection.BUY,
        strength=SignalStrength.STRONG,
        strategy=StrategyType.SWING,
        symbol=symbol,
    )


class TestRiskFilter:
    def test_initialization(self) -> None:
        rf = RiskFilter(
            max_position_size=0.1,
            max_risk_per_trade=0.02,
            max_daily_trades=10,
            min_confidence=30.0,
        )
        assert rf.max_position_size == 0.1
        assert rf.min_confidence == 30.0
        assert rf.max_daily_trades == 10

    def test_invalid_params(self) -> None:
        with pytest.raises(ValueError):
            RiskFilter(max_position_size=0)
        with pytest.raises(ValueError):
            RiskFilter(max_position_size=1.5)
        with pytest.raises(ValueError):
            RiskFilter(max_risk_per_trade=0)
        with pytest.raises(ValueError):
            RiskFilter(max_risk_per_trade=1.5)
        with pytest.raises(ValueError):
            RiskFilter(max_daily_trades=0)
        with pytest.raises(ValueError):
            RiskFilter(min_confidence=-1)
        with pytest.raises(ValueError):
            RiskFilter(min_confidence=101)
        with pytest.raises(ValueError):
            RiskFilter(max_drawdown=-0.1)
        with pytest.raises(ValueError):
            RiskFilter(max_drawdown=1.5)

    def test_allows_trade_when_all_checks_pass(self) -> None:
        async def exercise() -> None:
            rf = RiskFilter(min_confidence=30.0)
            result = await rf.check(
                signal=make_signal(),
                confidence=80.0,
            )
            assert result.is_allowed
            assert result.reason == "All risk checks passed"

        asyncio.run(exercise())

    def test_rejects_low_confidence(self) -> None:
        async def exercise() -> None:
            rf = RiskFilter(min_confidence=50.0)
            result = await rf.check(
                signal=make_signal(),
                confidence=30.0,
            )
            assert not result.is_allowed
            assert "confidence" in result.reason.lower()

        asyncio.run(exercise())

    def test_rejects_excessive_drawdown(self) -> None:
        async def exercise() -> None:
            rf = RiskFilter(max_drawdown=0.2)
            result = await rf.check(
                signal=make_signal(),
                confidence=80.0,
                current_drawdown=0.3,
            )
            assert not result.is_allowed
            assert "drawdown" in result.reason.lower()

        asyncio.run(exercise())

    def test_rejects_when_daily_limit_reached(self) -> None:
        async def exercise() -> None:
            rf = RiskFilter(max_daily_trades=2, min_confidence=0.0)
            # Record 2 trades
            await rf.record_trade()
            await rf.record_trade()

            result = await rf.check(
                signal=make_signal(),
                confidence=80.0,
            )
            assert not result.is_allowed
            assert "daily trade limit" in result.reason.lower()

        asyncio.run(exercise())

    def test_tracks_position_size(self) -> None:
        async def exercise() -> None:
            rf = RiskFilter(max_position_size=0.1, min_confidence=0.0)
            await rf.set_position("EUR/USD", 0.1)

            result = await rf.check(
                signal=make_signal(),
                confidence=80.0,
            )
            assert not result.is_allowed
            assert "position size" in result.reason.lower()

        asyncio.run(exercise())

    def test_reset_daily_counter(self) -> None:
        async def exercise() -> None:
            rf = RiskFilter(max_daily_trades=1, min_confidence=0.0)
            await rf.record_trade()
            assert await rf.get_daily_trade_count() == 1

            await rf.reset_daily()
            assert await rf.get_daily_trade_count() == 0

        asyncio.run(exercise())

    def test_risk_filter_result_immutable(self) -> None:
        result = RiskFilterResult(
            allowed=True,
            reason="Test",
            max_position_size=0.1,
            daily_trade_count=5,
        )
        assert result.is_allowed
        assert result.max_position_size == 0.1
        assert result.daily_trade_count == 5

    def test_concurrent_trade_recording(self) -> None:
        async def exercise() -> None:
            rf = RiskFilter(max_daily_trades=100, min_confidence=0.0)
            await asyncio.gather(
                rf.record_trade(),
                rf.record_trade(),
                rf.record_trade(),
            )
            assert await rf.get_daily_trade_count() == 3

        asyncio.run(exercise())
