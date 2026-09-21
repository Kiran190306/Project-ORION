"""Quant Safety: Data Leakage and Look-Ahead Bias Prevention Guard.

Strictly prevents strategy models, indicators, and execution simulators from
observing future prices, future candles, future spreads, or future signals.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from libraries.domain.strategy.models import StrategyContext


class DataLeakageDetectedError(RuntimeError):
    """Raised when data from the future is detected at the current simulation step."""


class LeakageGuard:
    """Institutional guard preventing look-ahead bias in research backtests."""

    @staticmethod
    def filter_visible_candles(
        candles: list[dict[str, Any]],
        current_time: datetime,
    ) -> list[dict[str, Any]]:
        """Return only candles strictly up to the current simulation time T."""
        visible: list[dict[str, Any]] = []
        for c in candles:
            ts = c["timestamp"]
            if ts <= current_time:
                visible.append(c)
            else:
                # Chronologically sorted, so we can stop
                break
        return visible

    @staticmethod
    def validate_strategy_context(
        context: StrategyContext,
        current_time: datetime,
    ) -> None:
        """Assert that no historical or current candle in the context leaks future data.

        Raises:
            DataLeakageDetectedError: If any timestamp in context exceeds current_time.
        """
        # 1. Check context timestamp
        if context.timestamp > current_time:
            raise DataLeakageDetectedError(
                f"Look-ahead bias detected: context timestamp {context.timestamp.isoformat()} "
                f"is in the future relative to simulation time {current_time.isoformat()}"
            )

        # 2. Check current candle if present in metadata or attribute
        current_candle = getattr(context, "current_candle", None) or context.metadata.get("current_candle")
        if current_candle is not None:
            c_ts = getattr(current_candle, "timestamp", None)
            if c_ts and c_ts > current_time:
                raise DataLeakageDetectedError(
                    f"Look-ahead bias detected: current candle timestamp {c_ts.isoformat()} "
                    f"is in the future relative to simulation time {current_time.isoformat()}"
                )

        # 3. Check all historical candles in metadata or attribute
        historical = getattr(context, "historical_candles", None) or context.metadata.get("historical_candles", [])
        if historical:
            for idx, bar in enumerate(historical):
                b_ts = getattr(bar, "timestamp", None)
                if b_ts and b_ts > current_time:
                    raise DataLeakageDetectedError(
                        f"Look-ahead bias detected: historical candle [{idx}] timestamp "
                        f"{b_ts.isoformat()} is in the future relative to simulation time "
                        f"{current_time.isoformat()}"
                    )

    @staticmethod
    def assert_monotonic_timestamps(timestamps: list[datetime]) -> None:
        """Verify that a sequence of timestamps is strictly non-decreasing."""
        for i in range(1, len(timestamps)):
            if timestamps[i] < timestamps[i - 1]:
                raise DataLeakageDetectedError(
                    f"Timestamp anomaly: candle {i} ({timestamps[i].isoformat()}) "
                    f"is earlier than candle {i-1} ({timestamps[i-1].isoformat()})"
                )
