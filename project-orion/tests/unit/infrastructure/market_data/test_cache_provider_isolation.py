"""Unit tests for Phase 4.7 MarketDataCache provider isolation and canonical key generation."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from apps.trading_engine.src.services.market_data_service import MarketDataService

from libraries.domain.market_data.interfaces import MarketDataProviderPort
from libraries.domain.market_data.models import OHLCV, BarType
from libraries.infrastructure.market_data.cache import MarketDataCache


def test_candle_cache_key_generation_and_provider_isolation() -> None:
    """Verify cache keys isolate providers and handle canonical normalization."""
    # 1. Mock EUR/USD H1 vs TwelveData EUR/USD H1
    key_mock = MarketDataCache.candle_cache_key("EUR/USD", "H1", provider="mock")
    key_td = MarketDataCache.candle_cache_key("EUR/USD", "H1", provider="twelvedata")
    assert key_mock == "market:candles:mock:EUR/USD:H1"
    assert key_td == "market:candles:twelvedata:EUR/USD:H1"
    assert key_mock != key_td

    # 2. EUR/USD H1 does not collide with EUR/USD H4
    key_h4 = MarketDataCache.candle_cache_key("EUR/USD", "H4", provider="mock")
    assert key_h4 == "market:candles:mock:EUR/USD:H4"
    assert key_mock != key_h4

    # 3. EUR/USD H1 does not collide with GBP/USD H1
    key_gbp = MarketDataCache.candle_cache_key("GBP/USD", "H1", provider="mock")
    assert key_gbp == "market:candles:mock:GBP/USD:H1"
    assert key_mock != key_gbp

    # 4. EUR/USD H1 does not collide with XAU/USD H1
    key_gold = MarketDataCache.candle_cache_key("XAU/USD", "H1", provider="mock")
    assert key_gold == "market:candles:mock:XAU/USD:H1"
    assert key_mock != key_gold

    # 5. Canonical aliases produce the same logical cache key
    key_raw1 = MarketDataCache.candle_cache_key("EURUSD", "1h", provider="mock")
    key_raw2 = MarketDataCache.candle_cache_key("eur/usd", "60min", provider="mock")
    assert key_raw1 == key_mock
    assert key_raw2 == key_mock

    # 6. Commodity & Monthly canonical alias mapping
    key_gold_alias = MarketDataCache.candle_cache_key("xauusd", "monthly", provider="mock")
    assert key_gold_alias == "market:candles:mock:XAU/USD:MN1"


def test_quote_cache_key_generation_and_provider_isolation() -> None:
    """Verify quote cache keys isolate providers and canonicalize symbols."""
    key_mock = MarketDataCache.quote_cache_key("eurusd", provider="mock")
    key_td = MarketDataCache.quote_cache_key("EUR/USD", provider="twelvedata")

    assert key_mock == "market:quote:mock:EUR/USD"
    assert key_td == "market:quote:twelvedata:EUR/USD"
    assert key_mock != key_td


@pytest.mark.asyncio
async def test_cache_set_and_get_candles_with_provider_isolation() -> None:
    """Ensure candles cached for Provider A cannot be retrieved by Provider B."""
    store: dict[str, str] = {}
    mock_redis = MagicMock()
    mock_redis.is_connected = True

    async def _set(key: str, val: str, ttl_seconds: int | None = None) -> None:
        store[key] = val

    async def _get(key: str) -> str | None:
        return store.get(key)

    async def _delete(key: str) -> int:
        return 1 if store.pop(key, None) is not None else 0

    mock_redis.set = AsyncMock(side_effect=_set)
    mock_redis.get = AsyncMock(side_effect=_get)
    mock_redis.delete = AsyncMock(side_effect=_delete)

    cache = MarketDataCache(redis_client=mock_redis)

    candles_mock = [
        OHLCV(
            symbol="EUR/USD",
            timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
            open=Decimal("1.0800"),
            high=Decimal("1.0850"),
            low=Decimal("1.0790"),
            close=Decimal("1.0820"),
            volume=Decimal(1000),
            bar_type=BarType.H1,
        )
    ]

    # Store candles for provider 'mock'
    await cache.set_candles("EUR/USD", "H1", candles_mock, provider="mock", ttl_seconds=300)
    mock_redis.set.assert_called_with("market:candles:mock:EUR/USD:H1", mock_redis.set.call_args[0][1], ttl_seconds=300)

    # Provider 'mock' should HIT cache
    cached_mock = await cache.get_candles("EUR/USD", "H1", provider="mock")
    assert cached_mock is not None
    assert len(cached_mock) == 1
    assert cached_mock[0].close == Decimal("1.0820")

    # Provider 'twelvedata' should MISS cache
    cached_td = await cache.get_candles("EUR/USD", "H1", provider="twelvedata")
    assert cached_td is None

    # Invalidation works
    deleted = await cache.delete_candles("EUR/USD", "H1", provider="mock")
    assert deleted is True
    assert await cache.get_candles("EUR/USD", "H1", provider="mock") is None


@pytest.mark.asyncio
async def test_provider_switch_stale_data_prevention_scenario() -> None:
    """Verify B8: Provider B must never receive Provider A's cached data."""
    store: dict[str, str] = {}
    mock_redis = MagicMock()
    mock_redis.is_connected = True

    async def _set(key: str, val: str, ttl_seconds: int | None = None) -> None:
        store[key] = val

    async def _get(key: str) -> str | None:
        return store.get(key)

    mock_redis.set = AsyncMock(side_effect=_set)
    mock_redis.get = AsyncMock(side_effect=_get)

    cache = MarketDataCache(redis_client=mock_redis)

    # Provider A (mock) returns Dataset A
    provider_a = MagicMock(spec=MarketDataProviderPort)
    provider_a.provider_name = "mock"
    dataset_a = [
        OHLCV(
            symbol="EUR/USD",
            timestamp=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            open=Decimal("1.0800"),
            high=Decimal("1.0820"),
            low=Decimal("1.0790"),
            close=Decimal("1.0810"),
            volume=Decimal(500),
            bar_type=BarType.H1,
        )
    ]
    provider_a.get_candles = AsyncMock(return_value=dataset_a)

    # Provider B (twelvedata) returns Dataset B
    provider_b = MagicMock(spec=MarketDataProviderPort)
    provider_b.provider_name = "twelvedata"
    dataset_b = [
        OHLCV(
            symbol="EUR/USD",
            timestamp=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            open=Decimal("1.0900"),
            high=Decimal("1.0950"),
            low=Decimal("1.0880"),
            close=Decimal("1.0920"),
            volume=Decimal(2500),
            bar_type=BarType.H1,
        )
    ]
    provider_b.get_candles = AsyncMock(return_value=dataset_b)

    service_a = MarketDataService(provider=provider_a, cache=cache)
    service_b = MarketDataService(provider=provider_b, cache=cache)

    # 1. Service A queries EUR/USD H1 -> fetches from provider_a, caches under mock
    res_a = await service_a.get_candles("eurusd", "1h", limit=1)
    assert len(res_a) == 1
    assert res_a[0].close == Decimal("1.0810")
    provider_a.get_candles.assert_called_once()

    # 2. Service B queries EUR/USD H1 -> must NOT return dataset_a from cache!
    res_b = await service_b.get_candles("EUR/USD", "H1", limit=1)
    assert len(res_b) == 1
    assert res_b[0].close == Decimal("1.0920")
    provider_b.get_candles.assert_called_once()

    # 3. Subsequent query to Service A hits Service A's cache (provider_a not called again)
    res_a_second = await service_a.get_candles("EUR/USD", "H1", limit=1)
    assert res_a_second[0].close == Decimal("1.0810")
    assert provider_a.get_candles.call_count == 1  # Cache HIT

    # 4. Subsequent query to Service B hits Service B's cache (provider_b not called again)
    res_b_second = await service_b.get_candles("EUR/USD", "H1", limit=1)
    assert res_b_second[0].close == Decimal("1.0920")
    assert provider_b.get_candles.call_count == 1  # Cache HIT


