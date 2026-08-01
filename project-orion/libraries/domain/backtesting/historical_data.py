"""Historical data providers for backtesting.

Provides data access abstractions for loading historical market data
from various sources including CSV, Parquet, Databases, Compressed files,
and streaming replay. All providers follow the same interface.
"""

from __future__ import annotations

import abc
import csv
from datetime import date, datetime
from decimal import Decimal
from typing import Any, AsyncIterator

from libraries.domain.backtesting.exceptions import (
    DataFormatError,
    DataNotFoundError,
)
from libraries.domain.backtesting.models import Timeframe


class HistoricalDataProvider(abc.ABC):
    """Abstract base for historical data providers."""

    @abc.abstractmethod
    async def load_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Load OHLC candle data.

        Args:
            symbol: Trading symbol.
            timeframe: Candle timeframe.
            start_date: Start date.
            end_date: End date.

        Returns:
            List of candle dicts with keys: timestamp, open, high, low, close, volume.
        """
        ...

    @abc.abstractmethod
    async def load_ticks(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Load tick data.

        Args:
            symbol: Trading symbol.
            start_date: Start date.
            end_date: End date.

        Returns:
            List of tick dicts with keys: timestamp, bid, ask, volume.
        """
        ...

    @abc.abstractmethod
    async def get_available_symbols(self) -> list[str]:
        """Get list of available symbols.

        Returns:
            List of available trading symbols.
        """
        ...

    @abc.abstractmethod
    async def validate_data_available(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> bool:
        """Check if data is available for the given range.

        Args:
            symbol: Trading symbol.
            start_date: Start date.
            end_date: End date.

        Returns:
            True if data is available.
        """
        ...


class ChunkedIterator:
    """Iterator that yields data in chunks for streaming replay."""

    def __init__(
        self,
        data: list[dict[str, Any]],
        chunk_size: int = 1000,
    ) -> None:
        """Initialize chunked iterator.

        Args:
            data: Full data list.
            chunk_size: Number of items per chunk.
        """
        self._data = data
        self._chunk_size = chunk_size
        self._index = 0

    def __aiter__(self) -> ChunkedIterator:
        return self

    async def __anext__(self) -> list[dict[str, Any]]:
        if self._index >= len(self._data):
            raise StopAsyncIteration
        chunk = self._data[self._index : self._index + self._chunk_size]
        self._index += self._chunk_size
        return chunk

    @property
    def total_items(self) -> int:
        return len(self._data)

    @property
    def items_remaining(self) -> int:
        return len(self._data) - self._index


class CsvProvider(HistoricalDataProvider):
    """Historical data provider for CSV files."""

    def __init__(self, file_path: str) -> None:
        """Initialize CSV provider.

        Args:
            file_path: Path to CSV file.
        """
        self._file_path = file_path
        self._data: dict[str, list[dict[str, Any]]] = {}

    async def load_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        try:
            with open(self._file_path, "r") as f:
                reader = csv.DictReader(f)
                candles = []
                for row in reader:
                    ts = datetime.fromisoformat(row["timestamp"])
                    if ts.date() < start_date or ts.date() > end_date:
                        continue
                    if row.get("symbol", symbol) != symbol:
                        continue
                    candles.append(
                        {
                            "timestamp": ts,
                            "open": Decimal(row["open"]),
                            "high": Decimal(row["high"]),
                            "low": Decimal(row["low"]),
                            "close": Decimal(row["close"]),
                            "volume": Decimal(row.get("volume", "0")),
                        }
                    )
                return candles
        except FileNotFoundError:
            raise DataNotFoundError(f"CSV file not found: {self._file_path}")
        except Exception as e:
            raise DataFormatError(f"Failed to parse CSV: {e}")

    async def load_ticks(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        raise DataFormatError("Tick data not supported in CSV provider")

    async def get_available_symbols(self) -> list[str]:
        return ["UNKNOWN"]

    async def validate_data_available(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> bool:
        import os as os_module

        return os_module.path.exists(self._file_path)


class ParquetProvider(HistoricalDataProvider):
    """Historical data provider for Parquet files."""

    def __init__(self, file_path: str) -> None:
        self._file_path = file_path

    async def load_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError("Parquet support requires pyarrow")

    async def load_ticks(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError("Parquet support requires pyarrow")

    async def get_available_symbols(self) -> list[str]:
        return ["UNKNOWN"]

    async def validate_data_available(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> bool:
        import os as os_module

        return os_module.path.exists(self._file_path)


class DatabaseProvider(HistoricalDataProvider):
    """Historical data provider for SQL databases."""

    def __init__(self, connection_string: str) -> None:
        self._connection_string = connection_string

    async def load_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError("Database support requires async DB driver")

    async def load_ticks(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError("Database support requires async DB driver")

    async def get_available_symbols(self) -> list[str]:
        return []

    async def validate_data_available(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> bool:
        return False


class DuckDbProvider(HistoricalDataProvider):
    """Historical data provider using DuckDB for fast local analytics."""

    def __init__(self, database_path: str) -> None:
        self._database_path = database_path

    async def load_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError("DuckDB support requires duckdb package")

    async def load_ticks(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError("DuckDB support requires duckdb package")

    async def get_available_symbols(self) -> list[str]:
        return []

    async def validate_data_available(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> bool:
        return False


class CompressedFileProvider(HistoricalDataProvider):
    """Historical data provider for compressed files (zip, gz, bz2)."""

    def __init__(self, file_path: str, inner_provider: HistoricalDataProvider) -> None:
        self._file_path = file_path
        self._inner = inner_provider

    async def load_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        return await self._inner.load_candles(symbol, timeframe, start_date, end_date)

    async def load_ticks(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        return await self._inner.load_ticks(symbol, start_date, end_date)

    async def get_available_symbols(self) -> list[str]:
        return await self._inner.get_available_symbols()

    async def validate_data_available(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> bool:
        import os as os_module

        return os_module.path.exists(self._file_path)


class StreamingReplayProvider(HistoricalDataProvider):
    """Provider that streams data for real-time replay simulation."""

    def __init__(self, data_stream: AsyncIterator[list[dict[str, Any]]]) -> None:
        self._stream = data_stream

    async def load_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        raise DataFormatError("Streaming provider does not support bulk candle loading")

    async def load_ticks(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        raise DataFormatError("Streaming provider does not support bulk tick loading")

    async def get_available_symbols(self) -> list[str]:
        return ["STREAM"]

    async def validate_data_available(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> bool:
        return True
