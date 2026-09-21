"""Unit tests for MarketDataCache."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
import pytest

from libraries.domain.market_data.models import (
    BarType,
    DataQuality,
    MarketDataHealth,
    OHLCV,
    ProviderStatus,
    Quote,
)
from libraries.infrastructure.market_data.cache import MarketDataCache


@pytest.mark.asyncio
class TestMarketDataCache:
    """Test MarketDataCache serialization, retrieval, and graceful failure handling."""

    async def test_get_quote_none_when_disconnected(self) -> None:
        cache = MarketDataCache(redis_client=None)
        assert cache.is_available is False
        assert await cache.get_quote("EUR/USD") is None

    async def test_set_and_get_quote(self) -> None:
        store: dict[str, str] = {}
        mock_redis = MagicMock()
        mock_redis.is_connected = True

        async def _set(key: str, val: str, ex: int | None = None) -> None:
            store[key] = val

        async def _get(key: str) -> str | None:
            return store.get(key)

        mock_redis.set = AsyncMock(side_effect=_set)
        mock_redis.get = AsyncMock(side_effect=_get)

        cache = MarketDataCache(redis_client=mock_redis)
        now = datetime.now(timezone.utc)
        quote = Quote(
            symbol="EUR/USD",
            bid=Decimal("1.08500"),
            ask=Decimal("1.08510"),
            timestamp=now,
            provider="test",
        )

        await cache.set_quote(quote, ttl_seconds=15)
        mock_redis.set.assert_called_once()

        cached_quote = await cache.get_quote("EUR/USD")
        assert cached_quote is not None
        assert cached_quote.symbol == "EUR/USD"
        assert cached_quote.bid == Decimal("1.08500")
        assert cached_quote.ask == Decimal("1.08510")

    async def test_set_and_get_health(self) -> None:
        store: dict[str, str] = {}
        mock_redis = MagicMock()
        mock_redis.is_connected = True

        async def _set(key: str, val: str, ex: int | None = None) -> None:
            store[key] = val

        async def _get(key: str) -> str | None:
            return store.get(key)

        mock_redis.set = AsyncMock(side_effect=_set)
        mock_redis.get = AsyncMock(side_effect=_get)

        cache = MarketDataCache(redis_client=mock_redis)
        now = datetime.now(timezone.utc)
        health = MarketDataHealth(
            provider="mock",
            status=ProviderStatus.HEALTHY,
            data_quality=DataQuality.EXCELLENT,
            last_update_utc=now,
            symbols_active=("EUR/USD", "GBP/USD"),
            latency_ms=1.5,
        )

        await cache.set_health(health)
        retrieved = await cache.get_health()
        assert retrieved is not None
        assert retrieved.provider == "mock"
        assert retrieved.status == ProviderStatus.HEALTHY
        assert retrieved.data_quality == DataQuality.EXCELLENT
        assert "EUR/USD" in retrieved.symbols_active
