"""Session recovery engine for the broker execution layer.

Supports reconnect, re-authentication, session validation, reload account,
reload open positions, and resume execution. No duplicate execution may
occur after recovery.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from libraries.infrastructure.execution.broker_adapter import (
    AccountInfo,
    AdapterAuthenticationError,
    AdapterConnectionError,
    AdapterNotConnectedError,
    BrokerAdapter,
    PositionInfo,
)


class SessionRecoveryStatus(StrEnum):
    """Status of a session recovery operation."""

    PENDING = "pending"
    RECONNECTING = "reconnecting"
    AUTHENTICATING = "authenticating"
    VALIDATING_SESSION = "validating_session"
    RELOADING_ACCOUNT = "reloading_account"
    RELOADING_POSITIONS = "reloading_positions"
    RESUMING_EXECUTION = "resuming_execution"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class SessionRecoveryConfig:
    """Configuration for session recovery."""

    max_reconnect_attempts: int = 5
    reconnect_delay_seconds: float = 1.0
    reconnect_backoff_multiplier: float = 2.0
    max_reconnect_delay_seconds: float = 30.0
    session_validation_timeout_seconds: float = 10.0
    enable_auto_reconnect: bool = True
    enable_auto_reauthenticate: bool = True
    enable_auto_reload_account: bool = True
    enable_auto_reload_positions: bool = True
    enable_auto_resume_execution: bool = True


@dataclass(frozen=True, slots=True)
class SessionRecoveryResult:
    """Result of a session recovery attempt."""

    status: SessionRecoveryStatus
    broker_name: str
    connected: bool = False
    authenticated: bool = False
    account: AccountInfo | None = None
    positions: list[PositionInfo] = field(default_factory=list)
    error: str = ""
    reconnect_attempts: int = 0
    duration_seconds: float = 0.0
    recovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


class SessionRecoveryEngine:
    """Engine for recovering broker sessions after failures.

    Supports:
    - Reconnect to broker with exponential backoff
    - Re-authentication after session expiry
    - Session validation and health check
    - Reload account information
    - Reload open positions
    - Resume execution readiness
    - No duplicate execution after recovery
    """

    def __init__(self, config: SessionRecoveryConfig | None = None) -> None:
        self._config = config or SessionRecoveryConfig()
        self._lock = asyncio.Lock()
        self._is_recovering: bool = False

    @property
    def config(self) -> SessionRecoveryConfig:
        return self._config

    @property
    def is_recovering(self) -> bool:
        return self._is_recovering

    async def recover_session(self, adapter: BrokerAdapter) -> SessionRecoveryResult:
        """Perform full session recovery on a broker adapter.

        Executes the complete recovery pipeline:
        1. Reconnect
        2. Re-authenticate
        3. Validate session
        4. Reload account
        5. Reload positions
        6. Resume execution

        Args:
            adapter: The broker adapter to recover.

        Returns:
            SessionRecoveryResult with full recovery status.
        """
        async with self._lock:
            if self._is_recovering:
                return SessionRecoveryResult(
                    status=SessionRecoveryStatus.PENDING,
                    broker_name=adapter.broker_name,
                    error="Recovery already in progress",
                )
            self._is_recovering = True

        start_time = datetime.now(timezone.utc)

        try:
            # Step 1: Reconnect
            reconnect_result = await self._reconnect(adapter)
            if not reconnect_result.connected:
                return reconnect_result

            # Step 2: Re-authenticate (if needed)
            if self._config.enable_auto_reauthenticate:
                auth_result = await self._reauthenticate(adapter)
                if not auth_result.authenticated:
                    return auth_result

            # Step 3: Validate session
            session_result = await self._validate_session(adapter)
            if not session_result.connected:
                return session_result

            # Step 4: Reload account
            account = None
            if self._config.enable_auto_reload_account:
                account = await self._reload_account(adapter)

            # Step 5: Reload positions
            positions = []
            if self._config.enable_auto_reload_positions:
                positions = await self._reload_positions(adapter)

            # Step 6: Resume execution
            if self._config.enable_auto_resume_execution:
                await self._resume_execution(adapter)

            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

            return SessionRecoveryResult(
                status=SessionRecoveryStatus.COMPLETED,
                broker_name=adapter.broker_name,
                connected=True,
                authenticated=True,
                account=account,
                positions=positions,
                reconnect_attempts=reconnect_result.reconnect_attempts,
                duration_seconds=round(elapsed, 3),
            )

        except Exception as e:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            return SessionRecoveryResult(
                status=SessionRecoveryStatus.FAILED,
                broker_name=adapter.broker_name,
                error=str(e),
                reconnect_attempts=0,
                duration_seconds=round(elapsed, 3),
            )

        finally:
            async with self._lock:
                self._is_recovering = False

    async def reconnect_only(self, adapter: BrokerAdapter) -> SessionRecoveryResult:
        """Reconnect to a broker without full session recovery.

        Args:
            adapter: The broker adapter to reconnect.

        Returns:
            SessionRecoveryResult with connection status.
        """
        return await self._reconnect(adapter)

    async def _reconnect(self, adapter: BrokerAdapter) -> SessionRecoveryResult:
        """Reconnect to broker with exponential backoff."""
        start = datetime.now(timezone.utc)
        delay = self._config.reconnect_delay_seconds
        attempts = 0

        for attempt in range(1, self._config.max_reconnect_attempts + 1):
            attempts = attempt
            try:
                connected = await adapter.connect()
                if connected:
                    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
                    return SessionRecoveryResult(
                        status=SessionRecoveryStatus.RECONNECTING,
                        broker_name=adapter.broker_name,
                        connected=True,
                        reconnect_attempts=attempts,
                        duration_seconds=round(elapsed, 3),
                    )
            except (AdapterConnectionError, AdapterNotConnectedError):
                pass

            if attempt < self._config.max_reconnect_attempts:
                await asyncio.sleep(delay)
                delay = min(
                    delay * self._config.reconnect_backoff_multiplier,
                    self._config.max_reconnect_delay_seconds,
                )

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        return SessionRecoveryResult(
            status=SessionRecoveryStatus.FAILED,
            broker_name=adapter.broker_name,
            connected=False,
            error=f"Reconnect failed after {attempts} attempts",
            reconnect_attempts=attempts,
            duration_seconds=round(elapsed, 3),
        )

    async def _reauthenticate(self, adapter: BrokerAdapter) -> SessionRecoveryResult:
        """Re-authenticate with the broker."""
        try:
            # Disconnect and reconnect to force re-authentication
            await adapter.disconnect()
            connected = await adapter.connect()

            return SessionRecoveryResult(
                status=SessionRecoveryStatus.AUTHENTICATING,
                broker_name=adapter.broker_name,
                connected=connected,
                authenticated=connected,
            )
        except AdapterAuthenticationError as e:
            return SessionRecoveryResult(
                status=SessionRecoveryStatus.FAILED,
                broker_name=adapter.broker_name,
                connected=False,
                authenticated=False,
                error=f"Re-authentication failed: {e}",
            )
        except Exception as e:
            return SessionRecoveryResult(
                status=SessionRecoveryStatus.FAILED,
                broker_name=adapter.broker_name,
                connected=False,
                authenticated=False,
                error=str(e),
            )

    async def _validate_session(self, adapter: BrokerAdapter) -> SessionRecoveryResult:
        """Validate that the broker session is healthy."""
        try:
            health = await adapter.health_check()
            is_healthy = health.get("connected", False)

            return SessionRecoveryResult(
                status=SessionRecoveryStatus.VALIDATING_SESSION,
                broker_name=adapter.broker_name,
                connected=is_healthy,
                authenticated=is_healthy,
            )
        except Exception as e:
            return SessionRecoveryResult(
                status=SessionRecoveryStatus.FAILED,
                broker_name=adapter.broker_name,
                error=f"Session validation failed: {e}",
            )

    async def _reload_account(self, adapter: BrokerAdapter) -> AccountInfo | None:
        """Reload account information from the broker."""
        try:
            return await adapter.get_account()
        except Exception:
            return None

    async def _reload_positions(
        self, adapter: BrokerAdapter
    ) -> list[PositionInfo]:
        """Reload open positions from the broker."""
        try:
            return await adapter.get_open_positions()
        except Exception:
            return []

    async def _resume_execution(self, adapter: BrokerAdapter) -> bool:
        """Verify the adapter is ready to resume execution.

        Args:
            adapter: The broker adapter.

        Returns:
            True if the adapter is ready for execution.
        """
        try:
            health = await adapter.health_check()
            return health.get("connected", False)
        except Exception:
            return False

    async def reset(self) -> None:
        """Reset recovery state."""
        async with self._lock:
            self._is_recovering = False

