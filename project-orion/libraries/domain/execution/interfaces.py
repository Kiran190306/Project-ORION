"""Protocol/port definitions for the Smart Order Execution Engine.

Defines all ports that the domain execution engine depends on.
All broker-specific logic is behind these ports.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from libraries.domain.execution.models import (
    BrokerOrderId,
    ExecutionEvent,
    ExecutionResult,
    Fill,
    Order,
    OrderId,
    OrderStatus,
    SlippageMetrics,
)
from libraries.domain.trading.decision_result import TradeDecision

# ─── External Ports (Integration Points) ─────────────────────────────────


@runtime_checkable
class TradeDecisionSource(Protocol):
    """Source of approved TradeDecisions (the DecisionEngine + RiskEngine pipeline)."""

    async def get_approved_decision(self, symbol: str) -> TradeDecision | None:
        """Return the next approved trade decision for a symbol, if any."""
        ...


@runtime_checkable
class RiskEnginePort(Protocol):
    """Port to the Risk Engine for final approval."""

    async def evaluate(self, decision: TradeDecision) -> Any:
        """Evaluate a TradeDecision against risk policies.

        Returns a RiskResult with APPROVED/REJECTED/DEFERRED.
        """
        ...


@runtime_checkable
class MarketDataPort(Protocol):
    """Port for querying market data needed during execution."""

    async def get_current_price(self, symbol: str) -> Decimal | None:
        """Return the current market price for a symbol."""
        ...

    async def get_bid_ask(self, symbol: str) -> tuple[Decimal, Decimal] | None:
        """Return current (bid, ask) for a symbol."""
        ...

    async def get_volume(self, symbol: str) -> Decimal | None:
        """Return current volume for a symbol."""
        ...

    async def is_market_open(self, symbol: str) -> bool:
        """Return whether the market is open for trading."""
        ...


@runtime_checkable
class PortfolioSyncPort(Protocol):
    """Port for syncing execution results back to the portfolio/position tracker."""

    async def on_fill(self, fill: Fill) -> None:
        """Called when a fill is confirmed."""
        ...

    async def on_order_rejected(self, order: Order, reason: str) -> None:
        """Called when an order is rejected."""
        ...

    async def on_order_cancelled(self, order: Order) -> None:
        """Called when an order is cancelled."""
        ...


# ─── Domain Service Ports ────────────────────────────────────────────────


@runtime_checkable
class OrderValidatorPort(Protocol):
    """Port for order validation."""

    async def validate(self, order: Order, context: Any) -> tuple[bool, list[str]]:
        """Validate an order before submission.

        Returns (is_valid, list_of_errors).
        """
        ...


@runtime_checkable
class OrderBuilderPort(Protocol):
    """Port for building orders from trade decisions."""

    async def build(self, decision: TradeDecision, context: Any) -> Order:
        """Build a broker-neutral Order from a TradeDecision.

        Args:
            decision: Approved trade decision.
            context: Execution context with market data.

        Returns:
            Constructed Order.
        """
        ...


@runtime_checkable
class OrderRouterPort(Protocol):
    """Port for routing orders to brokers."""

    async def route(self, order: Order, context: Any) -> str:
        """Select a broker/provider for the order.

        Args:
            order: The order to route.
            context: Execution context.

        Returns:
            Broker name/identifier.
        """
        ...


@runtime_checkable
class OrderRetryPort(Protocol):
    """Port for retry logic."""

    async def should_retry(
        self,
        order: Order,
        attempt: int,
        error: Exception | None,
    ) -> tuple[bool, float]:
        """Determine if an order should be retried.

        Args:
            order: The failed order.
            attempt: Current attempt number (1-based).
            error: The error that caused the failure.

        Returns:
            (should_retry, delay_seconds).
        """
        ...


@runtime_checkable
class OrderConfirmationPort(Protocol):
    """Port for tracking order confirmations."""

    async def wait_for_confirmation(
        self,
        order: Order,
        timeout_seconds: float,
    ) -> tuple[OrderStatus, list[Fill], str]:
        """Wait for order confirmation/fills from the broker.

        Args:
            order: The submitted order.
            timeout_seconds: Max time to wait.

        Returns:
            (final_status, fills, rejection_reason).
        """
        ...


@runtime_checkable
class OrderDeduplicationPort(Protocol):
    """Port for preventing duplicate order submissions."""

    async def is_duplicate(self, execution_id: str, decision_id: str, request_hash: str) -> bool:
        """Check if an order submission is a duplicate.

        Args:
            execution_id: Unique execution ID.
            decision_id: Source decision ID.
            request_hash: Hash of the order request.

        Returns:
            True if this is a duplicate submission.
        """
        ...

    async def mark_submitted(self, execution_id: str, decision_id: str, request_hash: str) -> None:
        """Mark an order as submitted to prevent duplicates."""
        ...


@runtime_checkable
class OrderLifecyclePort(Protocol):
    """Port for managing order lifecycle state."""

    async def transition(self, order: Order, new_status: OrderStatus) -> Order:
        """Transition an order to a new status.

        Args:
            order: Current order.
            new_status: Desired new status.

        Returns:
            Order with updated status.
        """
        ...

    async def get_order(self, order_id: OrderId) -> Order | None:
        """Retrieve an order by ID."""
        ...

    async def get_active_orders(self) -> list[Order]:
        """Return all active (non-finalized) orders."""
        ...

    async def get_pending_orders(self) -> list[Order]:
        """Return all pending/submitted orders."""
        ...


@runtime_checkable
class OrderStatisticsPort(Protocol):
    """Port for recording execution statistics."""

    async def record_execution(self, result: ExecutionResult) -> None:
        """Record an execution result in statistics."""
        ...

    async def record_slippage(self, metrics: SlippageMetrics) -> None:
        """Record slippage metrics."""
        ...

    async def record_retry(self, order_id: OrderId, attempt: int) -> None:
        """Record a retry attempt."""
        ...


# ─── Broker Communication Ports ──────────────────────────────────────────


@runtime_checkable
class BrokerSubmitterPort(Protocol):
    """Port for submitting orders to a broker.

    This is the ONLY port that communicates with external broker systems.
    Implementations live in the infrastructure layer.
    """

    async def submit_order(self, order: Order) -> BrokerOrderId:
        """Submit an order to the broker.

        Args:
            order: The order to submit.

        Returns:
            Broker-assigned order ID.

        Raises:
            OrderRejectedByBrokerError: If broker rejects the order.
            TimeoutError: If submission times out.
        """
        ...

    async def cancel_order(self, broker_order_id: BrokerOrderId) -> bool:
        """Cancel an order with the broker.

        Args:
            broker_order_id: Broker-assigned order ID.

        Returns:
            True if cancellation was successful.
        """
        ...

    async def get_order_status(self, broker_order_id: BrokerOrderId) -> OrderStatus:
        """Query the current status of an order from the broker."""
        ...


@runtime_checkable
class BrokerOrderStatusPort(Protocol):
    """Port for polling/streaming order status from a broker."""

    async def poll_status(
        self,
        broker_order_id: BrokerOrderId,
    ) -> tuple[OrderStatus, list[Fill], str]:
        """Poll the current status and fills for an order.

        Returns:
            (status, fills, rejection_reason).
        """
        ...


# ─── Manager Port ────────────────────────────────────────────────────────


@runtime_checkable
class ExecutionManagerPort(Protocol):
    """Public API of the ExecutionManager."""

    async def start(self) -> None:
        """Start the execution manager."""
        ...

    async def stop(self) -> None:
        """Stop the execution manager."""
        ...

    async def is_running(self) -> bool:
        """Return whether the manager is running."""
        ...

    async def health_check(self) -> dict[str, Any]:
        """Return health status."""
        ...


# ─── Event Handler Port ──────────────────────────────────────────────────


@runtime_checkable
class ExecutionEventHandlerPort(Protocol):
    """Port for handling execution events.

    Designed for future Event Bus integration.
    """

    async def on_event(self, event: ExecutionEvent) -> None:
        """Handle an execution event.

        Args:
            event: The execution event to handle.
        """
        ...


# ─── Sink ────────────────────────────────────────────────────────────────


@runtime_checkable
class ExecutionSink(Protocol):
    """Consumer of final execution results."""

    async def on_execution_result(self, result: ExecutionResult) -> None:
        """Called when an execution completes.

        Args:
            result: The final execution result.
        """
        ...
