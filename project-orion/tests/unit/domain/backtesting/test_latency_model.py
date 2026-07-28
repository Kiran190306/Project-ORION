"""Tests for EPIC-010 LatencyModel — broker delay simulation."""

from __future__ import annotations

import pytest

from libraries.domain.backtesting.latency_model import LatencyModel, LatencyModelConfig


class TestLatencyModelConfig:
    """Test LatencyModelConfig defaults and validation."""

    def test_default_config(self):
        cfg = LatencyModelConfig()
        assert cfg.base_latency_ms == 50.0
        assert cfg.jitter_ms == 20.0
        assert cfg.min_latency_ms == 10.0
        assert cfg.max_latency_ms == 500.0
        assert cfg.use_jitter is True
        assert cfg.random_seed is None

    def test_custom_config(self):
        cfg = LatencyModelConfig(
            base_latency_ms=100.0,
            jitter_ms=10.0,
            min_latency_ms=20.0,
            max_latency_ms=1000.0,
            use_jitter=False,
            random_seed=42,
        )
        assert cfg.base_latency_ms == 100.0
        assert cfg.jitter_ms == 10.0
        assert cfg.use_jitter is False
        assert cfg.random_seed == 42

    def test_config_frozen(self):
        cfg = LatencyModelConfig()
        with pytest.raises(AttributeError):
            cfg.base_latency_ms = 100.0  # type: ignore[misc]


class TestLatencyModel:
    """Test LatencyModel calculation."""

    def test_default_initialization(self):
        model = LatencyModel()
        assert model.config.base_latency_ms == 50.0

    def test_custom_config_via_init(self):
        cfg = LatencyModelConfig(base_latency_ms=200.0, use_jitter=False)
        model = LatencyModel(config=cfg)
        assert model.config.base_latency_ms == 200.0

    def test_config_property(self):
        model = LatencyModel()
        assert isinstance(model.config, LatencyModelConfig)

    def test_base_latency_no_jitter(self):
        cfg = LatencyModelConfig(base_latency_ms=100.0, use_jitter=False)
        model = LatencyModel(config=cfg)
        result = model.calculate_latency_ms()
        assert result == 100.0

    def test_latency_with_jitter(self):
        cfg = LatencyModelConfig(base_latency_ms=100.0, jitter_ms=10.0, random_seed=42)
        model = LatencyModel(config=cfg)
        result = model.calculate_latency_ms()
        # With seed 42, jitter should be deterministic
        assert 90.0 <= result <= 110.0

    def test_market_order_latency(self):
        cfg = LatencyModelConfig(base_latency_ms=100.0, use_jitter=False)
        model = LatencyModel(config=cfg)
        result = model.calculate_latency_ms(order_type="market")
        assert result == 100.0  # No multiplier for market

    def test_limit_order_latency(self):
        cfg = LatencyModelConfig(base_latency_ms=100.0, use_jitter=False)
        model = LatencyModel(config=cfg)
        result = model.calculate_latency_ms(order_type="limit")
        assert result == 150.0  # 100 * 1.5

    def test_stop_order_latency(self):
        cfg = LatencyModelConfig(base_latency_ms=100.0, use_jitter=False)
        model = LatencyModel(config=cfg)
        result = model.calculate_latency_ms(order_type="stop")
        assert result == 130.0  # 100 * 1.3

    def test_large_volume_increases_latency(self):
        cfg = LatencyModelConfig(base_latency_ms=100.0, use_jitter=False)
        model = LatencyModel(config=cfg)
        result = model.calculate_latency_ms(order_type="market", volume=20.0)
        # 100 * (1 + (20-10) * 0.02) = 100 * 1.2 = 120
        assert result == 120.0

    def test_small_volume_no_increase(self):
        cfg = LatencyModelConfig(base_latency_ms=100.0, use_jitter=False)
        model = LatencyModel(config=cfg)
        result = model.calculate_latency_ms(order_type="market", volume=5.0)
        assert result == 100.0

    def test_latency_clamped_to_min(self):
        cfg = LatencyModelConfig(base_latency_ms=5.0, min_latency_ms=10.0, use_jitter=False)
        model = LatencyModel(config=cfg)
        result = model.calculate_latency_ms()
        assert result == 10.0

    def test_latency_clamped_to_max(self):
        cfg = LatencyModelConfig(base_latency_ms=1000.0, max_latency_ms=500.0, use_jitter=False)
        model = LatencyModel(config=cfg)
        result = model.calculate_latency_ms()
        assert result == 500.0

    def test_rounding_to_one_decimal(self):
        cfg = LatencyModelConfig(base_latency_ms=100.123, use_jitter=False)
        model = LatencyModel(config=cfg)
        result = model.calculate_latency_ms()
        assert result == 100.1

    def test_confirmation_delay_with_latency(self):
        cfg = LatencyModelConfig(base_latency_ms=100.0, use_jitter=False, random_seed=42)
        model = LatencyModel(config=cfg)
        result = model.calculate_confirmation_delay_ms(latency_ms=100.0)
        # Confirmation is 1-2x latency
        assert 100.0 <= result <= 200.0

    def test_confirmation_delay_without_latency(self):
        cfg = LatencyModelConfig(base_latency_ms=100.0, use_jitter=False, random_seed=42)
        model = LatencyModel(config=cfg)
        result = model.calculate_confirmation_delay_ms()
        # Should calculate latency first, then apply multiplier
        assert 100.0 <= result <= 200.0

    def test_deterministic_with_seed(self):
        cfg = LatencyModelConfig(base_latency_ms=100.0, jitter_ms=20.0, random_seed=12345)
        model1 = LatencyModel(config=cfg)
        model2 = LatencyModel(config=cfg)
        result1 = model1.calculate_latency_ms()
        result2 = model2.calculate_latency_ms()
        assert result1 == result2

    def test_different_seeds_different_results(self):
        cfg1 = LatencyModelConfig(base_latency_ms=100.0, jitter_ms=20.0, random_seed=1)
        cfg2 = LatencyModelConfig(base_latency_ms=100.0, jitter_ms=20.0, random_seed=2)
        model1 = LatencyModel(config=cfg1)
        model2 = LatencyModel(config=cfg2)
        result1 = model1.calculate_latency_ms()
        result2 = model2.calculate_latency_ms()
        # Different seeds should (almost certainly) give different results
        assert result1 != result2

    def test_latency_with_limit_and_volume(self):
        cfg = LatencyModelConfig(base_latency_ms=100.0, use_jitter=False)
        model = LatencyModel(config=cfg)
        result = model.calculate_latency_ms(order_type="limit", volume=20.0)
        # 100 * 1.5 * 1.2 = 180
        assert result == 180.0

    def test_latency_with_stop_and_volume(self):
        cfg = LatencyModelConfig(base_latency_ms=100.0, use_jitter=False)
        model = LatencyModel(config=cfg)
        result = model.calculate_latency_ms(order_type="stop", volume=15.0)
        # 100 * 1.3 * 1.1 = 143
        assert result == 143.0

    def test_case_insensitive_order_type(self):
        cfg = LatencyModelConfig(base_latency_ms=100.0, use_jitter=False)
        model = LatencyModel(config=cfg)
        result = model.calculate_latency_ms(order_type="LIMIT")
        assert result == 150.0

    def test_empty_order_type_defaults_market(self):
        cfg = LatencyModelConfig(base_latency_ms=100.0, use_jitter=False)
        model = LatencyModel(config=cfg)
        result = model.calculate_latency_ms(order_type="")
        assert result == 100.0
