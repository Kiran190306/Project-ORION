"""Order confirmation and fill tracking.

Handles broker fill confirmations, partial fills, fill validation,
and position reconciliation. Every fill is validated against the
original order before being recorded.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.execution.exceptions import FillValidationError
from libraries.domain.execution.models import (
    ExecutionReport,
    Order,
    OrderStatus,
)


@dataclass(frozen=True, slots=True)
class FillConfirmation:
    """A confirmed fill from the broker."""

    fill_id: str
    order_id: str
    symbol: str
    side: str
    filled_volume: Decimal
    remaining_volume: Decimal
    fill_price: Decimal
    total_cost: Decimal
    commission: Decimal = Decimal("0")
    liquidity: str = ""  # maker / taker
    broker_fill_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_report: ExecutionReport | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_full_fill(self) -> bool:
        return self.remaining_volume == Decimal("0")

    @property
    def is_partial_fill(self) -> bool:
        return self.remaining_volume > Decimal("0")


@dataclass(frozen=True, slots=True)
class FillValidatorConfig:
    """Configuration for fill validation."""

    max_price_deviation_pct: float = 1.0  # 1% max deviation from expected
    max_volume_deviation_pct: float = 0.5  # 0.5% max deviation
    check_commission: bool = True
    max_commission_pct: float = 0.1  # 0.1% of notional
    require_broker_fill_id: bool = True


class FillValidator:
    """Validates broker fill confirmations against original order.

    Thread-safe via asyncio.Lock.
    """

    def __init__(
        self,
        config: FillValidatorConfig | None = None,
    ) -> None:
        self._config = config or FillValidatorConfig()
        self._lock = asyncio.Lock()

    async def validate_fill(
        self,
        order: Order,
        fill: FillConfirmation,
    ) -> None:
        """Validate a fill against the original order.

        Args:
            order: The original order.
            fill: The fill confirmation.

        Raises:
            FillValidationError: If validation fails.
        """
        async with self._lock:
            errors: list[str] = []

            # 1. Order ID match
            if fill.order_id != order.order_id:
                errors.append(
                    f"Fill order_id {fill.order_id} does not match order {order.order_id}"
                )

            # 2. Symbol match
            if fill.symbol != order.symbol:
                errors.append(
                    f"Fill symbol {fill.symbol} does not match order {order.symbol}"
                )

            # 3. Side match
            if fill.side != order.side.value:
                errors.append(
                    f"Fill side {fill.side} does not match order {order.side.value}"
                )

            # 4. Volume check
            if fill.filled_volume <= Decimal("0"):
                errors.append(f"Fill volume must be positive, got {fill.filled_volume}")

            if fill.remaining_volume < Decimal("0"):
                errors.append(f"Remaining volume cannot be negative: {fill.remaining_volume}")

            total = fill.filled_volume + fill.remaining_volume
            if order.volume is not None and total > order.volume:
                errors.append(
                    f"Fill total {total} exceeds order volume {order.volume}"
                )

            # 5. Price deviation check
            if order.price is not None and fill.fill_price > Decimal("0"):
                deviation = abs(float(fill.fill_price - order.price) / float(order.price)) * 100
                if deviation > self._config.max_price_deviation_pct:
                    errors.append(
                        f"Fill price deviation {deviation:.2f}% exceeds "
                        f"max {self._config.max_price_deviation_pct}%"
                    )

            # 6. Commission check
            if self._config.check_commission and fill.commission > Decimal("0"):
                notional = fill.filled_volume * fill.fill_price
                if notional > Decimal("0"):
                    commission_pct = float(fill.commission / notional) * 100
                    if commission_pct > self._config.max_commission_pct:
                        errors.append(
                            f"Commission {commission_pct:.2f}% exceeds "
                            f"max {self._config.max_commission_pct}%"
                        )

            # 7. Broker fill ID check
            if self._config.require_broker_fill_id and not fill.broker_fill_id:
                errors.append("Broker fill ID is required but missing")

            if errors:
                raise FillValidationError("; ".join(errors))

    async def build_confirmation(
        self,
        order: Order,
        report: ExecutionReport,
    ) -> FillConfirmation:
        """Build a FillConfirmation from an ExecutionReport.

        Args:
            order: The original order.
            report: The execution report from the broker.

        Returns:
            Validated FillConfirmation.
        """
        filled_volume = report.filled_volume or Decimal("0")
        remaining = (order.volume or Decimal("0")) - filled_volume
        if remaining < Decimal("0"):
            remaining = Decimal("0")

        confirmation = FillConfirmation(
            fill_id=report.report_id or f"FL-{order.order_id}-{datetime.now(timezone.utc).timestamp()}",
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side.value,
            filled_volume=filled_volume,
            remaining_volume=remaining,
            fill_price=report.price or Decimal("0"),
            total_cost=report.cost or Decimal("0"),
            commission=report.commission or Decimal("0"),
            liquidity=report.liquidity or "",
            broker_fill_id=report.broker_order_id or "",
            timestamp=report.report_time or datetime.now(timezone.utc),
            raw_report=report,
        )

        await self.validate_fill(order, confirmation)
        return confirmation
