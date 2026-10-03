"""Unit tests for Phase 4.7 Symbol / Instrument canonical architecture alignment."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.market.exceptions import DuplicateSymbolError, UnknownSymbolError
from libraries.domain.market.models import Symbol
from libraries.domain.market.symbol_registry import SymbolRegistry
from libraries.domain.market_data.models import Instrument
from libraries.domain.market_data.normalization import canonical_instruments


def test_instrument_to_symbol_bridge() -> None:
    """Instrument.to_symbol() must accurately construct tick-engine Symbol."""
    instruments = canonical_instruments()
    eur_usd_inst = instruments["EUR/USD"]

    symbol_obj = eur_usd_inst.to_symbol()
    assert isinstance(symbol_obj, Symbol)
    assert symbol_obj.code == "EUR/USD"
    assert symbol_obj.base_currency == "EUR"
    assert symbol_obj.quote_currency == "USD"
    assert symbol_obj.tick_size == Decimal("0.00001")
    assert symbol_obj.pip_size == Decimal("0.0001")
    assert symbol_obj.active is True


def test_symbol_from_instrument_and_to_instrument_round_trip() -> None:
    """Symbol.from_instrument and Symbol.to_instrument must maintain contract fidelity."""
    instruments = canonical_instruments()
    xau_usd_inst = instruments["XAU/USD"]

    symbol_obj = Symbol.from_instrument(xau_usd_inst)
    assert symbol_obj.code == "XAU/USD"
    assert symbol_obj.base_currency == "XAU"
    assert symbol_obj.quote_currency == "USD"
    assert symbol_obj.tick_size == Decimal("0.01")
    assert symbol_obj.pip_size == Decimal("0.10")
    assert symbol_obj.active is True

    converted_back = symbol_obj.to_instrument(display_name="Gold Spot / US Dollar")
    assert isinstance(converted_back, Instrument)
    assert converted_back.symbol == "XAU/USD"
    assert converted_back.base_currency == "XAU"
    assert converted_back.quote_currency == "USD"
    assert converted_back.pip_size == Decimal("0.10")
    assert converted_back.tick_size == Decimal("0.01")
    assert converted_back.display_name == "Gold Spot / US Dollar"
    assert converted_back.is_active is True


@pytest.mark.asyncio
async def test_symbol_registry_load_canonical_instruments() -> None:
    """SymbolRegistry seeded with canonical instruments must resolve all 8 instruments and aliases."""
    registry = await SymbolRegistry.create_with_canonical_instruments()

    registered_symbols = await registry.list_symbols()
    registered_codes = [s.code for s in registered_symbols]

    # Must contain all 8 canonical instruments
    expected = [
        "AUD/USD",
        "EUR/USD",
        "GBP/USD",
        "NZD/USD",
        "USD/CAD",
        "USD/CHF",
        "USD/JPY",
        "XAU/USD",
    ]
    assert sorted(registered_codes) == sorted(expected)

    # Must resolve standard canonical codes
    eur = await registry.get("EUR/USD")
    assert eur.code == "EUR/USD"

    gold = await registry.get("XAU/USD")
    assert gold.code == "XAU/USD"

    # Must resolve aliases
    eur_alias = await registry.get("EURUSD")
    assert eur_alias.code == "EUR/USD"

    eur_hyphen = await registry.get("EUR-USD")
    assert eur_hyphen.code == "EUR/USD"

    gold_alias = await registry.get("XAUUSD")
    assert gold_alias.code == "XAU/USD"

    gold_lower = await registry.get("xau_usd")
    assert gold_lower.code == "XAU/USD"


@pytest.mark.asyncio
async def test_symbol_registry_rejects_invalid_instruments() -> None:
    """SymbolRegistry must reject unknown or non-canonical instruments."""
    registry = await SymbolRegistry.create_with_canonical_instruments()

    with pytest.raises(UnknownSymbolError):
        await registry.get("EUR/GBP")

    with pytest.raises(UnknownSymbolError):
        await registry.get("BTC/USD")

    with pytest.raises(UnknownSymbolError):
        await registry.get("INVALID")


@pytest.mark.asyncio
async def test_symbol_registry_duplicate_registration_fails() -> None:
    """SymbolRegistry must prevent duplicate symbol registration."""
    registry = await SymbolRegistry.create_with_canonical_instruments()

    duplicate_symbol = Symbol(
        code="EUR/USD",
        base_currency="EUR",
        quote_currency="USD",
        tick_size=Decimal("0.0001"),
        pip_size=Decimal("0.0001"),
    )
    with pytest.raises(DuplicateSymbolError):
        await registry.register(duplicate_symbol)
