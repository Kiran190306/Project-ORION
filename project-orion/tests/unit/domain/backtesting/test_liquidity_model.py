"""Tests for EPIC-010 LiquidityModel — market liquidity simulation."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.backtesting.liquidity_model import (
    LiquidityModel,
    LiquidityModelConfig,
)


class TestLiquidityModelConfig:
    """Test LiquidityModelConfig defaults."""

    def test_default_config(self):
        cfg = LiquidityModelConfig()
        assert cfg.default_liquidity_score == 0.8
        assert cfg.max_order_pct_of_volume == 0.1
        assert cfg.volume_threshold_lots == Decimal("50")
        assert cfg.liquidity_decay_factor == 0.95
        assert cfg.min_liquidity_score == 0.1

    def test_custom_config(self):
        cfg = LiquidityModelConfig(
            default_liquidity_score=0.9,
            max_order_pct_of_volume=0.2,
            volume_threshold_lots=Decimal("100"),
            liquidity_decay_factor=0.9,
            min_liquidity_score=0.05,
        )
        assert cfg.default_liquidity_score == 0.9
        assert cfg.max_order_pct_of_volume == 0.2
        assert cfg.min_liquidity_score == 0.05

    def test_config_frozen(self):
        cfg = LiquidityModelConfig()
        with pytest.raises(AttributeError):
            cfg.default_liquidity_score = 0.5  # type: ignore[misc]


class TestLiquidityModel:
    """Test LiquidityModel calculation."""

    def test_default_initialization(self):
        model = LiquidityModel()
        assert model.config.default_liquidity_score == 0.8

    def test_config_property(self):
        model = LiquidityModel()
        assert isinstance(model.config, LiquidityModelConfig)

    def test_default_liquidity_score(self):
        model = LiquidityModel()
        # Use deterministic timestamp during regular market hours (10 AM UTC)
        # to avoid time-dependent failures when tests run during London/NY overlap.
        ts = datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc)
        score = model.get_liquidity_score("EURUSD", Decimal("1"), timestamp=ts)
        assert score == 0.8

    def test_custom_base_score(self):
        model = LiquidityModel()
        score = model.get_liquidity_score("EURUSD", Decimal("1"), base_score=0.95)
        assert score == 0.95

    def test_large_order_reduces_liquidity(self):
        model = LiquidityModel()
        score = model.get_liquidity_score("EURUSD", Decimal("100"))
        assert score < 0.8
        assert score >= 0.1

    def test_very_large_order_min_liquidity(self):
        model = LiquidityModel()
        score = model.get_liquidity_score("EURUSD", Decimal("10000"))
        assert score == 0.1  # Should be clamped to min

    def test_order_below_threshold_no_decay(self):
        model = LiquidityModel()
        score = model.get_liquidity_score("EURUSD", Decimal("10"))
        assert score == 0.8

    def test_asian_session_lower_liquidity(self):
        model = LiquidityModel()
        ts = datetime(2023, 1, 1, 3, 0, tzinfo=timezone.utc)  # 3 AM UTC = Asian
        score = model.get_liquidity_score("EURUSD", Decimal("1"), timestamp=ts)
        assert score == 0.56  # 0.8 * 0.7

    def test_london_ny_overlap_higher_liquidity(self):
        model = LiquidityModel()
        ts = datetime(2023, 1, 1, 14, 0, tzinfo=timezone.utc)  # 2 PM UTC = London/NY overlap
        score = model.get_liquidity_score("EURUSD", Decimal("1"), timestamp=ts)
        assert score == 0.96  # 0.8 * 1.2

    def test_late_session_reduced_liquidity(self):
        model = LiquidityModel()
        ts = datetime(2023, 1, 1, 19, 0, tzinfo=timezone.utc)  # 7 PM UTC
        score = model.get_liquidity_score("EURUSD", Decimal("1"), timestamp=ts)
        assert score == 0.68  # 0.8 * 0.85

    def test_regular_hours_normal_liquidity(self):
        model = LiquidityModel()
        ts = datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc)  # 10 AM UTC
        score = model.get_liquidity_score("EURUSD", Decimal("1"), timestamp=ts)
        assert score == 0.8

    def test_is_executable_small_order(self):
        model = LiquidityModel()
        result = model.is_executable(Decimal("1"), Decimal("100"))
        assert result is True

    def test_is_executable_large_order(self):
        model = LiquidityModel()
        result = model.is_executable(Decimal("50"), Decimal("100"))
        # 50/100 = 0.5 > 0.1 max
        assert result is False

    def test_is_executable_no_current_volume(self):
        model = LiquidityModel()
        result = model.is_executable(Decimal("1000"))
        assert result is True

    def test_is_executable_zero_volume(self):
        model = LiquidityModel()
        result = model.is_executable(Decimal("0"), Decimal("100"))
        assert result is True

    def test_is_executable_boundary(self):
        model = LiquidityModel()
        result = model.is_executable(Decimal("10"), Decimal("100"))
        # 10/100 = 0.1, exactly at threshold
        assert result is True

    def test_get_max_executable_volume(self):
        model = LiquidityModel()
        result = model.get_max_executable_volume(Decimal("1000"))
        assert result == Decimal("100.00")  # 1000 * 0.1

    def test_get_max_executable_volume_zero(self):
        model = LiquidityModel()
        result = model.get_max_executable_volume(Decimal("0"))
        assert result == Decimal("0.00")

    def test_get_max_executable_volume_small(self):
        model = LiquidityModel()
        result = model.get_max_executable_volume(Decimal("1.5"))
        assert result == Decimal("0.15")

    def test_get_max_executable_volume_custom_config(self):
        cfg = LiquidityModelConfig(max_order_pct_of_volume=0.25)
        model = LiquidityModel(config=cfg)
        result = model.get_max_executable_volume(Decimal("1000"))
        assert result == Decimal("250.00")

    def test_liquidity_score_rounding(self):
        model = LiquidityModel()
        score = model.get_liquidity_score("EURUSD", Decimal("1"), base_score=0.12345)
        assert score == 0.1235  # Rounded to 4 decimal places

    def test_decay_factor_effect(self):
        cfg = LiquidityModelConfig(volume_threshold_lots=Decimal("1"), liquidity_decay_factor=0.5)
        model = LiquidityModel(config=cfg)
        score = model.get_liquidity_score("EURUSD", Decimal("5"))
        # score = 0.8 * (0.5 ** 4) = 0.8 * 0.0625 = 0.05, clamped to 0.1
        assert score == 0.1

    def test_min_liquidity_clamping(self):
        cfg = LiquidityModelConfig(min_liquidity_score=0.2)
        model = LiquidityModel(config=cfg)
        score = model.get_liquidity_score("EURUSD", Decimal("10000"))
        assert score == 0.2

    def test_symbol_agnostic(self):
        model = LiquidityModel()
        score1 = model.get_liquidity_score("EURUSD", Decimal("1"))
        score2 = model.get_liquidity_score("GBPJPY", Decimal("1"))
        assert score1 == score2  # Symbol doesn't affect base score
