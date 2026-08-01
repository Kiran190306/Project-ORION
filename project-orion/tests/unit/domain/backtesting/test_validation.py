"""Tests for EPIC-010 Backtesting Validation Layer."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.backtesting.exceptions import (
    ExecutionSimulationError,
    PortfolioSimulationError,
    SimulationError,
)
from libraries.domain.backtesting.models import (
    ExecutionSimulationResult,
    ExecutionSimulationStatus,
    FillSimulation,
    OrderSimulation,
    OrderSimulationSide,
    OrderSimulationStatus,
    OrderSimulationType,
    PortfolioSnapshot,
    DrawdownSnapshot,
)
from libraries.domain.backtesting.validation import (
    detect_duplicate_execution,
    validate_backtest_operation,
    validate_cash_balance,
    validate_currency,
    validate_currency_consistency,
    validate_execution_result,
    validate_fill_price,
    validate_fill_quantity,
    validate_margin_consistency,
    validate_order_side,
    validate_order_transition,
    validate_order_type,
    validate_portfolio_consistency,
    validate_position_lifecycle,
    validate_timestamp_not_future,
    validate_timestamp_ordering,
)


class TestValidateOrderTransition:
    """Test order state transition validation."""

    def test_pending_to_filled(self) -> None:
        order = OrderSimulation(order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, order_type=OrderSimulationType.MARKET, quantity=Decimal("1000"))
        result = validate_order_transition(order, OrderSimulationStatus.FILLED)
        assert result == OrderSimulationStatus.FILLED

    def test_pending_to_rejected(self) -> None:
        order = OrderSimulation(order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, order_type=OrderSimulationType.MARKET, quantity=Decimal("1000"))
        result = validate_order_transition(order, OrderSimulationStatus.REJECTED)
        assert result == OrderSimulationStatus.REJECTED

    def test_filled_to_anything_raises(self) -> None:
        order = OrderSimulation(order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, order_type=OrderSimulationType.MARKET, quantity=Decimal("1000"), status=OrderSimulationStatus.FILLED)
        with pytest.raises(SimulationError, match="Invalid order state transition"):
            validate_order_transition(order, OrderSimulationStatus.PENDING)

    def test_rejected_to_anything_raises(self) -> None:
        order = OrderSimulation(order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, order_type=OrderSimulationType.MARKET, quantity=Decimal("1000"), status=OrderSimulationStatus.REJECTED)
        with pytest.raises(SimulationError, match="Invalid order state transition"):
            validate_order_transition(order, OrderSimulationStatus.FILLED)

    def test_pending_to_partial(self) -> None:
        order = OrderSimulation(order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, order_type=OrderSimulationType.MARKET, quantity=Decimal("1000"))
        result = validate_order_transition(order, OrderSimulationStatus.PARTIAL)
        assert result == OrderSimulationStatus.PARTIAL

    def test_partial_to_filled(self) -> None:
        order = OrderSimulation(order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, order_type=OrderSimulationType.MARKET, quantity=Decimal("1000"), status=OrderSimulationStatus.PARTIAL, filled_quantity=Decimal("500"))
        result = validate_order_transition(order, OrderSimulationStatus.FILLED)
        assert result == OrderSimulationStatus.FILLED


class TestValidateOrderSide:
    """Test order side validation."""

    def test_valid_buy(self) -> None:
        result = validate_order_side(OrderSimulationSide.BUY)
        assert result == OrderSimulationSide.BUY

    def test_valid_sell(self) -> None:
        result = validate_order_side(OrderSimulationSide.SELL)
        assert result == OrderSimulationSide.SELL

    def test_string_buy(self) -> None:
        result = validate_order_side("buy")
        assert result == OrderSimulationSide.BUY

    def test_string_sell(self) -> None:
        result = validate_order_side("sell")
        assert result == OrderSimulationSide.SELL

    def test_invalid_string_raises(self) -> None:
        with pytest.raises(SimulationError, match="Invalid order side"):
            validate_order_side("invalid")


class TestValidateOrderType:
    """Test order type validation."""

    def test_valid_market(self) -> None:
        result = validate_order_type(OrderSimulationType.MARKET)
        assert result == OrderSimulationType.MARKET

    def test_valid_limit(self) -> None:
        result = validate_order_type(OrderSimulationType.LIMIT)
        assert result == OrderSimulationType.LIMIT

    def test_string_market(self) -> None:
        result = validate_order_type("market")
        assert result == OrderSimulationType.MARKET

    def test_invalid_string_raises(self) -> None:
        with pytest.raises(SimulationError, match="Invalid order type"):
            validate_order_type("invalid")


class TestValidateFillQuantity:
    """Test fill quantity validation."""

    def test_valid_fill(self) -> None:
        order = OrderSimulation(order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, order_type=OrderSimulationType.MARKET, quantity=Decimal("1000"))
        fill = FillSimulation(fill_id="f1", order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, quantity=Decimal("500"), price=Decimal("1.10"))
        result = validate_fill_quantity(fill, order)
        assert result == fill

    def test_fill_exceeds_remaining(self) -> None:
        order = OrderSimulation(order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, order_type=OrderSimulationType.MARKET, quantity=Decimal("1000"), filled_quantity=Decimal("600"))
        fill = FillSimulation(fill_id="f1", order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, quantity=Decimal("500"), price=Decimal("1.10"))
        with pytest.raises(ExecutionSimulationError, match="exceeds remaining"):
            validate_fill_quantity(fill, order)

    def test_zero_quantity_raises(self) -> None:
        order = OrderSimulation(order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, order_type=OrderSimulationType.MARKET, quantity=Decimal("1000"))
        fill = FillSimulation(fill_id="f1", order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, quantity=Decimal("0"), price=Decimal("1.10"))
        with pytest.raises(ExecutionSimulationError, match="must be positive"):
            validate_fill_quantity(fill, order)


class TestValidateFillPrice:
    """Test fill price validation."""

    def test_valid_price(self) -> None:
        result = validate_fill_price(Decimal("1.12345"))
        assert result == Decimal("1.12345")

    def test_non_decimal_raises(self) -> None:
        with pytest.raises(ExecutionSimulationError, match="must be a Decimal"):
            validate_fill_price(1.50)  # type: ignore[arg-type]

    def test_below_minimum_raises(self) -> None:
        with pytest.raises(ExecutionSimulationError, match="below minimum"):
            validate_fill_price(Decimal("0.000000001"))

    def test_above_maximum_raises(self) -> None:
        with pytest.raises(ExecutionSimulationError, match="exceeds maximum"):
            validate_fill_price(Decimal("1000000000"))


class TestValidateTimestampOrdering:
    """Test timestamp ordering validation."""

    def test_ordered_timestamps(self) -> None:
        ts = [
            datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
            datetime(2023, 1, 1, 11, 0, tzinfo=timezone.utc),
            datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc),
        ]
        result = validate_timestamp_ordering(ts)
        assert result == ts

    def test_unordered_timestamps_raises(self) -> None:
        ts = [
            datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc),
            datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
        ]
        with pytest.raises(SimulationError, match="not in chronological order"):
            validate_timestamp_ordering(ts)

    def test_empty_list(self) -> None:
        result = validate_timestamp_ordering([])
        assert result == []

    def test_single_timestamp(self) -> None:
        ts = [datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc)]
        result = validate_timestamp_ordering(ts)
        assert result == ts


class TestValidateTimestampNotFuture:
    """Test future timestamp validation."""

    def test_past_timestamp(self) -> None:
        ts = datetime(2020, 1, 1, tzinfo=timezone.utc)
        result = validate_timestamp_not_future(ts)
        assert result == ts

    def test_future_timestamp_raises(self) -> None:
        from datetime import timedelta
        ts = datetime.now(timezone.utc) + timedelta(days=365)
        with pytest.raises(SimulationError, match="in the future"):
            validate_timestamp_not_future(ts)


class TestValidatePositionLifecycle:
    """Test position lifecycle validation."""

    def test_add_to_position(self) -> None:
        new_qty, delta = validate_position_lifecycle("EURUSD", Decimal("1000"), Decimal("500"), OrderSimulationSide.BUY)
        assert new_qty == Decimal("1500")
        assert delta == Decimal("500")

    def test_reduce_position(self) -> None:
        new_qty, delta = validate_position_lifecycle("EURUSD", Decimal("1000"), Decimal("500"), OrderSimulationSide.SELL)
        assert new_qty == Decimal("500")
        assert delta == Decimal("500")

    def test_partial_close(self) -> None:
        new_qty, delta = validate_position_lifecycle("EURUSD", Decimal("1000"), Decimal("300"), OrderSimulationSide.SELL)
        assert new_qty == Decimal("700")
        assert delta == Decimal("300")

    def test_sell_exceeds_position_raises(self) -> None:
        with pytest.raises(PortfolioSimulationError, match="Cannot sell"):
            validate_position_lifecycle("EURUSD", Decimal("500"), Decimal("1000"), OrderSimulationSide.SELL)

    def test_negative_delta_raises(self) -> None:
        with pytest.raises(PortfolioSimulationError, match="must be positive"):
            validate_position_lifecycle("EURUSD", Decimal("1000"), Decimal("-500"), OrderSimulationSide.BUY)


class TestValidateCashBalance:
    """Test cash balance validation."""

    def test_sufficient_balance(self) -> None:
        result = validate_cash_balance(Decimal("10000"), Decimal("5000"))
        assert result == Decimal("5000")

    def test_insufficient_balance_raises(self) -> None:
        with pytest.raises(PortfolioSimulationError, match="Insufficient"):
            validate_cash_balance(Decimal("1000"), Decimal("5000"))

    def test_exact_balance(self) -> None:
        result = validate_cash_balance(Decimal("5000"), Decimal("5000"))
        assert result == Decimal("0")

    def test_allow_negative(self) -> None:
        result = validate_cash_balance(Decimal("1000"), Decimal("5000"), allow_negative=True)
        assert result == Decimal("-4000")


class TestValidateMarginConsistency:
    """Test margin consistency validation."""

    def test_no_margin_used(self) -> None:
        is_call, is_stop = validate_margin_consistency(Decimal("10000"), Decimal("0"))
        assert not is_call
        assert not is_stop

    def test_healthy_margin(self) -> None:
        is_call, is_stop = validate_margin_consistency(Decimal("20000"), Decimal("5000"))
        assert not is_call
        assert not is_stop

    def test_margin_call(self) -> None:
        is_call, is_stop = validate_margin_consistency(Decimal("5000"), Decimal("5000"))
        assert is_call
        assert not is_stop

    def test_stop_out(self) -> None:
        is_call, is_stop = validate_margin_consistency(Decimal("2000"), Decimal("5000"))
        assert is_call
        assert is_stop

    def test_negative_used_margin_raises(self) -> None:
        with pytest.raises(PortfolioSimulationError, match="cannot be negative"):
            validate_margin_consistency(Decimal("10000"), Decimal("-1000"))


class TestDetectDuplicateExecution:
    """Test duplicate execution detection."""

    def test_no_duplicate(self) -> None:
        order = OrderSimulation(order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, order_type=OrderSimulationType.MARKET, quantity=Decimal("1000"))
        result = ExecutionSimulationResult(order=order, status=ExecutionSimulationStatus.SUCCESS)
        with pytest.raises(ExecutionSimulationError, match="Duplicate execution"):
            detect_duplicate_execution(result, [result])

    def test_failure_allowed_duplicate(self) -> None:
        order = OrderSimulation(order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, order_type=OrderSimulationType.MARKET, quantity=Decimal("1000"))
        fail_result = ExecutionSimulationResult(order=order, status=ExecutionSimulationStatus.FAILURE)
        result = detect_duplicate_execution(fail_result, [fail_result])
        assert not result

    def test_no_previous_results(self) -> None:
        order = OrderSimulation(order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, order_type=OrderSimulationType.MARKET, quantity=Decimal("1000"))
        result = ExecutionSimulationResult(order=order, status=ExecutionSimulationStatus.SUCCESS)
        is_dup = detect_duplicate_execution(result, [])
        assert not is_dup


class TestValidatePortfolioConsistency:
    """Test portfolio consistency validation."""

    def test_valid_snapshot(self) -> None:
        snap = PortfolioSnapshot(
            timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
            balance=Decimal("10000"),
            equity=Decimal("12000"),
            margin_used=Decimal("2000"),
            free_margin=Decimal("10000"),
            position_count=5,
            portfolio_heat=50.0,
        )
        result = validate_portfolio_consistency(snap)
        assert result == snap

    def test_negative_balance_raises(self) -> None:
        snap = PortfolioSnapshot(
            timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
            balance=Decimal("-1000"),
            equity=Decimal("10000"),
        )
        with pytest.raises(PortfolioSimulationError, match="cannot be negative"):
            validate_portfolio_consistency(snap)

    def test_negative_position_count_raises(self) -> None:
        snap = PortfolioSnapshot(
            timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
            balance=Decimal("10000"),
            equity=Decimal("10000"),
            position_count=-1,
        )
        with pytest.raises(PortfolioSimulationError, match="cannot be negative"):
            validate_portfolio_consistency(snap)

    def test_invalid_portfolio_heat_raises(self) -> None:
        snap = PortfolioSnapshot(
            timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
            balance=Decimal("10000"),
            equity=Decimal("10000"),
            portfolio_heat=150.0,
        )
        with pytest.raises(PortfolioSimulationError, match="must be between"):
            validate_portfolio_consistency(snap)


class TestValidateCurrency:
    """Test currency validation."""

    def test_valid_currency(self) -> None:
        result = validate_currency("USD")
        assert result == "USD"

    def test_lowercase(self) -> None:
        result = validate_currency("eur")
        assert result == "EUR"

    def test_empty_raises(self) -> None:
        with pytest.raises(SimulationError, match="cannot be empty"):
            validate_currency("")

    def test_invalid_length_raises(self) -> None:
        with pytest.raises(SimulationError, match="must be exactly 3 characters"):
            validate_currency("USDD")

    def test_unsupported_currency_raises(self) -> None:
        with pytest.raises(SimulationError, match="Unsupported currency"):
            validate_currency("XYZ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(SimulationError, match="must be a string"):
            validate_currency(123)  # type: ignore[arg-type]


class TestValidateCurrencyConsistency:
    """Test currency consistency validation."""

    def test_valid_pair(self) -> None:
        base, quote = validate_currency_consistency("USD", "EUR")
        assert base == "USD"
        assert quote == "EUR"

    def test_same_currency_raises(self) -> None:
        with pytest.raises(SimulationError, match="must differ"):
            validate_currency_consistency("USD", "USD")


class TestValidateExecutionResult:
    """Test execution result validation."""

    def test_successful_result(self) -> None:
        order = OrderSimulation(order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, order_type=OrderSimulationType.MARKET, quantity=Decimal("1000"))
        fill = FillSimulation(fill_id="f1", order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, quantity=Decimal("1000"), price=Decimal("1.10"))
        result = ExecutionSimulationResult(
            order=order,
            status=ExecutionSimulationStatus.SUCCESS,
            fills=(fill,),
            total_quantity=Decimal("1000"),
            average_price=Decimal("1.10"),
        )
        validated = validate_execution_result(result)
        assert validated == result

    def test_success_missing_fills_raises(self) -> None:
        order = OrderSimulation(order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, order_type=OrderSimulationType.MARKET, quantity=Decimal("1000"))
        result = ExecutionSimulationResult(order=order, status=ExecutionSimulationStatus.SUCCESS)
        with pytest.raises(ExecutionSimulationError, match="must have at least one fill"):
            validate_execution_result(result)

    def test_success_no_average_price_raises(self) -> None:
        order = OrderSimulation(order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, order_type=OrderSimulationType.MARKET, quantity=Decimal("1000"))
        fill = FillSimulation(fill_id="f1", order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, quantity=Decimal("1000"), price=Decimal("1.10"))
        result = ExecutionSimulationResult(order=order, status=ExecutionSimulationStatus.SUCCESS, fills=(fill,), total_quantity=Decimal("1000"))
        with pytest.raises(ExecutionSimulationError, match="must have an average price"):
            validate_execution_result(result)

    def test_failure_allowed(self) -> None:
        order = OrderSimulation(order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, order_type=OrderSimulationType.MARKET, quantity=Decimal("1000"))
        result = ExecutionSimulationResult(order=order, status=ExecutionSimulationStatus.FAILURE)
        validated = validate_execution_result(result)
        assert validated == result


class TestValidateBacktestOperation:
    """Test validate_backtest_operation convenience function."""

    def test_all_valid(self) -> None:
        snap = PortfolioSnapshot(
            timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
            balance=Decimal("10000"),
            equity=Decimal("10000"),
        )
        ts = [
            datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
            datetime(2023, 1, 1, 11, 0, tzinfo=timezone.utc),
        ]
        result = validate_backtest_operation(
            snapshot=snap,
            timestamps=ts,
            currency="USD",
            base_currency="USD",
            quote_currency="EUR",
        )
        assert result["portfolio_consistent"] is True
        assert result["timestamps_ordered"] is True
        assert result["currency_valid"] is True
        assert result["currency_consistency_valid"] is True

    def test_fill_validation(self) -> None:
        order = OrderSimulation(order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, order_type=OrderSimulationType.MARKET, quantity=Decimal("1000"))
        fill = FillSimulation(fill_id="f1", order_id="o1", symbol="EURUSD", side=OrderSimulationSide.BUY, quantity=Decimal("500"), price=Decimal("1.10"))
        result = validate_backtest_operation(order=order, fill=fill)
        assert result == {}
