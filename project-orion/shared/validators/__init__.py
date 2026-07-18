"""
Project ORION - Validators

Validation functions and classes for common domain validation patterns.
All validators return Result monad for composable error handling.

Provides:
- Primitive validators (strings, numbers, dates)
- Domain validators (symbols, prices, volumes)
- Composite validators (combine multiple validations)
- Validation chains
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Optional

from shared.common.result import Failure, Result, Success, failure, success

# ─── Primitive Validators ─────────────────────────────────────


def validate_required(value: Any, field_name: str = "value") -> Result[Any, Exception]:
    """Validate that a value is not None or empty."""
    if value is None:
        return failure(ValueError(f"{field_name} is required"))
    if isinstance(value, str) and not value.strip():
        return failure(ValueError(f"{field_name} cannot be empty"))
    if isinstance(value, (list, dict, set, tuple)) and len(value) == 0:
        return failure(ValueError(f"{field_name} cannot be empty"))
    return success(value)


def validate_string(
    value: str,
    min_length: int = 0,
    max_length: Optional[int] = None,
    pattern: Optional[str] = None,
    field_name: str = "string",
) -> Result[Any, Exception]:
    """Validate a string value."""
    result = validate_required(value, field_name)
    if isinstance(result, Failure):
        return result

    if len(value) < min_length:
        return failure(
            ValueError(
                f"{field_name} must be at least {min_length} characters, " f"got {len(value)}"
            )
        )

    if max_length is not None and len(value) > max_length:
        return failure(
            ValueError(
                f"{field_name} must not exceed {max_length} characters, " f"got {len(value)}"
            )
        )

    if pattern is not None and not re.match(pattern, value):
        return failure(ValueError(f"{field_name} does not match required pattern: {pattern}"))

    return success(value)


def validate_number(
    value: float | Decimal | int,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    field_name: str = "number",
) -> Result[Any, Exception]:
    """Validate a numeric value."""
    result = validate_required(value, field_name)
    if isinstance(result, Failure):
        return result

    num = float(value)

    if min_value is not None and num < min_value:
        return failure(ValueError(f"{field_name} must be >= {min_value}, got {num}"))

    if max_value is not None and num > max_value:
        return failure(ValueError(f"{field_name} must be <= {max_value}, got {num}"))

    return success(num)


def validate_positive(
    value: float | Decimal | int,
    field_name: str = "value",
) -> Result[Any, Exception]:
    """Validate that a numeric value is positive."""
    result = validate_number(value, min_value=0, field_name=field_name)
    return result


def validate_in_range(
    value: float | Decimal | int,
    min_value: float,
    max_value: float,
    field_name: str = "value",
) -> Result[Any, Exception]:
    """Validate that a numeric value is within a range."""
    return validate_number(
        value,
        min_value=min_value,
        max_value=max_value,
        field_name=field_name,
    )


def validate_in_enum(
    value: str,
    enum_values: list[str],
    field_name: str = "value",
) -> Result[Any, Exception]:
    """Validate that a string value is one of a set of allowed values."""
    result = validate_required(value, field_name)
    if isinstance(result, Failure):
        return result

    if value not in enum_values:
        return failure(ValueError(f"{field_name} must be one of {enum_values}, got '{value}'"))

    return success(value)


# ─── Domain-Specific Validators ───────────────────────────────


def validate_symbol(symbol: str) -> Result[Any, Exception]:
    """Validate a trading symbol (e.g., 'EUR/USD')."""
    result = validate_string(
        symbol,
        min_length=5,
        max_length=10,
        pattern=r"^[A-Z]{3}/[A-Z]{3}$",
        field_name="symbol",
    )
    return result


def validate_price(
    price: Decimal | float | str,
    field_name: str = "price",
) -> Result[Any, Exception]:
    """Validate a price value (must be positive)."""
    try:
        dec_price = Decimal(str(price))
    except Exception as exc:
        return failure(ValueError(f"Invalid price format: {exc}"))

    if dec_price <= Decimal("0"):
        return failure(ValueError(f"{field_name} must be positive, got {dec_price}"))

    return success(dec_price)


def validate_volume(
    volume: Decimal | float | int,
    field_name: str = "volume",
) -> Result[Any, Exception]:
    """Validate a volume/quantity value (must be non-negative)."""
    try:
        dec_volume = Decimal(str(volume))
    except Exception as exc:
        return failure(ValueError(f"Invalid volume format: {exc}"))

    if dec_volume < Decimal("0"):
        return failure(ValueError(f"{field_name} cannot be negative, got {dec_volume}"))

    return success(dec_volume)


def validate_percentage(
    percentage: float,
    field_name: str = "percentage",
    allow_negative: bool = False,
) -> Result[Any, Exception]:
    """Validate a percentage value."""
    result = validate_required(percentage, field_name)
    if isinstance(result, Failure):
        return result

    if not allow_negative and percentage < 0:
        return failure(ValueError(f"{field_name} must be non-negative, got {percentage}"))

    if percentage > 1.0:
        return failure(ValueError(f"{field_name} must be <= 1.0 (100%), got {percentage}"))

    return success(percentage)


def validate_email(email: str) -> Result[Any, Exception]:
    """Validate an email address format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return validate_string(
        email,
        min_length=5,
        max_length=254,
        pattern=pattern,
        field_name="email",
    )


