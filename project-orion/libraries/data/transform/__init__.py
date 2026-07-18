"""
Transform Module

Module Description:
This module provides data transformation for data platform.
It handles data aggregation, resampling, and derived data generation.

Implementation Checklist:
- [ ] Tick to OHLC aggregation
- [ ] Multi-timeframe generation
- [ ] Data resampling
- [ ] Derived data calculation
- [ ] Transform registry

Dependency Notes:
- Depends on: shared/ (errors), libraries/data/schemas/
- Used by: pipelines/, datasets/
"""

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Optional

from libraries.data.schemas import OHLC, Tick
from shared.errors import OrionError


class TransformError(OrionError):
    """Transform error."""

    pass


class TickToOHLCAggregator:
    """Aggregator for converting tick data to OHLC candles."""

    def __init__(self, timeframe: str) -> None:
        """Initialize aggregator.

        Args:
            timeframe: Target timeframe (e.g., "M1", "M5", "H1", "D1")
        """
        self.timeframe = timeframe
        self._timeframe_seconds = self._parse_timeframe(timeframe)

    def _parse_timeframe(self, timeframe: str) -> int:
        """Parse timeframe string to seconds."""
        timeframe_map = {
            "M1": 60,
            "M5": 300,
            "M15": 900,
            "M30": 1800,
            "H1": 3600,
            "H4": 14400,
            "D1": 86400,
            "W1": 604800,
            "M2": 2592000,  # Approximate
        }
        return timeframe_map.get(timeframe, 60)

    def aggregate(self, ticks: list[Tick], symbol: str) -> list[OHLC]:
        """Aggregate ticks to OHLC candles."""
        if not ticks:
            return []

        # Sort ticks by timestamp
        sorted_ticks = sorted(ticks, key=lambda t: t.timestamp)

        # Group ticks by timeframe
        candle_groups = self._group_ticks_by_timeframe(sorted_ticks)

        # Aggregate each group
        candles: list[OHLC] = []
        for group_start, group_ticks in candle_groups.items():
            candle = self._aggregate_group(group_ticks, symbol, group_start)
            candles.append(candle)

        return candles

    def _group_ticks_by_timeframe(self, ticks: list[Tick]) -> dict[datetime, list[Tick]]:
        """Group ticks by timeframe intervals."""
        groups: defaultdict[datetime, list[Tick]] = defaultdict(list)

        for tick in ticks:
            # Calculate candle start time
            candle_start = self._calculate_candle_start(tick.timestamp)
            groups[candle_start].append(tick)

        return groups

    def _calculate_candle_start(self, timestamp: datetime) -> datetime:
        """Calculate candle start time for given timestamp."""
        timestamp = timestamp.replace(tzinfo=None)
        seconds = timestamp.timestamp()
        candle_seconds = int(seconds // self._timeframe_seconds) * self._timeframe_seconds
        return datetime.fromtimestamp(candle_seconds)

    def _aggregate_group(self, ticks: list[Tick], symbol: str, candle_start: datetime) -> OHLC:
        """Aggregate a group of ticks into an OHLC candle."""
        if not ticks:
            raise TransformError("Cannot aggregate empty tick group")

        # Calculate OHLC from bid/ask midpoints
        midpoints = [(t.bid_price + t.ask_price) / 2 for t in ticks]
        volumes = [
            (tick.bid_size or Decimal("0")) + (tick.ask_size or Decimal("0")) for tick in ticks
        ]

        open_price = midpoints[0]
        high_price = max(midpoints)
        low_price = min(midpoints)
        close_price = midpoints[-1]
        volume = sum(volumes, Decimal("0"))

        return OHLC(
            candle_id=f"{symbol}_{self.timeframe}_{candle_start.isoformat()}",
            symbol=symbol,
            timeframe=self.timeframe,
            timestamp=candle_start,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            tick_count=len(ticks),
            data_version="1.0.0",
        )


class MultiTimeframeGenerator:
    """Generator for creating multiple timeframes from base data."""

    def __init__(self) -> None:
        """Initialize multi-timeframe generator."""
        self.timeframe_hierarchy = [
            "M1",
            "M5",
            "M15",
            "M30",
            "H1",
            "H4",
            "D1",
            "W1",
            "M1",
        ]

    def generate_timeframes(
        self,
        ticks: list[Tick],
        symbol: str,
        target_timeframes: Optional[list[str]] = None,
    ) -> dict[str, list[OHLC]]:
        """Generate OHLC data for multiple timeframes."""
        if target_timeframes is None:
            target_timeframes = self.timeframe_hierarchy

        result: dict[str, list[OHLC]] = {}

        # Generate M1 from ticks
        m1_aggregator = TickToOHLCAggregator("M1")
        m1_candles = m1_aggregator.aggregate(ticks, symbol)
        result["M1"] = m1_candles

        # Generate higher timeframes from M1
        for timeframe in target_timeframes[1:]:
            if timeframe in result:
                continue

            # Find parent timeframe
            parent_tf = self._find_parent_timeframe(timeframe)
            if parent_tf and parent_tf in result:
                candles = self._resample_ohlc(result[parent_tf], timeframe, symbol)
                result[timeframe] = candles

        return result

    def _find_parent_timeframe(self, timeframe: str) -> Optional[str]:
        """Find parent timeframe for given timeframe."""
        idx = self.timeframe_hierarchy.index(timeframe)
        if idx > 0:
            return self.timeframe_hierarchy[idx - 1]
        return None

    def _resample_ohlc(
        self, ohlc_data: list[OHLC], target_timeframe: str, symbol: str
    ) -> list[OHLC]:
        """Resample OHLC data to target timeframe."""
        # TODO: Implement OHLC resampling logic
        # For now, return empty list
        return []


class DataTransformer:
    """High-level data transformer."""

    def __init__(self) -> None:
        """Initialize data transformer."""
        self.ohlc_aggregator = TickToOHLCAggregator("M1")
        self.multi_tf_generator = MultiTimeframeGenerator()

    def ticks_to_ohlc(self, ticks: list[Tick], symbol: str, timeframe: str = "M1") -> list[OHLC]:
        """Convert ticks to OHLC candles."""
        aggregator = TickToOHLCAggregator(timeframe)
        return aggregator.aggregate(ticks, symbol)

    def generate_multi_timeframe(
        self, ticks: list[Tick], symbol: str, timeframes: Optional[list[str]] = None
    ) -> dict[str, list[OHLC]]:
        """Generate multiple timeframes from ticks."""
        return self.multi_tf_generator.generate_timeframes(ticks, symbol, timeframes)
