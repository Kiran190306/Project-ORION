"""Execution auditor for the broker execution layer.

Records immutable audit entries for submission, acceptance, modification,
cancellation, execution, recovery, failure, retry, latency, and broker
responses. Audit records are immutable once created.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class AuditEventType(StrEnum):
    """Types of audit events."""

    SUBMISSION = "submission"
    ACCEPTANCE = "acceptance"
    MODIFICATION = "modification"
    CANCELLATION = "cancellation"
    EXECUTION = "execution"
    FILL = "fill"
    PARTIAL_FILL = "partial_fill"
    RECOVERY = "recovery"
    FAILURE = "failure"
    RETRY = "retry"
    TIMEOUT = "timeout"
    REJECTION = "rejection"
    ROUTING = "routing"
    CONNECTION = "connection"
    DISCONNECTION = "disconnection"
    LATENCY = "latency"
    BROKER_RESPONSE = "broker_response"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """An immutable audit entry.

    Once created, audit entries cannot be modified.
    """

    entry_id: str
    event_type: AuditEventType
    broker_name: str
    order_id: str = ""
    execution_id: str = ""
    symbol: str = ""
    details: str = ""
    latency_ms: float = 0.0
    broker_response: str = ""
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class AuditRecord:
    """A collection of audit entries for a single execution flow."""

    execution_id: str
    entries: tuple[AuditEntry, ...] = ()
    first_event: datetime | None = None
    last_event: datetime | None = None
    entry_count: int = 0


@dataclass(frozen=True, slots=True)
class ExecutionAuditorConfig:
    """Configuration for the execution auditor."""

    max_entries: int = 1000000
    enable_latency_tracking: bool = True
    enable_broker_response_logging: bool = True
    enable_error_tracking: bool = True


class ExecutionAuditor:
    """Records immutable audit entries for all execution events.

    Thread-safe via asyncio.Lock. Maintains a time-ordered sequence of
    audit entries per execution flow. Entries are immutable once created.
    """

    def __init__(self, config: ExecutionAuditorConfig | None = None) -> None:
        self._config = config or ExecutionAuditorConfig()
        self._entries: list[AuditEntry] = []
        self._execution_entries: dict[str, list[AuditEntry]] = {}
        self._lock = asyncio.Lock()

    @property
    def config(self) -> ExecutionAuditorConfig:
        return self._config

    async def record(
        self,
        event_type: AuditEventType,
        broker_name: str,
        *,
        order_id: str = "",
        execution_id: str = "",
        symbol: str = "",
        details: str = "",
        latency_ms: float = 0.0,
        broker_response: str = "",
        error: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """Record an immutable audit entry.

        Args:
            event_type: Type of audit event.
            broker_name: Name of the broker.
            order_id: Order identifier (optional).
            execution_id: Execution identifier (optional).
            symbol: Trading symbol (optional).
            details: Human-readable details (optional).
            latency_ms: Operation latency in ms (optional).
            broker_response: Raw broker response (optional).
            error: Error message if failed (optional).
            metadata: Additional structured data (optional).

        Returns:
            The created immutable AuditEntry.
        """
        entry = AuditEntry(
            entry_id=str(uuid.uuid4()),
            event_type=event_type,
            broker_name=broker_name,
            order_id=order_id,
            execution_id=execution_id,
            symbol=symbol,
            details=details,
            latency_ms=latency_ms,
            broker_response=broker_response,
            error=error,
            metadata=metadata or {},
        )

        async with self._lock:
            self._entries.append(entry)

            if execution_id:
                if execution_id not in self._execution_entries:
                    self._execution_entries[execution_id] = []
                self._execution_entries[execution_id].append(entry)

            # Enforce max entries
            if len(self._entries) > self._config.max_entries:
                self._entries = self._entries[-self._config.max_entries :]

        return entry

    async def record_submission(
        self,
        broker_name: str,
        order_id: str,
        execution_id: str,
        symbol: str,
        details: str = "",
    ) -> AuditEntry:
        """Record an order submission event."""
        return await self.record(
            event_type=AuditEventType.SUBMISSION,
            broker_name=broker_name,
            order_id=order_id,
            execution_id=execution_id,
            symbol=symbol,
            details=details or f"Order submitted to {broker_name}",
        )

    async def record_execution(
        self,
        broker_name: str,
        order_id: str,
        execution_id: str,
        symbol: str,
        filled_qty: str,
        fill_price: str,
        latency_ms: float,
    ) -> AuditEntry:
        """Record an order execution event."""
        return await self.record(
            event_type=AuditEventType.EXECUTION,
            broker_name=broker_name,
            order_id=order_id,
            execution_id=execution_id,
            symbol=symbol,
            details=f"Executed {filled_qty} @ {fill_price}",
            latency_ms=latency_ms,
        )

    async def record_failure(
        self,
        broker_name: str,
        order_id: str,
        execution_id: str,
        error: str,
        details: str = "",
    ) -> AuditEntry:
        """Record an execution failure event."""
        return await self.record(
            event_type=AuditEventType.FAILURE,
            broker_name=broker_name,
            order_id=order_id,
            execution_id=execution_id,
            details=details or "Execution failed",
            error=error,
        )

    async def record_retry(
        self,
        broker_name: str,
        order_id: str,
        execution_id: str,
        attempt: int,
        delay_ms: float,
        error: str = "",
    ) -> AuditEntry:
        """Record a retry event."""
        return await self.record(
            event_type=AuditEventType.RETRY,
            broker_name=broker_name,
            order_id=order_id,
            execution_id=execution_id,
            details=f"Retry attempt {attempt} with delay {delay_ms:.0f}ms",
            latency_ms=delay_ms,
            error=error,
        )

    async def record_recovery(
        self,
        broker_name: str,
        order_id: str,
        execution_id: str,
        recovery_type: str,
        details: str = "",
    ) -> AuditEntry:
        """Record a recovery event."""
        return await self.record(
            event_type=AuditEventType.RECOVERY,
            broker_name=broker_name,
            order_id=order_id,
            execution_id=execution_id,
            details=details or f"Recovery: {recovery_type}",
        )

    async def record_cancellation(
        self,
        broker_name: str,
        order_id: str,
        execution_id: str,
        reason: str = "",
    ) -> AuditEntry:
        """Record an order cancellation event."""
        return await self.record(
            event_type=AuditEventType.CANCELLATION,
            broker_name=broker_name,
            order_id=order_id,
            execution_id=execution_id,
            details=reason or "Order cancelled",
        )

    async def record_broker_response(
        self,
        broker_name: str,
        order_id: str,
        execution_id: str,
        response: str,
        latency_ms: float,
    ) -> AuditEntry:
        """Record a broker response event."""
        return await self.record(
            event_type=AuditEventType.BROKER_RESPONSE,
            broker_name=broker_name,
            order_id=order_id,
            execution_id=execution_id,
            details="Broker response received",
            latency_ms=latency_ms,
            broker_response=response,
        )

    async def get_execution_audit(self, execution_id: str) -> AuditRecord:
        """Get the complete audit trail for an execution.

        Args:
            execution_id: Execution identifier.

        Returns:
            AuditRecord containing all entries for the execution.
        """
        async with self._lock:
            entries = list(self._execution_entries.get(execution_id, []))
            first = entries[0].timestamp if entries else None
            last = entries[-1].timestamp if entries else None

            return AuditRecord(
                execution_id=execution_id,
                entries=tuple(entries),
                first_event=first,
                last_event=last,
                entry_count=len(entries),
            )

    async def get_all_entries(
        self,
        event_type: AuditEventType | None = None,
        broker_name: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Get audit entries with optional filtering.

        Args:
            event_type: Filter by event type (optional).
            broker_name: Filter by broker name (optional).
            limit: Maximum number of entries.

        Returns:
            List of matching audit entries.
        """
        async with self._lock:
            results = list(self._entries)

        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if broker_name:
            results = [e for e in results if e.broker_name == broker_name]

        return results[-limit:]

    async def entry_count(self) -> int:
        """Return the total number of audit entries."""
        async with self._lock:
            return len(self._entries)

    async def clear(self) -> None:
        """Clear all audit entries."""
        async with self._lock:
            self._entries.clear()
            self._execution_entries.clear()
