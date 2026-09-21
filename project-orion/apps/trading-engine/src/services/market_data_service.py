"""Application service orchestrating market data ingestion, quality validation, caching, and paper feeding."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.market_data.exceptions import (
    DataUnavailableError,
    InvalidQuoteError,
    MarketDataError,
    SymbolNotFoundError,
)
from libraries.domain.market_data.interfaces import MarketDataProviderPort
from libraries.domain.market_data.models import (
    BarType,
    DataQuality,
    Instrument,
    MarketDataHealth,
    OHLCV,
    ProviderStatus,
    Quote,
)
from libraries.domain.market_data.normalization import (
    canonical_instruments,
    normalize_symbol,
    normalize_timeframe,
)
from libraries.domain.market_data.quality_engine import MarketDataQualityEngine
from libraries.infrastructure.execution.paper_execution import PaperExecutionAdapter
from libraries.infrastructure.market_data.cache import MarketDataCache
from libraries.observability.metrics import MetricsRegistry

logger = logging.getLogger("trading_engine.services.market_data")


class MarketDataService:
    """High-integrity application service for consuming institutional market data.

    Orchestrates:
    - Provider ingestion (Twelve Data, Mock, etc.)
    - Normalization into canonical symbols and timeframes
    - Quality governance (OHLC relationships, spread sanity, deduplication, staleness)
    - Redis caching with TTL
    - Automatic feeding of simulated mid-prices into PaperExecutionAdapter
    """

    def __init__(
        self,
        provider: MarketDataProviderPort,
        quality_engine: MarketDataQualityEngine | None = None,
        cache: MarketDataCache | None = None,
        paper_adapter: PaperExecutionAdapter | None = None,
        metrics: MetricsRegistry | None = None,
    ) -> None:
        self._provider = provider
        self._quality = quality_engine or MarketDataQualityEngine()
        self._cache = cache or MarketDataCache()
        self._paper_adapter = paper_adapter
        self._metrics = metrics
        self._stale_count = 0

    @property
    def provider(self) -> MarketDataProviderPort:
        return self._provider

    async def get_instruments(self) -> list[Instrument]:
        """Return all supported canonical financial instruments."""
        return list(canonical_instruments().values())

    async def get_quote(self, symbol: str) -> Quote:
        """Fetch latest validated quote for symbol using cache-aside pattern."""
        canonical = normalize_symbol(symbol)

        # 1. Try cache first
        cached = await self._cache.get_quote(canonical)
        if cached is not None:
            if self._metrics:
                self._metrics.inc("market_data_cache_hits_total")
            return cached

        if self._metrics:
            self._metrics.inc("market_data_cache_misses_total")

        # 2. Fetch from provider
        try:
            quote = await self._provider.get_quote(canonical)
        except Exception as exc:
            if self._metrics:
                self._metrics.inc("market_data_provider_errors_total")
            logger.error("Provider failed to fetch quote for %s: %s", canonical, exc)
            raise

        # 3. Quality governance check
        assessment = await self._quality.evaluate_quote(quote)
        if not assessment.is_valid:
            if self._metrics:
                self._metrics.inc("market_data_invalid_quotes_total")
            raise InvalidQuoteError(f"Market quote rejected for {canonical}: {'; '.join(assessment.issues)}")

        if assessment.is_stale:
            self._stale_count += 1
            if self._metrics:
                self._metrics.inc("market_data_stale_quotes_total")
            logger.warning("Market quote for %s is stale: %s", canonical, quote.timestamp)

        # 4. Cache valid quote
        await self._cache.set_quote(quote, ttl_seconds=15)

        # 5. Feed into Paper Execution Adapter so paper simulated fills reflect live market prices
        if self._paper_adapter is not None:
            try:
                if hasattr(self._paper_adapter, "update_quote"):
                    await self._paper_adapter.update_quote(quote)
                else:
                    await self._paper_adapter.set_current_price(canonical, quote.mid)
            except Exception as exc:
                logger.warning("Failed to update paper execution quote for %s: %s", canonical, exc)

        if self._metrics:
            self._metrics.inc("market_data_quotes_total")

        return quote

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> list[OHLCV]:
        """Fetch historical candles with validation and caching."""
        canonical = normalize_symbol(symbol)
        tf = normalize_timeframe(timeframe)
        clamped_limit = max(1, min(limit, 1000))

        # Check cache if recent request without explicit start/end
        if start is None and end is None:
            cached = await self._cache.get_candles(canonical, tf.value)
            if cached and len(cached) >= clamped_limit:
                return cached[-clamped_limit:]

        candles = await self._provider.get_candles(
            canonical,
            tf,
            start=start,
            end=end,
            limit=clamped_limit,
        )

        # Validate each candle
        valid_candles: list[OHLCV] = []
        for c in candles:
            assessment = await self._quality.evaluate_ohlcv(c)
            if assessment.is_valid:
                valid_candles.append(c)

        # Cache recent candles
        if start is None and end is None and valid_candles:
            await self._cache.set_candles(canonical, tf.value, valid_candles, ttl_seconds=300)

        return valid_candles

    async def get_health(self) -> MarketDataHealth:
        """Return complete operational telemetry for market data infrastructure."""
        cached_health = await self._cache.get_health()
        if cached_health:
            return cached_health

        try:
            probe = await self._provider.health_check()
            connected = probe.get("connected", False)
            status = ProviderStatus.HEALTHY if connected else ProviderStatus.DISCONNECTED
            latency = float(probe.get("latency_ms", 0.0))
        except Exception as exc:
            logger.error("Provider health probe failed: %s", exc)
            status = ProviderStatus.ERROR
            latency = 999.0

        quality = DataQuality.EXCELLENT if status == ProviderStatus.HEALTHY else DataQuality.DEGRADED
        active_symbols = tuple(canonical_instruments().keys())

        health = MarketDataHealth(
            provider=self._provider.provider_name,
            status=status,
            data_quality=quality,
            last_update_utc=datetime.now(timezone.utc),
            symbols_active=active_symbols,
            latency_ms=latency,
            stale_count=self._stale_count,
            is_paper_feed=True,
        )

        await self._cache.set_health(health, ttl_seconds=30)
        return health
