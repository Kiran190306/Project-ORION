# Market Data Domain

## Overview

The Market Data Domain is the foundation layer of Project ORION's trading
intelligence platform. It provides a **broker-agnostic**, **pure domain**
abstraction for consuming financial market data — ticks, bars, quotes, order
books, corporate actions, economic events, and market sessions.

### Design Principles

- **Domain-Driven Design** — The domain is isolated from all infrastructure concerns.
  No REST, WebSocket, or broker-specific code exists in this module.
- **Dependency Inversion** — All I/O and external integrations are injected through
  `Protocol` ports defined in `interfaces.py`.
- **Immutability** — All data models are `@dataclass(frozen=True, slots=True)`.
- **Strong Typing** — Full type annotations enforced by `mypy --strict`.
- **Runtime-checkable Protocols** — Every interface uses `@runtime_checkable` for
  adapter verification.

### Package Structure

```
libraries/domain/market_data/
├── __init__.py      # Public API — re-exports all models, interfaces, events, validators
├── models.py        # Immutable data models (OHLCV, Tick, Quote, Trade, OrderBook, etc.)
├── interfaces.py    # Runtime-checkable Protocol ports for dependency injection
├── events.py        # Domain events emitted by market data providers
├── validation.py    # Pure validation functions for market data primitives
└── exceptions.py    # Domain exception hierarchy
```

---

## Models (`models.py`)

All models are frozen dataclasses with `slots=True` for memory efficiency and
immutability guarantees.

### Enums

| Enum | Values | Description |
|------|--------|-------------|
| `TickPriceType` | `trade`, `bid`, `ask`, `mid` | Classification of tick price type |
| `BarType` | `1m`, `5m`, `15m`, `30m`, `1h`, `4h`, `1d`, `1w`, `1mo` | Supported bar/timeframe types |
| `MarketSessionType` | `asian`, `european`, `north_american`, `london`, `tokyo`, `sydney`, `new_york`, `overnight`, `closed` | Standard market session types |
| `CorporateActionType` | `dividend`, `stock_split`, `reverse_split`, `merger`, `rights_issue`, `spin_off`, `name_change`, `symbol_change` | Types of corporate actions |
| `EconomicEventImportance` | `low`, `medium`, `high`, `non_farm` | Importance level of economic events |

### Data Models

| Model | Fields | Description |
|-------|--------|-------------|
| `Tick` | `symbol`, `price`, `volume`, `timestamp`, `price_type`, `bid?`, `ask?`, `exchange_timestamp?`, `provider`, `metadata` | A single price tick from any source |
| `TickData` | `symbol`, `ticks`, `timestamp` | Container for a batch of ticks |
| `TradeTick` | `symbol`, `price`, `volume`, `timestamp`, `side`, `bid?`, `ask?`, `aggressor`, `exchange_timestamp?`, `metadata` | An executed trade tick with bid/ask context |
| `Quote` | `symbol`, `bid`, `ask`, `timestamp`, `bid_volume?`, `ask_volume?`, `provider`, `exchange_timestamp?`, `metadata` | A single quote with bid, ask, and mid prices |
| `Trade` | `trade_id`, `symbol`, `price`, `volume`, `timestamp`, `side`, `aggressor`, `exchange_timestamp?`, `commission?`, `metadata` | A generic executed trade |
| `OHLCV` | `symbol`, `timestamp`, `open`, `high`, `low`, `close`, `volume`, `tick_volume?`, `spread?`, `bar_type`, `metadata` | Open, High, Low, Close, Volume data point |
| `Bar` | `symbol`, `bar_type`, `timestamp`, `ohlcv`, `vwap?`, `count`, `metadata` | Aggregated bar data with OHLCV and statistics |
| `BookLevel` | `price`, `volume`, `order_count` | A single level in the order book |
| `OrderBook` | `symbol`, `timestamp`, `bids`, `asks`, `depth`, `metadata` | A snapshot of the order book |
| `OrderBookSnapshot` | `symbol`, `timestamp`, `bids`, `asks`, `sequence`, `snapshot_type`, `metadata` | Full order book snapshot with sequence tracking |
| `MarketSession` | `session_type`, `symbol`, `open_time`, `close_time`, `description`, `metadata` | Definition of a market trading session |
| `CorporateAction` | `symbol`, `action_type`, `announcement_date`, `effective_date`, `description`, `ratio?`, `dividend_amount?`, `metadata` | A corporate action event |
| `EconomicEvent` | `event_id`, `title`, `timestamp`, `importance`, `currency`, `actual`, `forecast`, `previous`, `description`, `metadata` | A scheduled economic event / news release |

