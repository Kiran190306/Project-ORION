"""Tests for the session recovery engine."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.infrastructure.execution.broker_adapter import (
    AccountInfo,
    BrokerAdapter,
    BrokerAdapterConfig,
)
from libraries.infrastructure.execution.session_recovery import (
    SessionRecoveryConfig,
    SessionRecoveryEngine,
    SessionRecoveryStatus,
)


class _RecoverableAdapter(BrokerAdapter):
    """Adapter that can be recovered."""

    def __init__(self, name: str, connect_success: bool = True):
        super().__init__(BrokerAdapterConfig(broker_name=name))
        self._connect_success = connect_success
        self._connect_count = 0

    async def connect(self) -> bool:
        self._connect_count += 1
        if self._connect_success:
            self._connected = True
            return True
        return False

    async def disconnect(self) -> bool:
        self._connected = False
        return True

    async def health_check(self) -> dict:
        return {"connected": self._connected, "latency_ms": 5.0}

    async def submit_order(self, order): return None
    async def modify_order(self, broker_order_id, **kwargs): return None
    async def cancel_order(self, broker_order_id): return True
    async def close_position(self, position_id): return None
    async def get_open_positions(self): return []
    async def get_account(self) -> AccountInfo:
        return AccountInfo(
            account_id="test",
            broker_name=self.broker_name,
            balance=Decimal("10000"),
            equity=Decimal("10000"),
            margin=Decimal("0"),
            margin_free=Decimal("10000"),
            margin_level=0.0,
            currency="USD",
            leverage=100,
        )
    async def get_symbol_information(self, symbol): return None
    async def get_execution_history(self, symbol=None, since=None, limit=100): return []


class TestSessionRecoveryEngine:
    """Test suite for SessionRecoveryEngine."""

    @pytest.fixture
    def engine(self):
        config = SessionRecoveryConfig(
            max_reconnect_attempts=3,
            reconnect_delay_seconds=0.05,
            reconnect_backoff_multiplier=1.5,
            max_reconnect_delay_seconds=0.5,
        )
        return SessionRecoveryEngine(config)

    @pytest.mark.asyncio
    async def test_recover_session_success(self, engine):
        adapter = _RecoverableAdapter("test")
        result = await engine.recover_session(adapter)
        assert result.status == SessionRecoveryStatus.COMPLETED
        assert result.connected
        assert result.authenticated

    @pytest.mark.asyncio
    async def test_recover_session_reconnect_fails(self, engine):
        adapter = _RecoverableAdapter("test", connect_success=False)
        result = await engine.recover_session(adapter)
        assert result.status == SessionRecoveryStatus.FAILED
        assert not result.connected

    @pytest.mark.asyncio
    async def test_reconnect_only(self, engine):
        adapter = _RecoverableAdapter("test")
        result = await engine.reconnect_only(adapter)
        assert result.status == SessionRecoveryStatus.RECONNECTING
        assert result.connected

    @pytest.mark.asyncio
    async def test_reconnect_failure(self, engine):
        config = SessionRecoveryConfig(max_reconnect_attempts=2, reconnect_delay_seconds=0.05)
        engine = SessionRecoveryEngine(config)
        adapter = _RecoverableAdapter("test", connect_success=False)
        result = await engine.reconnect_only(adapter)
        assert result.status == SessionRecoveryStatus.FAILED
        assert result.reconnect_attempts == 2

    @pytest.mark.asyncio
    async def test_concurrent_recovery_prevents_duplicate(self, engine):
        adapter = _RecoverableAdapter("test")
        # Start first recovery
        engine._is_recovering = True
        result = await engine.recover_session(adapter)
        assert result.status == SessionRecoveryStatus.PENDING

    def test_session_recovery_status_enum(self):
        assert SessionRecoveryStatus.PENDING.value == "pending"
        assert SessionRecoveryStatus.COMPLETED.value == "completed"
        assert SessionRecoveryStatus.FAILED.value == "failed"

    @pytest.mark.asyncio
    async def test_recovery_includes_account_and_positions(self, engine):
        adapter = _RecoverableAdapter("test")
        result = await engine.recover_session(adapter)
        assert result.status == SessionRecoveryStatus.COMPLETED
        assert result.account is not None
        assert result.account.balance == Decimal("10000")
        assert isinstance(result.positions, list)

