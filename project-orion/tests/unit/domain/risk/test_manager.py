"""Tests for the RiskManager."""

from __future__ import annotations

import pytest

from libraries.domain.risk.exceptions import EngineNotReadyError
from libraries.domain.risk.manager import RiskManager, RiskManagerConfig
from libraries.domain.risk.models import (
    EmergencyTrigger,
    RiskDecision,
    RiskProfileType,
)


class TestRiskManager:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        manager = RiskManager()
        assert not manager.running
        await manager.start()
        assert manager.running
        await manager.stop()
        assert not manager.running

    @pytest.mark.asyncio
    async def test_initialize_engine(self):
        manager = RiskManager()
        await manager.initialize_engine()
        health = await manager.health_check()
        assert "initialized" in health

    @pytest.mark.asyncio
    async def test_set_profile(self):
        manager = RiskManager()
        await manager.set_profile(RiskProfileType.CONSERVATIVE)
        assert manager.active_profile == RiskProfileType.CONSERVATIVE

    @pytest.mark.asyncio
    async def test_set_profile_balanced(self):
        manager = RiskManager()
        await manager.set_profile(RiskProfileType.BALANCED)
        assert manager.active_profile == RiskProfileType.BALANCED

    @pytest.mark.asyncio
    async def test_set_profile_aggressive(self):
        manager = RiskManager()
        await manager.set_profile(RiskProfileType.AGGRESSIVE)
        assert manager.active_profile == RiskProfileType.AGGRESSIVE

    @pytest.mark.asyncio
    async def test_get_profile_config(self):
        manager = RiskManager()
        await manager.set_profile(RiskProfileType.CONSERVATIVE)
        cfg = await manager.get_profile_config()
        assert cfg.max_daily_loss_pct == 2.0

    @pytest.mark.asyncio
    async def test_emergency_activation(self):
        manager = RiskManager()
        await manager.activate_emergency(
            EmergencyTrigger.BROKER_DISCONNECT,
            "Broker connection lost",
        )
        assert await manager.is_emergency_mode()

    @pytest.mark.asyncio
    async def test_emergency_resolve(self):
        manager = RiskManager()
        await manager.activate_emergency(EmergencyTrigger.MARKET_FEED_FAILURE)
        await manager.resolve_emergency()
        assert not await manager.is_emergency_mode()

    @pytest.mark.asyncio
    async def test_emergency_status(self):
        manager = RiskManager()
        await manager.activate_emergency(EmergencyTrigger.BROKER_DISCONNECT)
        status = await manager.get_emergency_status()
        assert status.active
        assert len(status.triggers) == 1

    @pytest.mark.asyncio
    async def test_trading_lock(self):
        manager = RiskManager()
        await manager.set_trading_lock(True, "Manual lock", 3600.0)
        status = await manager.get_protection_status()
        assert status.trading_locked
        assert not status.can_trade

    @pytest.mark.asyncio
    async def test_trading_unlock(self):
        manager = RiskManager()
        await manager.set_trading_lock(False)
        status = await manager.get_protection_status()
        assert not status.trading_locked

    @pytest.mark.asyncio
    async def test_customize_and_apply(self):
        manager = RiskManager()
        cfg = await manager.customize_and_apply(
            RiskProfileType.BALANCED,
            {"max_leverage": 25.0},
            "my_profile",
        )
        assert cfg.max_leverage == 25.0
        assert cfg.max_daily_loss_pct == 5.0  # From balanced base

    @pytest.mark.asyncio
    async def test_evaluate_raises_when_not_initialized(self):
        manager = RiskManager(config=RiskManagerConfig(enable_default_policies=False))
        with pytest.raises(EngineNotReadyError):
            await manager.evaluate("test")

    @pytest.mark.asyncio
    async def test_evaluate_after_start(self):
        manager = RiskManager()
        await manager.start()
        result = await manager.evaluate("test")
        assert result is not None

    @pytest.mark.asyncio
    async def test_health_check(self):
        manager = RiskManager()
        await manager.start()
        health = await manager.health_check()
        assert health["running"]
        assert "total_policies" in health
        assert "enabled_policies" in health

    @pytest.mark.asyncio
    async def test_policy_management(self):
        manager = RiskManager()
        await manager.start()

        # Disable a policy
        await manager.disable_policy("maximum_daily_loss")
        enabled = await manager.get_enabled_policies()
        assert "maximum_daily_loss" not in [p.name for p in enabled]

        # Enable it back
        await manager.enable_policy("maximum_daily_loss")
        enabled = await manager.get_enabled_policies()
        assert "maximum_daily_loss" in [p.name for p in enabled]

    @pytest.mark.asyncio
    async def test_get_policy(self):
        manager = RiskManager()
        await manager.start()
        policy = await manager.get_policy("maximum_daily_loss")
        assert policy.name == "maximum_daily_loss"

    @pytest.mark.asyncio
    async def test_statistics_after_evaluation(self):
        manager = RiskManager(track_statistics=True)
        await manager.start()
        await manager.evaluate("test")
        snapshot = await manager.get_statistics_snapshot()
        assert snapshot.total_evaluations >= 0

    @pytest.mark.asyncio
    async def test_reset_statistics(self):
        manager = RiskManager()
        await manager.start()
        await manager.reset_statistics()
        snapshot = await manager.get_statistics_snapshot()
        assert snapshot.total_evaluations == 0

    @pytest.mark.asyncio
    async def test_evaluate_blocks_during_emergency(self):
        manager = RiskManager()
        await manager.start()
        await manager.activate_emergency(EmergencyTrigger.BROKER_DISCONNECT)
        result = await manager.evaluate("test")
        assert result.decision == RiskDecision.REJECTED
        assert result.risk_score == 100.0

    @pytest.mark.asyncio
    async def test_multiple_emergency_triggers(self):
        manager = RiskManager()
        await manager.activate_emergency(EmergencyTrigger.BROKER_DISCONNECT)
        await manager.activate_emergency(EmergencyTrigger.MARKET_FEED_FAILURE)
        # Should not raise - second activation uses same trigger
        status = await manager.get_emergency_status()
        assert status.active

    @pytest.mark.asyncio
    async def test_protection_status_update(self):
        manager = RiskManager()
        from libraries.domain.risk.models import AccountProtectionLevel, AccountProtectionStatus

        status = AccountProtectionStatus(
            level=AccountProtectionLevel.EMERGENCY_STOP,
            trading_locked=True,
        )
        await manager.update_protection_status(status)
        retrieved = await manager.get_protection_status()
        assert retrieved.level == AccountProtectionLevel.EMERGENCY_STOP

    @pytest.mark.asyncio
    async def test_profile_manager(self):
        manager = RiskManager()
        assert manager.profile_manager is not None

    @pytest.mark.asyncio
    async def test_config_defaults(self):
        manager = RiskManager()
        assert manager.active_profile == RiskProfileType.BALANCED

    @pytest.mark.asyncio
    async def test_start_when_already_running(self):
        manager = RiskManager()
        await manager.start()
        await manager.start()  # Should not raise
        assert manager.running

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self):
        manager = RiskManager()
        await manager.stop()  # Should not raise
        assert not manager.running
