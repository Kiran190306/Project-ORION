"""Contract tests for EPIC-002 shared-foundation public APIs."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any, Callable

import pytest
from shared.common.decorators import async_retry, retry, singleton, validate_args
from shared.common.result import Failure, Result, Success, attempt_async, failure, success
from shared.events import TickReceivedEvent, create_event, event_from_dict
from shared.identifiers import EntityId, generate_id, is_valid_id
from shared.responses import ApiResponse, PaginatedResponse
from shared.validators import (
    Validator,
    validate_dict,
    validate_email,
    validate_price,
    validate_symbol,
)
from shared.value_objects import Money, PriceValue, RiskRewardRatio, Spread, Symbol
from shared.versioning import Version, VersionRange, is_compatible


def test_result_factories_preserve_success_and_failure_semantics() -> None:
    assert success(3).map(lambda value: value + 1).unwrap() == 4
    assert failure(ValueError("bad")).unwrap_or("fallback") == "fallback"


def test_attempt_async_wraps_async_success_and_exception() -> None:
    async def succeeds() -> str:
        return "ok"

    async def fails() -> str:
        raise ValueError("failed")

    assert isinstance(asyncio.run(attempt_async(succeeds)), Success)
    failed = asyncio.run(attempt_async(fails))
    assert isinstance(failed, Failure)
    assert failed.code == "ValueError"


def test_decorators_preserve_contracts_and_retry_only_configured_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    @singleton
    class Counter:
        pass

    @validate_args(lambda value: value > 0)
    def positive(value: int) -> int:
        return value

    @retry(max_attempts=3, delay=0)
    def flaky() -> int:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ValueError("transient")
        return calls

    monkeypatch.setattr("shared.common.decorators.time.sleep", lambda _: None)
    assert Counter() is Counter()
    assert positive(1) == 1
    with pytest.raises(ValueError, match="argument 0"):
        positive(0)
    assert flaky() == 3


def test_async_retry_retries_and_preserves_return_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    @async_retry(max_attempts=2, delay=0)
    async def flaky() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("retry")
        return "done"

    async def no_wait(_: float) -> None:
        return None

    monkeypatch.setattr("shared.common.decorators.asyncio.sleep", no_wait)
    assert asyncio.run(flaky()) == "done"
    assert calls == 2


def test_identifiers_are_prefixed_unique_and_serializable() -> None:
    entity_id = EntityId.generate("evt")
    generated = generate_id("evt")

    assert str(entity_id).startswith("evt_")
    assert entity_id.to_dict()["id"] == str(entity_id)
    assert is_valid_id(generated)
    with pytest.raises(ValueError, match="cannot be empty"):
        EntityId("")


def test_value_objects_validate_and_apply_domain_arithmetic() -> None:
    amount = Money(Decimal("10.005"), "USD")
    assert amount.round_to().amount == Decimal("10.01")
    assert (amount + Money(Decimal("1"), "USD")).amount == Decimal("11.005")
    assert PriceValue(Decimal("1.23456")).to_dict()["value"] == "1.23456"
    assert Symbol("EUR", "USD").name == "EUR/USD"
    assert Spread(Decimal("1.1002"), Decimal("1.1000")).value == Decimal("0.0002")
    assert RiskRewardRatio(amount, Money(Decimal("20"), "USD")).ratio == pytest.approx(2)

    with pytest.raises(ValueError, match="Cannot add"):
        amount + Money(Decimal("1"), "EUR")
    with pytest.raises(ValueError, match="positive"):
        PriceValue(Decimal("0"))


def test_validators_return_result_objects_for_valid_and_invalid_values() -> None:
    assert validate_symbol("EUR/USD").unwrap() == "EUR/USD"
    assert isinstance(validate_symbol("eur/usd"), Failure)
    assert validate_price("1.1000").unwrap() == Decimal("1.1000")
    assert isinstance(validate_price("0"), Failure)
    assert validate_email("qa@orion.test").unwrap() == "qa@orion.test"


def test_composite_and_dictionary_validators_short_circuit_errors() -> None:
    chain = Validator().add(lambda value: validate_symbol(value))
    assert chain.validate("EUR/USD").unwrap() == "EUR/USD"
    assert isinstance(chain.validate("bad"), Failure)

    schema: dict[str, Callable[[Any], Result[Any, Exception]]] = {
        "symbol": lambda x: validate_symbol(x),
        "price": lambda x: validate_price(x),
    }
    validated = validate_dict({"symbol": "EUR/USD", "price": "1.1"}, schema)
    assert isinstance(validated, Success)
    assert validated.unwrap()["price"] == Decimal("1.1")
    assert isinstance(validate_dict({"symbol": "EUR/USD"}, schema), Failure)


def test_events_round_trip_through_the_public_serialization_contract() -> None:
    event = TickReceivedEvent.create("EUR/USD", "1.1", "1.2", "2026-01-01T00:00:00")
    restored = event_from_dict(event.to_dict())

    assert restored.event_id == event.event_id
    assert restored.data == event.data
    assert restored.event_type == event.event_type
    assert create_event("unknown.event", data={"key": "value"}).data == {"key": "value"}


def test_response_and_version_public_contracts() -> None:
    response = ApiResponse.from_result(success({"id": "1"}), success_message="created")
    assert response.to_dict()["data"] == {"id": "1"}
    error_response: ApiResponse[None] = ApiResponse.from_result(failure(ValueError("bad")))
    assert error_response.error is not None
    assert error_response.error["code"] == "ValueError"

    page = PaginatedResponse.create(["a"], total=3, page=1, page_size=1)
    assert page.has_next and not page.has_previous

    version = Version.parse("1.2.3-rc.1+build.5")
    assert str(version) == "1.2.3-rc.1+build.5"
    assert VersionRange(Version(1, 0, 0), Version(2, 0, 0)).contains(Version(1, 9, 0))
    assert is_compatible(Version(1, 5, 0), [Version(1, 0, 0)])
