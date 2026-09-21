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
from libraries.domain.market_data.normalization import canonical_instruments
from libraries.domain.organization.permissions import Permission

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
        candles = await market_service.get_candles(
            symbol=symbol,
            timeframe=timeframe,
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
        symbol=symbol,
        timeframe=timeframe,
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
