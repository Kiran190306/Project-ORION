"""Unit tests for RegimeAnalyzer in EPIC-024."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.research.regime_analyzer import RegimeAnalyzer


def _generate_synthetic_candles(n: int = 60) -> list[dict[str, Any]]:
    base_time = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = []
    price = Decimal("1.1000")
    for i in range(n):
        # Create an upward trend then downward trend
        delta = Decimal("0.0010") if i < 30 else Decimal("-0.0010")
        o = price
        c = price + delta
        h = max(o, c) + Decimal("0.0005")
        l = min(o, c) - Decimal("0.0005")
        candles.append(
            {
                "timestamp": base_time + timedelta(hours=i),
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": Decimal(1000),
            }
        )
        price = c
    return candles


def test_classify_candles():
    candles = _generate_synthetic_candles(60)
    regimes = RegimeAnalyzer.classify_candles(candles)

    assert len(regimes) == 60
    assert any(r in ("TRENDING_BULL", "TRENDING_BEAR", "RANGING_LOW_VOL") for r in regimes.values())


def test_analyze_regimes_with_trades():
    candles = _generate_synthetic_candles(60)

    trades = [
        {"entry_time": candles[10]["timestamp"], "realized_pnl": 150.0},
        {"entry_time": candles[25]["timestamp"], "realized_pnl": 200.0},
        {"entry_time": candles[45]["timestamp"], "realized_pnl": -80.0},
    ]

    breakdowns = RegimeAnalyzer.analyze_regimes(candles, trades, initial_capital=Decimal("10000.00"))

    assert len(breakdowns) == 4
    names = [b.regime_name for b in breakdowns]
    assert "TRENDING_BULL" in names
    assert "TRENDING_BEAR" in names
    assert "RANGING_LOW_VOL" in names
    assert "HIGH_VOLATILITY_CHOP" in names

    total_trades = sum(b.trade_count for b in breakdowns)
    assert total_trades == 3


def test_analyze_regimes_empty_trades():
    candles = _generate_synthetic_candles(40)
    breakdowns = RegimeAnalyzer.analyze_regimes(candles, [], initial_capital=Decimal("10000.00"))
    assert len(breakdowns) == 4
    for b in breakdowns:
        assert b.trade_count == 0
        assert b.win_rate == 0.0
