"""FastAPI REST routes for Real Market Data Platform (EPIC-021)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from libraries.domain.market_data.exceptions import (
    CircuitBreakerOpenError,
    DataUnavailableError,
    InvalidQuoteError,
    MarketDataError,
    RateLimitExceededError,
    StaleDataError,
    SymbolNotFoundError,
    UnsupportedBarTypeError,
)
from libraries.domain.market_data.normalization import (
    canonical_instruments,
    normalize_symbol,
    normalize_timeframe,
)
from libraries.domain.organization.permissions import Permission
from libraries.domain.patterns import detect_patterns, get_default_pattern_registry

from ..dependencies import (
    get_current_active_user,
    get_market_data_service,
    require_permission,
)
from ..schemas import (
    MarketCandleResponse,
    MarketCandlesListResponse,
    MarketHealthResponse,
    MarketInstrumentResponse,
    MarketPatternResponse,
    MarketPatternsListResponse,
    MarketQuoteResponse,
)
from ..services.market_data_service import MarketDataService

logger = logging.getLogger("trading_engine.routes.market_data")

router = APIRouter(prefix="/api/v1/market-data", tags=["Market Data"])


@router.get(
    "/instruments",
    response_model=list[MarketInstrumentResponse],
    status_code=status.HTTP_200_OK,
    summary="List Supported Market Instruments",
    description="Retrieve all supported canonical forex and commodity instruments with precision metadata.",
)
async def list_instruments(
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.ACCOUNT_READ))],
    market_service: Annotated[MarketDataService, Depends(get_market_data_service)],
) -> list[MarketInstrumentResponse]:
    """Return all canonical instruments."""
    instruments = await market_service.get_instruments()
    return [
        MarketInstrumentResponse(
            symbol=inst.symbol,
            base_currency=inst.base_currency,
            quote_currency=inst.quote_currency,
            pip_size=inst.pip_size,
            tick_size=inst.tick_size,
            display_name=inst.display_name,
            is_active=inst.is_active,
        )
        for inst in instruments
    ]


@router.get(
    "/quotes/{symbol:path}",
    response_model=MarketQuoteResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Real-Time Quote",
    description="Fetch latest institutional market quote for a canonical symbol with spread and quality telemetry.",
)
async def get_quote(
    symbol: Annotated[str, Path(description="Forex pair symbol, e.g. EUR/USD or EURUSD")],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.ACCOUNT_READ))],
    market_service: Annotated[MarketDataService, Depends(get_market_data_service)],
) -> MarketQuoteResponse:
    """Fetch validated market quote for symbol."""
    try:
        quote = await market_service.get_quote(symbol)
    except SymbolNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (InvalidQuoteError, UnsupportedBarTypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except RateLimitExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Market data rate limit exceeded: {exc}",
        ) from exc
    except (CircuitBreakerOpenError, StaleDataError, DataUnavailableError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Market data service degraded: {exc}",
        ) from exc
    except MarketDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Market data provider error: {exc}",
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error retrieving quote for %s: %s", symbol, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve market quote",
        ) from exc

    # Determine pip size for pip spread calculation
    instruments = canonical_instruments()
    inst = instruments.get(quote.symbol)
    pip_size = inst.pip_size if inst else Decimal("0.0001")
    spread_pips = (quote.spread / pip_size).quantize(Decimal("0.1"))

    # Staleness check (> 30s)
    age_seconds = (datetime.now(timezone.utc) - quote.timestamp).total_seconds()
    is_stale = age_seconds > 30.0

    return MarketQuoteResponse(
        symbol=quote.symbol,
        bid=quote.bid,
        ask=quote.ask,
        mid=quote.mid,
        spread=quote.spread,
        spread_pips=spread_pips,
        timestamp=quote.timestamp,
        provider=quote.provider,
        is_stale=is_stale,
        quality="STALE" if is_stale else "EXCELLENT",
    )


@router.get(
    "/candles",
    response_model=MarketCandlesListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Historical Candles",
    description="Fetch validated historical OHLCV candle bars for a symbol and timeframe.",
)
async def get_candles(
    symbol: Annotated[str, Query(description="Forex pair symbol, e.g. EUR/USD or EURUSD")],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.ACCOUNT_READ))],
    market_service: Annotated[MarketDataService, Depends(get_market_data_service)],
    timeframe: Annotated[str, Query(description="Candle timeframe e.g. 1m, 5m, 1h, 1d")] = "1h",
    start: Annotated[datetime | None, Query(description="Start time (UTC)")] = None,
    end: Annotated[datetime | None, Query(description="End time (UTC)")] = None,
    limit: Annotated[int, Query(ge=1, le=1000, description="Max candle count")] = 100,
) -> MarketCandlesListResponse:
    """Fetch validated historical candles."""
    try:
        canonical_symbol = normalize_symbol(symbol)
        canonical_tf = normalize_timeframe(timeframe)
        candles = await market_service.get_candles(
            symbol=canonical_symbol,
            timeframe=canonical_tf.value,
            start=start,
            end=end,
            limit=limit,
        )
    except SymbolNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (UnsupportedBarTypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RateLimitExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Market data rate limit exceeded: {exc}",
        ) from exc
    except (CircuitBreakerOpenError, DataUnavailableError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Market data provider unavailable: {exc}",
        ) from exc
    except MarketDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Market data provider error: {exc}",
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error retrieving candles for %s: %s", symbol, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve market candles",
        ) from exc

    return MarketCandlesListResponse(
        symbol=canonical_symbol,
        timeframe=canonical_tf.name,
        provider=market_service.provider.provider_name,
        candles=[
            MarketCandleResponse(
                timestamp=c.timestamp,
                open=c.open,
                high=c.high,
                low=c.low,
                close=c.close,
                volume=c.volume,
            )
            for c in candles
        ],
    )


@router.get(
    "/patterns",
    response_model=MarketPatternsListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Candlestick Patterns",
    description="Detect deterministic institutional candlestick patterns across historical candle data.",
)
async def get_patterns(
    symbol: Annotated[str, Query(description="Forex pair symbol, e.g. EUR/USD or EURUSD")],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.ACCOUNT_READ))],
    market_service: Annotated[MarketDataService, Depends(get_market_data_service)],
    timeframe: Annotated[str, Query(description="Candle timeframe e.g. 1m, 5m, 1h, 1d")] = "1h",
    start: Annotated[datetime | None, Query(description="Start time (UTC)")] = None,
    end: Annotated[datetime | None, Query(description="End time (UTC)")] = None,
    limit: Annotated[int, Query(ge=1, le=1000, description="Max candle count to evaluate")] = 60,
    pattern_ids: Annotated[
        str | None,
        Query(description="Optional comma-separated pattern IDs to filter (e.g. doji,hammer)"),
    ] = None,
) -> MarketPatternsListResponse:
    """Fetch historical candles and detect deterministic candlestick patterns."""
    # 1. Validate and filter pattern IDs if requested
    target_pattern_ids: list[str] | None = None
    if pattern_ids is not None:
        raw_ids = [pid.strip().lower() for pid in pattern_ids.split(",") if pid.strip()]
        if not raw_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="pattern_ids parameter must contain at least one valid pattern ID",
            )
        registry = get_default_pattern_registry()
        valid_ids = set(registry.list_pattern_ids())
        unknown_ids = [pid for pid in raw_ids if pid not in valid_ids]
        if unknown_ids:
            available_str = ", ".join(sorted(valid_ids))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unknown pattern ID(s): {', '.join(unknown_ids)}. "
                    f"Available patterns: {available_str}"
                ),
            )
        target_pattern_ids = list(dict.fromkeys(raw_ids))

    # 2. Retrieve candles through existing market data service
    try:
        canonical_symbol = normalize_symbol(symbol)
        canonical_tf = normalize_timeframe(timeframe)
        candles = await market_service.get_candles(
            symbol=canonical_symbol,
            timeframe=canonical_tf.value,
            start=start,
            end=end,
            limit=limit,
        )
    except SymbolNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (UnsupportedBarTypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RateLimitExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Market data rate limit exceeded: {exc}",
        ) from exc
    except (CircuitBreakerOpenError, DataUnavailableError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Market data provider unavailable: {exc}",
        ) from exc
    except MarketDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Market data provider error: {exc}",
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error retrieving candles for patterns on %s: %s", symbol, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve market candles",
        ) from exc

    # 3. Detect patterns using pure deterministic engine
    detected = detect_patterns(candles, pattern_ids=target_pattern_ids)

    # 4. Map to response schema (preserving chronological order)
    return MarketPatternsListResponse(
        symbol=canonical_symbol,
        timeframe=canonical_tf.name,
        provider=market_service.provider.provider_name,
        patterns=[
            MarketPatternResponse(
                pattern_id=p.pattern_id,
                name=p.name,
                direction=p.direction.value,
                strength=p.strength.value,
                candle_index=p.candle_index,
                timestamp=p.timestamp,
                description=p.description,
                confidence=p.confidence,
                metadata=p.metadata,
            )
            for p in detected
        ],
        total_detected=len(detected),
    )


@router.get(
    "/health",
    response_model=MarketHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Market Data Health",
    description="Retrieve operational telemetry and connection status for the market data platform.",
)
async def get_health(
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.ACCOUNT_READ))],
    market_service: Annotated[MarketDataService, Depends(get_market_data_service)],
) -> MarketHealthResponse:
    """Return health telemetry."""
    health = await market_service.get_health()
    return MarketHealthResponse(
        provider=health.provider,
        status=health.status.value,
        data_quality=health.data_quality.value,
        last_update_utc=health.last_update_utc,
        symbols_active=len(health.symbols_active),
        latency_ms=health.latency_ms,
        stale_count=health.stale_count,
        is_paper_feed=health.is_paper_feed,
    )
