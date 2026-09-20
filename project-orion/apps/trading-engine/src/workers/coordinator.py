"""Autonomous Worker Coordinator — top-level facade.

Assembles all worker components and integrates with the FastAPI lifespan:
- MarketDataPoller (periodic tick fetching)
- TradingCycleWorker (pipeline orchestration)
- AsyncScheduler (interval management)
- WorkerLifecycle (state machine)
- HealthCheck integration
- MetricsRegistry integration

Designed to be attached to app.state.worker by the lifespan context manager.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.notification.service import (
    NotificationService,
    NotificationServiceConfig,
)
from libraries.domain.risk.engine import RiskEngine
from libraries.domain.trading.decision_engine import DecisionEngine
from libraries.infrastructure.execution.paper_execution import PaperExecutionAdapter
from libraries.infrastructure.health import HealthCheck, HealthCheckResult, HealthStatus
from libraries.observability.metrics import MetricsRegistry

from .lifecycle import WorkerLifecycle, WorkerState
from .market_data import MarketDataPoller
from .scheduler import AsyncScheduler
from .trading_cycle import TradingCycleWorker

logger = logging.getLogger("trading_engine.worker.coordinator")


class WorkerHealthCheck(HealthCheck):
    """Health check that reports the autonomous worker's current state."""

    def __init__(self, coordinator: AutonomousWorkerCoordinator) -> None:
        super().__init__(name="worker", timeout_seconds=2.0)
        self._coordinator = coordinator

    async def check(self) -> HealthCheckResult:
        state = self._coordinator.state
        last_cycle = self._coordinator.last_cycle_at
        if state == WorkerState.RUNNING:
            if last_cycle is not None:
                age = (datetime.now(timezone.utc) - last_cycle).total_seconds()
                details: dict[str, Any] = {
                    "state": state,
                    "last_cycle_age_seconds": round(age, 1),
                    "cycles_completed": self._coordinator.cycles_completed,
                    "cycles_failed": self._coordinator.cycles_failed,
                }
            else:
                details = {"state": state, "last_cycle_age_seconds": None}
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message="Autonomous worker is running",
                details=details,
            )
        elif state == WorkerState.STOPPED and not self._coordinator.enabled:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message="Autonomous worker is disabled (ORION_WORKER_ENABLED=false)",
                details={"state": state},
            )
        else:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.DEGRADED,
                message=f"Autonomous worker is in state: {state}",
                details={"state": state},
            )


