"""Order Validator.

Validates orders before submission to ensure they meet all
requirements for price, volume, precision, market status,
broker availability, and order type compatibility.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from libraries.domain.execution.exceptions import OrderValidationError
from libraries.domain.execution.models import Order, OrderStatus, OrderType


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Result of order validation."""

    is_valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    validated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_invalid(self) -> bool:
        return not self.is_valid

    def raise_if_invalid(self) -> None:
        """Raise OrderValidationError if validation failed."""
        if not self.is_valid:
            raise OrderValidationError("; ".join(self.errors))


@dataclass(frozen=True, slots=True)
class OrderValidatorConfig:
    """Configuration for the OrderValidator."""

    min_volume: Decimal = Decimal("0.001")
    max_volume: Decimal = Decimal(1000000)
    max_price: Decimal = Decimal(1000000)
    min_price: Decimal = Decimal("0.00001")
    max_slippage_pips: float = 10.0
    require_stop_loss: bool = False
    require_take_profit: bool = False
    max_position_size: Decimal = Decimal(10000)
    precision_check_enabled: bool = True
    market_status_check_enabled: bool = True
    broker_availability_check_enabled: bool = True


class OrderValidator:
    """Validates orders before broker submission.

    Thread-safe via asyncio.Lock.
    """

    def __init__(
        self,
        config: OrderValidatorConfig | None = None,
    ) -> None:
        self._config = config or OrderValidatorConfig()
        self._lock = asyncio.Lock()

    @property
    def config(self) -> OrderValidatorConfig:
        return self._config

    async def validate(
        self,
        order: Order,
        market_open: bool = True,
        broker_available: bool = True,
        tick_size: Decimal | None = None,
        lot_size: Decimal | None = None,
        current_spread: float | None = None,
    ) -> ValidationResult:
        """Validate an order before submission.

        Args:
            order: The order to validate.
            market_open: Whether the market is currently open.
            broker_available: Whether the broker is available.
            tick_size: Instrument tick size for precision check.
            lot_size: Minimum lot size for volume check.
            current_spread: Current spread in pips.

        Returns:
            ValidationResult with any errors/warnings.
        """
        async with self._lock:
            errors: list[str] = []
            warnings: list[str] = []

            # 1. Check order is in a validatable state
            if order.status != OrderStatus.NEW and order.status != OrderStatus.VALIDATED:
                errors.append(f"Cannot validate order in status {order.status.value}")

            # 2. Volume checks
            if order.quantity is not None:
                if order.quantity <= Decimal("0"):
                    errors.append("Quantity must be positive")
                if order.quantity < self._config.min_volume:
                    errors.append(f"Quantity {order.quantity} below minimum {self._config.min_volume}")
                if order.quantity > self._config.max_volume:
                    errors.append(
                        f"Quantity {order.quantity} exceeds maximum {self._config.max_volume}"
                    )
                if lot_size is not None:
                    remainder = order.quantity % lot_size
                    if remainder != Decimal("0"):
                        errors.append(
                            f"Quantity {order.quantity} not a multiple of lot size {lot_size}"
                        )

            # 3. Price checks
            if order.price is not None:
                if order.price <= Decimal(0):
                    errors.append("Price must be positive")
                if order.price < self._config.min_price:
                    errors.append(f"Price {order.price} below minimum {self._config.min_price}")
                if order.price > self._config.max_price:
                    errors.append(f"Price {order.price} exceeds maximum {self._config.max_price}")
                if tick_size is not None and self._config.precision_check_enabled:
                    remainder = order.price % tick_size
                    if remainder != Decimal(0):
                        errors.append(
                            f"Price {order.price} not a multiple of tick size {tick_size}"
                        )

            # 4. Stop loss checks
            if self._config.require_stop_loss and order.stop_price is None:
                errors.append("Stop loss is required but not set")

            # 5. Take profit checks
            if self._config.require_take_profit and order.price is None:
                errors.append("Take profit is required but not set")

            # 6. Market status
            if self._config.market_status_check_enabled and not market_open:
                errors.append("Market is currently closed")

            # 7. Broker availability
            if self._config.broker_availability_check_enabled and not broker_available:
                errors.append("Broker is currently unavailable")

            # 8. Spread check
            if current_spread is not None and current_spread > self._config.max_slippage_pips:
                warnings.append(
                    f"Current spread {current_spread} pips exceeds max {self._config.max_slippage_pips} pips"
                )

            # 9. Order type specific checks
            if order.order_type == OrderType.LIMIT and order.price is None:
                errors.append("Limit order requires a price")
            if order.order_type == OrderType.STOP and order.price is None:
                errors.append("Stop order requires a price")
            if order.order_type == OrderType.STOP_LIMIT and order.price is None:
                errors.append("Stop limit order requires a price")
            if (
                order.order_type in (OrderType.IOC, OrderType.FOK)
                and order.time_in_force is not None
            ):
                warnings.append("IOC/FOK orders ignore time_in_force setting")

            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=tuple(errors),
                warnings=tuple(warnings),
            )
