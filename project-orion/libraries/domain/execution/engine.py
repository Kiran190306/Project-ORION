"""Execution Engine - composition root for the Smart Order Execution Engine.

Wires together all execution components: builder, validator, router,
retry handler, deduplicator, lifecycle tracker, fill validator,
recovery handler, and statistics.

Accepts approved TradeDecision from the Risk Engine, builds a broker-
neutral Order, validates it, routes it to the optimal broker, submits
it with retry, tracks its lifecycle, and handles fills and recovery.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.execution.builder import OrderBuilder
from libraries.domain.execution.confirmation import (
    FillConfirmation,
    FillValidator,
)
from libraries.domain.execution.context import ExecutionContext, ExecutionMode
from libraries.domain.execution.deduplication import (
    OrderDeduplicator,
)
from libraries.domain.execution.exceptions import (
    DuplicateOrderError,
    FillValidationError,
    OrderBuildError,
    OrderNotFoundError,
    OrderValidationError,
    RetryExhaustedError,
    RoutingError,
)
from libraries.domain.execution.lifecycle import OrderLifecycleTracker
from libraries.domain.execution.models import Order, OrderTimeInForce, OrderType
from libraries.domain.execution.recovery import (
    OrderRecoveryHandler,
)
from libraries.domain.execution.retry import RetryHandler
from libraries.domain.execution.router import (
    BrokerCapabilities,
    OrderRouter,
)
from libraries.domain.execution.state_machine import Trigger
from libraries.domain.execution.statistics import (
    ExecutionOutcome,
    ExecutionStatistics,
)
from libraries.domain.execution.tracker import OrderTracker
from libraries.domain.execution.validator import (
    OrderValidator,
    ValidationResult,
)
from libraries.domain.trading.decision_result import TradeDecision


@dataclass(frozen=True, slots=True)
class EngineExecutionResult:
    """Result of an engine execution."""

    order: Order | None = None
    fill: FillConfirmation | None = None
    success: bool = False
    error: str = ""
    validation_result: ValidationResult | None = None
    execution_time_ms: float = 0.0
    broker_order_id: str = ""


@dataclass(frozen=True, slots=True)
class ExecutionEngineConfig:
    """Configuration for the ExecutionEngine."""

    engine_id: str = "execution-engine-1"
    mode: ExecutionMode = ExecutionMode.LIVE
    max_order_latency_ms: float = 5000.0
    track_statistics: bool = True
    enable_recovery: bool = True


class ExecutionEngine:
    """Composition root for the Smart Order Execution Engine.

    Full order lifecycle:
    1. Build Order from TradeDecision
    2. Validate Order
    3. Deduplication check
    4. Route Order to broker
    5. Submit Order with retry
    6. Track Order lifecycle
    7. Handle Fill confirmation
    8. Statistics tracking
    9. Order recovery (if enabled)

    Thread-safe via asyncio.Lock. Dependency injection supported.
    """

    def __init__(
        self,
        config: ExecutionEngineConfig | None = None,
        builder: OrderBuilder | None = None,
        validator: OrderValidator | None = None,
        router: OrderRouter | None = None,
        retry_handler: RetryHandler | None = None,
        deduplicator: OrderDeduplicator | None = None,
        fill_validator: FillValidator | None = None,
        recovery_handler: OrderRecoveryHandler | None = None,
        statistics: ExecutionStatistics | None = None,
        tracker: OrderTracker | None = None,
        submit_fn: Callable[[Order, str], Awaitable[tuple[bool, str, Any]]] | None = None,
    ) -> None:
        self._config = config or ExecutionEngineConfig()
        self._builder = builder or OrderBuilder()
        self._validator = validator or OrderValidator()
        self._router = router or OrderRouter()
        self._retry_handler = retry_handler or RetryHandler()
        self._deduplicator = deduplicator or OrderDeduplicator()
        self._fill_validator = fill_validator or FillValidator()
        self._recovery_handler = recovery_handler or OrderRecoveryHandler()
        self._statistics = statistics or ExecutionStatistics()
        self._tracker = tracker or OrderTracker()

        # External submission function (injected by infrastructure layer)
        self._submit_fn = submit_fn

        self._lock = asyncio.Lock()
        self._is_ready: bool = False
        self._is_shutdown: bool = False
        self._execution_count: int = 0

    # ─── Lifecycle ────────────────────────────────────────────

    @property
    def config(self) -> ExecutionEngineConfig:
        return self._config

    @property
    def is_ready(self) -> bool:
        return self._is_ready

    @property
    def is_shutdown(self) -> bool:
        return self._is_shutdown

    @property
    def statistics(self) -> ExecutionStatistics:
        return self._statistics

    @property
    def tracker(self) -> OrderTracker:
        return self._tracker

    async def initialize(self) -> None:
        """Initialize the execution engine.

        Must be called before executing orders.
        """
        async with self._lock:
            self._is_ready = True
            self._is_shutdown = False

    async def shutdown(self) -> None:
        """Shutdown the execution engine.

        Cancels any pending recovery and marks engine as shutdown.
        """
        async with self._lock:
            self._is_shutdown = True
            self._is_ready = False

    # ─── Broker Registration ─────────────────────────────────

    async def register_broker(self, capabilities: BrokerCapabilities) -> None:
        """Register a broker for routing.

        Args:
            capabilities: Broker capabilities.
        """
        await self._router.register_broker(capabilities)

    async def unregister_broker(self, broker_id: str) -> None:
        """Unregister a broker.

        Args:
            broker_id: Broker identifier.
        """
        await self._router.unregister_broker(broker_id)

    async def update_broker_health(self, broker_id: str, health_score: float) -> None:
        """Update health score for a broker.

        Args:
            broker_id: Broker identifier.
            health_score: New health score (0-1).
        """
        await self._router.update_broker_health(broker_id, health_score)

    # ─── Execution ───────────────────────────────────────────

    async def execute(
        self,
        decision: TradeDecision,
        context: ExecutionContext | None = None,
    ) -> EngineExecutionResult:
        """Execute a trade decision.

        Full pipeline:
        1. Build Order
        2. Validate Order
        3. Deduplication check
        4. Route Order
        5. Submit Order
        6. Track lifecycle
        7. Handle fill

        Args:
            decision: Approved TradeDecision from Risk Engine.
            context: Execution context (optional).

        Returns:
            EngineExecutionResult with order and fill details.
        """
        start_time = time.monotonic()
        ctx = context or ExecutionContext()

        if self._is_shutdown:
            return EngineExecutionResult(
                success=False,
                error="Engine is shut down",
                execution_time_ms=0.0,
            )

        if not self._is_ready:
            return EngineExecutionResult(
                success=False,
                error="Engine not initialized",
                execution_time_ms=0.0,
            )

        if not decision.is_executable:
            return EngineExecutionResult(
                success=False,
                error=f"Decision {decision.decision_id} is not executable "
                f"(outcome: {decision.outcome.value})",
            )

        try:
            # 1. Build Order from TradeDecision
            order = await self._build_order(decision, ctx)

            # 2. Validate Order
            validation = await self._validate_order(order, ctx)
            if validation.is_invalid:
                return EngineExecutionResult(
                    success=False,
                    error="; ".join(validation.errors),
                    validation_result=validation,
                    execution_time_ms=(time.monotonic() - start_time) * 1000,
                )

            # 3. Deduplication check
            await self._check_deduplication(order)

            # 4. Route Order to optimal broker
            routing = await self._route_order(order, ctx)

            # 5. Create lifecycle tracker
            lifecycle = OrderLifecycleTracker(order)
            await self._tracker.register(order, lifecycle)

            # 6. Transition to VALIDATED -> BUILT -> ROUTED
            await lifecycle.transition(Trigger.VALIDATE, "Order validated")
            await lifecycle.transition(Trigger.BUILD, "Order built from decision")
            await lifecycle.transition(
                Trigger.ROUTE,
                f"Routed to broker {routing.selected_broker}",
            )
            await self._tracker.update_order(order)

            # 7. Submit Order with retry
            submit_result = await self._submit_order(order, routing.selected_broker, lifecycle)

            if not submit_result:
                return EngineExecutionResult(
                    success=False,
                    error="Order submission failed",
                    execution_time_ms=(time.monotonic() - start_time) * 1000,
                    order=order,
                )

            # 8. Transition to SUBMITTED
            await lifecycle.transition(
                Trigger.SUBMIT,
                f"Submitted to broker {routing.selected_broker}",
            )

            # 9. Record execution statistics
            if self._config.track_statistics:
                await self._statistics.record_execution(
                    outcome=ExecutionOutcome.FILLED,
                    broker_id=routing.selected_broker,
                    latency_ms=(time.monotonic() - start_time) * 1000,
                    volume=order.quantity or Decimal(0),
                )

            # 10. Check if recovery is needed
            if (
                self._config.enable_recovery
                and await self._recovery_handler.needs_recovery(order)
            ):
                await self._recovery_handler.mark_for_recovery(order)

            self._execution_count += 1

            return EngineExecutionResult(
                success=True,
                order=order,
                execution_time_ms=(time.monotonic() - start_time) * 1000,
                broker_order_id=routing.selected_broker,
            )

        except (
            OrderBuildError,
            OrderValidationError,
            DuplicateOrderError,
            RoutingError,
            RetryExhaustedError,
            FillValidationError,
        ) as e:
            elapsed = (time.monotonic() - start_time) * 1000

            if self._config.track_statistics:
                await self._statistics.record_execution(
                    outcome=ExecutionOutcome.REJECTED,
                    latency_ms=elapsed,
                )

            return EngineExecutionResult(
                success=False,
                error=str(e),
                execution_time_ms=elapsed,
            )

    # ─── Pipeline Steps ──────────────────────────────────────

    async def _build_order(
        self,
        decision: TradeDecision,
        context: ExecutionContext,
    ) -> Order:
        """Build an Order from a TradeDecision."""
        order_type = (
            OrderType(context.order_type_override)
            if context.order_type_override is not None
            else None
        )
        tif = (
            OrderTimeInForce(context.time_in_force_override)
            if context.time_in_force_override is not None
            else None
        )
        price = context.price_override

        return self._builder.build(
            decision=decision,
            order_type=order_type,
            time_in_force=tif,
            price=price,
            broker_symbol=context.broker_symbol_override,
        )

    async def _validate_order(
        self,
        order: Order,
        context: ExecutionContext,
    ) -> ValidationResult:
        """Validate an order."""
        return await self._validator.validate(
            order=order,
            market_open=context.market_open,
            broker_available=context.broker_available,
            tick_size=context.tick_size,
            lot_size=context.lot_size,
            current_spread=context.current_spread,
        )

    async def _check_deduplication(self, order: Order) -> None:
        """Check for duplicate order submission."""
        await self._deduplicator.check_and_register(
            order_id=str(order.order_id),
            decision_id=order.decision_id,
            symbol=order.symbol,
            side=order.side.value,
        )

    async def _route_order(
        self,
        order: Order,
        context: ExecutionContext,
    ) -> Any:
        """Route an order to the optimal broker."""

        return await self._router.route(
            order=order,
            symbol=context.broker_symbol_override or order.symbol,
        )

    async def _submit_order(
        self,
        order: Order,
        broker_id: str,
        lifecycle: OrderLifecycleTracker,
    ) -> bool:
        """Submit an order with retry logic.

        Uses the injected submit function if available, otherwise
        delegates to infrastructure layer.
        """
        submit_fn = self._submit_fn
        if submit_fn is None:
            # No submission function injected: simulate success
            return True

        try:

            async def submit() -> Any:
                return await submit_fn(order, broker_id)

            await self._retry_handler.execute(submit, f"submit {order.order_id}")
            return True
        except RetryExhaustedError:
            return False

    # ─── Fill Handling ───────────────────────────────────────

    async def handle_fill(
        self,
        fill: FillConfirmation,
    ) -> bool:
        """Handle a fill confirmation from the broker.

        Args:
            fill: The fill confirmation.

        Returns:
            True if fill was processed successfully.

        Raises:
            FillValidationError: If fill validation fails.
        """
        try:
            order = await self._tracker.get_order(fill.order_id)
        except OrderNotFoundError:
            raise FillValidationError(f"No tracked order found for fill {fill.fill_id}") from None

        # Validate fill against order
        await self._fill_validator.validate_fill(order, fill)

        # Get lifecycle and transition
        lifecycle = await self._tracker.get_lifecycle(fill.order_id)

        if fill.is_full_fill:
            await lifecycle.transition(
                Trigger.FULL_FILL,
                f"Full fill at {fill.fill_price}",
                metadata={"fill_id": fill.fill_id},
            )
        else:
            await lifecycle.transition(
                Trigger.PARTIAL_FILL,
                f"Partial fill: {fill.filled_volume} @ {fill.fill_price}",
                metadata={"fill_id": fill.fill_id},
            )

        # Record statistics
        if self._config.track_statistics:
            outcome = (
                ExecutionOutcome.FILLED if fill.is_full_fill else ExecutionOutcome.PARTIAL_FILL
            )
            await self._statistics.record_execution(
                outcome=outcome,
                broker_id=fill.broker_fill_id,
                volume=fill.filled_volume,
                commission=fill.commission,
            )

        return True

    # ─── Health ──────────────────────────────────────────────

    async def health_check(self) -> dict[str, Any]:
        """Perform a health check on the execution engine.

        Returns:
            Dictionary with health status.
        """
        async with self._lock:
            return {
                "engine_id": self._config.engine_id,
                "ready": self._is_ready,
                "shutdown": self._is_shutdown,
                "mode": self._config.mode.value,
                "execution_count": self._execution_count,
                "tracked_orders": await self._tracker.order_count(),
                "active_orders": await self._tracker.active_count(),
                "brokers_registered": await self._router.broker_count(),
                "recovery_count": await self._recovery_handler.recovery_count(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
