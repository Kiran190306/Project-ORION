"""
Project ORION - Smart Order Execution Engine (EPIC-008 Sprint-1).

Broker-agnostic execution engine that receives APPROVED trades from the
Risk Engine, constructs executable orders, routes them to the appropriate
broker, tracks lifecycle, and returns execution results.

No broker-specific logic exists in the domain layer. Broker communication
happens exclusively through injected protocol ports.
"""

from __future__ import annotations

from libraries.domain.execution.builder import OrderBuilder, OrderBuilderConfig
from libraries.domain.execution.confirmation import (
    FillConfirmation,
    FillValidator,
    FillValidatorConfig,
)
from libraries.domain.execution.context import ExecutionContext, ExecutionMode
from libraries.domain.execution.deduplication import (
    DeduplicationConfig,
    OrderDeduplicator,
    TrackedEntry,
)
from libraries.domain.execution.engine import (
    EngineExecutionResult,
    ExecutionEngine,
    ExecutionEngineConfig,
)
from libraries.domain.execution.exceptions import (
    DuplicateOrderError,
    ExecutionEngineError,
    ExecutionEngineNotReadyError,
    ExecutionEngineShutdownError,
    ExecutionError,
    FillValidationError,
    InvalidOrderStateError,
    InvalidTransitionError,
    OrderBuildError,
    OrderNotFoundError,
    OrderRejectedByBrokerError,
    OrderValidationError,
    RecoveryError,
    RetryExhaustedError,
    RoutingError,
    TimeoutError,
)
from libraries.domain.execution.interfaces import (
    BrokerOrderStatusPort,
    BrokerSubmitterPort,
    ExecutionEventHandlerPort,
    ExecutionManagerPort,
    ExecutionSink,
    MarketDataPort,
    OrderBuilderPort,
    OrderConfirmationPort,
    OrderDeduplicationPort,
    OrderLifecyclePort,
    OrderRetryPort,
    OrderRouterPort,
    OrderStatisticsPort,
    OrderValidatorPort,
    PortfolioSyncPort,
    RiskEnginePort,
    TradeDecisionSource,
)
from libraries.domain.execution.lifecycle import (
    LifecycleSnapshot,
    OrderLifecycleTracker,
)
from libraries.domain.execution.models import (
    BrokerOrderId,
    ExecutionEvent,
    ExecutionEventType,
    ExecutionQualityScore,
    ExecutionReport,
    ExecutionResult,
    ExecutionResultStatus,
    Fill,
    Order,
    OrderId,
    OrderSide,
    OrderStatus,
    OrderTimeInForce,
    OrderType,
    PartialFillTracker,
    SlippageMetrics,
    SlippageReport,
)
from libraries.domain.execution.recovery import (
    OrderRecoveryHandler,
    RecoveryAttempt,
    RecoveryConfig,
    RecoveryState,
)
from libraries.domain.execution.retry import (
    RetryAttempt,
    RetryConfig,
    RetryHandler,
    RetryState,
)
from libraries.domain.execution.router import (
    BrokerCapabilities,
    OrderRouter,
    OrderRouterConfig,
    RouterScore,
    RoutingResult,
)
from libraries.domain.execution.state_machine import (
    OrderStateMachine,
    StateTransition,
    Trigger,
)
from libraries.domain.execution.statistics import (
    ExecutionOutcome,
    ExecutionStatistics,
    ExecutionStats,
)
from libraries.domain.execution.tracker import OrderTracker
from libraries.domain.execution.validator import (
    OrderValidator,
    OrderValidatorConfig,
    ValidationResult,
)

__all__ = [
    # Engine
    "ExecutionEngine",
    "ExecutionEngineConfig",
    "EngineExecutionResult",
    "ExecutionContext",
    "ExecutionMode",
    # Builder
    "OrderBuilder",
    "OrderBuilderConfig",
    # Validator
    "OrderValidator",
    "OrderValidatorConfig",
    "ValidationResult",
    # Router
    "OrderRouter",
    "OrderRouterConfig",
    "RouterScore",
    "RoutingResult",
    "BrokerCapabilities",
    # Retry
    "RetryHandler",
    "RetryConfig",
    "RetryAttempt",
    "RetryState",
    # Confirmation
    "FillConfirmation",
    "FillValidator",
    "FillValidatorConfig",
    # Deduplication
    "OrderDeduplicator",
    "DeduplicationConfig",
    "TrackedEntry",
    # Lifecycle / State Machine
    "OrderLifecycleTracker",
    "LifecycleSnapshot",
    "OrderStateMachine",
    "StateTransition",
    "Trigger",
    # Tracker
    "OrderTracker",
    # Recovery
    "OrderRecoveryHandler",
    "RecoveryConfig",
    "RecoveryAttempt",
    "RecoveryState",
    # Statistics
    "ExecutionStatistics",
    "ExecutionStats",
    "ExecutionOutcome",
    # Models
    "Order",
    "OrderId",
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "OrderTimeInForce",
    "Fill",
    "PartialFillTracker",
    "ExecutionResult",
    "ExecutionResultStatus",
    "ExecutionReport",
    "ExecutionQualityScore",
    "SlippageMetrics",
    "SlippageReport",
    "BrokerOrderId",
    "ExecutionEvent",
    "ExecutionEventType",
    # Interfaces
    "ExecutionSink",
    "TradeDecisionSource",
    "RiskEnginePort",
    "MarketDataPort",
    "OrderValidatorPort",
    "OrderBuilderPort",
    "OrderRouterPort",
    "OrderRetryPort",
    "OrderConfirmationPort",
    "OrderDeduplicationPort",
    "OrderLifecyclePort",
    "OrderStatisticsPort",
    "BrokerSubmitterPort",
    "BrokerOrderStatusPort",
    "ExecutionManagerPort",
    "ExecutionEventHandlerPort",
    "PortfolioSyncPort",
    # Exceptions
    "ExecutionError",
    "ExecutionEngineError",
    "ExecutionEngineNotReadyError",
    "ExecutionEngineShutdownError",
    "OrderValidationError",
    "OrderBuildError",
    "RoutingError",
    "DuplicateOrderError",
    "OrderNotFoundError",
    "OrderRejectedByBrokerError",
    "InvalidOrderStateError",
    "InvalidTransitionError",
    "FillValidationError",
    "RetryExhaustedError",
    "TimeoutError",
    "RecoveryError",
]
