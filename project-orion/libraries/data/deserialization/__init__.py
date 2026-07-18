"""
Data Deserialization Module

Module Description:
This module provides deserialization functionality for data platform objects.
It handles type conversion, schema validation during deserialization, and error handling.

Implementation Checklist:
- [ ] JSON deserializer with type conversion
- [ ] MessagePack deserializer with type conversion
- [ ] Schema-aware deserialization
- [ ] Error handling for invalid data
- [ ] Partial deserialization support

Dependency Notes:
- Depends on: shared/ (errors), libraries/data/schemas/, libraries/data/validators/
- Used by: storage/, datasets/, pipelines/
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Type, TypeVar

from libraries.data.schemas import OHLC, SymbolMetadata, Tick
from libraries.data.validators import OHLCValidator, TickValidator
from shared.errors import OrionError


class DeserializationError(OrionError):
    """Deserialization error."""

    pass


T = TypeVar("T")


class Deserializer(ABC):
    """Abstract deserializer interface."""

    @abstractmethod
    def deserialize(self, data: bytes) -> Dict[str, Any]:
        """Deserialize bytes to dictionary."""
        pass

    @abstractmethod
    def deserialize_to_type(self, data: bytes, target_type: Type[T]) -> T:
        """Deserialize bytes to specific type."""
        pass

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Get format name."""
        pass


class TypeConverter:
    """Type converter for deserialization."""

    @staticmethod
    def to_decimal(value: Any) -> Decimal:
        """Convert value to Decimal."""
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float, str)):
            return Decimal(str(value))
        raise DeserializationError(f"Cannot convert {type(value)} to Decimal")

    @staticmethod
    def to_datetime(value: Any) -> datetime:
        """Convert value to datetime."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                raise DeserializationError(f"Invalid datetime format: {value}")
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value)
        raise DeserializationError(f"Cannot convert {type(value)} to datetime")

    @staticmethod
    def to_bool(value: Any) -> bool:
        """Convert value to bool."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        if isinstance(value, (int, float)):
            return bool(value)
        raise DeserializationError(f"Cannot convert {type(value)} to bool")


class JSONDeserializer(Deserializer):
    """JSON deserializer with type conversion."""

    def __init__(self) -> None:
        """Initialize deserializer."""
        self.converter = TypeConverter()

    def deserialize(self, data: bytes) -> Dict[str, Any]:
        """Deserialize JSON bytes to dictionary."""
        try:
            result = json.loads(data.decode("utf-8"))
            if not isinstance(result, dict) or not all(
                isinstance(key, str) for key in result
            ):
                raise DeserializationError(
                    "JSON payload must be an object with string keys"
                )
            return {key: value for key, value in result.items()}
        except Exception as e:
            raise DeserializationError(f"JSON deserialization failed: {str(e)}")

    def deserialize_to_type(self, data: bytes, target_type: Type[T]) -> T:
        """Deserialize JSON bytes to specific type."""
        try:
            dict_data = self.deserialize(data)
            return self._convert_dict_to_type(dict_data, target_type)
        except Exception as e:
            raise DeserializationError(f"Type deserialization failed: {str(e)}")

    def _convert_dict_to_type(self, data: Dict[str, Any], target_type: Type[T]) -> T:
        """Convert dictionary to target type."""
        # TODO: Implement type-specific conversion
        # For now, return the data as-is
        return data  # type: ignore

    @property
    def format_name(self) -> str:
        """Get format name."""
        return "json"


class SchemaAwareDeserializer:
    """Schema-aware deserializer with validation."""

    def __init__(self) -> None:
        """Initialize deserializer."""
        self.json_deserializer = JSONDeserializer()
        self.tick_validator = TickValidator()
        self.ohlc_validator = OHLCValidator()

    def deserialize_tick(self, data: bytes, validate: bool = True) -> Tick:
        """Deserialize and validate tick data."""
        dict_data = self.json_deserializer.deserialize(data)

        # Type conversion
        if "timestamp" in dict_data:
            dict_data["timestamp"] = TypeConverter.to_datetime(dict_data["timestamp"])
        if "bid_price" in dict_data:
            dict_data["bid_price"] = TypeConverter.to_decimal(dict_data["bid_price"])
        if "ask_price" in dict_data:
            dict_data["ask_price"] = TypeConverter.to_decimal(dict_data["ask_price"])
        if "bid_size" in dict_data and dict_data["bid_size"] is not None:
            dict_data["bid_size"] = TypeConverter.to_decimal(dict_data["bid_size"])
        if "ask_size" in dict_data and dict_data["ask_size"] is not None:
            dict_data["ask_size"] = TypeConverter.to_decimal(dict_data["ask_size"])

        tick = Tick(**dict_data)

        if validate:
            errors = self.tick_validator.validate_tick(tick)
            if errors:
                raise DeserializationError(f"Tick validation failed: {errors}")

        return tick

    def deserialize_ohlc(self, data: bytes, validate: bool = True) -> OHLC:
        """Deserialize and validate OHLC data."""
        dict_data = self.json_deserializer.deserialize(data)

        # Type conversion
        if "timestamp" in dict_data:
            dict_data["timestamp"] = TypeConverter.to_datetime(dict_data["timestamp"])
        if "open" in dict_data:
            dict_data["open"] = TypeConverter.to_decimal(dict_data["open"])
        if "high" in dict_data:
            dict_data["high"] = TypeConverter.to_decimal(dict_data["high"])
        if "low" in dict_data:
            dict_data["low"] = TypeConverter.to_decimal(dict_data["low"])
        if "close" in dict_data:
            dict_data["close"] = TypeConverter.to_decimal(dict_data["close"])
        if "volume" in dict_data:
            dict_data["volume"] = TypeConverter.to_decimal(dict_data["volume"])

        ohlc = OHLC(**dict_data)

        if validate:
            errors = self.ohlc_validator.validate_ohlc(ohlc)
            if errors:
                raise DeserializationError(f"OHLC validation failed: {errors}")

        return ohlc
