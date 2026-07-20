"""
Project ORION - Production Streaming Layer (EPIC-005 Sprint-3).

Event-driven streaming infrastructure for market data delivery.
Provides event bus, buffering, backpressure, caching, rate limiting,
circuit breaking, health monitoring, metrics, and graceful shutdown
for the Market Data Engine and Broker Connectors.

Extensible for Kafka, Redis Streams, NATS, RabbitMQ and ZeroMQ
by implementing the EventBus ABC.
"""

from __future__ import annotations

from libraries.infrastructure.event_stream.backpressure import (
    AdaptiveFlowController,
    BackpressureMode,
    FlowControlState,
)
from libraries.infrastructure.event_stream.buffer import (
    BufferMetrics,
    BufferOverflowPolicy,
    StreamBuffer,
)
from libraries.infrastructure.event_stream.cache import (
    CachedSnapshot,
    CacheMetrics,
    MarketSnapshotCache,
)
from libraries.infrastructure.event_stream.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitBreakerStats,
    CircuitState,
)
from libraries.infrastructure.event_stream.event_bus import (
    DeadLetterEvent,
    EventBus,
    EventBusError,
    EventSubscription,
    InMemoryPriorityBus,
    PriorityEventBus,
)
from libraries.infrastructure.event_stream.event_types import (
    BufferDroppedEvent,
    CacheHitRateEvent,
    CircuitBreakerEvent,
    ConnectionStatusEvent,
    ErrorIsolatedEvent,
    EventPriority,
    EventStreamEvent,
    ProviderUptimeEvent,
    QueueDepthEvent,
    RateLimitEvent,
    SnapshotPublishedEvent,
    ThroughputEvent,
    TickReceivedEvent,
)
from libraries.infrastructure.event_stream.health import (
    HealthStatus,
    StreamHealth,
)
from libraries.infrastructure.event_stream.metrics import (
    MetricSample,
    StreamMetricsCollector,
    StreamMetricSnapshot,
)
from libraries.infrastructure.event_stream.publisher import (
    PublisherStats,
    StreamPublisher,
)
from libraries.infrastructure.event_stream.queue import (
    PriorityQueue,
    PriorityQueueItem,
)
from libraries.infrastructure.event_stream.rate_limiter import (
    RateLimiter,
    RateLimiterConfig,
    RateLimiterStats,
)
from libraries.infrastructure.event_stream.shutdown import (
    GracefulShutdown,
    ShutdownPhase,
    ShutdownResult,
    ShutdownTask,
)
from libraries.infrastructure.event_stream.stream_manager import (
    StreamManager,
    StreamManagerConfig,
)
from libraries.infrastructure.event_stream.subscriber import (
    StreamSubscriber,
    SubscriberCallbackError,
    SubscriberStats,
)

__all__ = [
    "AdaptiveFlowController",
    "BackpressureMode",
    "BufferDroppedEvent",
    "BufferMetrics",
    "BufferOverflowPolicy",
    "CacheHitRateEvent",
    "CacheMetrics",
    "CachedSnapshot",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerEvent",
    "CircuitBreakerOpenError",
    "CircuitBreakerStats",
    "CircuitState",
    "ConnectionStatusEvent",
    "DeadLetterEvent",
    "ErrorIsolatedEvent",
    "EventBus",
    "EventBusError",
    "EventPriority",
    "EventStreamEvent",
    "EventSubscription",
    "FlowControlState",
    "GracefulShutdown",
    "HealthStatus",
    "InMemoryPriorityBus",
    "MarketSnapshotCache",
    "MetricSample",
    "PriorityEventBus",
    "PriorityQueue",
    "PriorityQueueItem",
    "ProviderUptimeEvent",
    "PublisherStats",
    "QueueDepthEvent",
    "RateLimitEvent",
    "RateLimiter",
    "RateLimiterConfig",
    "RateLimiterStats",
    "ShutdownPhase",
    "ShutdownResult",
    "ShutdownTask",
    "SnapshotPublishedEvent",
    "StreamBuffer",
    "StreamHealth",
    "StreamManager",
    "StreamManagerConfig",
    "StreamMetricsCollector",
    "StreamMetricSnapshot",
    "StreamPublisher",
    "StreamSubscriber",
    "SubscriberCallbackError",
    "SubscriberStats",
    "ThroughputEvent",
    "TickReceivedEvent",
]
