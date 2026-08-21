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
    "BrokerCapabilities",
    "BrokerOrderId",
    "BrokerOrderStatusPort",
    "BrokerSubmitterPort",
    "DeduplicationConfig",
    "DuplicateOrderError",
    "EngineExecutionResult",
    "ExecutionContext",
    # Engine
    "ExecutionEngine",
    "ExecutionEngineConfig",
    "ExecutionEngineError",
    "ExecutionEngineNotReadyError",
    "ExecutionEngineShutdownError",
    # Exceptions
    "ExecutionError",
    "ExecutionEvent",
    "ExecutionEventHandlerPort",
    "ExecutionEventType",
    "ExecutionManagerPort",
    "ExecutionMode",
    "ExecutionOutcome",
    "ExecutionQualityScore",
    "ExecutionReport",
    "ExecutionResult",
    "ExecutionResultStatus",
    # Interfaces
    "ExecutionSink",
    # Statistics
    "ExecutionStatistics",
    "ExecutionStats",
    "Fill",
    # Confirmation
    "FillConfirmation",
    "FillValidationError",
    "FillValidator",
    "FillValidatorConfig",
    "InvalidOrderStateError",
    "InvalidTransitionError",
    "LifecycleSnapshot",
    "MarketDataPort",
    # Models
    "Order",
    "OrderBuildError",
    # Builder
    "OrderBuilder",
    "OrderBuilderConfig",
    "OrderBuilderPort",
    "OrderConfirmationPort",
    "OrderDeduplicationPort",
    # Deduplication
    "OrderDeduplicator",
    "OrderId",
    "OrderLifecyclePort",
    # Lifecycle / State Machine
    "OrderLifecycleTracker",
    "OrderNotFoundError",
    # Recovery
    "OrderRecoveryHandler",
    "OrderRejectedByBrokerError",
    "OrderRetryPort",
    # Router
    "OrderRouter",
    "OrderRouterConfig",
    "OrderRouterPort",
    "OrderSide",
    "OrderStateMachine",
    "OrderStatisticsPort",
    "OrderStatus",
    "OrderTimeInForce",
    # Tracker
    "OrderTracker",
    "OrderType",
    "OrderValidationError",
    # Validator
    "OrderValidator",
    "OrderValidatorConfig",
    "OrderValidatorPort",
    "PartialFillTracker",
    "PortfolioSyncPort",
    "RecoveryAttempt",
    "RecoveryConfig",
    "RecoveryError",
    "RecoveryState",
    "RetryAttempt",
    "RetryConfig",
    "RetryExhaustedError",
    # Retry
    "RetryHandler",
    "RetryState",
    "RiskEnginePort",
    "RouterScore",
    "RoutingError",
    "RoutingResult",
    "SlippageMetrics",
    "SlippageReport",
    "StateTransition",
    "TimeoutError",
    "TrackedEntry",
    "TradeDecisionSource",
    "Trigger",
    "ValidationResult",
]
