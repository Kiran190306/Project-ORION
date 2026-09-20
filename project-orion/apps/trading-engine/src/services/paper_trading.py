"""Paper Trading application service.

Thin orchestration layer that wires existing domain components:
  TradeDecision → OrderBuilder → PaperExecutionAdapter → result

No business logic lives here. All logic is in the domain/infrastructure layers.
No live broker credentials are used or required.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from libraries.domain.execution.builder import OrderBuilder, OrderBuilderConfig
from libraries.domain.execution.validator import OrderValidator, OrderValidatorConfig
from libraries.domain.trading.decision_result import DecisionOutcome, TradeDecision
from libraries.domain.trading.signals import SignalDirection
from libraries.infrastructure.execution.broker_adapter import (
    AdapterOrderRejectedError,
    ExecutionAdapterError,
)
from libraries.infrastructure.execution.paper_execution import PaperExecutionAdapter

logger = logging.getLogger("trading_engine.paper_trading")


class PaperTradingError(Exception):
    """Raised when a paper trade cannot be executed."""


class PaperTradingNotReadyError(PaperTradingError):
    """Raised when the paper adapter is not connected."""


@dataclass(frozen=True)
class PaperExecutionResult:
    """Structured result of a paper trade execution."""

    order_id: str
    status: str
    symbol: str
    direction: str
    fill_price: Decimal | None
    filled_quantity: Decimal | None
    commission: Decimal | None
    is_paper: bool = True
    metadata: dict[str, Any] | None = None


class PaperTradingService:
    """Application service that orchestrates a single paper trade.

    Connects the decision → builder → validator → adapter pipeline using
    existing domain and infrastructure components. Thread-safe
    via the PaperExecutionAdapter's internal asyncio.Lock.

    Args:
        adapter: A configured PaperExecutionAdapter (injected).
        builder_config: Optional OrderBuilder configuration overrides.
        validator_config: Optional OrderValidator configuration overrides.
    """

    def __init__(
        self,
        adapter: PaperExecutionAdapter,
        builder_config: OrderBuilderConfig | None = None,
        validator_config: OrderValidatorConfig | None = None,
    ) -> None:
        self._adapter = adapter
        self._builder = OrderBuilder(builder_config)
        self._validator = OrderValidator(validator_config)

    @property
    def paper_adapter(self) -> PaperExecutionAdapter:
        """Expose the paper adapter for account summary queries."""
        return self._adapter

    async def execute(self, decision: TradeDecision) -> PaperExecutionResult:
        """Execute a paper trade from an approved TradeDecision.

        Args:
            decision: A TradeDecision with outcome == EXECUTE.

        Returns:
            PaperExecutionResult with fill details.

        Raises:
            PaperTradingError: If the decision is not executable or validation fails.
            PaperTradingNotReadyError: If the adapter is not connected.
            PaperTradingError: If the broker rejects the order.
        """
        if not decision.is_executable:
            raise PaperTradingError(
                f"Decision is not executable: outcome={decision.outcome!r}, "
                f"reason={decision.reason!r}"
            )

        if not self._adapter.is_connected:
            logger.info("Paper adapter not connected — connecting now")
            try:
                await self._adapter.connect()
            except Exception as exc:
                raise PaperTradingNotReadyError(
                    f"Failed to connect paper adapter: {exc}"
                ) from exc

        # Build a broker-neutral Order from the decision (synchronous)
        try:
            order = self._builder.build(decision)
        except Exception as exc:
            raise PaperTradingError(f"Failed to build order: {exc}") from exc

        # Validate order through domain OrderValidator
        validation_result = await self._validator.validate(order)
        if not validation_result.is_valid:
            error_msgs = "; ".join(validation_result.errors)
            logger.warning("Order validation failed: %s", error_msgs)
            raise PaperTradingError(f"Order validation failed: {error_msgs}")

        logger.info(
            "Submitting paper order: symbol=%s side=%s qty=%s",
            order.symbol,
            order.side,
            order.quantity,
        )

        # Submit to paper broker
        try:
            execution_info = await self._adapter.submit_order(order)
        except AdapterOrderRejectedError as exc:
            raise PaperTradingError(f"Paper broker rejected order: {exc}") from exc
        except ExecutionAdapterError as exc:
            raise PaperTradingError(f"Paper adapter error: {exc}") from exc

        fill_price: Decimal | None = execution_info.average_fill_price
        filled_qty: Decimal | None = (
            execution_info.filled_quantity if execution_info.filled_quantity else None
        )
        commission: Decimal | None = (
            execution_info.commission if execution_info.commission else None
        )

        status = (
            execution_info.status.value
            if hasattr(execution_info.status, "value")
            else str(execution_info.status)
        )

        logger.info(
            "Paper order completed: order_id=%s status=%s fill_price=%s",
            order.order_id,
            status,
            fill_price,
        )

        order_id_str = (
            order.order_id.value
            if hasattr(order.order_id, "value")
            else str(order.order_id)
        )

        return PaperExecutionResult(
            order_id=order_id_str,
            status=status,
            symbol=order.symbol,
            direction=order.side.value,
            fill_price=fill_price,
            filled_quantity=filled_qty,
            commission=commission,
            is_paper=True,
            metadata={
                "broker_order_id": str(execution_info.broker_order_id)
                if execution_info.broker_order_id
                else None,
                "decision_id": decision.decision_id,
                "confidence": decision.confidence,
            },
        )

    @classmethod
    def create_decision(
        cls,
        symbol: str,
        direction: str,
        confidence: float,
        entry_price: Decimal,
        stop_loss: Decimal | None,
        take_profit: Decimal | None,
        position_size: Decimal,
    ) -> TradeDecision:
        """Build an EXECUTE TradeDecision from API request fields.

        Args:
            symbol: Trading symbol.
            direction: 'buy' or 'sell'.
            confidence: Signal confidence 0–100.
            entry_price: Desired entry price.
            stop_loss: Optional stop-loss price.
            take_profit: Optional take-profit price.
            position_size: Position size in units.

        Returns:
            TradeDecision with outcome=EXECUTE.
        """
        signal_direction = (
            SignalDirection.BUY if direction.lower() == "buy" else SignalDirection.SELL
        )
        return TradeDecision(
            symbol=symbol,
            outcome=DecisionOutcome.EXECUTE,
            direction=signal_direction,
            confidence=confidence,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            decision_id=f"DEC-{uuid.uuid4().hex[:8].upper()}",
        )
