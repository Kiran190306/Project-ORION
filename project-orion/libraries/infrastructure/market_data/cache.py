"""Redis-backed market data caching layer with TTL invalidation."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.market_data.models import (
    BarType,
    DataQuality,
    MarketDataHealth,
    OHLCV,
    ProviderStatus,
    Quote,
)
from libraries.infrastructure.caching.client import RedisClient

logger = logging.getLogger("orion.market_data.cache")


class MarketDataCache:
    """Redis cache layer for real-time quotes, historical candles, and health state."""

    def __init__(self, redis_client: RedisClient | None = None) -> None:
        self._redis = redis_client

    @property
    def is_available(self) -> bool:
        return self._redis is not None and self._redis.is_connected

    async def get_quote(self, symbol: str) -> Quote | None:
        """Fetch cached Quote snapshot from Redis."""
        if not self.is_available or self._redis is None:
            return None
        key = f"market:quote:{symbol}"
        try:
            raw = await self._redis.get(key)
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
        except Exception as exc:
            logger.warning("Failed to retrieve quote from Redis cache (%s): %s", key, exc)
            return None

    async def set_quote(self, quote: Quote, ttl_seconds: int = 15) -> None:
        """Cache Quote in Redis with TTL expiration."""
        if not self.is_available or self._redis is None:
            return
        key = f"market:quote:{quote.symbol}"
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
            await self._redis.set(key, payload, ex=ttl_seconds)
        except Exception as exc:
            logger.warning("Failed to cache quote in Redis (%s): %s", key, exc)

    async def get_candles(self, symbol: str, timeframe: str) -> list[OHLCV] | None:
        """Fetch cached historical candles from Redis."""
        if not self.is_available or self._redis is None:
            return None
        key = f"market:candles:{symbol}:{timeframe}"
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
        except Exception as exc:
            logger.warning("Failed to retrieve candles from Redis cache (%s): %s", key, exc)
            return None

    async def set_candles(self, symbol: str, timeframe: str, candles: list[OHLCV], ttl_seconds: int = 300) -> None:
        """Cache list of OHLCV candles in Redis with TTL expiration."""
        if not self.is_available or self._redis is None:
            return
        key = f"market:candles:{symbol}:{timeframe}"
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
            await self._redis.set(key, payload, ex=ttl_seconds)
        except Exception as exc:
            logger.warning("Failed to cache candles in Redis (%s): %s", key, exc)

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
        except Exception as exc:
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
            await self._redis.set(key, payload, ex=ttl_seconds)
        except Exception as exc:
            logger.warning("Failed to cache market health in Redis: %s", exc)
