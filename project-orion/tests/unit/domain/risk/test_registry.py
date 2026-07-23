"""Tests for the RiskPolicyRegistry."""

from __future__ import annotations

import pytest

from libraries.domain.risk.exceptions import (
    PolicyNotFoundError,
    PolicyRegistrationError,
    RegistryFullError,
)
from libraries.domain.risk.models import PolicyCategory, PolicySeverity
from libraries.domain.risk.policy import (
    MaximumDailyLossPolicy,
    MaximumPositionSizePolicy,
    SpreadProtectionPolicy,
    create_default_policies,
)
from libraries.domain.risk.registry import RiskPolicyRegistry


class TestRiskPolicyRegistry:
    @pytest.mark.asyncio
    async def test_register_and_get(self):
        registry = RiskPolicyRegistry()
        policy = MaximumDailyLossPolicy()
        await registry.register(policy)
        retrieved = await registry.get("maximum_daily_loss")
        assert retrieved.name == "maximum_daily_loss"

    @pytest.mark.asyncio
    async def test_register_duplicate_raises(self):
        registry = RiskPolicyRegistry()
        policy = MaximumDailyLossPolicy()
        await registry.register(policy)
        with pytest.raises(PolicyRegistrationError, match="already registered"):
            await registry.register(MaximumDailyLossPolicy())

    @pytest.mark.asyncio
    async def test_get_not_found_raises(self):
        registry = RiskPolicyRegistry()
        with pytest.raises(PolicyNotFoundError):
            await registry.get("nonexistent_policy")

    @pytest.mark.asyncio
    async def test_unregister(self):
        registry = RiskPolicyRegistry()
        policy = MaximumDailyLossPolicy()
        await registry.register(policy)
        await registry.unregister("maximum_daily_loss")
        assert not await registry.contains("maximum_daily_loss")

    @pytest.mark.asyncio
    async def test_unregister_not_found_raises(self):
        registry = RiskPolicyRegistry()
        with pytest.raises(PolicyNotFoundError):
            await registry.unregister("nonexistent")

    @pytest.mark.asyncio
    async def test_contains(self):
        registry = RiskPolicyRegistry()
        assert not await registry.contains("test")
        await registry.register(MaximumDailyLossPolicy())
        assert await registry.contains("maximum_daily_loss")

    @pytest.mark.asyncio
    async def test_count(self):
        registry = RiskPolicyRegistry()
        assert await registry.count() == 0
        await registry.register(MaximumDailyLossPolicy())
        assert await registry.count() == 1
        await registry.register(MaximumPositionSizePolicy())
        assert await registry.count() == 2

    @pytest.mark.asyncio
    async def test_enabled_count(self):
        registry = RiskPolicyRegistry()
        await registry.register(MaximumDailyLossPolicy())
        assert await registry.enabled_count() == 1

    @pytest.mark.asyncio
    async def test_disabled_count(self):
        registry = RiskPolicyRegistry()
        policy = MaximumDailyLossPolicy()
        policy._enabled = False
        await registry.register(policy)
        assert await registry.disabled_count() == 1

    @pytest.mark.asyncio
    async def test_list_all(self):
        registry = RiskPolicyRegistry()
        policies = create_default_policies()
        for p in policies:
            await registry.register(p)
        all_policies = await registry.get_all()
        assert len(all_policies) == 28

    @pytest.mark.asyncio
    async def test_list_enabled(self):
        registry = RiskPolicyRegistry()
        policies = create_default_policies()
        for p in policies:
            await registry.register(p)
        enabled = await registry.list_enabled()
        assert len(enabled) == 28  # All enabled by default

    @pytest.mark.asyncio
    async def test_list_by_category(self):
        registry = RiskPolicyRegistry()
        await registry.register(MaximumDailyLossPolicy())
        await registry.register(SpreadProtectionPolicy())

        loss_policies = await registry.list_by_category(PolicyCategory.LOSS_LIMITS)
        assert len(loss_policies) == 1
        assert loss_policies[0].name == "maximum_daily_loss"

    @pytest.mark.asyncio
    async def test_list_with_enabled_filter(self):
        registry = RiskPolicyRegistry()
        policy = MaximumDailyLossPolicy()
        await registry.register(policy)

        enabled = await registry.list(enabled_only=True)
        assert len(enabled) == 1

        disabled = await registry.list(enabled_only=False)
        assert len(disabled) == 0

    @pytest.mark.asyncio
    async def test_max_policies_raises(self):
        registry = RiskPolicyRegistry(max_policies=2)
        await registry.register(MaximumDailyLossPolicy())
        await registry.register(MaximumPositionSizePolicy())
        with pytest.raises(RegistryFullError):
            await registry.register(SpreadProtectionPolicy())

    @pytest.mark.asyncio
    async def test_clear(self):
        registry = RiskPolicyRegistry()
        await registry.register(MaximumDailyLossPolicy())
        await registry.register(MaximumPositionSizePolicy())
        assert await registry.count() == 2
        await registry.clear()
        assert await registry.count() == 0

    @pytest.mark.asyncio
    async def test_get_policy_names(self):
        registry = RiskPolicyRegistry()
        await registry.register(MaximumDailyLossPolicy())
        await registry.register(MaximumPositionSizePolicy())
        names = await registry.get_policy_names()
        assert "maximum_daily_loss" in names
        assert "maximum_position_size" in names
        assert len(names) == 2

    @pytest.mark.asyncio
    async def test_get_categories(self):
        registry = RiskPolicyRegistry()
        await registry.register(MaximumDailyLossPolicy())
        await registry.register(MaximumPositionSizePolicy())
        categories = await registry.get_categories()
        assert PolicyCategory.LOSS_LIMITS in categories
        assert PolicyCategory.POSITION_SIZING in categories

    @pytest.mark.asyncio
    async def test_empty_name_raises(self):
        registry = RiskPolicyRegistry()
        policy = MaximumDailyLossPolicy()
        policy._name = ""
        with pytest.raises(PolicyRegistrationError):
            await registry.register(policy)

    @pytest.mark.asyncio
    async def test_policy_sorting(self):
        registry = RiskPolicyRegistry()
        # Register in reverse priority order
        from libraries.domain.risk.policy import EmergencyStopPolicy, MaximumPositionSizePolicy

        await registry.register(MaximumPositionSizePolicy())  # priority 10
        await registry.register(EmergencyStopPolicy())  # priority 5

        policies = await registry.list_enabled()
        assert policies[0].priority <= policies[1].priority
