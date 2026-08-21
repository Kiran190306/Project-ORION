"""Order Builder.

Converts an approved TradeDecision into a broker-neutral Order.
Supports precision, tick size, lot size, rounding, and broker capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from libraries.domain.execution.exceptions import OrderBuildError
from libraries.domain.execution.models import (
    Order,
    OrderId,
    OrderSide,
    OrderStatus,
    OrderTimeInForce,
    OrderType,
)
from libraries.domain.trading.decision_result import TradeDecision


@dataclass(frozen=True, slots=True)
class OrderBuilderConfig:
    """Configuration for the OrderBuilder."""

    default_order_type: OrderType = OrderType.MARKET
    default_time_in_force: OrderTimeInForce = OrderTimeInForce.GTC
    tick_size: Decimal = Decimal("0.00001")
    lot_size: Decimal = Decimal("0.01")
    volume_precision: int = 2
    price_precision: int = 5
    max_slippage_pips: float = 2.0
    build_order_id_prefix: str = "ORD"


class OrderBuilder:
    """Converts TradeDecision into a broker-neutral Order.

    Handles precision management, rounding, and broker capability
    constraints. All outputs are immutable.
    """

    def __init__(
        self,
        config: OrderBuilderConfig | None = None,
    ) -> None:
        self._config = config or OrderBuilderConfig()
        self._counter: int = 0

    @property
    def config(self) -> OrderBuilderConfig:
        return self._config

    def build(
        self,
        decision: TradeDecision,
        order_type: OrderType | None = None,
        time_in_force: OrderTimeInForce | None = None,
        price: Decimal | None = None,
        broker_symbol: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Order:
        """Build an Order from a TradeDecision.

        Args:
            decision: Approved TradeDecision from the engine.
            order_type: Override order type (default: from config).
            time_in_force: Override time in force.
            price: Override price (required for limit/stop orders).
            broker_symbol: Broker-specific symbol mapping.
            metadata: Additional order metadata.

        Returns:
            A broker-neutral Order.

        Raises:
            OrderBuildError: If the decision cannot be converted.
        """
        if decision.entry_price is None and price is None and order_type != OrderType.MARKET:
            raise OrderBuildError(
                f"Order type {order_type or self._config.default_order_type} requires a price"
            )
        if decision.direction is None:
            raise OrderBuildError("Decision has no direction")

        if not decision.is_executable:
            raise OrderBuildError(
                f"Cannot build order from non-executable decision (outcome: {decision.outcome.value})"
            )

        # Determine order side
        from libraries.domain.trading.signals import SignalDirection

        side = OrderSide.BUY if decision.direction == SignalDirection.BUY else OrderSide.SELL

        # Determine order type
        ot = order_type or self._config.default_order_type

        # Determine price with rounding
        final_price: Decimal | None = None
        if price is not None:
            final_price = self._round_price(price)
        elif decision.entry_price is not None and ot != OrderType.MARKET:
            final_price = self._round_price(decision.entry_price)

        # Determine volume with rounding
        volume = self._round_volume(decision.position_size or Decimal(0))

        # Time in force
        tif = time_in_force or self._config.default_time_in_force

        # Generate order ID
        order_id = self._next_order_id()

        # Build metadata
        meta = dict(metadata or {})
        meta["decision_id"] = decision.decision_id
        meta["strategy"] = decision.strategy.value if decision.strategy else ""
        meta["confidence"] = decision.confidence
        meta["risk_amount"] = str(decision.risk_amount) if decision.risk_amount else ""
        meta["account_risk_pct"] = decision.account_risk_pct
        meta["original_entry_price"] = str(decision.entry_price) if decision.entry_price else ""

        return Order(
            order_id=OrderId(value=order_id),
            decision_id=decision.decision_id,
            execution_id="",
            symbol=broker_symbol or decision.symbol,
            side=side,
            order_type=ot,
            quantity=volume,
            price=final_price,
            time_in_force=tif,
            status=OrderStatus.NEW,
            created_at=datetime.now(timezone.utc),
            metadata=meta,
        )

    def _round_price(self, price: Decimal) -> Decimal:
        """Round price to configured tick size precision."""
        if price <= Decimal(0):
            raise OrderBuildError(f"Invalid price: {price}")
        quantize = Decimal(1).scaleb(-self._config.price_precision)
        return price.quantize(quantize, rounding=ROUND_HALF_UP)

    def _round_volume(self, volume: Decimal) -> Decimal:
        """Round volume to configured lot size precision."""
        if volume < Decimal(0):
            raise OrderBuildError(f"Invalid volume: {volume}")
        if volume == Decimal(0):
            return Decimal(0)
        quantize = Decimal(1).scaleb(-self._config.volume_precision)
        return volume.quantize(quantize, rounding=ROUND_HALF_UP)

    def _next_order_id(self) -> str:
        """Generate a unique order ID."""
        self._counter += 1
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"{self._config.build_order_id_prefix}-{ts}-{self._counter:04d}"
