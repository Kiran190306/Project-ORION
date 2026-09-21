"""Market Data Abstraction Layer.

Provides broker-agnostic interfaces and models for consuming
financial market data. Designed as a pure domain module with
zero external dependencies — all I/O and broker integration is
injected through protocol ports.
"""

from __future__ import annotations

from libraries.domain.market_data.events import (
    BarEvent,
    CorporateActionEvent,
    EconomicEventEvent,
    MarketDataEvent,
    MarketDataEventType,
    OHLCVEvent,
    OrderBookEvent,
    ProviderEvent,
    SessionEvent,
    TickEvent,
)
from libraries.domain.market_data.interfaces import (
    BarBuilderPort,
    CorporateActionProviderPort,
    EconomicCalendarPort,
    HistoricalDataProviderPort,
    MarketDataConsumerPort,
    MarketDataProviderPort,
    MarketSnapshotProviderPort,
    OrderBookProviderPort,
    SessionCalendarPort,
    TickDataProviderPort,
)
from libraries.domain.market_data.models import (
    Bar,
    BarType,
    BookLevel,
    CorporateAction,
    CorporateActionType,
    DataQuality,
    EconomicEvent,
    EconomicEventImportance,
    Instrument,
    MarketDataHealth,
    MarketSession,
    MarketSessionType,
    OHLCV,
    OrderBook,
    OrderBookSnapshot,
    ProviderStatus,
    Quote,
    Tick,
    TickData,
    TickPriceType,
    Trade,
    TradeTick,
)
from libraries.domain.market_data.normalization import (
    canonical_instruments,
    normalize_symbol,
    normalize_timeframe,
)
from libraries.domain.market_data.quality_engine import (
    MarketDataQualityEngine,
    QualityAssessment,
)
from libraries.domain.market_data.validation import (
    check_staleness,
    validate_bar_type,
    validate_ohlc,
    validate_optional_price,
    validate_price,
    validate_quote,
    validate_symbol,
    validate_tick_fields,
    validate_timestamp,
    validate_volume,
)

__all__ = [
    # Models
    "Bar",
    "BarType",
    "BookLevel",
    "CorporateAction",
    "CorporateActionType",
    "DataQuality",
    "EconomicEvent",
    "EconomicEventImportance",
    "Instrument",
    "MarketDataHealth",
    "MarketSession",
    "MarketSessionType",
    "OHLCV",
    "OrderBook",
    "OrderBookSnapshot",
    "ProviderStatus",
    "Quote",
    "Tick",
    "TickData",
    "TickPriceType",
    "Trade",
    "TradeTick",
    # Events
    "BarEvent",
    "CorporateActionEvent",
    "EconomicEventEvent",
    "MarketDataEvent",
    "MarketDataEventType",
    "OHLCVEvent",
    "OrderBookEvent",
    "ProviderEvent",
    "SessionEvent",
    "TickEvent",
    # Interfaces
    "BarBuilderPort",
    "CorporateActionProviderPort",
    "EconomicCalendarPort",
    "HistoricalDataProviderPort",
    "MarketDataConsumerPort",
    "MarketDataProviderPort",
    "MarketSnapshotProviderPort",
    "OrderBookProviderPort",
    "SessionCalendarPort",
    # Normalization & Quality
    "canonical_instruments",
    "normalize_symbol",
    "normalize_timeframe",
    "MarketDataQualityEngine",
    "QualityAssessment",
    # Validation
    "check_staleness",
    "validate_bar_type",
    "validate_ohlc",
    "validate_optional_price",
    "validate_price",
    "validate_quote",
    "validate_symbol",
    "validate_tick_fields",
    "validate_timestamp",
    "validate_volume",
]
