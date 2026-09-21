"""Unit tests for LeakageGuard look-ahead bias prevention (EPIC-023 Phase 5)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from libraries.domain.backtesting.leakage_guard import (
    DataLeakageDetectedError,
    LeakageGuard,
)
from libraries.domain.strategy.models import StrategyContext


def test_leakage_guard_filter_visible_candles() -> None:
    """filter_visible_candles must strictly return candles where timestamp <= current_time."""
    base_t = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    dataset = [
        {"timestamp": base_t + timedelta(hours=i), "close": 1.0500 + i * 0.0010}
        for i in range(10)
    ]

    # Current time is step 5 (index 5)
    current_t = dataset[5]["timestamp"]
    visible = LeakageGuard.filter_visible_candles(dataset, current_time=current_t)

    assert len(visible) == 6  # indices 0 through 5 inclusive
    assert all(item["timestamp"] <= current_t for item in visible)

    # Any candle with timestamp > current_t is excluded
    future_timestamps = [item["timestamp"] for item in dataset[6:]]
    assert all(ts not in [v["timestamp"] for v in visible] for ts in future_timestamps)


def test_leakage_guard_assert_monotonic_timestamps_valid() -> None:
    """Monotonically increasing timestamps pass validation without errors."""
    base_t = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    timestamps = [base_t + timedelta(hours=i) for i in range(10)]
    LeakageGuard.assert_monotonic_timestamps(timestamps)


def test_leakage_guard_assert_monotonic_timestamps_invalid() -> None:
    """Decreasing timestamp sequence must raise DataLeakageDetectedError."""
    base_t = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    timestamps = [
        base_t,
        base_t + timedelta(hours=1),
        base_t + timedelta(minutes=30),  # Decreases!
    ]
    with pytest.raises(DataLeakageDetectedError, match="Timestamp anomaly"):
        LeakageGuard.assert_monotonic_timestamps(timestamps)


def test_leakage_guard_validate_strategy_context_valid() -> None:
    """Valid strategy context at or before simulation time passes."""
    current_t = datetime(2025, 1, 1, 15, 0, tzinfo=timezone.utc)
    context = StrategyContext(
        strategy_id="trend_following",
        symbol="EUR/USD",
        current_price=Decimal("1.0850"),
        timestamp=current_t,
        metadata={"current_time": current_t},
    )
    LeakageGuard.validate_strategy_context(context, current_time=current_t)


def test_leakage_guard_validate_strategy_context_future_timestamp_rejected() -> None:
    """Strategy context timestamp in the future relative to current simulation time is rejected."""
    current_t = datetime(2025, 1, 1, 15, 0, tzinfo=timezone.utc)
    future_t = current_t + timedelta(minutes=15)
    context = StrategyContext(
        strategy_id="trend_following",
        symbol="EUR/USD",
        current_price=Decimal("1.0850"),
        timestamp=future_t,
    )
    with pytest.raises(DataLeakageDetectedError, match="Look-ahead bias detected"):
        LeakageGuard.validate_strategy_context(context, current_time=current_t)
