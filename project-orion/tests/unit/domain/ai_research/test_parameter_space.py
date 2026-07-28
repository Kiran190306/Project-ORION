"""Tests for parameter_space module."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.ai_research.exceptions import ParameterSpaceError
from libraries.domain.ai_research.models import (
    ParameterConstraint,
    ParameterDefinition,
    ParameterSpace,
    ParameterType,
)
from libraries.domain.ai_research.parameter_space import ParameterSpaceBuilder


class TestParameterConstraint:
    def test_default_constraint(self):
        c = ParameterConstraint()
        assert c.min_value is None
        assert c.max_value is None
        assert c.step is None
        assert c.values == ()

    def test_valid_range(self):
        c = ParameterConstraint(min_value=1, max_value=10)
        assert c.min_value == 1
        assert c.max_value == 10

    def test_invalid_range_raises_error(self):
        with pytest.raises(ValueError, match="min_value must not exceed max_value"):
            ParameterConstraint(min_value=10, max_value=1)

    def test_negative_step_raises_error(self):
        with pytest.raises(ValueError, match="step must be positive"):
            ParameterConstraint(min_value=1, max_value=10, step=-1)

    def test_zero_step_raises_error(self):
        with pytest.raises(ValueError, match="step must be positive"):
            ParameterConstraint(min_value=1, max_value=10, step=0)


class TestParameterDefinition:
    def test_valid_int_parameter(self):
        p = ParameterDefinition(
            name="lookback",
            parameter_type=ParameterType.INT,
            default=14,
            constraint=ParameterConstraint(min_value=5, max_value=50),
        )
        assert p.name == "lookback"
        assert p.parameter_type == ParameterType.INT
        assert p.default == 14

    def test_empty_name_raises_error(self):
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            ParameterDefinition(name="", parameter_type=ParameterType.INT)

    def test_float_parameter(self):
        p = ParameterDefinition(
            name="threshold",
            parameter_type=ParameterType.FLOAT,
            default=0.5,
            constraint=ParameterConstraint(min_value=0.0, max_value=1.0, step=0.1),
        )
        assert p.parameter_type == ParameterType.FLOAT

    def test_bool_parameter(self):
        p = ParameterDefinition(
            name="enabled",
            parameter_type=ParameterType.BOOL,
            default=True,
        )
        assert p.parameter_type == ParameterType.BOOL

    def test_categorical_parameter(self):
        p = ParameterDefinition(
            name="method",
            parameter_type=ParameterType.CATEGORICAL,
            default="sma",
            constraint=ParameterConstraint(values=("sma", "ema", "wma")),
        )
        assert p.parameter_type == ParameterType.CATEGORICAL

    def test_metadata(self):
        p = ParameterDefinition(
            name="test", parameter_type=ParameterType.INT, metadata={"description": "test param"}
        )
        assert p.metadata == {"description": "test param"}

    def test_frozen(self):
        p = ParameterDefinition(name="test", parameter_type=ParameterType.INT)
        with pytest.raises(AttributeError):
            p.name = "new_name"  # type: ignore[misc]


class TestParameterSpace:
    def test_empty_space(self):
        space = ParameterSpace(parameters=())
        assert space.size == 0

    def test_valid_space(self):
        p1 = ParameterDefinition(name="p1", parameter_type=ParameterType.INT)
        p2 = ParameterDefinition(name="p2", parameter_type=ParameterType.FLOAT)
        space = ParameterSpace(parameters=(p1, p2))
        assert space.size == 2

    def test_duplicate_names_raises_error(self):
        p1 = ParameterDefinition(name="dup", parameter_type=ParameterType.INT)
        p2 = ParameterDefinition(name="dup", parameter_type=ParameterType.FLOAT)
        with pytest.raises(ValueError, match="parameter names must be unique"):
            ParameterSpace(parameters=(p1, p2))

    def test_frozen(self):
        p = ParameterDefinition(name="p1", parameter_type=ParameterType.INT)
        space = ParameterSpace(parameters=(p,))
        with pytest.raises(AttributeError):
            space.parameters = ()  # type: ignore[misc]

    def test_metadata(self):
        space = ParameterSpace(parameters=(), metadata={"key": "value"})
        assert space.metadata == {"key": "value"}


class TestParameterSpaceBuilder:
    def test_build_empty(self):
        builder = ParameterSpaceBuilder()
        space = builder.build()
        assert space.size == 0

    def test_build_with_int(self):
        builder = ParameterSpaceBuilder()
        builder.add_int("lookback", min_value=5, max_value=50, step=5, default=14)
        space = builder.build()
        assert space.size == 1
        assert space.parameters[0].name == "lookback"
        assert space.parameters[0].parameter_type == ParameterType.INT

    def test_build_with_float(self):
        builder = ParameterSpaceBuilder()
        builder.add_float("threshold", min_value=0.0, max_value=1.0, default=0.5)
        space = builder.build()
        assert space.size == 1
        assert space.parameters[0].parameter_type == ParameterType.FLOAT

    def test_build_with_bool(self):
        builder = ParameterSpaceBuilder()
        builder.add_bool("enabled", default=True)
        space = builder.build()
        assert space.size == 1
        assert space.parameters[0].parameter_type == ParameterType.BOOL

    def test_build_with_categorical(self):
        builder = ParameterSpaceBuilder()
        builder.add_categorical("method", values=("sma", "ema"), default="sma")
        space = builder.build()
        assert space.size == 1
        assert space.parameters[0].parameter_type == ParameterType.CATEGORICAL

    def test_build_with_enum(self):
        builder = ParameterSpaceBuilder()
        builder.add_enum("mode", values=("fast", "slow"), default="fast")
        space = builder.build()
        assert space.size == 1
        assert space.parameters[0].parameter_type == ParameterType.ENUM

    def test_build_with_decimal(self):
        builder = ParameterSpaceBuilder()
        builder.add_decimal("price", min_value="1.0", max_value="100.0", default="50.0")
        space = builder.build()
        assert space.size == 1
        assert space.parameters[0].parameter_type == ParameterType.DECIMAL

    def test_build_multiple(self):
        builder = ParameterSpaceBuilder()
        builder.add_int("p1", min_value=1, max_value=10)
        builder.add_float("p2", min_value=0.0, max_value=1.0)
        builder.add_bool("p3")
        space = builder.build()
        assert space.size == 3

    def test_duplicate_names_raises_error(self):
        builder = ParameterSpaceBuilder()
        builder.add_int("dup", min_value=1, max_value=10)
        builder.add_float("dup", min_value=0.0, max_value=1.0)
        with pytest.raises(ValueError, match="parameter names must be unique"):
            builder.build()

    def test_build_with_metadata(self):
        builder = ParameterSpaceBuilder()
        builder.add_int("p1", min_value=1, max_value=10, metadata={"unit": "days"})
        space = builder.build()
        assert space.parameters[0].metadata == {"unit": "days"}

    def test_build_with_different_range_types(self):
        builder = ParameterSpaceBuilder()
        builder.add_int("p1", min_value=1, max_value=100)
        builder.add_float("p2", min_value=0.0, max_value=1.0)
        builder.add_decimal("p3")
        space = builder.build()
        assert space.size == 3

    def test_add_int_with_values(self):
        builder = ParameterSpaceBuilder()
        builder.add_int("p1", values=(5, 10, 15), default=10)
        space = builder.build()
        assert space.parameters[0].constraint.values == (5, 10, 15)

    def test_add_float_with_step(self):
        builder = ParameterSpaceBuilder()
        builder.add_float("p1", min_value=0.0, max_value=1.0, step=0.5)
        space = builder.build()
        assert space.parameters[0].constraint.step == 0.5

    # ── Validation tests (coverage boost) ──────────────────────────────

    def test_validate_bool_with_non_bool_values_raises_error(self):
        builder = ParameterSpaceBuilder()
        # Trigger _validate_definition for bool with non-boolean values
        from libraries.domain.ai_research.models import ParameterConstraint

        definition = ParameterDefinition(
            name="flag",
            parameter_type=ParameterType.BOOL,
            constraint=ParameterConstraint(values=(1, 2)),  # non-boolean values
        )
        with pytest.raises(ParameterSpaceError, match="'bool' parameter.*values must be booleans"):
            builder._validate_definition(definition)

    def test_validate_categorical_missing_values_raises_error(self):
        builder = ParameterSpaceBuilder()
        definition = ParameterDefinition(
            name="method",
            parameter_type=ParameterType.CATEGORICAL,
            constraint=ParameterConstraint(values=()),
        )
        with pytest.raises(
            ParameterSpaceError, match="'categorical' parameter.*must have at least one value"
        ):
            builder._validate_definition(definition)

    def test_validate_enum_missing_values_raises_error(self):
        builder = ParameterSpaceBuilder()
        definition = ParameterDefinition(
            name="mode",
            parameter_type=ParameterType.ENUM,
            constraint=ParameterConstraint(values=()),
        )
        with pytest.raises(
            ParameterSpaceError, match="'enum' parameter.*must have at least one value"
        ):
            builder._validate_definition(definition)

    def test_validate_step_on_non_numeric_raises_error(self):
        builder = ParameterSpaceBuilder()
        definition = ParameterDefinition(
            name="method",
            parameter_type=ParameterType.CATEGORICAL,
            constraint=ParameterConstraint(values=("a", "b"), step=1),
        )
        with pytest.raises(ParameterSpaceError, match="step is not supported"):
            builder._validate_definition(definition)

    def test_validate_int_with_non_integer_float_raises_error(self):
        builder = ParameterSpaceBuilder()
        definition = ParameterDefinition(
            name="lookback",
            parameter_type=ParameterType.INT,
            constraint=ParameterConstraint(min_value=1.5, max_value=10.5),
        )
        with pytest.raises(ParameterSpaceError, match="must be an integer value"):
            builder._validate_definition(definition)

    def test_validate_int_with_invalid_values_type_raises_error(self):
        builder = ParameterSpaceBuilder()
        # Use valid min/max for constraint comparison, but non-int in values
        definition = ParameterDefinition(
            name="lookback",
            parameter_type=ParameterType.INT,
            constraint=ParameterConstraint(min_value=1, max_value=10, values=("not-an-int",)),
        )
        with pytest.raises(ParameterSpaceError, match="must be numeric"):
            builder._validate_definition(definition)

    def test_validate_float_with_invalid_values_type_raises_error(self):
        builder = ParameterSpaceBuilder()
        definition = ParameterDefinition(
            name="threshold",
            parameter_type=ParameterType.FLOAT,
            constraint=ParameterConstraint(min_value=0.0, max_value=1.0, values=(None,)),
        )
        with pytest.raises(ParameterSpaceError, match="must be numeric"):
            builder._validate_definition(definition)

    def test_validate_decimal_with_invalid_values_type_raises_error(self):
        builder = ParameterSpaceBuilder()
        definition = ParameterDefinition(
            name="price",
            parameter_type=ParameterType.DECIMAL,
            constraint=ParameterConstraint(
                min_value=Decimal("0"), max_value=Decimal("10"), values=(None,)
            ),
        )
        with pytest.raises(ParameterSpaceError, match="must be numeric"):
            builder._validate_definition(definition)

    # ── Expand tests ───────────────────────────────────────────────────

    def test_expand_empty_space(self):
        builder = ParameterSpaceBuilder()
        space = ParameterSpace(parameters=())
        combos = builder.expand(space)
        assert combos == [{}]

    def test_expand_single_int(self):
        builder = ParameterSpaceBuilder()
        builder.add_int("x", min_value=1, max_value=3)
        space = builder.build()
        combos = builder.expand(space)
        assert len(combos) == 3
        assert combos[0] == {"x": 1}
        assert combos[1] == {"x": 2}
        assert combos[2] == {"x": 3}

    def test_expand_single_bool(self):
        builder = ParameterSpaceBuilder()
        builder.add_bool("flag")
        space = builder.build()
        combos = builder.expand(space)
        assert len(combos) == 2
        assert combos[0] == {"flag": True}
        assert combos[1] == {"flag": False}

    def test_expand_single_categorical(self):
        builder = ParameterSpaceBuilder()
        builder.add_categorical("method", values=("a", "b", "c"))
        space = builder.build()
        combos = builder.expand(space)
        assert len(combos) == 3
        assert combos[0] == {"method": "a"}
        assert combos[2] == {"method": "c"}

    def test_expand_single_decimal(self):
        builder = ParameterSpaceBuilder()
        builder.add_decimal("price", min_value="1.0", max_value="3.0", step="1.0")
        space = builder.build()
        combos = builder.expand(space)
        assert len(combos) == 3
        assert combos[0] == {"price": Decimal("1.0")}
        assert combos[2] == {"price": Decimal("3.0")}

    def test_expand_mixed_types(self):
        builder = ParameterSpaceBuilder()
        builder.add_int("x", min_value=1, max_value=2)
        builder.add_bool("y")
        space = builder.build()
        combos = builder.expand(space)
        assert len(combos) == 4
        assert {"x": 1, "y": True} in combos
        assert {"x": 2, "y": False} in combos

    # ── Int range tests ────────────────────────────────────────────────

    def test_int_range_no_min_max(self):
        builder = ParameterSpaceBuilder()
        definition = ParameterDefinition(
            name="x",
            parameter_type=ParameterType.INT,
            constraint=ParameterConstraint(),
        )
        values = builder._values_for_param(definition)
        assert len(values) == 11  # 0..10 default range

    def test_int_range_step_larger_than_range(self):
        builder = ParameterSpaceBuilder()
        definition = ParameterDefinition(
            name="x",
            parameter_type=ParameterType.INT,
            constraint=ParameterConstraint(min_value=1, max_value=5, step=10),
        )
        values = builder._values_for_param(definition)
        assert len(values) == 1
        assert values[0] == 1

    def test_float_range_precision(self):
        builder = ParameterSpaceBuilder()
        definition = ParameterDefinition(
            name="x",
            parameter_type=ParameterType.FLOAT,
            constraint=ParameterConstraint(min_value=0.0, max_value=1.0, step=0.3),
        )
        values = builder._values_for_param(definition)
        assert len(values) == 4
        assert values[0] == 0.0
        assert values[1] == 0.3
        assert values[2] == 0.6
        assert values[3] == 0.9

    def test_int_constraint_with_values(self):
        builder = ParameterSpaceBuilder()
        definition = ParameterDefinition(
            name="x",
            parameter_type=ParameterType.INT,
            constraint=ParameterConstraint(values=(10, 20, 30)),
        )
        values = builder._values_for_param(definition)
        assert values == [10, 20, 30]

    # ── Enum parameter alias ───────────────────────────────────────────

    def test_enum_parameter_alias(self):
        """ParameterSpaceEngine should be an alias for ParameterSpaceBuilder."""
        from libraries.domain.ai_research.parameter_space import ParameterSpaceEngine

        engine = ParameterSpaceEngine()
        engine.add_enum("mode", values=("fast", "slow"))
        space = engine.build()
        assert space.size == 1
        assert space.parameters[0].parameter_type == ParameterType.ENUM