---

## Interfaces (`interfaces.py`)

All interfaces are `@runtime_checkable` Protocols using `async` methods for
non-blocking data access.

| Protocol | Methods | Purpose |
|----------|---------|---------|
| `TickDataProviderPort` | `subscribe`, `unsubscribe`, `stream`, `latest_tick`, `is_connected` | Stream real-time tick data |
| `HistoricalDataProviderPort` | `load_bars`, `load_ticks`, `validate_availability`, `available_symbols`, `available_bar_types`, `date_range` | Load historical market data |
| `OrderBookProviderPort` | `subscribe`, `unsubscribe`, `stream`, `snapshot` | Stream order book snapshots |
| `SessionCalendarPort` | `active_sessions`, `is_market_open`, `next_session_open`, `next_session_close` | Query market trading sessions |
| `CorporateActionProviderPort` | `get_actions`, `get_upcoming_actions` | Fetch corporate action events |
| `EconomicCalendarPort` | `get_events`, `get_high_impact_events` | Fetch scheduled economic events |
| `MarketDataConsumerPort` | `on_tick`, `on_bar`, `on_order_book` | Consume processed market data |
| `BarBuilderPort` | `add_tick`, `current_bar` | Build aggregated bars from tick data |
| `MarketSnapshotProviderPort` | `snapshot`, `latest`, `stream` | Provide market snapshots |

---

## Events (`events.py`)

Domain events use a discriminated event type system for routing without
`isinstance` checks.

### Event Types

| Event | `MarketDataEventType` | Payload |
|-------|----------------------|---------|
| `TickEvent` | `tick_received` | `Tick` |
| `BarEvent` | `bar_completed` / `bar_updated` | `Bar`, `is_complete` |
| `OHLCVEvent` | `bar_updated` | `OHLCV` |
| `OrderBookEvent` | `order_book_snapshot` / `order_book_update` | `OrderBookSnapshot` |
| `SessionEvent` | `market_session_open` / `market_session_close` | `MarketSession`, `is_open` |
| `CorporateActionEvent` | `corporate_action` | `CorporateAction` |
| `EconomicEventEvent` | `economic_event` | `EconomicEvent` |
| `ProviderEvent` | `provider_connected` / `provider_disconnected` / `provider_error` | `provider_name`, `error_message` |

All events inherit from `MarketDataEvent` which provides:
- `event_type` — String enum discriminator
- `symbol` — The instrument symbol
- `timestamp` — When the event occurred (default: `datetime.now(timezone.utc)`)
- `metadata` — Optional key-value store

---

## Validation (`validation.py`)

Pure functions for validating market data primitives:

| Function | Validates | Raises |
|----------|-----------|--------|
| `validate_price` | Price bounds and type | `InvalidTickError` |
| `validate_volume` | Volume bounds and type | `InvalidTickError` |
| `validate_symbol` | Symbol format and length | `SymbolNotFoundError` |
| `validate_timestamp` | Timestamp type and future check | `InvalidTickError` |
| `validate_bar_type` | Bar type support | `UnsupportedBarTypeError` |
| `validate_optional_price` | Optional price (pass-through for `None`) | `InvalidTickError` |
| `validate_tick_fields` | Convenience wrapper for common tick fields | Various |

