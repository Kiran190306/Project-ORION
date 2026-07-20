"""Tests for signal enums."""

from __future__ import annotations

from libraries.domain.trading.signals import SignalDirection, SignalStrength


class TestSignalDirection:
    def test_enum_values(self) -> None:
        assert SignalDirection.BUY == "buy"
        assert SignalDirection.SELL == "sell"
        assert SignalDirection.EXIT == "exit"
        assert SignalDirection.HOLD == "hold"
        assert SignalDirection.SCALE_IN == "scale_in"
        assert SignalDirection.SCALE_OUT == "scale_out"

    def test_all_directions_covered(self) -> None:
        assert len(SignalDirection) == 6

    def test_buy_and_sell_are_opposite(self) -> None:
        assert SignalDirection.BUY != SignalDirection.SELL


class TestSignalStrength:
    def test_enum_values(self) -> None:
        assert SignalStrength.STRONG == "strong"
        assert SignalStrength.MODERATE == "moderate"
        assert SignalStrength.WEAK == "weak"

    def test_all_strengths_covered(self) -> None:
        assert len(SignalStrength) == 3

    def test_ordering(self) -> None:
        assert SignalStrength.STRONG != SignalStrength.WEAK
