"""Validation layer for the Institutional Backtesting Domain.

Provides comprehensive validation for trade ordering, position lifecycle,
cash balance integrity, margin consistency, duplicate execution detection,
timestamp ordering, portfolio consistency, order state transitions,
fill quantity validation, price validation, and currency consistency.

All validation functions raise existing domain exceptions from
libraries.domain.backtesting.exceptions.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

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
)


# ─── Constants ────────────────────────────────────────────────────────────


_MIN_PRICE = Decimal("0.00000001")
_MAX_PRICE = Decimal("999999999.99999999")
_MIN_QUANTITY = Decimal("0")
_MAX_QUANTITY = Decimal("999999999")
_SUPPORTED_CURRENCIES: tuple[str, ...] = (
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD", "SGD", "HKD", "NOK", "SEK",
)


# ─── Order Validation ─────────────────────────────────────────────────────


def validate_order_transition(
    order: OrderSimulation,
    new_status: OrderSimulationStatus,
) -> OrderSimulationStatus:
    """Validate an order state transition.

    Ensures order status transitions follow a valid lifecycle:
        PENDING -> PARTIAL | FILLED | REJECTED | CANCELLED | EXPIRED
        PARTIAL -> PARTIAL | FILLED | REJECTED | CANCELLED | EXPIRED
        FILLED -> (no valid transitions)
        REJECTED -> (no valid transitions)
        CANCELLED -> (no valid transitions)
        EXPIRED -> (no valid transitions)

    Args:
        order: The current order state.
        new_status: The requested new status.

    Returns:
        The validated new status.

    Raises:
        SimulationError: If the transition is invalid.
    """
    VALID_TRANSITIONS: dict[OrderSimulationStatus, set[OrderSimulationStatus]] = {
        OrderSimulationStatus.PENDING: {
            OrderSimulationStatus.PARTIAL,
            OrderSimulationStatus.FILLED,
            OrderSimulationStatus.REJECTED,
            OrderSimulationStatus.CANCELLED,
            OrderSimulationStatus.EXPIRED,
        },
        OrderSimulationStatus.PARTIAL: {
            OrderSimulationStatus.PARTIAL,
            OrderSimulationStatus.FILLED,
            OrderSimulationStatus.REJECTED,
            OrderSimulationStatus.CANCELLED,
            OrderSimulationStatus.EXPIRED,
        },
        OrderSimulationStatus.FILLED: set(),
        OrderSimulationStatus.REJECTED: set(),
        OrderSimulationStatus.CANCELLED: set(),
        OrderSimulationStatus.EXPIRED: set(),
    }

    allowed = VALID_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise SimulationError(
            f"Invalid order state transition: {order.status.value} -> {new_status.value} "
            f"for order {order.order_id}"
        )
    return new_status


def validate_order_side(side: OrderSimulationSide | str) -> OrderSimulationSide:
    """Validate order side.

    Args:
        side: Order side to validate.

    Returns:
        The validated OrderSimulationSide.

    Raises:
        SimulationError: If the side is invalid.
    """
    if isinstance(side, str):
        try:
            side = OrderSimulationSide(side)
        except ValueError:
            raise SimulationError(
                f"Invalid order side: {side}. Must be 'buy' or 'sell'."
            )
    if side not in (OrderSimulationSide.BUY, OrderSimulationSide.SELL):
        raise SimulationError(
            f"Invalid order side: {side}. Must be buy or sell."
        )
    return side


def validate_order_type(order_type: OrderSimulationType | str) -> OrderSimulationType:
    """Validate order type.

    Args:
        order_type: Order type to validate.

    Returns:
        The validated OrderSimulationType.

    Raises:
        SimulationError: If the order type is invalid.
    """
    if isinstance(order_type, str):
        try:
            order_type = OrderSimulationType(order_type)
        except ValueError:
            raise SimulationError(
                f"Invalid order type: {order_type}. "
                f"Must be market, limit, stop, or stop_limit."
            )
    return order_type


# ─── Fill Validation ──────────────────────────────────────────────────────


def validate_fill_quantity(
    fill: FillSimulation,
    order: OrderSimulation,
) -> FillSimulation:
    """Validate fill quantity against order.

    Ensures fill quantity does not exceed remaining order quantity.

    Args:
        fill: The fill to validate.
        order: The parent order.

    Returns:
        The validated fill.

    Raises:
        ExecutionSimulationError: If quantity exceeds remaining.
    """
    if fill.quantity <= _MIN_QUANTITY:
        raise ExecutionSimulationError(
            f"Fill quantity ({fill.quantity}) must be positive"
        )

    if fill.quantity > order.remaining_quantity:
        raise ExecutionSimulationError(
            f"Fill quantity ({fill.quantity}) exceeds remaining order quantity "
            f"({order.remaining_quantity}) for order {order.order_id}"
        )

    total_filled = order.filled_quantity + fill.quantity
    if total_filled > order.quantity:
        raise ExecutionSimulationError(
            f"Total filled quantity ({total_filled}) exceeds order quantity "
            f"({order.quantity}) for order {order.order_id}"
        )

    return fill


def validate_fill_price(price: Decimal) -> Decimal:
    """Validate fill price.

    Args:
        price: The price to validate.

    Returns:
        The validated price.

    Raises:
        ExecutionSimulationError: If price is invalid.
    """
    if not isinstance(price, Decimal):
        raise ExecutionSimulationError(
            f"Price must be a Decimal, got {type(price).__name__}"
        )
    if price < _MIN_PRICE:
        raise ExecutionSimulationError(
            f"Price ({price}) is below minimum ({_MIN_PRICE})"
        )
    if price > _MAX_PRICE:
        raise ExecutionSimulationError(
            f"Price ({price}) exceeds maximum ({_MAX_PRICE})"
        )
    return price


# ─── Timestamp Validation ─────────────────────────────────────────────────


def validate_timestamp_ordering(
    timestamps: list[datetime],
    field_name: str = "timestamp",
) -> list[datetime]:
    """Validate that timestamps are in chronological order.

    Args:
        timestamps: List of timestamps to validate.
        field_name: Name of the field for error messages.

    Returns:
        The validated timestamps (unchanged if valid).

    Raises:
        SimulationError: If timestamps are not in order.
    """
    for i in range(1, len(timestamps)):
        if timestamps[i] < timestamps[i - 1]:
            raise SimulationError(
                f"{field_name}s are not in chronological order: "
                f"{timestamps[i - 1]} > {timestamps[i]} at index {i}"
            )
    return timestamps


def validate_timestamp_not_future(
    timestamp: datetime,
    field_name: str = "timestamp",
) -> datetime:
    """Validate that a timestamp is not in the future.

    Args:
        timestamp: The timestamp to validate.
        field_name: Name of the field for error messages.

    Returns:
        The validated timestamp.

    Raises:
        SimulationError: If the timestamp is in the future.
    """
    if timestamp > datetime.now(timestamp.tzinfo):
        raise SimulationError(
            f"{field_name} ({timestamp}) is in the future"
        )
    return timestamp


# ─── Position Lifecycle Validation ────────────────────────────────────────


def validate_position_lifecycle(
    symbol: str,
    current_quantity: Decimal,
    delta_quantity: Decimal,
    side: OrderSimulationSide,
) -> tuple[Decimal, Decimal]:
    """Validate a position lifecycle operation.

    Ensures that closing a position does not exceed the current position size
    and that the resulting position is valid.

    Args:
        symbol: Trading symbol.
        current_quantity: Current position quantity (absolute).
        delta_quantity: Quantity being added/removed (positive).
        side: Order side (buy adds to long, sell removes from long).

    Returns:
        Tuple of (new_position_quantity, delta_quantity).

    Raises:
        PortfolioSimulationError: If the operation would result in an invalid position.
    """
    if delta_quantity <= _MIN_QUANTITY:
        raise PortfolioSimulationError(
            f"Position delta ({delta_quantity}) must be positive for {symbol}"
        )

    if side == OrderSimulationSide.SELL:
        if delta_quantity > current_quantity:
            raise PortfolioSimulationError(
                f"Cannot sell {delta_quantity} of {symbol} when "
                f"position is only {current_quantity}"
            )
        new_quantity = current_quantity - delta_quantity
    else:
        new_quantity = current_quantity + delta_quantity

    if new_quantity < _MIN_QUANTITY:
        raise PortfolioSimulationError(
            f"Position quantity ({new_quantity}) cannot be negative for {symbol}"
        )

    return new_quantity, delta_quantity


# ─── Cash Balance Validation ──────────────────────────────────────────────


def validate_cash_balance(
    balance: Decimal,
    required_amount: Decimal,
    currency: str = "USD",
    allow_negative: bool = False,
) -> Decimal:
    """Validate that cash balance is sufficient for a transaction.

    Args:
        balance: Current cash balance.
        required_amount: Amount required for the transaction.
        currency: Currency code.
        allow_negative: If True, allow negative balance (margin).

    Returns:
        The remaining balance after the transaction.

    Raises:
        PortfolioSimulationError: If balance is insufficient.
    """
    if not allow_negative and balance < required_amount:
        raise PortfolioSimulationError(
            f"Insufficient {currency} balance: {balance} < {required_amount}"
        )
    return balance - required_amount


# ─── Margin Consistency ──────────────────────────────────────────────────


def validate_margin_consistency(
    equity: Decimal,
    used_margin: Decimal,
    margin_call_level: float = 100.0,
    stop_out_level: float = 50.0,
) -> tuple[bool, bool]:
    """Validate margin consistency.

    Checks margin level against margin call and stop out thresholds.

    Args:
        equity: Current account equity.
        used_margin: Current used margin.
        margin_call_level: Margin call level percentage.
        stop_out_level: Stop out level percentage.

    Returns:
        Tuple of (is_margin_call, is_stop_out).

    Raises:
        PortfolioSimulationError: If margin is inconsistent.
    """
    if used_margin < Decimal("0"):
        raise PortfolioSimulationError(
            f"Used margin ({used_margin}) cannot be negative"
        )
    if equity < Decimal("0"):
        raise PortfolioSimulationError(
            f"Equity ({equity}) cannot be negative"
        )

    if used_margin == Decimal("0"):
        return False, False

    margin_level = float(equity / used_margin * 100)
    is_margin_call = margin_level <= margin_call_level
    is_stop_out = margin_level <= stop_out_level

    return is_margin_call, is_stop_out


# ─── Duplicate Execution Detection ────────────────────────────────────────


def detect_duplicate_execution(
    result: ExecutionSimulationResult,
    previous_results: list[ExecutionSimulationResult],
) -> bool:
    """Detect duplicate execution of the same order.

    Args:
        result: The execution result to check.
        previous_results: Previously recorded execution results.

    Returns:
        True if this is a duplicate execution.

    Raises:
        ExecutionSimulationError: If duplicate execution is detected.
    """
    for prev in previous_results:
        if prev.order.order_id == result.order.order_id:
            if prev.status != ExecutionSimulationStatus.FAILURE:
                raise ExecutionSimulationError(
                    f"Duplicate execution detected for order {result.order.order_id}: "
                    f"already executed with status {prev.status.value}"
                )
    return False


# ─── Portfolio Consistency ────────────────────────────────────────────────


def validate_portfolio_consistency(
    snapshot: PortfolioSnapshot,
) -> PortfolioSnapshot:
    """Validate portfolio snapshot consistency.

    Ensures balance, equity, margin, and PnL relationships hold.

    Args:
        snapshot: The portfolio snapshot to validate.

    Returns:
        The validated snapshot.

    Raises:
        PortfolioSimulationError: If portfolio is inconsistent.
    """
    if snapshot.balance < Decimal("0"):
        raise PortfolioSimulationError(
            f"Balance ({snapshot.balance}) cannot be negative"
        )
    if snapshot.equity < Decimal("0"):
        raise PortfolioSimulationError(
            f"Equity ({snapshot.equity}) cannot be negative"
        )
    if snapshot.margin_used < Decimal("0"):
        raise PortfolioSimulationError(
            f"Margin used ({snapshot.margin_used}) cannot be negative"
        )
    if snapshot.free_margin < Decimal("0"):
        raise PortfolioSimulationError(
            f"Free margin ({snapshot.free_margin}) cannot be negative"
        )
    if snapshot.position_count < 0:
        raise PortfolioSimulationError(
            f"Position count ({snapshot.position_count}) cannot be negative"
        )
    if snapshot.portfolio_heat < 0 or snapshot.portfolio_heat > 100:
        raise PortfolioSimulationError(
            f"Portfolio heat ({snapshot.portfolio_heat}) must be between 0 and 100"
        )

    # Free margin should approximately equal equity - used margin
    expected_free = snapshot.equity - snapshot.margin_used
    if snapshot.free_margin != expected_free and snapshot.free_margin != Decimal("0"):
        raise PortfolioSimulationError(
            f"Free margin mismatch: {snapshot.free_margin} != {expected_free}"
        )

    return snapshot


# ─── Currency Consistency ─────────────────────────────────────────────────


def validate_currency(currency: str) -> str:
    """Validate currency code.

    Args:
        currency: Currency code to validate.

    Returns:
        The validated currency code (uppercase).

    Raises:
        SimulationError: If currency is invalid.
    """
    if not isinstance(currency, str):
        raise SimulationError(
            f"Currency must be a string, got {type(currency).__name__}"
        )
    currency = currency.upper().strip()
    if not currency:
        raise SimulationError("Currency code cannot be empty")
    if len(currency) != 3:
        raise SimulationError(
            f"Currency code '{currency}' must be exactly 3 characters"
        )
    if currency not in _SUPPORTED_CURRENCIES:
        raise SimulationError(
            f"Unsupported currency: {currency}. "
            f"Supported currencies: {', '.join(_SUPPORTED_CURRENCIES)}"
        )
    return currency


def validate_currency_consistency(
    base_currency: str,
    quote_currency: str,
) -> tuple[str, str]:
    """Validate currency consistency between base and quote.

    Args:
        base_currency: Base currency code.
        quote_currency: Quote currency code.

    Returns:
        Tuple of (validated base_currency, validated quote_currency).

    Raises:
        SimulationError: If currencies are inconsistent.
    """
    base = validate_currency(base_currency)
    quote = validate_currency(quote_currency)

    if base == quote:
        raise SimulationError(
            f"Base currency ({base}) and quote currency ({quote}) must differ"
        )

    return base, quote


# ─── Execution Result Validation ──────────────────────────────────────────


def validate_execution_result(
    result: ExecutionSimulationResult,
) -> ExecutionSimulationResult:
    """Validate an execution simulation result.

    Performs comprehensive validation of the result including
    fill quantities, prices, and status consistency.

    Args:
        result: The execution result to validate.

    Returns:
        The validated result.

    Raises:
        ExecutionSimulationError: If validation fails.
    """
    if result.status == ExecutionSimulationStatus.SUCCESS:
        if not result.fills:
            raise ExecutionSimulationError(
                "Successful execution must have at least one fill"
            )
        if result.total_quantity <= _MIN_QUANTITY:
            raise ExecutionSimulationError(
                f"Total quantity ({result.total_quantity}) must be positive for successful execution"
            )
        if result.average_price is None:
            raise ExecutionSimulationError(
                "Successful execution must have an average price"
            )
        if result.total_commission < Decimal("0"):
            raise ExecutionSimulationError(
                f"Total commission ({result.total_commission}) cannot be negative"
            )

    return result


# ─── Convenience Aggregate Validator ──────────────────────────────────────


def validate_backtest_operation(
    *,
    order: OrderSimulation | None = None,
    fill: FillSimulation | None = None,
    snapshot: PortfolioSnapshot | None = None,
    execution_result: ExecutionSimulationResult | None = None,
    previous_results: list[ExecutionSimulationResult] | None = None,
    timestamps: list[datetime] | None = None,
    currency: str | None = None,
    base_currency: str | None = None,
    quote_currency: str | None = None,
) -> dict[str, Any]:
    """Convenience function to run multiple validations at once.

    Allows running all relevant validations for a backtest operation
    in a single call, aggregating only the validations that apply.

    Args:
        order: Order to validate state transition (optional).
        fill: Fill to validate (optional).
        snapshot: Portfolio snapshot to validate (optional).
        execution_result: Execution result to validate (optional).
        previous_results: Previous execution results for duplicate detection (optional).
        timestamps: Timestamps to validate ordering (optional).
        currency: Currency to validate (optional).
        base_currency: Base currency to validate (optional).
        quote_currency: Quote currency to validate (optional).

    Returns:
        Dict of validation results keyed by validation type.

    Raises:
        SimulationError / ExecutionSimulationError / PortfolioSimulationError:
            If any validation fails.
    """
    results: dict[str, Any] = {}

    if order is not None and fill is not None:
        validate_fill_quantity(fill, order)

    if snapshot is not None:
        validate_portfolio_consistency(snapshot)
        results["portfolio_consistent"] = True

    if execution_result is not None:
        validate_execution_result(execution_result)
        results["execution_valid"] = True

    if previous_results is not None and execution_result is not None:
        detect_duplicate_execution(execution_result, previous_results)
        results["no_duplicate"] = True

    if timestamps is not None:
        validate_timestamp_ordering(timestamps)
        results["timestamps_ordered"] = True

    if currency is not None:
        validate_currency(currency)
        results["currency_valid"] = True

    if base_currency is not None and quote_currency is not None:
        validate_currency_consistency(base_currency, quote_currency)
        results["currency_consistency_valid"] = True

    return results
