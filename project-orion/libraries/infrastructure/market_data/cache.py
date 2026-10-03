"""Redis-backed market data caching layer with TTL invalidation."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from decimal import Decimal

from libraries.domain.market_data.models import (
    OHLCV,
    BarType,
    DataQuality,
    MarketDataHealth,
    ProviderStatus,
    Quote,
)
from libraries.infrastructure.caching.client import RedisClient
from libraries.infrastructure.caching.exceptions import RedisError

logger = logging.getLogger("orion.market_data.cache")

CACHE_EXCEPTIONS = (
    RedisError,
    ConnectionError,
    TimeoutError,
    OSError,
    ValueError,
    KeyError,
    json.JSONDecodeError,
)


class MarketDataCache:
    """Redis cache layer for real-time quotes, historical candles, and health state."""

    def __init__(self, redis_client: RedisClient | None = None) -> None:
        self._redis = redis_client

    @property
    def is_available(self) -> bool:
        return self._redis is not None and self._redis.is_connected

    @staticmethod
    def candle_cache_key(symbol: str, timeframe: str, provider: str = "default") -> str:
        """Generate provider-isolated canonical Redis key for historical candles.

        Normalizes symbol to canonical uppercase format (e.g. 'EUR/USD') and
        timeframe to canonical BarType member name (e.g. 'H1', 'MN1').
        """
        from libraries.domain.market_data.normalization import (
            normalize_symbol,
            normalize_timeframe,
        )

        canonical_sym = normalize_symbol(symbol)
        canonical_tf = normalize_timeframe(timeframe).name
        prov = (provider or "default").strip().lower()
        return f"market:candles:{prov}:{canonical_sym}:{canonical_tf}"

    @staticmethod
    def quote_cache_key(symbol: str, provider: str = "default") -> str:
        """Generate provider-isolated canonical Redis key for real-time quotes."""
        from libraries.domain.market_data.normalization import normalize_symbol

        canonical_sym = normalize_symbol(symbol)
        prov = (provider or "default").strip().lower()
        return f"market:quote:{prov}:{canonical_sym}"

    async def get_quote(self, symbol: str, provider: str | None = None) -> Quote | None:
        """Fetch cached Quote snapshot from Redis with optional provider isolation."""
        if not self.is_available or self._redis is None:
            return None
        from libraries.domain.market_data.normalization import normalize_symbol

        canonical = normalize_symbol(symbol)
        key = self.quote_cache_key(canonical, provider) if provider else f"market:quote:{canonical}"
        try:
            raw = await self._redis.get(key)
            if not raw and provider is None:
                # Fallback to default-isolated key
                raw = await self._redis.get(self.quote_cache_key(canonical, "default"))
            if not raw:
                return None
            data = json.loads(raw)
            return Quote(
                symbol=data["symbol"],
                bid=Decimal(data["bid"]),
                ask=Decimal(data["ask"]),
                timestamp=datetime.fromisoformat(data["timestamp"]),
                bid_volume=Decimal(data["bid_volume"]) if data.get("bid_volume") else None,
                ask_volume=Decimal(data["ask_volume"]) if data.get("ask_volume") else None,
                provider=data.get("provider", ""),
                metadata=data.get("metadata", {}),
            )
        except CACHE_EXCEPTIONS as exc:
            logger.warning("Failed to retrieve quote from Redis cache (%s): %s", key, exc)
            return None

    async def set_quote(self, quote: Quote, provider: str | None = None, ttl_seconds: int = 15) -> None:
        """Cache Quote in Redis with TTL expiration and provider isolation."""
        if not self.is_available or self._redis is None:
            return
        from libraries.domain.market_data.normalization import normalize_symbol

        canonical = normalize_symbol(quote.symbol)
        prov = provider or getattr(quote, "provider", None) or "default"
        key = self.quote_cache_key(canonical, prov)
        try:
            payload = json.dumps({
                "symbol": quote.symbol,
                "bid": str(quote.bid),
                "ask": str(quote.ask),
                "timestamp": quote.timestamp.isoformat(),
                "bid_volume": str(quote.bid_volume) if quote.bid_volume else None,
                "ask_volume": str(quote.ask_volume) if quote.ask_volume else None,
                "provider": quote.provider,
                "metadata": quote.metadata,
            })
            await self._redis.set(key, payload, ttl_seconds=ttl_seconds)
        except CACHE_EXCEPTIONS as exc:
            logger.warning("Failed to cache quote in Redis (%s): %s", key, exc)

    async def delete_quote(self, symbol: str, provider: str = "default") -> bool:
        """Delete cached quote for the specified provider and symbol."""
        if not self.is_available or self._redis is None:
            return False
        key = self.quote_cache_key(symbol, provider)
        try:
            res = await self._redis.delete(key)
            return bool(res)
        except CACHE_EXCEPTIONS as exc:
            logger.warning("Failed to delete quote from Redis cache (%s): %s", key, exc)
            return False

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        provider: str = "default",
    ) -> list[OHLCV] | None:
        """Fetch cached historical candles from Redis with provider isolation."""
        if not self.is_available or self._redis is None:
            return None
        key = self.candle_cache_key(symbol, timeframe, provider)
        try:
            raw = await self._redis.get(key)
            if not raw:
                return None
            items = json.loads(raw)
            return [
                OHLCV(
                    symbol=i["symbol"],
                    timestamp=datetime.fromisoformat(i["timestamp"]),
                    open=Decimal(i["open"]),
                    high=Decimal(i["high"]),
                    low=Decimal(i["low"]),
                    close=Decimal(i["close"]),
                    volume=Decimal(i["volume"]),
                    bar_type=BarType(i["bar_type"]),
                    metadata=i.get("metadata", {}),
                )
                for i in items
            ]
        except CACHE_EXCEPTIONS as exc:
            logger.warning("Failed to retrieve candles from Redis cache (%s): %s", key, exc)
            return None

    async def set_candles(
        self,
        symbol: str,
        timeframe: str,
        candles: list[OHLCV],
        provider: str = "default",
        ttl_seconds: int = 300,
    ) -> None:
        """Cache list of OHLCV candles in Redis with TTL expiration and provider isolation."""
        if not self.is_available or self._redis is None:
            return
        key = self.candle_cache_key(symbol, timeframe, provider)
        try:
            payload = json.dumps([
                {
                    "symbol": c.symbol,
                    "timestamp": c.timestamp.isoformat(),
                    "open": str(c.open),
                    "high": str(c.high),
                    "low": str(c.low),
                    "close": str(c.close),
                    "volume": str(c.volume),
                    "bar_type": c.bar_type.value,
                    "metadata": c.metadata,
                }
                for c in candles
            ])
            await self._redis.set(key, payload, ttl_seconds=ttl_seconds)
        except CACHE_EXCEPTIONS as exc:
            logger.warning("Failed to cache candles in Redis (%s): %s", key, exc)

    async def delete_candles(
        self,
        symbol: str,
        timeframe: str,
        provider: str = "default",
    ) -> bool:
        """Delete cached candles for the specified provider, symbol, and timeframe."""
        if not self.is_available or self._redis is None:
            return False
        key = self.candle_cache_key(symbol, timeframe, provider)
        try:
            res = await self._redis.delete(key)
            return bool(res)
        except CACHE_EXCEPTIONS as exc:
            logger.warning("Failed to delete candles from Redis cache (%s): %s", key, exc)
            return False

    async def get_health(self) -> MarketDataHealth | None:
        """Fetch cached MarketDataHealth state."""
        if not self.is_available or self._redis is None:
            return None
        key = "market:health"
        try:
            raw = await self._redis.get(key)
            if not raw:
                return None
            data = json.loads(raw)
            return MarketDataHealth(
                provider=data["provider"],
                status=ProviderStatus(data["status"]),
                data_quality=DataQuality(data["data_quality"]),
                last_update_utc=datetime.fromisoformat(data["last_update_utc"]),
                symbols_active=tuple(data.get("symbols_active", ())),
                latency_ms=float(data.get("latency_ms", 0.0)),
                stale_count=int(data.get("stale_count", 0)),
                is_paper_feed=bool(data.get("is_paper_feed", True)),
                metadata=data.get("metadata", {}),
            )
        except CACHE_EXCEPTIONS as exc:
            logger.warning("Failed to retrieve market health from Redis cache: %s", exc)
            return None

    async def set_health(self, health: MarketDataHealth, ttl_seconds: int = 30) -> None:
        """Cache MarketDataHealth in Redis with TTL expiration."""
        if not self.is_available or self._redis is None:
            return
        key = "market:health"
        try:
            payload = json.dumps({
                "provider": health.provider,
                "status": health.status.value,
                "data_quality": health.data_quality.value,
                "last_update_utc": health.last_update_utc.isoformat(),
                "symbols_active": list(health.symbols_active),
                "latency_ms": health.latency_ms,
                "stale_count": health.stale_count,
                "is_paper_feed": health.is_paper_feed,
                "metadata": health.metadata,
            })
            await self._redis.set(key, payload, ttl_seconds=ttl_seconds)
        except CACHE_EXCEPTIONS as exc:
            logger.warning("Failed to cache market health in Redis: %s", exc)