def validate_uuid(uuid_str: str) -> Result[Any, Exception]:
    """Validate a UUID string."""
    pattern = r"^[0-9a-f]{32}$|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    return validate_string(
        uuid_str,
        min_length=32,
        max_length=36,
        pattern=pattern,
        field_name="UUID",
    )


def validate_datetime(
    dt_value: datetime | str,
    field_name: str = "datetime",
) -> Result[Any, Exception]:
    """Validate a datetime value."""
    if isinstance(dt_value, datetime):
        return success(dt_value)

    if isinstance(dt_value, str):
        try:
            return success(datetime.fromisoformat(dt_value))
        except ValueError as exc:
            return failure(ValueError(f"Invalid {field_name} format: {exc}"))

    return failure(
        ValueError(f"{field_name} must be a datetime or ISO string, " f"got {type(dt_value)}")
    )


# ─── Composite Validator ─────────────────────────────────────


class Validator:
    """
    Composite validator chain for building complex validation rules.

    Usage:
        result = (
            Validator()
            .add(lambda x: validate_required(x, "order"))
            .add(lambda x: validate_string(x, max_length=100))
            .validate("test_value")
        )
    """

    def __init__(self) -> None:
        self._validators: list[Callable[[Any], Result[Any, Exception]]] = []

    def add(
        self,
        validator_fn: Callable[[Any], Result[Any, Exception]],
    ) -> Validator:
        """Add a validation function to the chain."""
        self._validators.append(validator_fn)
        return self

    def validate(self, value: Any) -> Result[Any, Exception]:
        """Run all validators in sequence."""
        current: Any = value
        for validator_fn in self._validators:
            result = validator_fn(current)
            match result:
                case Success(data):
                    current = data
                case Failure():
                    return result
        return success(current)


# ─── Validation Helpers ──────────────────────────────────────


def validate_dict(
    data: dict[str, Any],
    schema: dict[str, Callable[[Any], Result[Any, Exception]]],
) -> Result[dict[str, Any], Exception]:
    """
    Validate a dictionary against a schema of field validators.

    Args:
        data: The dictionary to validate.
        schema: Mapping of field names to validator functions.

    Returns:
        Result with validated data or first validation error.
    """
    validated: dict[str, Any] = {}
    for field_name, validator_fn in schema.items():
        if field_name not in data:
            return failure(ValueError(f"Missing required field: {field_name}"))
        result = validator_fn(data[field_name])
        match result:
            case Success(value):
                validated[field_name] = value
            case Failure():
                return failure(
                    ValueError(f"Validation failed for '{field_name}': {result.message}")
                )
    return success(validated)
