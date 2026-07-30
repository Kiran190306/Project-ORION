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
    EconomicEvent,
    EconomicEventImportance,
    MarketSession,
    MarketSessionType,
    OHLCV,
    OrderBook,
    OrderBookSnapshot,
    Quote,
    Tick,
    TickData,
    TickPriceType,
    Trade,
    TradeTick,
)
from libraries.domain.market_data.validation import (
    validate_bar_type,
    validate_optional_price,
    validate_price,
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
    "EconomicEvent",
    "EconomicEventImportance",
    "MarketSession",
    "MarketSessionType",
    "OHLCV",
    "OrderBook",
    "OrderBookSnapshot",
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
    "MarketSnapshotProviderPort",
    "OrderBookProviderPort",
    "SessionCalendarPort",
    "TickDataProviderPort",
    # Validation
    "validate_bar_type",
    "validate_optional_price",
    "validate_price",
    "validate_symbol",
    "validate_tick_fields",
    "validate_timestamp",
    "validate_volume",
]
