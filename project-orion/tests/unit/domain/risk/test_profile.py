"""Tests for risk profiles."""

from __future__ import annotations

import pytest

from libraries.domain.risk.exceptions import ProfileNotFoundError, ProfileValidationError
from libraries.domain.risk.models import RiskProfileType
from libraries.domain.risk.profile import RiskProfileConfig, RiskProfileManager


class TestRiskProfileConfig:
    def test_conservative_defaults(self):
        cfg = RiskProfileConfig.conservative()
        assert cfg.max_position_size_pct == 5.0
        assert cfg.max_daily_loss_pct == 2.0
        assert cfg.max_leverage == 20.0
        assert cfg.max_open_positions == 5
        assert not cfg.allow_weekend_trading
        assert cfg.cooldown_after_loss_minutes == 30.0

    def test_balanced_defaults(self):
        cfg = RiskProfileConfig.balanced()
        assert cfg.max_position_size_pct == 10.0
        assert cfg.max_daily_loss_pct == 5.0
        assert cfg.max_leverage == 50.0
        assert cfg.max_open_positions == 10
        assert not cfg.allow_weekend_trading
        assert cfg.cooldown_after_loss_minutes == 15.0

    def test_aggressive_defaults(self):
        cfg = RiskProfileConfig.aggressive()
        assert cfg.max_position_size_pct == 20.0
        assert cfg.max_daily_loss_pct == 10.0
        assert cfg.max_leverage == 100.0
        assert cfg.max_open_positions == 20
        assert cfg.allow_weekend_trading
        assert cfg.cooldown_after_loss_minutes == 5.0

    def test_custom_defaults_match_balanced(self):
        cfg = RiskProfileConfig.custom()
        assert cfg.max_position_size_pct == 10.0
        assert cfg.max_daily_loss_pct == 5.0

    def test_to_dict(self):
        cfg = RiskProfileConfig.balanced()
        d = cfg.to_dict()
        assert d["max_position_size_pct"] == 10.0
        assert d["max_leverage"] == 50.0
        assert "max_daily_loss_pct" in d

    def test_from_dict(self):
        data = {
            "max_position_size_pct": 15.0,
            "max_leverage": 30.0,
            "max_daily_loss_pct": 8.0,
        }
        cfg = RiskProfileConfig.from_dict(data)
        assert cfg.max_position_size_pct == 15.0
        assert cfg.max_leverage == 30.0
        assert cfg.max_daily_loss_pct == 8.0

    def test_from_dict_ignores_unknown_keys(self):
        data = {"max_position_size_pct": 10.0, "unknown_key": 999}
        cfg = RiskProfileConfig.from_dict(data)
        assert cfg.max_position_size_pct == 10.0
        assert not hasattr(cfg, "unknown_key")


class TestRiskProfileManager:
    @pytest.mark.asyncio
    async def test_get_builtin_profiles(self):
        manager = RiskProfileManager()
        for pt in [
            RiskProfileType.CONSERVATIVE,
            RiskProfileType.BALANCED,
            RiskProfileType.AGGRESSIVE,
        ]:
            config = await manager.get_profile(pt)
            assert config is not None

    @pytest.mark.asyncio
    async def test_get_custom_profile_not_found(self):
        manager = RiskProfileManager()
        with pytest.raises(ProfileNotFoundError):
            await manager.get_profile("nonexistent_profile")

    @pytest.mark.asyncio
    async def test_customize_profile(self):
        manager = RiskProfileManager()
        overrides = {"max_leverage": 25.0, "max_position_size_pct": 7.5}
        cfg = await manager.customize_profile(RiskProfileType.BALANCED, overrides, "my_profile")
        assert cfg.max_leverage == 25.0
        assert cfg.max_position_size_pct == 7.5
        assert cfg.max_daily_loss_pct == 5.0  # From balanced base

    @pytest.mark.asyncio
    async def test_customize_profile_invalid_key(self):
        manager = RiskProfileManager()
        with pytest.raises(ProfileValidationError):
            await manager.customize_profile(
                RiskProfileType.BALANCED,
                {"invalid_key": 100},
            )

    @pytest.mark.asyncio
    async def test_customize_profile_out_of_range(self):
        manager = RiskProfileManager()
        with pytest.raises(ProfileValidationError):
            await manager.customize_profile(
                RiskProfileType.BALANCED,
                {"max_position_size_pct": -1},
            )

    @pytest.mark.asyncio
    async def test_list_profiles(self):
        manager = RiskProfileManager()
        profiles = await manager.list_profiles()
        # Built-in profiles
        for pt in RiskProfileType:
            assert pt.value in profiles

    @pytest.mark.asyncio
    async def test_delete_custom_profile(self):
        manager = RiskProfileManager()
        await manager.customize_profile(RiskProfileType.BALANCED, {}, "temp_profile")
        await manager.delete_custom_profile("temp_profile")
        profiles = await manager.list_profiles()
        assert "temp_profile" not in profiles

    @pytest.mark.asyncio
    async def test_delete_builtin_profile_raises(self):
        manager = RiskProfileManager()
        with pytest.raises(ProfileNotFoundError):
            await manager.delete_custom_profile("balanced")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_profile_raises(self):
        manager = RiskProfileManager()
        with pytest.raises(ProfileNotFoundError):
            await manager.delete_custom_profile("does_not_exist")

    @pytest.mark.asyncio
    async def test_validate_config_valid(self):
        manager = RiskProfileManager()
        cfg = RiskProfileConfig.balanced()
        errors = await manager.validate_config(cfg)
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_validate_config_invalid(self):
        manager = RiskProfileManager()
        cfg = RiskProfileConfig(
            max_position_size_pct=200.0,  # > 100
            max_leverage=0,  # < 1
            soft_stop_loss_pct=30.0,
            hard_stop_loss_pct=10.0,  # soft > hard -> invalid
        )
        errors = await manager.validate_config(cfg)
        assert len(errors) >= 1

    @pytest.mark.asyncio
    async def test_apply_profile(self):
        manager = RiskProfileManager()
        cfg = await manager.apply_profile(RiskProfileType.CONSERVATIVE)
        assert cfg.max_daily_loss_pct == 2.0

    @pytest.mark.asyncio
    async def test_custom_profile_persists(self):
        manager = RiskProfileManager()
        await manager.customize_profile(RiskProfileType.BALANCED, {"max_leverage": 15.0}, "low_lev")
        cfg = await manager.get_profile("low_lev")
        assert cfg.max_leverage == 15.0
        assert cfg.max_position_size_pct == 10.0  # From balanced base

    @pytest.mark.asyncio
    async def test_string_profile_lookup(self):
        manager = RiskProfileManager()
        cfg = await manager.get_profile("conservative")
        assert cfg.max_position_size_pct == 5.0