class AutonomousWorkerCoordinator:
    """Top-level coordinator for the autonomous paper-trading worker.

    Lifecycle:
      - ``start()``: transitions STOPPED -> STARTING -> RUNNING.
      - ``stop()``: transitions RUNNING -> STOPPING -> STOPPED.
      - Integrates into FastAPI lifespan context manager.

    Args:
        symbols: Canonical symbol universe for autonomous trading.
        market_poll_interval: Seconds between market data polls.
        trading_cycle_interval: Seconds between trading cycle evaluations.
        stale_threshold_seconds: Tick age limit before considered stale.
        account_balance: Starting paper account balance.
        paper_adapter: Injected PaperExecutionAdapter from lifespan.
        metrics_registry: Optional shared MetricsRegistry.
        enabled: If False, coordinator is a no-op (worker stays stopped).
    """

    def __init__(
        self,
        symbols: tuple[str, ...],
        market_poll_interval: float,
        trading_cycle_interval: float,
        stale_threshold_seconds: float,
        account_balance: Decimal,
        paper_adapter: PaperExecutionAdapter,
        metrics_registry: MetricsRegistry | None = None,
        enabled: bool = True,
    ) -> None:
        self._symbols = symbols
        self._enabled = enabled
        self._paper_adapter = paper_adapter
        self._metrics_registry = metrics_registry

        # Domain components (no framework deps)
        self._decision_engine = DecisionEngine()
        self._risk_engine = RiskEngine()
        self._notification_service = NotificationService(
            config=NotificationServiceConfig(enabled=True)
        )

        # Worker subsystems
        self._lifecycle = WorkerLifecycle()
        self._poller = MarketDataPoller(
            symbols=symbols,
            stale_threshold_seconds=stale_threshold_seconds,
        )
        self._cycle_worker = TradingCycleWorker(
            decision_engine=self._decision_engine,
            risk_engine=self._risk_engine,
            paper_adapter=paper_adapter,
            notification_service=self._notification_service,
            account_balance=account_balance,
        )

        self._market_scheduler = AsyncScheduler(
            name="market_data_poll",
            callback=self._market_poll_cycle,
            interval_seconds=market_poll_interval,
            error_hook=self._on_market_poll_error,
        )
        self._trading_scheduler = AsyncScheduler(
            name="trading_cycle",
            callback=self._trading_cycle,
            interval_seconds=trading_cycle_interval,
            error_hook=self._on_trading_cycle_error,
        )

        self._last_cycle_at: datetime | None = None
        self._start_time: float | None = None

        # Register metrics
        if metrics_registry is not None:
            self._register_metrics(metrics_registry)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def state(self) -> WorkerState:
        return self._lifecycle.state

    @property
    def last_cycle_at(self) -> datetime | None:
        return self._last_cycle_at

    @property
    def cycles_completed(self) -> int:
        return self._trading_scheduler.cycles_completed

    @property
    def cycles_failed(self) -> int:
        return self._trading_scheduler.cycles_failed

    @property
    def uptime_seconds(self) -> float | None:
        if self._start_time is None:
            return None
        return time.monotonic() - self._start_time

    async def start(self) -> None:
        """Start the autonomous worker.

        If ``enabled`` is False, logs and returns immediately.
        Transitions: STOPPED -> STARTING -> RUNNING.
        """
        if not self._enabled:
            logger.info("Autonomous worker is disabled (ORION_WORKER_ENABLED=false). Skipping.")
            return

        if not await self._lifecycle.transition_to(WorkerState.STARTING):
            logger.warning("Worker already starting or running; ignoring start().")
            return

        logger.info("Autonomous worker starting up (symbols=%s).", self._symbols)
        try:
            # Initialize RiskEngine (auto-init but explicit for clarity)
            await self._risk_engine.initialize()

            # Start schedulers
            await self._market_scheduler.start()
            await self._trading_scheduler.start()

            self._start_time = time.monotonic()
            await self._lifecycle.transition_to(WorkerState.RUNNING)
            logger.info("Autonomous worker is running.")

            if self._metrics_registry is not None:
                self._metrics_registry.set("worker_status", 1.0)
        except Exception:
            logger.exception("Autonomous worker failed to start")
            await self._market_scheduler.stop()
            await self._trading_scheduler.stop()
            await self._lifecycle.transition_to(WorkerState.STOPPED)
            raise

    async def stop(self) -> None:
        """Stop the autonomous worker gracefully.

        Stops schedulers, drains tasks, then transitions to STOPPED.
        """
        if not self._enabled:
            return

        if not await self._lifecycle.transition_to(WorkerState.STOPPING):
            logger.info("Worker not running; nothing to stop.")
            return

        logger.info("Autonomous worker shutting down...")
        try:
            await self._trading_scheduler.stop()
            await self._market_scheduler.stop()
            await self._lifecycle.drain_tasks(timeout_seconds=5.0)
        finally:
            await self._lifecycle.transition_to(WorkerState.STOPPED)
            self._start_time = None
            if self._metrics_registry is not None:
                self._metrics_registry.set("worker_status", 0.0)
            logger.info("Autonomous worker stopped.")

    def build_health_check(self) -> WorkerHealthCheck:
        """Build and return a HealthCheck for this coordinator."""
        return WorkerHealthCheck(self)

    # ─── Scheduler Callbacks ────────────────────────────────────────────────

    async def _market_poll_cycle(self) -> None:
        """Scheduled callback: poll market data for all configured symbols."""
        if not self._lifecycle.is_running:
            return
        market_data = await self._poller.poll()
        logger.debug("Market poll complete: %d symbol(s) updated.", len(market_data))
        self._update_metrics_after_poll()

    async def _trading_cycle(self) -> None:
        """Scheduled callback: run the autonomous trading pipeline."""
        if not self._lifecycle.is_running:
            return

        # Gather latest (non-stale) ticks
        market_data = {}
        for symbol in self._symbols:
            tick = await self._poller.latest(symbol)
            if tick is not None:
                market_data[symbol] = tick

        results = await self._cycle_worker.run_cycle(market_data)
        self._last_cycle_at = datetime.now(timezone.utc)

        executed = sum(1 for r in results if r.outcome == "executed")
        failed = sum(1 for r in results if not r.success)
        logger.info(
            "Trading cycle complete: %d symbol(s), %d executed, %d failed.",
            len(results), executed, failed,
        )
        self._update_metrics_after_cycle(executed=executed, failed=failed)

    async def _on_market_poll_error(self, exc: Exception) -> None:
        logger.error("Market data poll error: %s", exc)
        if self._metrics_registry is not None:
            self._metrics_registry.inc("worker_market_poll_failures_total")

    async def _on_trading_cycle_error(self, exc: Exception) -> None:
        logger.error("Trading cycle error: %s", exc)
        if self._metrics_registry is not None:
            self._metrics_registry.inc("worker_cycle_errors_total")

    # ─── Metrics ────────────────────────────────────────────────────────────

    def _register_metrics(self, registry: MetricsRegistry) -> None:
        """Register worker-specific metrics into the shared registry."""
        registry.counter("worker_cycles_total", "Total autonomous trading cycles started")
        registry.counter("worker_cycles_completed_total", "Total trading cycles completed")
        registry.counter("worker_cycle_errors_total", "Total trading cycle errors")
        registry.counter("worker_market_poll_failures_total", "Total market data poll failures")
        registry.counter("worker_orders_submitted_total", "Total paper orders submitted")
        registry.counter("worker_risk_rejections_total", "Total orders rejected by risk engine")
        registry.counter("worker_execution_failures_total", "Total execution failures")
        registry.gauge("worker_status", "Worker running state (1=running, 0=stopped)")
        registry.set("worker_status", 0.0)

    def _update_metrics_after_poll(self) -> None:
        if self._metrics_registry is None:
            return
        stats = self._poller.stats
        if stats.polls_failed > 0:
            self._metrics_registry.inc(
                "worker_market_poll_failures_total", float(stats.polls_failed)
            )

    def _update_metrics_after_cycle(self, *, executed: int, failed: int) -> None:
        if self._metrics_registry is None:
            return
        self._metrics_registry.inc("worker_cycles_total")
        self._metrics_registry.inc("worker_cycles_completed_total")
        if executed > 0:
            self._metrics_registry.inc("worker_orders_submitted_total", float(executed))
        if failed > 0:
            self._metrics_registry.inc("worker_cycle_errors_total", float(failed))
        cycle_metrics = self._cycle_worker.metrics
        if cycle_metrics.risk_rejections > 0:
            self._metrics_registry.inc(
                "worker_risk_rejections_total", float(cycle_metrics.risk_rejections)
            )