---

## Exceptions (`exceptions.py`)

```
MarketDataError (base)
├── ProviderConnectionError      — Connection to data provider failed
├── ProviderDisconnectedError    — Provider disconnected unexpectedly
├── SymbolNotFoundError          — Requested symbol not found
├── DataUnavailableError         — Historical data not available
├── InvalidTickError             — Tick failed validation
├── SubscriptionError            — Data feed subscription failed
├── UnsupportedBarTypeError      — Unsupported bar type requested
├── SessionLookupError           — Market session data unavailable
└── EconomicCalendarError        — Economic calendar data unavailable
```

---

## Usage Examples

### Creating Models

```python
from datetime import datetime, timezone
from decimal import Decimal
from libraries.domain.market_data import Tick, TickPriceType, OHLCV, BarType

tick = Tick(
    symbol="EURUSD",
    price=Decimal("1.12345"),
    volume=Decimal("1000000"),
    timestamp=datetime.now(timezone.utc),
    price_type=TickPriceType.BID,
)

ohlcv = OHLCV(
    symbol="EURUSD",
    timestamp=datetime.now(timezone.utc),
    open=Decimal("1.10000"),
    high=Decimal("1.11000"),
    low=Decimal("1.09000"),
    close=Decimal("1.10500"),
    volume=Decimal("1000000"),
    bar_type=BarType.H1,
)
```

### Implementing an Adapter

```python
from datetime import datetime
from decimal import Decimal
from typing import AsyncIterator
from libraries.domain.market_data import (
    TickDataProviderPort,
    Tick,
    TickPriceType,
)

class BrokerTickProvider:
    """Adapter that implements TickDataProviderPort for a specific broker."""

    async def subscribe(self, symbols: list[str]) -> None:
        # Broker-specific subscription logic
        pass

    async def unsubscribe(self, symbols: list[str]) -> None:
        pass

    async def stream(self) -> AsyncIterator[Tick]:
        # Broker-specific streaming logic
        yield Tick(
            symbol="EURUSD",
            price=Decimal("1.12345"),
            volume=Decimal("1000000"),
            timestamp=datetime.now(),
            price_type=TickPriceType.TRADE,
        )

    async def latest_tick(self, symbol: str) -> Tick | None:
        return None

    async def is_connected(self) -> bool:
        return True
```

### Validating Data

```python
from decimal import Decimal
from libraries.domain.market_data.validation import validate_price, validate_symbol

validated_price = validate_price(Decimal("1.12345"))  # OK
validated_symbol = validate_symbol("EURUSD")          # Returns "EURUSD"
```

---

## Testing

Run the market data domain test suite:

```bash
# All market data tests
poetry run pytest tests/unit/domain/market_data/ -v

# Specific test modules
poetry run pytest tests/unit/domain/market_data/test_models.py -v
poetry run pytest tests/unit/domain/market_data/test_validation.py -v
poetry run pytest tests/unit/domain/market_data/test_interfaces.py -v
poetry run pytest tests/unit/domain/market_data/test_events.py -v
poetry run pytest tests/unit/domain/market_data/test_exceptions.py -v
```

### Test Coverage

| Test Module | Coverage |
|-------------|----------|
| `test_models.py` | All models, enums, immutability, slots |
| `test_validation.py` | All validation functions, boundary conditions |
| `test_interfaces.py` | Contract tests for all Protocols |
| `test_events.py` | All event types, discriminator routing |
| `test_exceptions.py` | Exception hierarchy, catchability |

---

## Dependencies

This domain module has **zero external dependencies**. It relies only on Python
standard library types:
- `dataclasses` — Frozen dataclasses with slots
- `datetime` — Timezone-aware timestamps
- `decimal` — Precision-safe price/volume representation
- `enum` — StrEnum for type-safe enumerations
- `typing` — Protocol, runtime_checkable, AsyncIterator, etc.

