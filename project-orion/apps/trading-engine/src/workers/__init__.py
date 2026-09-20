"""Autonomous Worker subsystem for the Trading Engine.

Provides:
- WorkerLifecycle: state machine managing STOPPED -> STARTING -> RUNNING -> STOPPING -> STOPPED.
- AsyncScheduler: cancellation-safe, overlap-preventing periodic task runner.
- MarketDataPoller: periodically fetches/simulates latest market ticks per symbol.
- TradingCycleWorker: orchestrates Decision -> Risk -> Portfolio -> Execution -> Notification.
- AutonomousWorkerCoordinator: top-level facade wired into FastAPI lifespan.
"""

from __future__ import annotations

from .coordinator import AutonomousWorkerCoordinator
from .lifecycle import WorkerLifecycle, WorkerState
from .scheduler import AsyncScheduler

__all__ = [
    "AsyncScheduler",
    "AutonomousWorkerCoordinator",
    "WorkerLifecycle",
    "WorkerState",
]
