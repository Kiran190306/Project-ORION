"""Integration tests for the Enterprise Broker Execution & Recovery Layer."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.execution.models import (
    Order,
    OrderId,
    OrderSide,
    OrderStatus,
    OrderType,
)
from libraries.infrastructure.execution.circuit_breaker import (
    ExecutionCircuitBreaker,
    ExecutionCircuitBreakerConfig,
)
from libraries.infrastructure.execution.execution_audit import ExecutionAuditor
from libraries.infrastructure.execution.execution_factory import (
    ExecutionAdapterFactory,
    ExecutionAdapterSpec,
)
from libraries.infrastructure.execution.execution_metrics import (
    ExecutionMetricsCollector,
)
from libraries.infrastructure.execution.execution_registry import (
    ExecutionRegistry,
    ExecutionRegistryConfig,
)
from libraries.infrastructure.execution.execution_router import (
    ExecutionRouter,
    ExecutionRouterConfig,
)
from libraries.infrastructure.execution.idempotency import (
    IdempotencyConfig,
    IdempotencyGuard,
)
from libraries.infrastructure.execution.order_recovery import (
    OrderRecoveryConfig,
    OrderRecoveryEngine,
)
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)
from libraries.infrastructure.execution.retry_policy import (
    ExecutionRetryConfig,
    ExecutionRetryPolicy,
)
from libraries.infrastructure.execution.session_recovery import (
    SessionRecoveryConfig,
    SessionRecoveryEngine,
)


class TestExecutionIntegration:
    """Integration tests combining multiple execution components."""

    @pytest.fixture
    async def components(self):
        """Set up a complete execution environment with paper trading."""
        # Create paper adapter
        paper_config = PaperExecutionConfig(
            broker_name="paper",
            balance=Decimal("100000"),
            latency_ms_mean=0.0,
            latency_ms_std=0.0,
        )
        paper = PaperExecutionAdapter(paper_config)
        await paper.connect()
        await paper.set_current_price("EURUSD", Decimal("1.20000"))

        # Create router
        router = ExecutionRouter(ExecutionRouterConfig(enable_fallback=True))
        spec = ExecutionAdapterSpec(provider="paper", name="paper", priority=1)
        target = ExecutionAdapterFactory.create_routing_target(spec)
        await router.register_adapter(paper, target)

        # Create other components
        metrics = ExecutionMetricsCollector()
        auditor = ExecutionAuditor()
        idempotency = IdempotencyGuard(IdempotencyConfig())
        retry = ExecutionRetryPolicy(
            ExecutionRetryConfig(
                max_retries=2,
                base_delay_ms=1.0,
            )
        )
        circuit_breaker = ExecutionCircuitBreaker(
            ExecutionCircuitBreakerConfig(name="execution", failure_threshold=5)
        )
        order_recovery = OrderRecoveryEngine(OrderRecoveryConfig(query_broker_on_recovery=False))
        session_recovery = SessionRecoveryEngine(SessionRecoveryConfig(max_reconnect_attempts=2))
        registry = ExecutionRegistry(
            router,
            ExecutionRegistryConfig(health_check_interval_seconds=3600),
        )

        yield {
            "paper": paper,
            "router": router,
            "metrics": metrics,
            "auditor": auditor,
            "idempotency": idempotency,
            "retry": retry,
            "circuit_breaker": circuit_breaker,
            "order_recovery": order_recovery,
            "session_recovery": session_recovery,
            "registry": registry,
        }

        await paper.disconnect()

    @pytest.mark.asyncio
    async def test_full_execution_flow(self, components):
        """Test the complete execution flow end-to-end."""
        order = Order(
            order_id=OrderId("integ_test_001"),
            decision_id="integ_dec1",
            execution_id="integ_exec1",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1"),
        )

        # 1. Route the order
        decision = await components["router"].route(order)
        assert decision.selected_broker == "paper"

        # 2. Check idempotency
        request_hash = IdempotencyGuard.compute_request_hash(
            {
                "symbol": order.symbol,
                "side": order.side.value,
                "quantity": str(order.quantity),
            }
        )
        is_dup = await components["idempotency"].is_duplicate(
            order.execution_id, order.order_id, request_hash
        )
        assert not is_dup
        await components["idempotency"].check_and_register(
            order.execution_id, order.order_id, request_hash
        )

        # 3. Execute through circuit breaker
        adapter = await components["router"].get_adapter("paper")
        assert adapter is not None

        async def execute():
            return await adapter.submit_order(order)

        result = await components["circuit_breaker"].execute(execute)

        # 4. Audit the execution
        await components["auditor"].record_submission(
            broker_name="paper",
            order_id=order.order_id,
            execution_id=order.execution_id,
            symbol=order.symbol,
        )

        # 5. Record metrics
        status_str = result.status.value if hasattr(result.status, "value") else str(result.status)
        await components["metrics"].record_execution(
            broker_name="paper",
            success=status_str in ("filled", "partially_filled"),
            latency_ms=50.0,
            volume=result.filled_quantity,
        )

        # 6. Verify results
        audit_record = await components["auditor"].get_execution_audit(order.execution_id)
        assert audit_record.entry_count >= 1

        snapshot = await components["metrics"].get_snapshot()
        assert snapshot.total_executions == 1

    @pytest.mark.asyncio
    async def test_recovery_flow(self, components):
        """Test recovery after simulated failure."""
        order = Order(
            order_id=OrderId("integ_recovery_001"),
            decision_id="integ_rec_dec1",
            execution_id="integ_rec_exec1",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1"),
            status=OrderStatus.SUBMITTED,
        )

        # Simulate order recovery
        adapter = components["paper"]
        result = await components["order_recovery"].recover_pending_order(order, adapter)
        assert result.status.value in ("recovered", "not_found")

    @pytest.mark.asyncio
    async def test_session_recovery_flow(self, components):
        """Test session recovery."""
        adapter = components["paper"]
        result = await components["session_recovery"].recover_session(adapter)
        assert result.status.value == "completed"

    @pytest.mark.asyncio
    async def test_retry_then_succeed(self, components):
        """Test retry policy with eventual success."""
        call_count = [0]

        async def operation():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("temporary")
            return "success"

        config = ExecutionRetryConfig(
            max_retries=3,
            retry_on_connection_error=True,
            base_delay_ms=1.0,
        )
        retry = ExecutionRetryPolicy(config)
        result, attempts = await retry.execute(operation, context="integration test")
        assert result == "success"
        assert call_count[0] >= 2

    @pytest.mark.asyncio
    async def test_circuit_breaker_protection(self, components):
        """Test circuit breaker prevents cascading failures."""
        cb = components["circuit_breaker"]

        async def fail():
            raise ValueError("persistent error")

        # Trip the circuit
        for _ in range(5):
            with pytest.raises(ValueError):
                await cb.execute(fail)

        from libraries.infrastructure.execution.circuit_breaker import (
            CircuitBreakerOpenError,
            ExecutionCircuitBreakerState,
        )

        assert cb.state == ExecutionCircuitBreakerState.OPEN

        # Should fail fast
        with pytest.raises(CircuitBreakerOpenError):
            await cb.execute(lambda: "should not run")

    @pytest.mark.asyncio
    async def test_idempotency_prevention(self, components):
        """Test that duplicate executions are prevented."""
        exec_id = "unique_exec_001"
        order_id = "unique_order_001"
        hash_val = "unique_hash_001"

        # First time should succeed
        await components["idempotency"].check_and_register(exec_id, order_id, hash_val)

        # Second time should raise
        from libraries.infrastructure.execution.idempotency import (
            DuplicateExecutionError,
        )

        with pytest.raises(DuplicateExecutionError):
            await components["idempotency"].check_and_register(exec_id, order_id, hash_val)
