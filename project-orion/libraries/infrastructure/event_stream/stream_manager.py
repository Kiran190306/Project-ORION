"""Stream manager - composition root for the event streaming layer.

Integrates all streaming components:
- EventBus (publish/subscribe)
- StreamBuffer (FIFO buffering)
- MarketSnapshotCache (latest data cache)
- RateLimiter (token bucket per provider)
- CircuitBreaker (failure isolation)
- AdaptiveFlowController (backpressure)
- StreamHealth (health monitoring)
- StreamMetricsCollector (metrics)
- GracefulShutdown (lifecycle)

Wires into MarketDataManager via MarketDataPublisher protocol
without modifying its public interface.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from libraries.domain.market import MarketDataManager
from libraries.domain.market.interfaces import MarketDataPublisher
from libraries.infrastructure.event_stream.backpressure import (
    AdaptiveFlowController,
    BackpressureMode,
)
from libraries.infrastructure.event_stream.buffer import (
    BufferOverflowPolicy,
    StreamBuffer,
)
from libraries.infrastructure.event_stream.cache import MarketSnapshotCache
from libraries.infrastructure.event_stream.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
)
from libraries.infrastructure.event_stream.event_bus import (
    EventBus,
    InMemoryPriorityBus,
    PriorityEventBus,
)
from libraries.infrastructure.event_stream.event_types import (
    ConnectionStatusEvent,
    EventStreamEvent,
)
from libraries.infrastructure.event_stream.health import HealthStatus, StreamHealth
from libraries.infrastructure.event_stream.metrics import (
    StreamMetricsCollector,
    StreamMetricSnapshot,
)
from libraries.infrastructure.event_stream.publisher import StreamPublisher
from libraries.infrastructure.event_stream.rate_limiter import (
    RateLimiter,
    RateLimiterConfig,
)
from libraries.infrastructure.event_stream.shutdown import (
    GracefulShutdown,
    ShutdownPhase,
    ShutdownResult,
)
from libraries.infrastructure.event_stream.subscriber import StreamSubscriber


@dataclass(frozen=True, slots=True)
class StreamManagerConfig:
    """Configuration for the stream manager."""

    buffer_maxsize: int = 10000
    buffer_overflow_policy: BufferOverflowPolicy = BufferOverflowPolicy.DROP_OLDEST
    backpressure_high_water: int = 8000
    backpressure_low_water: int = 2000
    backpressure_mode: BackpressureMode = BackpressureMode.PAUSE_PRODUCER
    cache_default_ttl_seconds: float = 5.0
    bus_max_queue_size: int = 10000
    bus_max_dead_letter: int = 1000
    shutdown_timeout_seconds: float = 30.0
    rate_limiter_enabled: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_success_threshold: int = 3
    circuit_breaker_recovery_timeout_seconds: float = 30.0


class StreamManager:
    """Composition root for the production streaming layer.

    Wires together all streaming components and provides a unified
    interface for managing the streaming pipeline.

    Multiple stream managers can operate independently (one per
    MarketDataManager instance).
    """

    def __init__(
        self,
        config: StreamManagerConfig | None = None,
    ) -> None:
        self._config = config or StreamManagerConfig()

        # Core components
        self._buffer = StreamBuffer(
            maxsize=self._config.buffer_maxsize,
            overflow_policy=self._config.buffer_overflow_policy,
        )
        self._cache = MarketSnapshotCache(
            default_ttl_seconds=self._config.cache_default_ttl_seconds,
        )
        self._backpressure = AdaptiveFlowController(
            high_water_mark=self._config.backpressure_high_water,
            low_water_mark=self._config.backpressure_low_water,
            mode=self._config.backpressure_mode,
        )
        self._bus: InMemoryPriorityBus = InMemoryPriorityBus(
            max_queue_size=self._config.bus_max_queue_size,
            max_dead_letter=self._config.bus_max_dead_letter,
        )
        self._priority_bus = PriorityEventBus(self._bus)
        self._health = StreamHealth()
        self._metrics = StreamMetricsCollector()
        self._shutdown = GracefulShutdown(
            timeout_seconds=self._config.shutdown_timeout_seconds,
        )

        # Publishers and subscribers registry
        self._publishers: dict[str, StreamPublisher] = {}
        self._subscribers: dict[str, StreamSubscriber] = {}
        self._rate_limiters: dict[str, RateLimiter] = {}
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._provider_connections: dict[str, bool] = {}
        self._running = False
        self._lock = asyncio.Lock()
        self._tasks: list[asyncio.Task[None]] = []

    @property
    def bus(self) -> InMemoryPriorityBus:
        return self._bus

    @property
    def buffer(self) -> StreamBuffer:
        return self._buffer

    @property
    def cache(self) -> MarketSnapshotCache:
        return self._cache

    @property
    def health(self) -> StreamHealth:
        return self._health

    @property
    def metrics(self) -> StreamMetricsCollector:
        return self._metrics

    @property
    def backpressure(self) -> AdaptiveFlowController:
        return self._backpressure

    @property
    def shutdown_coordinator(self) -> GracefulShutdown:
        return self._shutdown

    @property
    def running(self) -> bool:
        return self._running

    # ─── Lifecycle ────────────────────────────────────────────

    async def start(self) -> None:
        """Start the stream manager and all components."""
        async with self._lock:
            if self._running:
                return
            self._running = True

        # Register shutdown tasks
        self._register_shutdown_tasks()

        # Start the event bus
        await self._bus.start()

        # Start health monitoring
        await self._update_health()

    async def stop(self) -> None:
        """Stop the stream manager gracefully."""
        async with self._lock:
            if not self._running:
                return
            self._running = False

        # Execute graceful shutdown
        await self._shutdown.execute()

    def _register_shutdown_tasks(self) -> None:
        """Register shutdown tasks for all components."""

        # Stop publishers
        async def _stop_publishers() -> None:
            for publisher in self._publishers.values():
                pass  # Publishers are stateless; bus handles cleanup

        self._shutdown.register(
            name="stop_publishers",
            phase=ShutdownPhase.STOP_PUBLISHERS,
            coro=_stop_publishers,
            timeout_seconds=5.0,
        )

        # Flush queues
        async def _flush_queues() -> None:
            await self._buffer.clear()

        self._shutdown.register(
            name="flush_buffer",
            phase=ShutdownPhase.FLUSH_QUEUES,
            coro=_flush_queues,
            timeout_seconds=10.0,
        )

        # Close transports
        async def _clear_cache() -> None:
            await self._cache.clear()

        self._shutdown.register(
            name="clear_cache",
            phase=ShutdownPhase.PERSIST_SNAPSHOTS,
            coro=_clear_cache,
            timeout_seconds=5.0,
        )

        # Stop bus
        async def _close_transports() -> None:
            await self._bus.stop()

        self._shutdown.register(
            name="stop_bus",
            phase=ShutdownPhase.CLOSE_TRANSPORTS,
            coro=_close_transports,
            timeout_seconds=5.0,
        )

        # Cancel tasks
        async def _cancel_tasks() -> None:
            for task in self._tasks:
                task.cancel()
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()

        self._shutdown.register(
            name="cancel_tasks",
            phase=ShutdownPhase.CANCEL_TASKS,
            coro=_cancel_tasks,
            timeout_seconds=5.0,
        )

    # ─── Provider Management ──────────────────────────────────

    async def register_provider(
        self,
        provider: str,
        rate_limit_tokens_per_second: float = 100.0,
        rate_limit_max_burst: int = 200,
        circuit_breaker_failure_threshold: int | None = None,
    ) -> None:
        """Register a provider with rate limiting and circuit breaker.

        Args:
            provider: Provider identifier.
            rate_limit_tokens_per_second: Maximum request rate.
            rate_limit_max_burst: Maximum burst size.
            circuit_breaker_failure_threshold: Failure threshold (uses config default if None).
        """
        async with self._lock:
            # Create rate limiter
            self._rate_limiters[provider] = RateLimiter(
                RateLimiterConfig(
                    provider=provider,
                    tokens_per_second=rate_limit_tokens_per_second,
                    max_burst=rate_limit_max_burst,
                    enabled=self._config.rate_limiter_enabled,
                )
            )

            # Create circuit breaker
            cb_config = CircuitBreakerConfig(
                name=f"{provider}-cb",
                failure_threshold=(
                    circuit_breaker_failure_threshold
                    or self._config.circuit_breaker_failure_threshold
                ),
                success_threshold=self._config.circuit_breaker_success_threshold,
                recovery_timeout_seconds=self._config.circuit_breaker_recovery_timeout_seconds,
            )
            self._circuit_breakers[provider] = CircuitBreaker(cb_config)

            self._provider_connections[provider] = False
            await self._metrics.record_provider_start(provider)
            await self._health.set_provider_connected(provider)

    async def connect_provider(self, provider: str) -> None:
        """Mark a provider as connected."""
        async with self._lock:
            self._provider_connections[provider] = True
        await self._health.set_provider_connected(provider)

        # Emit connection event
        await self._bus.publish(ConnectionStatusEvent.create(provider=provider, connected=True))

    async def disconnect_provider(self, provider: str) -> None:
        """Mark a provider as disconnected."""
        async with self._lock:
            self._provider_connections[provider] = False
        await self._health.set_provider_disconnected(provider)
        await self._metrics.record_disconnect(provider)

        # Emit disconnection event
        await self._bus.publish(ConnectionStatusEvent.create(provider=provider, connected=False))

    # ─── Publisher Management ─────────────────────────────────

    async def create_publisher(
        self,
        publisher_id: str,
    ) -> StreamPublisher:
        """Create a stream publisher.

        The publisher can be registered with MarketDataManager via
        its subscribe() method.

        Args:
            publisher_id: Stable publisher identifier.

        Returns:
            A StreamPublisher instance.
        """
        publisher = StreamPublisher(
            publisher_id=publisher_id,
            bus=self._bus,
        )
        async with self._lock:
            self._publishers[publisher_id] = publisher
        return publisher

    def get_publisher(self, publisher_id: str) -> StreamPublisher | None:
        """Get a registered publisher by ID."""
        return self._publishers.get(publisher_id)

    # ─── Subscriber Management ────────────────────────────────

    async def create_subscriber(
        self,
        subscriber_id: str,
        event_type: str,
        callback,
    ) -> StreamSubscriber:
        """Create and start a stream subscriber.

        Args:
            subscriber_id: Stable subscriber identifier.
            event_type: Event type or pattern to subscribe to.
            callback: Async callback for matching events.

        Returns:
            An active StreamSubscriber instance.
        """
        subscriber = StreamSubscriber(
            subscriber_id=subscriber_id,
            bus=self._bus,
            event_type=event_type,
            callback=callback,
        )
        await subscriber.start()
        await self._metrics.record_subscribe()
        async with self._lock:
            self._subscribers[subscriber_id] = subscriber
        return subscriber

    async def remove_subscriber(self, subscriber_id: str) -> None:
        """Stop and remove a subscriber."""
        async with self._lock:
            subscriber = self._subscribers.pop(subscriber_id, None)
        if subscriber is not None:
            await subscriber.stop()

    # ─── Tick and Data Processing ─────────────────────────────

    async def process_event(
        self,
        event: EventStreamEvent,
        provider: str | None = None,
    ) -> bool:
        """Process a streaming event through the pipeline.

        Applies rate limiting, circuit breaker protection, backpressure
        control, and buffering.

        Args:
            event: Event to process.
            provider: Optional provider for rate limiting.

        Returns:
            True if the event was successfully processed.
        """
        if not self._running:
            return False

        # Apply rate limiting
        if provider and provider in self._rate_limiters:
            limiter = self._rate_limiters[provider]
            allowed = await limiter.acquire()
            if not allowed:
                await self._metrics.record_buffer_drop()
                return False

        # Apply circuit breaker
        if provider and provider in self._circuit_breakers:
            cb = self._circuit_breakers[provider]
            try:
                await cb.call(self._buffer_event, event)
            except CircuitBreakerOpenError:
                await self._metrics.record_buffer_drop()
                return False
        else:
            await self._buffer_event(event)

        # Record metrics
        await self._metrics.record_tick()
        await self._health.record_tick()
        await self._update_health()

        return True

    async def _buffer_event(self, event: EventStreamEvent) -> None:
        """Buffer an event with backpressure control."""
        # Check backpressure
        depth = await self._buffer.qsize()
        await self._backpressure.update_depth(depth)
        await self._backpressure.wait_if_paused()

        # Apply adaptive delay
        delay = await self._backpressure.compute_throttle_delay(depth)
        if delay > 0:
            await asyncio.sleep(delay)

        # Buffer the event
        start = time.monotonic()
        enqueued = await self._buffer.enqueue(event)
        if not enqueued:
            await self._metrics.record_buffer_drop()
            return

        # Publish to event bus
        await self._bus.publish(event)
        await self._metrics.record_event()
        await self._health.record_event()

        # Track latency
        latency_ms = (time.monotonic() - start) * 1000
        await self._metrics.record_queue_latency(latency_ms)

    # ─── Health and Metrics ───────────────────────────────────

    async def get_health(self) -> HealthStatus:
        """Return current health status."""
        metrics = await self._metrics.snapshot()
        await self._health.set_cache_hit_rate(metrics.cache_hit_ratio)
        return await self._health.get_health()

    async def get_metrics_snapshot(self) -> StreamMetricSnapshot:
        """Return current metrics snapshot."""
        return await self._metrics.snapshot()

    async def _update_health(self) -> None:
        """Update health status from current component states."""
        depth = await self._buffer.qsize()
        await self._health.set_queue_depth(depth, self._buffer.maxsize)

    # ─── Integration with MarketDataManager ───────────────────

    async def connect_to_manager(
        self,
        manager: MarketDataManager,
        publisher_id: str = "stream_publisher",
    ) -> StreamPublisher:
        """Connect the stream manager to a MarketDataManager instance.

        Creates a publisher, subscribes it to the manager, and starts
        processing accepted snapshots through the streaming pipeline.

        Args:
            manager: The MarketDataManager instance.
            publisher_id: Publisher identifier for registration.

        Returns:
            The StreamPublisher registered with the manager.
        """
        publisher = await self.create_publisher(publisher_id)
        await manager.subscribe(publisher_id, publisher)
        return publisher

    async def disconnect_from_manager(
        self,
        manager: MarketDataManager,
        publisher_id: str = "stream_publisher",
    ) -> None:
        """Disconnect from a MarketDataManager instance."""
        await manager.unsubscribe(publisher_id)
        async with self._lock:
            self._publishers.pop(publisher_id, None)
