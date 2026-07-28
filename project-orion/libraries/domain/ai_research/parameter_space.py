"""Strongly typed, validated parameter space definitions for search and optimization."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Any, Mapping

from libraries.domain.ai_research.exceptions import ParameterSpaceError
from libraries.domain.ai_research.models import (
    ParameterConstraint,
    ParameterDefinition,
    ParameterSpace,
    ParameterType,
)


class ParameterSpaceBuilder:
    """Builder for constructing validated parameter spaces."""

    def __init__(self) -> None:
        self._definitions: list[ParameterDefinition] = []

    def build(self) -> ParameterSpace:
        """Build a parameter space from added definitions.

        Returns:
            Validated parameter space.

        Raises:
            ParameterSpaceError: If definitions are invalid.
        """
        if not self._definitions:
            return ParameterSpace(parameters=())
        for definition in self._definitions:
            self._validate_definition(definition)
        names = [d.name for d in self._definitions]
        if len(names) != len(set(names)):
            raise ValueError("parameter names must be unique")
        return ParameterSpace(parameters=tuple(self._definitions))

    def _add(
        self,
        name: str,
        param_type: ParameterType,
        default: Any = None,
        constraint: ParameterConstraint | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        self._definitions.append(
            ParameterDefinition(
                name=name,
                parameter_type=param_type,
                default=default,
                constraint=constraint or ParameterConstraint(),
                metadata=metadata or {},
            )
        )

    def add_int(
        self,
        name: str,
        min_value: int | None = None,
        max_value: int | None = None,
        step: int | None = None,
        values: tuple[int, ...] | None = None,
        default: int | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        constraint = ParameterConstraint(
            min_value=min_value, max_value=max_value, step=step, values=values or ()
        )
        self._add(
            name, ParameterType.INT, default=default, constraint=constraint, metadata=metadata
        )

    def add_float(
        self,
        name: str,
        min_value: float | None = None,
        max_value: float | None = None,
        step: float | None = None,
        values: tuple[float, ...] | None = None,
        default: float | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        constraint = ParameterConstraint(
            min_value=min_value, max_value=max_value, step=step, values=values or ()
        )
        self._add(
            name, ParameterType.FLOAT, default=default, constraint=constraint, metadata=metadata
        )

    def add_bool(
        self, name: str, default: bool | None = None, metadata: Mapping[str, Any] | None = None
    ) -> None:
        self._add(name, ParameterType.BOOL, default=default, metadata=metadata)

    def add_categorical(
        self,
        name: str,
        values: tuple[str, ...],
        default: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        constraint = ParameterConstraint(values=values)
        self._add(
            name,
            ParameterType.CATEGORICAL,
            default=default,
            constraint=constraint,
            metadata=metadata,
        )

    def add_enum(
        self,
        name: str,
        values: tuple[str, ...],
        default: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        constraint = ParameterConstraint(values=values)
        self._add(
            name, ParameterType.ENUM, default=default, constraint=constraint, metadata=metadata
        )

    def add_decimal(
        self,
        name: str,
        min_value: str | None = None,
        max_value: str | None = None,
        step: str | None = None,
        default: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        constraint = ParameterConstraint(
            min_value=Decimal(str(min_value)) if min_value is not None else None,
            max_value=Decimal(str(max_value)) if max_value is not None else None,
            step=Decimal(str(step)) if step is not None else None,
        )
        self._add(
            name, ParameterType.DECIMAL, default=default, constraint=constraint, metadata=metadata
        )

    def _validate_definition(self, definition: ParameterDefinition) -> None:
        """Validate a single parameter definition."""
        constraint = definition.constraint
        param_type = definition.parameter_type

        if param_type == ParameterType.INT:
            if constraint.min_value is not None:
                self._assert_is_int(constraint.min_value, "min_value")
            if constraint.max_value is not None:
                self._assert_is_int(constraint.max_value, "max_value")
            if constraint.step is not None:
                self._assert_is_int(constraint.step, "step")
            if constraint.values:
                for v in constraint.values:
                    self._assert_is_int(v, "values")

        elif param_type == ParameterType.FLOAT:
            if constraint.min_value is not None:
                self._assert_is_float(constraint.min_value, "min_value")
            if constraint.max_value is not None:
                self._assert_is_float(constraint.max_value, "max_value")
            if constraint.step is not None:
                self._assert_is_float(constraint.step, "step")
            if constraint.values:
                for v in constraint.values:
                    self._assert_is_float(v, "values")

        elif param_type == ParameterType.DECIMAL:
            if constraint.min_value is not None:
                self._assert_is_decimal(constraint.min_value, "min_value")
            if constraint.max_value is not None:
                self._assert_is_decimal(constraint.max_value, "max_value")
            if constraint.step is not None:
                self._assert_is_decimal(constraint.step, "step")
            if constraint.values:
                for v in constraint.values:
                    self._assert_is_decimal(v, "values")

        elif param_type == ParameterType.BOOL:
            if constraint.values:
                for v in constraint.values:
                    if not isinstance(v, bool):
                        raise ParameterSpaceError(
                            f"'bool' parameter '{definition.name}' values must be booleans"
                        )

        elif param_type == ParameterType.CATEGORICAL:
            if not constraint.values:
                raise ParameterSpaceError(
                    f"'categorical' parameter '{definition.name}' must have at least one value"
                )

        elif param_type == ParameterType.ENUM:
            if not constraint.values:
                raise ParameterSpaceError(
                    f"'enum' parameter '{definition.name}' must have at least one value"
                )

        if constraint.step is not None and param_type not in (
            ParameterType.INT,
            ParameterType.FLOAT,
            ParameterType.DECIMAL,
        ):
            raise ParameterSpaceError(
                f"step is not supported for '{param_type.value}' parameter '{definition.name}'"
            )

    def expand(self, space: ParameterSpace) -> list[dict[str, Any]]:
        """Expand a parameter space into concrete combinations.

        Args:
            space: Parameter space to expand.

        Returns:
            List of parameter combinations.
        """
        if not space.parameters:
            return [{}]

        combinations: list[dict[str, Any]] = [{}]
        for param in space.parameters:
            values = self._values_for_param(param)
            new_combinations = []
            for base in combinations:
                for value in values:
                    new_combo = dict(base)
                    new_combo[param.name] = value
                    new_combinations.append(new_combo)
            combinations = new_combinations
        return combinations

    def _values_for_param(self, definition: ParameterDefinition) -> list[Any]:
        """Compute all possible values for a parameter."""
        constraint = definition.constraint
        param_type = definition.parameter_type

        if constraint.values:
            return list(constraint.values)

        if param_type == ParameterType.INT:
            return self._int_range(constraint)
        if param_type == ParameterType.FLOAT:
            return self._float_range(constraint)
        if param_type == ParameterType.DECIMAL:
            return self._decimal_range(constraint)
        if param_type == ParameterType.BOOL:
            return [True, False]

        return []

    @staticmethod
    def _int_range(constraint: ParameterConstraint) -> list[int]:
        lo = int(constraint.min_value) if constraint.min_value is not None else 0
        hi = int(constraint.max_value) if constraint.max_value is not None else lo + 10
        step = int(constraint.step) if constraint.step is not None else 1
        return list(range(lo, hi + 1, step))

    @staticmethod
    def _float_range(constraint: ParameterConstraint) -> list[float]:
        lo = float(constraint.min_value) if constraint.min_value is not None else 0.0
        hi = float(constraint.max_value) if constraint.max_value is not None else lo + 10.0
        step = float(constraint.step) if constraint.step is not None else 1.0
        result: list[float] = []
        current = lo
        while current <= hi:
            result.append(round(current, 10))
            current += step
        return result

    @staticmethod
    def _decimal_range(constraint: ParameterConstraint) -> list[Decimal]:
        lo = (
            Decimal(str(constraint.min_value)) if constraint.min_value is not None else Decimal("0")
        )
        hi = (
            Decimal(str(constraint.max_value))
            if constraint.max_value is not None
            else lo + Decimal("10")
        )
        step = Decimal(str(constraint.step)) if constraint.step is not None else Decimal("1")
        result: list[Decimal] = []
        current = lo
        while current <= hi:
            result.append(current)
            current += step
        return result

    @staticmethod
    def _assert_is_int(value: Any, name: str) -> None:
        if not isinstance(value, (int, float, Decimal)):
            raise ParameterSpaceError(f"{name} must be numeric for integer parameter")
        if isinstance(value, float) and not value.is_integer():
            raise ParameterSpaceError(f"{name} must be an integer value")

    @staticmethod
    def _assert_is_float(value: Any, name: str) -> None:
        if not isinstance(value, (int, float)):
            raise ParameterSpaceError(f"{name} must be numeric for float parameter")

    @staticmethod
    def _assert_is_decimal(value: Any, name: str) -> None:
        if not isinstance(value, (int, float, Decimal, str)):
            raise ParameterSpaceError(f"{name} must be numeric for decimal parameter")


# Default builder instance
ParameterSpaceEngine = ParameterSpaceBuilder
