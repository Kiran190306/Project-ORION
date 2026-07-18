"""Canonical normalization for provider market-data records."""

from __future__ import annotations

from datetime import timezone
from decimal import ROUND_HALF_EVEN, Decimal

from .models import RawTick, Symbol, Tick


class NormalizationEngine:
    """Normalizes provider formats into immutable canonical market models."""

    @staticmethod
    def normalize_symbol(value: str) -> str:
        """Normalize common provider symbol separators and casing.

        Args:
            value: Provider symbol representation.

        Returns:
            Normalized symbol key suitable for registry lookup.
        """
        return value.strip().upper().replace("-", "/").replace("_", "/").replace(" ", "")

    def normalize_tick(self, raw_tick: RawTick, symbol: Symbol) -> Tick:
        """Create a canonical tick using the registered instrument precision."""
        return Tick(
            symbol=symbol.code,
            timestamp=raw_tick.timestamp.astimezone(timezone.utc),
            bid=self._quantize(raw_tick.bid, symbol.tick_size),
            ask=self._quantize(raw_tick.ask, symbol.tick_size),
            source=raw_tick.source.strip(),
            bid_size=raw_tick.bid_size,
            ask_size=raw_tick.ask_size,
            sequence=raw_tick.sequence,
        )

    @staticmethod
    def _quantize(value: Decimal, tick_size: Decimal) -> Decimal:
        """Round a price to its nearest tradable increment."""
        units = (value / tick_size).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)
        return units * tick_size
