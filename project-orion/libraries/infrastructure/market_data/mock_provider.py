"""Deterministic mock market data provider for offline development and testing."""

from __future__ import annotations

import calendar
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.market_data.exceptions import (
    ProviderConnectionError,
    RateLimitExceededError,
    SymbolNotFoundError,
)
from libraries.domain.market_data.models import (
    OHLCV,
    BarType,
    Quote,
)
from libraries.domain.market_data.normalization import (
    normalize_symbol,
    normalize_timeframe,
)

_MOCK_BASE_PRICES: dict[str, Decimal] = {
    "EUR/USD": Decimal("1.08500"),
    "GBP/USD": Decimal("1.26300"),
    "USD/JPY": Decimal("149.500"),
    "USD/CHF": Decimal("0.89500"),
    "AUD/USD": Decimal("0.64200"),
    "USD/CAD": Decimal("1.36000"),
    "NZD/USD": Decimal("0.59500"),
    "XAU/USD": Decimal("2350.00"),
}

_MOCK_SPREAD_PIPS: dict[str, Decimal] = {
    "EUR/USD": Decimal("0.00010"),
    "GBP/USD": Decimal("0.00015"),
    "USD/JPY": Decimal("0.015"),
    "USD/CHF": Decimal("0.00015"),
    "AUD/USD": Decimal("0.00015"),
    "USD/CAD": Decimal("0.00020"),
    "NZD/USD": Decimal("0.00020"),
    "XAU/USD": Decimal("0.30"),
}

_STEP_MAP: dict[BarType, timedelta] = {
    BarType.M1: timedelta(minutes=1),
    BarType.M5: timedelta(minutes=5),
    BarType.M15: timedelta(minutes=15),
    BarType.M30: timedelta(minutes=30),
    BarType.H1: timedelta(hours=1),
    BarType.H4: timedelta(hours=4),
    BarType.D1: timedelta(days=1),
    BarType.W1: timedelta(weeks=1),
}


def _shift_months(dt: datetime, months_offset: int) -> datetime:
    """Shift datetime by integer number of calendar months, preserving end-of-month semantics."""
    is_eom = dt.day == calendar.monthrange(dt.year, dt.month)[1]
    total_months = dt.year * 12 + (dt.month - 1) + months_offset
    new_year = total_months // 12
    new_month = (total_months % 12) + 1
    max_days = calendar.monthrange(new_year, new_month)[1]
    new_day = max_days if is_eom else min(dt.day, max_days)
    return dt.replace(year=new_year, month=new_month, day=new_day)


class MockMarketDataProvider:
    """Offline, deterministic market data provider implementation of MarketDataProviderPort."""

    def __init__(
        self,
        base_prices: dict[str, Decimal] | None = None,
        spread_pips: dict[str, Decimal] | None = None,
        latency_ms: float = 2.0,
    ) -> None:
        self._provider_name = "mock"
        self._base_prices = dict(base_prices or _MOCK_BASE_PRICES)
        self._spread_pips = dict(spread_pips or _MOCK_SPREAD_PIPS)
        self._latency_ms = latency_ms
        self._connected = True

        # Fault injection toggles for testing
        self.simulate_timeout = False
        self.simulate_disconnect = False
        self.simulate_stale = False
        self.simulate_rate_limit = False
        self.simulate_error = False
        self.custom_quotes: dict[str, Quote] = {}

    @property
    def provider_name(self) -> str:
        return self._provider_name

    async def is_connected(self) -> bool:
        return self._connected and not self.simulate_disconnect

    async def health_check(self) -> dict[str, Any]:
        connected = await self.is_connected()
        return {
            "status": "healthy" if connected else "disconnected",
            "provider": self._provider_name,
            "connected": connected,
            "latency_ms": self._latency_ms,
            "symbols_supported": list(self._base_prices.keys()),
        }

    async def get_quote(self, symbol: str) -> Quote:
        """Fetch latest deterministic quote for canonical symbol."""
        if self.simulate_timeout:
            raise TimeoutError("Mock provider request timed out")
        if self.simulate_disconnect or not self._connected:
            raise ProviderConnectionError("Mock provider is disconnected")
        if self.simulate_rate_limit:
            raise RateLimitExceededError("Mock provider rate limit exceeded (429)")
        if self.simulate_error:
            raise RuntimeError("Mock provider simulated internal error")

        canonical = normalize_symbol(symbol)

        if canonical in self.custom_quotes:
            return self.custom_quotes[canonical]

        if canonical not in self._base_prices:
            raise SymbolNotFoundError(f"Symbol '{symbol}' not supported by mock provider")

        mid = self._base_prices[canonical]
        half_spread = self._spread_pips.get(canonical, Decimal("0.00010")) / Decimal(2)
        bid = mid - half_spread
        ask = mid + half_spread

        ts = datetime.now(timezone.utc)
        if self.simulate_stale:
            ts = ts - timedelta(minutes=15)

        return Quote(
            symbol=canonical,
            bid=bid,
            ask=ask,
            timestamp=ts,
            provider=self._provider_name,
            metadata={"is_mock": True, "source": "deterministic_test_engine"},
        )

    async def get_candles(
        self,
        symbol: str,
        timeframe: BarType | str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> list[OHLCV]:
        """Generate deterministic historical OHLCV bars satisfying all invariants."""
        if self.simulate_timeout:
            raise TimeoutError("Mock provider request timed out")
        if self.simulate_disconnect or not self._connected:
            raise ProviderConnectionError("Mock provider is disconnected")
        if self.simulate_rate_limit:
            raise RateLimitExceededError("Mock provider rate limit exceeded")
        if self.simulate_error:
            raise RuntimeError("Mock provider simulated error")

        canonical = normalize_symbol(symbol)
        if canonical not in self._base_prices:
            raise SymbolNotFoundError(f"Symbol '{symbol}' not supported")

        canonical_bt = normalize_timeframe(timeframe)

        limit = max(1, min(limit, 1000))
        ref_time = end or datetime.now(timezone.utc)
        if ref_time.tzinfo is None:
            ref_time = ref_time.replace(tzinfo=timezone.utc)

        mid = self._base_prices[canonical]
        candles: list[OHLCV] = []

        for i in range(limit):
            if canonical_bt == BarType.MN1:
                candle_time = _shift_months(ref_time, -(limit - i))
            else:
                step = _STEP_MAP[canonical_bt]
                candle_time = ref_time - (step * (limit - i))

            offset = Decimal(str((i % 10 - 5) * 0.0002))
            open_p = mid + offset
            close_p = open_p + Decimal("0.0001")
            high_p = max(open_p, close_p) + Decimal("0.0003")
            low_p = min(open_p, close_p) - Decimal("0.0003")
            vol = Decimal(str(500 + (i * 10)))

            candles.append(
                OHLCV(
                    symbol=canonical,
                    timestamp=candle_time,
                    open=open_p,
                    high=high_p,
                    low=low_p,
                    close=close_p,
                    volume=vol,
                    bar_type=canonical_bt,
                    metadata={"is_mock": True},
                )
            )

        if start is not None:
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            candles = [c for c in candles if c.timestamp >= start]

        return candles
