"""Tests for EPIC-010 CommissionModel — commission calculation."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.backtesting.commission_model import (
    CommissionModel,
    CommissionModelConfig,
    CommissionTier,
    CommissionType,
)


class TestCommissionType:
    """Test CommissionType enum."""

    def test_enum_values(self):
        assert CommissionType.FIXED_PER_LOT.value == "fixed_per_lot"
        assert CommissionType.FIXED_PER_TRADE.value == "fixed_per_trade"
        assert CommissionType.PERCENTAGE.value == "percentage"
        assert CommissionType.TIERED.value == "tiered"
        assert CommissionType.PER_UNIT.value == "per_unit"
        assert CommissionType.ZERO.value == "zero"


class TestCommissionModelConfig:
    """Test CommissionModelConfig defaults and validation."""

    def test_default_config(self):
        cfg = CommissionModelConfig()
        assert cfg.commission_type == CommissionType.FIXED_PER_LOT
        assert cfg.base_rate == Decimal("7.0")
        assert cfg.currency == "USD"
        assert cfg.minimum_commission == Decimal("0")
        assert cfg.maximum_commission == Decimal("0")
        assert cfg.tiers == ()
        assert cfg.discount_rate == Decimal("0")

    def test_custom_config(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.PERCENTAGE,
            base_rate=Decimal("10.0"),
            currency="EUR",
            minimum_commission=Decimal("1.0"),
            maximum_commission=Decimal("100.0"),
            discount_rate=Decimal("5.0"),
        )
        assert cfg.commission_type == CommissionType.PERCENTAGE
        assert cfg.base_rate == Decimal("10.0")
        assert cfg.currency == "EUR"
        assert cfg.discount_rate == Decimal("5.0")

    def test_config_frozen(self):
        cfg = CommissionModelConfig()
        with pytest.raises(AttributeError):
            cfg.commission_type = CommissionType.ZERO  # type: ignore[misc]


class TestCommissionTier:
    """Test CommissionTier dataclass."""

    def test_tier_creation(self):
        tier = CommissionTier(
            min_volume=Decimal("0"), max_volume=Decimal("10"), rate=Decimal("5.0")
        )
        assert tier.min_volume == Decimal("0")
        assert tier.max_volume == Decimal("10")
        assert tier.rate == Decimal("5.0")

    def test_tier_frozen(self):
        tier = CommissionTier(
            min_volume=Decimal("0"), max_volume=Decimal("10"), rate=Decimal("5.0")
        )
        with pytest.raises(AttributeError):
            tier.rate = Decimal("6.0")  # type: ignore[misc]


class TestCommissionModel:
    """Test CommissionModel calculation."""

    def test_default_initialization(self):
        model = CommissionModel()
        assert model.config.commission_type == CommissionType.FIXED_PER_LOT

    def test_custom_config_via_init(self):
        cfg = CommissionModelConfig(commission_type=CommissionType.ZERO)
        model = CommissionModel(config=cfg)
        assert model.config.commission_type == CommissionType.ZERO

    def test_config_property(self):
        model = CommissionModel()
        assert isinstance(model.config, CommissionModelConfig)

    def test_zero_commission(self):
        cfg = CommissionModelConfig(commission_type=CommissionType.ZERO)
        model = CommissionModel(config=cfg)
        result = model.calculate(Decimal("1"), Decimal("1.1000"))
        assert result == Decimal("0")

    def test_fixed_per_lot(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_LOT,
            base_rate=Decimal("7.0"),
        )
        model = CommissionModel(config=cfg)
        result = model.calculate(Decimal("1"), Decimal("1.1000"))
        assert result == Decimal("7.0")

    def test_fixed_per_lot_multiple_lots(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_LOT,
            base_rate=Decimal("7.0"),
        )
        model = CommissionModel(config=cfg)
        result = model.calculate(Decimal("2.5"), Decimal("1.1000"))
        assert result == Decimal("17.5")

    def test_fixed_per_trade(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_TRADE,
            base_rate=Decimal("10.0"),
        )
        model = CommissionModel(config=cfg)
        result = model.calculate(Decimal("5"), Decimal("1.1000"))
        assert result == Decimal("10.0")

    def test_percentage_commission(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.PERCENTAGE,
            percentage_rate=Decimal("0.1"),
        )
        model = CommissionModel(config=cfg)
        # notional = 1 * 1.1000 = 1.1, commission = 1.1 * 0.1/100 = 0.0011
        result = model.calculate(Decimal("1"), Decimal("1.1000"))
        assert result == Decimal("0.0011")

    def test_percentage_large_notional(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.PERCENTAGE,
            percentage_rate=Decimal("1.0"),
        )
        model = CommissionModel(config=cfg)
        # notional = 100000 * 1.1000 = 110000, commission = 110000 * 1/100 = 1100
        result = model.calculate(Decimal("100000"), Decimal("1.1000"))
        assert result == Decimal("1100")

    def test_per_unit_commission(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.PER_UNIT,
            per_unit_rate=Decimal("0.50"),
        )
        model = CommissionModel(config=cfg)
        result = model.calculate(Decimal("100"), Decimal("1.1000"))
        assert result == Decimal("50.0")

    def test_tiered_commission_within_tier(self):
        tiers = (
            CommissionTier(Decimal("0"), Decimal("10"), Decimal("7.0")),
            CommissionTier(Decimal("10"), Decimal("50"), Decimal("6.0")),
            CommissionTier(Decimal("50"), Decimal("100"), Decimal("5.0")),
        )
        cfg = CommissionModelConfig(
            commission_type=CommissionType.TIERED,
            tiers=tiers,
        )
        model = CommissionModel(config=cfg)
        result = model.calculate(Decimal("25"), Decimal("1.1000"))
        assert result == Decimal("150.0")  # 25 * 6.0

    def test_tiered_commission_exceeds_tiers(self):
        """Volume exceeds all tiers, falls to last tier rate."""
        tiers = (CommissionTier(Decimal("0"), Decimal("10"), Decimal("7.0")),)
        cfg = CommissionModelConfig(
            commission_type=CommissionType.TIERED,
            base_rate=Decimal("8.0"),
            tiers=tiers,
        )
        model = CommissionModel(config=cfg)
        result = model.calculate(Decimal("25"), Decimal("1.1000"))
        # volume=25 doesn't match tier 0-10, falls to last tier rate * volume = 7.0 * 25 = 175.0
        assert result == Decimal("175.0")

    def test_tiered_commission_exceeds_all_tiers(self):
        tiers = (
            CommissionTier(Decimal("0"), Decimal("10"), Decimal("7.0")),
            CommissionTier(Decimal("10"), Decimal("50"), Decimal("6.0")),
        )
        cfg = CommissionModelConfig(
            commission_type=CommissionType.TIERED,
            tiers=tiers,
        )
        model = CommissionModel(config=cfg)
        result = model.calculate(Decimal("100"), Decimal("1.1000"))
        assert result == Decimal("600.0")  # 100 * 6.0 (last tier)

    def test_minimum_commission_applied(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_LOT,
            base_rate=Decimal("1.0"),
            minimum_commission=Decimal("5.0"),
        )
        model = CommissionModel(config=cfg)
        result = model.calculate(Decimal("1"), Decimal("1.1000"))
        assert result == Decimal("5.0")

    def test_maximum_commission_applied(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_LOT,
            base_rate=Decimal("100.0"),
            maximum_commission=Decimal("50.0"),
        )
        model = CommissionModel(config=cfg)
        result = model.calculate(Decimal("1"), Decimal("1.1000"))
        assert result == Decimal("50.0")

    def test_discount_applied(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_LOT,
            base_rate=Decimal("10.0"),
            discount_rate=Decimal("10.0"),
        )
        model = CommissionModel(config=cfg)
        result = model.calculate(Decimal("1"), Decimal("1.1000"))
        assert result == Decimal("9.0")  # 10 - 10%

    def test_zero_discount_no_effect(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_LOT,
            base_rate=Decimal("10.0"),
            discount_rate=Decimal("0"),
        )
        model = CommissionModel(config=cfg)
        result = model.calculate(Decimal("1"), Decimal("1.1000"))
        assert result == Decimal("10.0")

    def test_calculate_for_order_rounding(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_LOT,
            base_rate=Decimal("7.123"),
        )
        model = CommissionModel(config=cfg)
        result = model.calculate_for_order(Decimal("1"), Decimal("1.1000"))
        assert result == Decimal("7.12")

    def test_calculate_for_order_open_close(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.PERCENTAGE,
            percentage_rate=Decimal("0.1"),
        )
        model = CommissionModel(config=cfg)
        result_open = model.calculate_for_order(Decimal("1"), Decimal("1.1000"), is_open=True)
        result_close = model.calculate_for_order(Decimal("1"), Decimal("1.1000"), is_open=False)
        assert result_open == result_close  # Same calculation for both

    def test_calculate_with_metadata(self):
        model = CommissionModel()
        result = model.calculate(
            Decimal("1"),
            Decimal("1.1000"),
            currency="EUR",
            metadata={"client_type": "institutional"},
        )
        assert result is not None

    def test_decimal_precision_in_tiered(self):
        tiers = (CommissionTier(Decimal("0"), Decimal("1"), Decimal("7.50")),)
        cfg = CommissionModelConfig(
            commission_type=CommissionType.TIERED,
            tiers=tiers,
        )
        model = CommissionModel(config=cfg)
        result = model.calculate(Decimal("0.5"), Decimal("1.1000"))
        assert result == Decimal("3.75")  # 0.5 * 7.50

    def test_large_volume_no_overflow(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_LOT,
            base_rate=Decimal("7.0"),
        )
        model = CommissionModel(config=cfg)
        result = model.calculate(Decimal("1000000"), Decimal("1.1000"))
        assert result == Decimal("7000000.0")

    def test_unknown_type_defaults_to_zero(self):
        cfg = CommissionModelConfig(
            commission_type="unknown_type",  # type: ignore[arg-type]
        )
        model = CommissionModel(config=cfg)
        result = model.calculate(Decimal("1"), Decimal("1.1000"))
        assert result == Decimal("0")

    def test_config_mutation_not_possible(self):
        model = CommissionModel()
        assert hasattr(model, "_config")
        config_id = id(model._config)
        # Calling calculate should not change the config
        model.calculate(Decimal("1"), Decimal("1.1000"))
        assert id(model._config) == config_id
