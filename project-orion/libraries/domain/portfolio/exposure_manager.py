"""Exposure Manager — tracks portfolio exposure across multiple dimensions.

Supports:
- Net Exposure
- Gross Exposure
- Per Symbol Exposure
- Per Currency Exposure
- Maximum Exposure
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from libraries.domain.portfolio.models import PositionSide


@dataclass(frozen=True, slots=True)
class SymbolExposure:
    """Exposure for a single symbol."""

    symbol: str
    long_exposure: Decimal = Decimal(0)
    short_exposure: Decimal = Decimal(0)
    net_exposure: Decimal = Decimal(0)
    gross_exposure: Decimal = Decimal(0)
    position_count: int = 0

    @property
    def is_long(self) -> bool:
        return self.net_exposure > 0

    @property
    def is_short(self) -> bool:
        return self.net_exposure < 0

    @property
    def is_flat(self) -> bool:
        return self.net_exposure == 0


@dataclass(frozen=True, slots=True)
class CurrencyExposure:
    """Exposure for a single currency."""

    currency: str
    long_exposure: Decimal = Decimal(0)
    short_exposure: Decimal = Decimal(0)
    net_exposure: Decimal = Decimal(0)
    gross_exposure: Decimal = Decimal(0)
    position_count: int = 0


@dataclass(frozen=True, slots=True)
class ExposureSnapshot:
    """Immutable snapshot of portfolio exposure."""

    net_exposure: Decimal = Decimal(0)
    gross_exposure: Decimal = Decimal(0)
    long_exposure: Decimal = Decimal(0)
    short_exposure: Decimal = Decimal(0)
    max_exposure: Decimal = Decimal(0)
    symbol_exposures: tuple[SymbolExposure, ...] = ()
    currency_exposures: tuple[CurrencyExposure, ...] = ()
    position_count: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ExposureManager:
    """Tracks and calculates portfolio exposure.

    Thread-safe via asyncio.Lock.
    Supports per-symbol, per-currency, and aggregate exposure.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._symbol_exposures: dict[str, SymbolExposure] = {}
        self._currency_exposures: dict[str, CurrencyExposure] = {}
        self._max_exposure: Decimal = Decimal(0)

    # ─── Exposure Registration ───────────────────────────────

    async def add_exposure(
        self,
        symbol: str,
        side: PositionSide,
        notional_value: Decimal,
        currency: str = "USD",
    ) -> None:
        """Register exposure from a new position.

        Args:
            symbol: Trading symbol.
            side: LONG or SHORT.
            notional_value: Position notional value.
            currency: Position currency.
        """
        async with self._lock:
            self._update_symbol_exposure(symbol, side, notional_value, 1)
            self._update_currency_exposure(currency, side, notional_value, 1)
            self._update_max_exposure()

    async def remove_exposure(
        self,
        symbol: str,
        side: PositionSide,
        notional_value: Decimal,
        currency: str = "USD",
    ) -> None:
        """Remove exposure from a closed/reduced position.

        Args:
            symbol: Trading symbol.
            side: LONG or SHORT.
            notional_value: Notional value to remove.
            currency: Position currency.
        """
        async with self._lock:
            self._update_symbol_exposure(symbol, side, -notional_value, -1)
            self._update_currency_exposure(currency, side, -notional_value, -1)

    async def update_exposure(
        self,
        symbol: str,
        side: PositionSide,
        old_notional: Decimal,
        new_notional: Decimal,
        currency: str = "USD",
    ) -> None:
        """Update exposure when a position changes.

        Args:
            symbol: Trading symbol.
            side: LONG or SHORT.
            old_notional: Previous notional value.
            new_notional: New notional value.
            currency: Position currency.
        """
        async with self._lock:
            delta = new_notional - old_notional
            if delta != 0:
                self._update_symbol_exposure(symbol, side, delta, 0)
                self._update_currency_exposure(currency, side, delta, 0)
                self._update_max_exposure()

    # ─── Query Methods ───────────────────────────────────────

    async def get_net_exposure(self) -> Decimal:
        """Get net exposure (long - short).

        Returns:
            Net exposure value.
        """
        async with self._lock:
            return sum((s.long_exposure - s.short_exposure for s in self._symbol_exposures.values()), Decimal(0))

    async def get_gross_exposure(self) -> Decimal:
        """Get gross exposure (long + short).

        Returns:
            Gross exposure value.
        """
        async with self._lock:
            return sum((s.long_exposure + s.short_exposure for s in self._symbol_exposures.values()), Decimal(0))

    async def get_long_exposure(self) -> Decimal:
        """Get total long exposure.

        Returns:
            Total long exposure.
        """
        async with self._lock:
            return sum((s.long_exposure for s in self._symbol_exposures.values()), Decimal(0))

    async def get_short_exposure(self) -> Decimal:
        """Get total short exposure.

        Returns:
            Total short exposure.
        """
        async with self._lock:
            return sum((s.short_exposure for s in self._symbol_exposures.values()), Decimal(0))

    async def get_symbol_exposure(self, symbol: str) -> SymbolExposure | None:
        """Get exposure for a specific symbol.

        Args:
            symbol: Trading symbol.

        Returns:
            SymbolExposure if found, None otherwise.
        """
        async with self._lock:
            return self._symbol_exposures.get(symbol)

    async def get_currency_exposure(self, currency: str) -> CurrencyExposure | None:
        """Get exposure for a specific currency.

        Args:
            currency: Currency code.

        Returns:
            CurrencyExposure if found, None otherwise.
        """
        async with self._lock:
            return self._currency_exposures.get(currency)

    async def get_all_symbol_exposures(self) -> list[SymbolExposure]:
        """Get exposure for all symbols.

        Returns:
            List of SymbolExposure.
        """
        async with self._lock:
            return list(self._symbol_exposures.values())

    async def get_all_currency_exposures(self) -> list[CurrencyExposure]:
        """Get exposure for all currencies.

        Returns:
            List of CurrencyExposure.
        """
        async with self._lock:
            return list(self._currency_exposures.values())

    async def get_max_exposure(self) -> Decimal:
        """Get maximum exposure across all symbols.

        Returns:
            Maximum symbol exposure.
        """
        async with self._lock:
            return self._max_exposure

    async def get_snapshot(self) -> ExposureSnapshot:
        """Get current exposure snapshot.

        Returns:
            ExposureSnapshot.
        """
        async with self._lock:
            symbols = list(self._symbol_exposures.values())
            currencies = list(self._currency_exposures.values())

            long_exp = sum((s.long_exposure for s in symbols), Decimal(0))
            short_exp = sum((s.short_exposure for s in symbols), Decimal(0))
            gross = long_exp + short_exp
            net = long_exp - short_exp
            pos_count = sum((s.position_count for s in symbols), 0)

            return ExposureSnapshot(
                net_exposure=net,
                gross_exposure=gross,
                long_exposure=long_exp,
                short_exposure=short_exp,
                max_exposure=self._max_exposure,
                symbol_exposures=tuple(symbols),
                currency_exposures=tuple(currencies),
                position_count=pos_count,
            )

    # ─── Internal Helpers ────────────────────────────────────

    def _update_symbol_exposure(
        self,
        symbol: str,
        side: PositionSide,
        delta: Decimal,
        position_delta: int,
    ) -> None:
        """Update symbol exposure with delta."""
        if symbol not in self._symbol_exposures:
            self._symbol_exposures[symbol] = SymbolExposure(symbol=symbol)

        current = self._symbol_exposures[symbol]

        if side == PositionSide.LONG:
            if delta > 0:
                new_long = current.long_exposure + delta
                new_short = current.short_exposure
            else:
                new_long = max(Decimal(0), current.long_exposure + delta)
                new_short = current.short_exposure
        else:  # SHORT
            if delta > 0:
                new_long = current.long_exposure
                new_short = current.short_exposure + delta
            else:
                new_long = current.long_exposure
                new_short = max(Decimal(0), current.short_exposure + delta)

        net = new_long - new_short
        gross = new_long + new_short
        new_count = max(0, current.position_count + position_delta)

        self._symbol_exposures[symbol] = SymbolExposure(
            symbol=symbol,
            long_exposure=new_long,
            short_exposure=new_short,
            net_exposure=net,
            gross_exposure=gross,
            position_count=new_count,
        )

    def _update_currency_exposure(
        self,
        currency: str,
        side: PositionSide,
        delta: Decimal,
        position_delta: int,
    ) -> None:
        """Update currency exposure with delta."""
        if currency not in self._currency_exposures:
            self._currency_exposures[currency] = CurrencyExposure(currency=currency)

        current = self._currency_exposures[currency]

        if side == PositionSide.LONG:
            long_exp = max(Decimal(0), current.long_exposure + delta)
            short_exp = current.short_exposure
        else:
            long_exp = current.long_exposure
            short_exp = max(Decimal(0), current.short_exposure + delta)

        net = long_exp - short_exp
        gross = long_exp + short_exp
        pos_count = max(0, current.position_count + position_delta)

        self._currency_exposures[currency] = CurrencyExposure(
            currency=currency,
            long_exposure=long_exp,
            short_exposure=short_exp,
            net_exposure=net,
            gross_exposure=gross,
            position_count=pos_count,
        )

    def _update_max_exposure(self) -> None:
        """Update the maximum exposure seen."""
        for symbol_exp in self._symbol_exposures.values():
            max_sym = max(symbol_exp.long_exposure, symbol_exp.short_exposure)
            self._max_exposure = max(self._max_exposure, max_sym)

    # ─── Maintenance ─────────────────────────────────────────

    async def clear_exposure(self, symbol: str) -> None:
        """Clear exposure for a specific symbol.

        Args:
            symbol: Symbol to clear.
        """
        async with self._lock:
            self._symbol_exposures.pop(symbol, None)
            self._recalculate_max()

    async def clear_all(self) -> None:
        """Clear all exposure tracking."""
        async with self._lock:
            self._symbol_exposures.clear()
            self._currency_exposures.clear()
            self._max_exposure = Decimal(0)

    def _recalculate_max(self) -> None:
        """Recalculate maximum exposure."""
        self._max_exposure = Decimal(0)
        self._update_max_exposure()
