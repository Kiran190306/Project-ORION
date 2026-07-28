"""
Project ORION - Enterprise Broker Execution & Recovery Layer (EPIC-009 Sprint-2).

Provides production-grade broker execution adapters that translate domain
execution requests into broker-specific API calls and broker responses back
into domain models. Execution remains completely broker-agnostic through
strict dependency inversion.

Modules:
- broker_adapter: Abstract base class defining the adapter contract
- execution_router: Routes execution requests to registered adapters
- retry_policy: Configurable retry strategy with exponential backoff
- circuit_breaker: Circuit breaker for protecting execution layer
- idempotency: Prevents duplicate execution via execution/order keys
- execution_metrics: Tracks execution latency, fill latency, retry, recovery
- paper_execution: Realistic simulated broker for paper trading
- mt5_execution: MT5 broker execution adapter
- oanda_execution: OANDA broker execution adapter
- binance_execution: Binance broker execution adapter
- order_recovery: Recovery for pending orders, open positions, partial fills
- session_recovery: Reconnect, re-authenticate, restore session, resume execution
- execution_audit: Immutable audit trail for all execution events
- execution_factory: Factory for creating adapter instances
- execution_registry: Registry managing adapter lifecycle and routing
"""

from __future__ import annotations

from libraries.infrastructure.execution.broker_adapter import (
    AccountInfo,
    BrokerAdapter,
    BrokerAdapterConfig,
    ExecutionAdapterError,
    ExecutionSymbolInfo,
    OrderExecutionInfo,
    PositionInfo,
)
from libraries.infrastructure.execution.circuit_breaker import (
    ExecutionCircuitBreaker,
    ExecutionCircuitBreakerConfig,
    ExecutionCircuitBreakerState,
    ExecutionCircuitBreakerStats,
)
from libraries.infrastructure.execution.execution_audit import (
    AuditEntry,
    AuditRecord,
    ExecutionAuditor,
    ExecutionAuditorConfig,
)
from libraries.infrastructure.execution.execution_factory import (
    ExecutionAdapterFactory,
    ExecutionAdapterSpec,
)
from libraries.infrastructure.execution.execution_metrics import (
    ExecutionMetricsCollector,
    ExecutionMetricsSnapshot,
)
from libraries.infrastructure.execution.execution_registry import (
    AdapterHealthStatus,
    ExecutionRegistry,
    ExecutionRegistryConfig,
    RegisteredAdapter,
)
from libraries.infrastructure.execution.execution_router import (
    ExecutionRouter,
    ExecutionRouterConfig,
    RoutingDecision,
    RoutingTarget,
)
from libraries.infrastructure.execution.idempotency import (
    IdempotencyConfig,
    IdempotencyGuard,
    IdempotencyRecord,
)
from libraries.infrastructure.execution.order_recovery import (
    OrderRecoveryConfig,
    OrderRecoveryEngine,
    OrderRecoveryResult,
    OrderRecoveryStatus,
)
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
    PaperFill,
    PaperOrder,
    PaperPosition,
)
from libraries.infrastructure.execution.retry_policy import (
    ExecutionRetryConfig,
    ExecutionRetryPolicy,
    RetryOutcome,
)
from libraries.infrastructure.execution.session_recovery import (
    SessionRecoveryConfig,
    SessionRecoveryEngine,
    SessionRecoveryResult,
    SessionRecoveryStatus,
)

__all__ = [
    # Broker Adapter
    "BrokerAdapter",
    "BrokerAdapterConfig",
    "ExecutionAdapterError",
    "AccountInfo",
    "PositionInfo",
    "OrderExecutionInfo",
    "ExecutionSymbolInfo",
    # Execution Router
    "ExecutionRouter",
    "ExecutionRouterConfig",
    "RoutingDecision",
    "RoutingTarget",
    # Retry Policy
    "ExecutionRetryPolicy",
    "ExecutionRetryConfig",
    "RetryOutcome",
    # Circuit Breaker
    "ExecutionCircuitBreaker",
    "ExecutionCircuitBreakerConfig",
    "ExecutionCircuitBreakerStats",
    "ExecutionCircuitBreakerState",
    # Idempotency
    "IdempotencyGuard",
    "IdempotencyConfig",
    "IdempotencyRecord",
    # Execution Metrics
    "ExecutionMetricsCollector",
    "ExecutionMetricsSnapshot",
    # Paper Execution
    "PaperExecutionAdapter",
    "PaperExecutionConfig",
    "PaperOrder",
    "PaperFill",
    "PaperPosition",
    # Order Recovery
    "OrderRecoveryEngine",
    "OrderRecoveryConfig",
    "OrderRecoveryResult",
    "OrderRecoveryStatus",
    # Session Recovery
    "SessionRecoveryEngine",
    "SessionRecoveryConfig",
    "SessionRecoveryResult",
    "SessionRecoveryStatus",
    # Execution Audit
    "ExecutionAuditor",
    "ExecutionAuditorConfig",
    "AuditEntry",
    "AuditRecord",
    # Factory
    "ExecutionAdapterFactory",
    "ExecutionAdapterSpec",
    # Registry
    "ExecutionRegistry",
    "ExecutionRegistryConfig",
    "RegisteredAdapter",
    "AdapterHealthStatus",
]
