"""Idempotency guard to prevent duplicate execution.

Prevents duplicate execution by tracking execution IDs, order IDs,
and request hashes. Supports replay detection and configurable
deduplication windows.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class DuplicateExecutionError(Exception):
    """Raised when a duplicate execution request is detected."""


@dataclass(frozen=True, slots=True)
class IdempotencyConfig:
    """Configuration for the idempotency guard."""

    window_seconds: float = 3600.0  # 1 hour default window
    max_entries: int = 100000
    check_execution_id: bool = True
    check_order_id: bool = True
    check_request_hash: bool = True


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    """A record of a previously processed execution request."""

    execution_id: str
    order_id: str
    request_hash: str
    status: str
    broker_order_id: str = ""
    processed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class IdempotencyGuard:
    """Guards against duplicate execution requests.

    Thread-safe via asyncio.Lock. Uses time-based expiration to
    automatically clean up old entries. Supports replay detection
    for safe retry of operations.

    Every execution request must be safely repeatable.
    """

    def __init__(self, config: IdempotencyConfig | None = None) -> None:
        self._config = config or IdempotencyConfig()
        self._records: dict[str, IdempotencyRecord] = {}
        self._lock = asyncio.Lock()

    @property
    def config(self) -> IdempotencyConfig:
        return self._config

    @staticmethod
    def compute_request_hash(order_data: dict[str, Any]) -> str:
        """Compute a hash of the order request for deduplication.

        Args:
            order_data: Dictionary of order parameters.

        Returns:
            SHA-256 hex digest of the canonical JSON representation.
        """
        canonical = json.dumps(order_data, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    async def check_and_register(
        self,
        execution_id: str,
        order_id: str,
        request_hash: str,
        status: str = "submitted",
        broker_order_id: str = "",
    ) -> None:
        """Check for duplicate and register if not found.

        Args:
            execution_id: Unique execution identifier.
            order_id: Order identifier.
            request_hash: Hash of the order request.
            status: Current status of the execution.
            broker_order_id: Broker-assigned order ID.

        Raises:
            DuplicateExecutionError: If a duplicate is detected.
        """
        async with self._lock:
            self._cleanup_expired()

            # Check by execution ID
            if self._config.check_execution_id:
                exec_key = f"exec:{execution_id}"
                if exec_key in self._records:
                    existing = self._records[exec_key]
                    raise DuplicateExecutionError(
                        f"Duplicate execution ID {execution_id}: "
                        f"already processed at {existing.processed_at.isoformat()} "
                        f"(broker order: {existing.broker_order_id})"
                    )

            # Check by order ID
            if self._config.check_order_id:
                order_key = f"order:{order_id}"
                if order_key in self._records:
                    existing = self._records[order_key]
                    raise DuplicateExecutionError(
                        f"Duplicate order ID {order_id}: "
                        f"already processed at {existing.processed_at.isoformat()}"
                    )

            # Check by request hash
            if self._config.check_request_hash:
                hash_key = f"hash:{request_hash}"
                if hash_key in self._records:
                    existing = self._records[hash_key]
                    raise DuplicateExecutionError(
                        f"Duplicate request hash {request_hash[:16]}...: "
                        f"already processed at {existing.processed_at.isoformat()}"
                    )

            # Register all keys
            expires_at = datetime.fromtimestamp(
                datetime.now(timezone.utc).timestamp() + self._config.window_seconds,
                tz=timezone.utc,
            )

            record = IdempotencyRecord(
                execution_id=execution_id,
                order_id=order_id,
                request_hash=request_hash,
                status=status,
                broker_order_id=broker_order_id,
                expires_at=expires_at,
            )

            if self._config.check_execution_id:
                self._records[f"exec:{execution_id}"] = record
            if self._config.check_order_id:
                self._records[f"order:{order_id}"] = record
            if self._config.check_request_hash:
                self._records[f"hash:{request_hash}"] = record

            # Enforce max entries
            if len(self._records) > self._config.max_entries:
                self._enforce_max_entries()

    async def is_duplicate(
        self,
        execution_id: str,
        order_id: str,
        request_hash: str,
    ) -> bool:
        """Check if a request would be a duplicate.

        Args:
            execution_id: Execution identifier.
            order_id: Order identifier.
            request_hash: Hash of the order request.

        Returns:
            True if duplicate detected.
        """
        async with self._lock:
            self._cleanup_expired()

            if self._config.check_execution_id and f"exec:{execution_id}" in self._records:
                return True
            if self._config.check_order_id and f"order:{order_id}" in self._records:
                return True
            if self._config.check_request_hash and f"hash:{request_hash}" in self._records:
                return True

            return False

    async def get_record(self, execution_id: str) -> IdempotencyRecord | None:
        """Get the record for a given execution ID.

        Args:
            execution_id: Execution identifier.

        Returns:
            IdempotencyRecord if found, None otherwise.
        """
        async with self._lock:
            self._cleanup_expired()
            return self._records.get(f"exec:{execution_id}")

    async def update_status(
        self,
        execution_id: str,
        status: str,
        broker_order_id: str = "",
    ) -> None:
        """Update the status of a tracked execution.

        Args:
            execution_id: Execution identifier.
            status: New status.
            broker_order_id: Broker-assigned order ID.
        """
        async with self._lock:
            exec_key = f"exec:{execution_id}"
            if exec_key in self._records:
                existing = self._records[exec_key]
                self._records[exec_key] = IdempotencyRecord(
                    execution_id=existing.execution_id,
                    order_id=existing.order_id,
                    request_hash=existing.request_hash,
                    status=status,
                    broker_order_id=broker_order_id or existing.broker_order_id,
                    processed_at=existing.processed_at,
                    expires_at=existing.expires_at,
                    metadata=existing.metadata,
                )

    async def remove(self, execution_id: str) -> None:
        """Remove records for a given execution ID.

        Args:
            execution_id: Execution identifier to remove.
        """
        async with self._lock:
            keys_to_remove = [
                key
                for key, record in self._records.items()
                if record.execution_id == execution_id
            ]
            for key in keys_to_remove:
                self._records.pop(key, None)

    async def clear(self) -> None:
        """Clear all tracked records."""
        async with self._lock:
            self._records.clear()

    async def record_count(self) -> int:
        """Return number of tracked records."""
        async with self._lock:
            self._cleanup_expired()
            return len(self._records)

    def _cleanup_expired(self) -> None:
        """Remove expired records."""
        now = datetime.now(timezone.utc)
        expired_keys = [
            key
            for key, record in self._records.items()
            if record.expires_at and record.expires_at <= now
        ]
        for key in expired_keys:
            self._records.pop(key, None)

    def _enforce_max_entries(self) -> None:
        """Remove oldest entries when max is exceeded."""
        while len(self._records) > self._config.max_entries:
            oldest_key = min(
                self._records.keys(),
                key=lambda k: self._records[k].processed_at,
            )
            self._records.pop(oldest_key, None)

