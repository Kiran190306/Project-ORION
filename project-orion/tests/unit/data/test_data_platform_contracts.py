"""Public-contract tests for the EPIC-004 data-platform foundation."""

from __future__ import annotations

import importlib
from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Any


def load(module_name: str) -> Any:
    """Import lazily to isolate module-level contract failures."""
    return importlib.import_module(module_name)


def make_tick(schemas: Any) -> Any:
    return schemas.Tick(
        tick_id="tick-1",
        symbol="EUR/USD",
        timestamp=datetime(2026, 1, 1),
        bid_price=Decimal("1.1000"),
        ask_price=Decimal("1.1002"),
    )


def make_ohlc(schemas: Any) -> Any:
    return schemas.OHLC(
        candle_id="bar-1",
        symbol="EUR/USD",
        timeframe="M1",
        timestamp=datetime(2026, 1, 1),
        open=Decimal("1.1000"),
        high=Decimal("1.1010"),
        low=Decimal("1.0990"),
        close=Decimal("1.1005"),
        volume=Decimal("10"),
        tick_count=4,
    )


def test_schema_defaults_and_data_records_are_constructible() -> None:
    schemas = load("libraries.data.schemas")
    tick = make_tick(schemas)
    bar = make_ohlc(schemas)
    session = schemas.Session("london", "London", "UTC", time(8), time(16))

    metadata = schemas.SymbolMetadata(
        symbol_id="eurusd",
        symbol="EUR/USD",
        asset_class=schemas.AssetClass.FOREX,
        base_currency="EUR",
        quote_currency="USD",
        pip_size=Decimal("0.0001"),
        tick_size=Decimal("0.00001"),
        contract_size=Decimal("100000"),
        trading_hours=schemas.TradingHours(),
        sessions=[session],
    )

    assert tick.symbol == bar.symbol == metadata.symbol
    assert metadata.margin_requirements is not None
    assert metadata.commission_structure is not None
    assert metadata.swap_rates is not None


def test_validators_return_all_record_level_errors_and_quality_scores() -> None:
    schemas = load("libraries.data.schemas")
    validators = load("libraries.data.validators")
    tick = make_tick(schemas)
    bar = make_ohlc(schemas)

    assert validators.TickValidator.validate_tick(tick) == []
    assert validators.OHLCValidator.validate_ohlc(bar) == []
    assert validators.TickValidator.validate_tick_sequence([tick]) == []
    assert validators.QualityChecker.check_missing_candles(100, 99).passed
    assert validators.QualityChecker.get_quality_bucket(0.8) == "acceptable"


def test_serialization_deserialization_and_compression_round_trip() -> None:
    schemas = load("libraries.data.schemas")
    serialization = load("libraries.data.serialization")
    deserialization = load("libraries.data.deserialization")
    compression = load("libraries.data.compression")
    tick = make_tick(schemas)

    payload = serialization.serialize(tick)
    restored = deserialization.SchemaAwareDeserializer().deserialize_tick(payload)
    packed = compression.compress(payload)

    assert restored == tick
    assert compression.decompress(packed) == payload


def test_cache_and_file_storage_preserve_values_and_expiry(tmp_path) -> None:
    cache_module = load("libraries.data.cache")
    storage_module = load("libraries.data.storage")
    cache = cache_module.InMemoryCache()
    cache.set("tick", {"symbol": "EUR/USD"})
    assert cache.get("tick") == {"symbol": "EUR/USD"}
    cache.set("expired", "stale", ttl=timedelta(seconds=0))
    assert cache.get("expired") is None

    storage = storage_module.FileSystemStorage(tmp_path)
    storage.write("ticks/sample.json", b'{"symbol":"EUR/USD"}')
    assert storage.read("ticks/sample.json") == b'{"symbol":"EUR/USD"}'