@pytest.mark.asyncio
async def test_historical_explicit_range_bypasses_cache() -> None:
    """Historical requests with explicit start/end dates must bypass cache."""
    cache = MagicMock(spec=MarketDataCache)
    cache.get_candles = AsyncMock()
    cache.set_candles = AsyncMock()

    provider = MagicMock(spec=MarketDataProviderPort)
    provider.provider_name = "mock"
    sample_candles = [
        OHLCV(
            symbol="EUR/USD",
            timestamp=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            open=Decimal("1.0800"),
            high=Decimal("1.0820"),
            low=Decimal("1.0790"),
            close=Decimal("1.0810"),
            volume=Decimal(500),
            bar_type=BarType.H1,
        )
    ]
    provider.get_candles = AsyncMock(return_value=sample_candles)

    service = MarketDataService(provider=provider, cache=cache)

    start_dt = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    end_dt = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)

    candles = await service.get_candles("EUR/USD", "H1", start=start_dt, end=end_dt)
    assert len(candles) == 1

    # Neither get_candles nor set_candles on cache should have been called
    cache.get_candles.assert_not_called()
    cache.set_candles.assert_not_called()


@pytest.mark.asyncio
async def test_legacy_cache_key_not_consumed_fallback_deprecated() -> None:
    """TD-005 Regression Test: Legacy key format market:candles:{symbol}:{timeframe}
    must never be read or consumed, ensuring strict provider isolation."""
    store: dict[str, str] = {}
    mock_redis = MagicMock()
    mock_redis.is_connected = True

    async def _set(key: str, val: str, ttl_seconds: int | None = None) -> None:
        store[key] = val

    async def _get(key: str) -> str | None:
        return store.get(key)

    mock_redis.set = AsyncMock(side_effect=_set)
    mock_redis.get = AsyncMock(side_effect=_get)

    cache = MarketDataCache(redis_client=mock_redis)

    # 1. Pre-seed ONLY the legacy un-isolated key in the redis store
    legacy_key = "market:candles:EUR/USD:H1"
    store[legacy_key] = (
        '[{"symbol": "EUR/USD", "timestamp": "2026-01-01T12:00:00+00:00", '
        '"open": "1.0800", "high": "1.0850", "low": "1.0790", "close": "1.0820", '
        '"volume": "1000", "bar_type": "1h", "metadata": {}}]'
    )

    # 2. Reading with provider="default" must NOT fall back to legacy key!
    res = await cache.get_candles("EUR/USD", "H1", provider="default")
    assert res is None  # Legacy key is ignored

    # 3. Canonical provider key works when written
    sample_candle = [
        OHLCV(
            symbol="EUR/USD",
            timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
            open=Decimal("1.0800"),
            high=Decimal("1.0850"),
            low=Decimal("1.0790"),
            close=Decimal("1.0820"),
            volume=Decimal(1000),
            bar_type=BarType.H1,
        )
    ]
    await cache.set_candles("EUR/USD", "H1", sample_candle, provider="default")
    assert "market:candles:default:EUR/USD:H1" in store

    # 4. Now reading with provider="default" hits the canonical provider key
    res_canonical = await cache.get_candles("EUR/USD", "H1", provider="default")
    assert res_canonical is not None
    assert len(res_canonical) == 1
    assert res_canonical[0].close == Decimal("1.0820")
