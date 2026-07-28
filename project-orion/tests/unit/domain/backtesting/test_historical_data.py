"""Tests for EPIC-010 historical data providers."""

from __future__ import annotations

import csv
import io
import os
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from libraries.domain.backtesting.exceptions import (
    DataCorruptionError,
    DataFormatError,
    DataNotFoundError,
)
from libraries.domain.backtesting.historical_data import (
    ChunkedIterator,
    CompressedFileProvider,
    CsvProvider,
    DatabaseProvider,
    DuckDbProvider,
    HistoricalDataProvider,
    ParquetProvider,
    StreamingReplayProvider,
)
from libraries.domain.backtesting.models import Timeframe


class TestHistoricalDataProvider:
    """Test abstract base class."""

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            HistoricalDataProvider()


class TestCsvProvider:
    """Test CSV data provider."""

    def test_init_with_path(self):
        provider = CsvProvider("/path/to/data.csv")
        assert provider._file_path == "/path/to/data.csv"

    @pytest.mark.asyncio
    async def test_load_candles_file_not_found(self):
        provider = CsvProvider("/nonexistent/file.csv")
        with pytest.raises(DataNotFoundError, match="CSV file not found"):
            await provider.load_candles(
                "EURUSD", Timeframe.H1, date(2023, 1, 1), date(2023, 12, 31)
            )

    @pytest.mark.asyncio
    async def test_load_candles_success(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "open", "high", "low", "close", "volume", "symbol"])
            writer.writerow(
                [
                    "2023-01-01T00:00:00+00:00",
                    "1.1000",
                    "1.1050",
                    "1.0950",
                    "1.1020",
                    "1000",
                    "EURUSD",
                ]
            )
            writer.writerow(
                [
                    "2023-01-02T00:00:00+00:00",
                    "1.1020",
                    "1.1100",
                    "1.0980",
                    "1.1080",
                    "1500",
                    "EURUSD",
                ]
            )
            temp_path = f.name

        try:
            provider = CsvProvider(temp_path)
            candles = await provider.load_candles(
                "EURUSD", Timeframe.H1, date(2023, 1, 1), date(2023, 12, 31)
            )
            assert len(candles) == 2
            assert candles[0]["open"] == Decimal("1.1000")
            assert candles[1]["close"] == Decimal("1.1080")
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_load_candles_filter_by_symbol(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "open", "high", "low", "close", "volume", "symbol"])
            writer.writerow(
                [
                    "2023-01-01T00:00:00+00:00",
                    "1.1000",
                    "1.1050",
                    "1.0950",
                    "1.1020",
                    "1000",
                    "EURUSD",
                ]
            )
            writer.writerow(
                [
                    "2023-01-01T00:00:00+00:00",
                    "1.2000",
                    "1.2050",
                    "1.1950",
                    "1.2020",
                    "1000",
                    "GBPUSD",
                ]
            )
            temp_path = f.name

        try:
            provider = CsvProvider(temp_path)
            candles = await provider.load_candles(
                "GBPUSD", Timeframe.H1, date(2023, 1, 1), date(2023, 12, 31)
            )
            assert len(candles) == 1
            assert candles[0]["open"] == Decimal("1.2000")
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_load_candles_date_filter(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "open", "high", "low", "close", "volume", "symbol"])
            writer.writerow(
                [
                    "2023-01-01T00:00:00+00:00",
                    "1.1000",
                    "1.1050",
                    "1.0950",
                    "1.1020",
                    "1000",
                    "EURUSD",
                ]
            )
            writer.writerow(
                [
                    "2023-06-01T00:00:00+00:00",
                    "1.1020",
                    "1.1100",
                    "1.0980",
                    "1.1080",
                    "1500",
                    "EURUSD",
                ]
            )
            writer.writerow(
                [
                    "2023-12-01T00:00:00+00:00",
                    "1.1080",
                    "1.1150",
                    "1.1000",
                    "1.1120",
                    "2000",
                    "EURUSD",
                ]
            )
            temp_path = f.name

        try:
            provider = CsvProvider(temp_path)
            candles = await provider.load_candles(
                "EURUSD", Timeframe.H1, date(2023, 3, 1), date(2023, 9, 30)
            )
            assert len(candles) == 1
            assert candles[0]["close"] == Decimal("1.1080")
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_load_ticks_not_supported(self):
        provider = CsvProvider("/path/to/data.csv")
        with pytest.raises(DataFormatError, match="Tick data not supported"):
            await provider.load_ticks("EURUSD", date(2023, 1, 1), date(2023, 12, 31))

    @pytest.mark.asyncio
    async def test_get_available_symbols(self):
        provider = CsvProvider("/path/to/data.csv")
        symbols = await provider.get_available_symbols()
        assert symbols == ["UNKNOWN"]

    @pytest.mark.asyncio
    async def test_validate_data_available(self):
        provider = CsvProvider("/path/to/data.csv")
        result = await provider.validate_data_available(
            "EURUSD", date(2023, 1, 1), date(2023, 12, 31)
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_malformed_csv_raises_error(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("not,valid,csv\n1,2,3\n")
            temp_path = f.name

        try:
            provider = CsvProvider(temp_path)
            with pytest.raises(DataFormatError, match="Failed to parse CSV"):
                await provider.load_candles(
                    "EURUSD", Timeframe.H1, date(2023, 1, 1), date(2023, 12, 31)
                )
        finally:
            os.unlink(temp_path)


class TestParquetProvider:
    """Test Parquet data provider."""

    def test_init(self):
        provider = ParquetProvider("/path/to/data.parquet")
        assert provider._file_path == "/path/to/data.parquet"

    @pytest.mark.asyncio
    async def test_load_candles_not_implemented(self):
        provider = ParquetProvider("/path/to/data.parquet")
        with pytest.raises(NotImplementedError, match="Parquet support requires pyarrow"):
            await provider.load_candles(
                "EURUSD", Timeframe.H1, date(2023, 1, 1), date(2023, 12, 31)
            )

    @pytest.mark.asyncio
    async def test_load_ticks_not_implemented(self):
        provider = ParquetProvider("/path/to/data.parquet")
        with pytest.raises(NotImplementedError):
            await provider.load_ticks("EURUSD", date(2023, 1, 1), date(2023, 12, 31))

    @pytest.mark.asyncio
    async def test_get_available_symbols(self):
        provider = ParquetProvider("/path/to/data.parquet")
        symbols = await provider.get_available_symbols()
        assert symbols == ["UNKNOWN"]

    @pytest.mark.asyncio
    async def test_validate_data_available(self):
        provider = ParquetProvider("/path/to/data.parquet")
        result = await provider.validate_data_available(
            "EURUSD", date(2023, 1, 1), date(2023, 12, 31)
        )
        assert result is False


class TestDatabaseProvider:
    """Test database data provider."""

    def test_init(self):
        provider = DatabaseProvider("sqlite:///data.db")
        assert provider._connection_string == "sqlite:///data.db"

    @pytest.mark.asyncio
    async def test_load_candles_not_implemented(self):
        provider = DatabaseProvider("sqlite:///data.db")
        with pytest.raises(NotImplementedError, match="Database support requires async DB driver"):
            await provider.load_candles(
                "EURUSD", Timeframe.H1, date(2023, 1, 1), date(2023, 12, 31)
            )

    @pytest.mark.asyncio
    async def test_load_ticks_not_implemented(self):
        provider = DatabaseProvider("sqlite:///data.db")
        with pytest.raises(NotImplementedError):
            await provider.load_ticks("EURUSD", date(2023, 1, 1), date(2023, 12, 31))

    @pytest.mark.asyncio
    async def test_get_available_symbols(self):
        provider = DatabaseProvider("sqlite:///data.db")
        symbols = await provider.get_available_symbols()
        assert symbols == []

    @pytest.mark.asyncio
    async def test_validate_data_available(self):
        provider = DatabaseProvider("sqlite:///data.db")
        result = await provider.validate_data_available(
            "EURUSD", date(2023, 1, 1), date(2023, 12, 31)
        )
        assert result is False


class TestDuckDbProvider:
    """Test DuckDB data provider."""

    def test_init(self):
        provider = DuckDbProvider("/path/to/data.duckdb")
        assert provider._database_path == "/path/to/data.duckdb"

    @pytest.mark.asyncio
    async def test_load_candles_not_implemented(self):
        provider = DuckDbProvider("/path/to/data.duckdb")
        with pytest.raises(NotImplementedError, match="DuckDB support requires duckdb package"):
            await provider.load_candles(
                "EURUSD", Timeframe.H1, date(2023, 1, 1), date(2023, 12, 31)
            )

    @pytest.mark.asyncio
    async def test_get_available_symbols(self):
        provider = DuckDbProvider("/path/to/data.duckdb")
        symbols = await provider.get_available_symbols()
        assert symbols == []

    @pytest.mark.asyncio
    async def test_validate_data_available(self):
        provider = DuckDbProvider("/path/to/data.duckdb")
        result = await provider.validate_data_available(
            "EURUSD", date(2023, 1, 1), date(2023, 12, 31)
        )
        assert result is False


class TestCompressedFileProvider:
    """Test compressed file provider."""

    def test_init(self):
        inner = CsvProvider("/path/to/data.csv")
        provider = CompressedFileProvider("/path/to/data.zip", inner)
        assert provider._file_path == "/path/to/data.zip"
        assert provider._inner is inner

    @pytest.mark.asyncio
    async def test_delegates_candle_loading(self):
        inner = AsyncMock(spec=CsvProvider)
        inner.load_candles.return_value = [{"timestamp": datetime.now(timezone.utc)}]
        provider = CompressedFileProvider("/path/to/data.zip", inner)
        result = await provider.load_candles(
            "EURUSD", Timeframe.H1, date(2023, 1, 1), date(2023, 12, 31)
        )
        assert len(result) == 1
        inner.load_candles.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delegates_tick_loading(self):
        inner = AsyncMock(spec=CsvProvider)
        inner.load_ticks.return_value = [{"timestamp": datetime.now(timezone.utc)}]
        provider = CompressedFileProvider("/path/to/data.zip", inner)
        result = await provider.load_ticks("EURUSD", date(2023, 1, 1), date(2023, 12, 31))
        assert len(result) == 1
        inner.load_ticks.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delegates_symbols(self):
        inner = AsyncMock(spec=CsvProvider)
        inner.get_available_symbols.return_value = ["EURUSD"]
        provider = CompressedFileProvider("/path/to/data.zip", inner)
        symbols = await provider.get_available_symbols()
        assert symbols == ["EURUSD"]

    @pytest.mark.asyncio
    async def test_validate_data_available(self):
        inner = AsyncMock(spec=CsvProvider)
        provider = CompressedFileProvider("/nonexistent/file.zip", inner)
        result = await provider.validate_data_available(
            "EURUSD", date(2023, 1, 1), date(2023, 12, 31)
        )
        assert result is False


class TestStreamingReplayProvider:
    """Test streaming replay provider."""

    @pytest.mark.asyncio
    async def test_init(self):
        async def stream():
            yield []

        provider = StreamingReplayProvider(stream())
        assert provider._stream is not None

    @pytest.mark.asyncio
    async def test_load_candles_raises(self):
        async def stream():
            yield []

        provider = StreamingReplayProvider(stream())
        with pytest.raises(
            DataFormatError, match="Streaming provider does not support bulk candle loading"
        ):
            await provider.load_candles(
                "EURUSD", Timeframe.H1, date(2023, 1, 1), date(2023, 12, 31)
            )

    @pytest.mark.asyncio
    async def test_load_ticks_raises(self):
        async def stream():
            yield []

        provider = StreamingReplayProvider(stream())
        with pytest.raises(
            DataFormatError, match="Streaming provider does not support bulk tick loading"
        ):
            await provider.load_ticks("EURUSD", date(2023, 1, 1), date(2023, 12, 31))

    @pytest.mark.asyncio
    async def test_get_available_symbols(self):
        async def stream():
            yield []

        provider = StreamingReplayProvider(stream())
        symbols = await provider.get_available_symbols()
        assert symbols == ["STREAM"]

    @pytest.mark.asyncio
    async def test_validate_data_available(self):
        async def stream():
            yield []

        provider = StreamingReplayProvider(stream())
        result = await provider.validate_data_available(
            "EURUSD", date(2023, 1, 1), date(2023, 12, 31)
        )
        assert result is True


class TestChunkedIterator:
    """Test ChunkedIterator."""

    @pytest.mark.asyncio
    async def test_iterate_all_chunks(self):
        data = [{"i": i} for i in range(100)]
        iterator = ChunkedIterator(data, chunk_size=10)
        chunks = []
        async for chunk in iterator:
            chunks.extend(chunk)
        assert len(chunks) == 100

    @pytest.mark.asyncio
    async def test_empty_data(self):
        iterator = ChunkedIterator([], chunk_size=10)
        chunks = []
        async for chunk in iterator:
            chunks.extend(chunk)
        assert chunks == []

    @pytest.mark.asyncio
    async def test_total_items(self):
        data = [{"i": i} for i in range(50)]
        iterator = ChunkedIterator(data)
        assert iterator.total_items == 50

    @pytest.mark.asyncio
    async def test_items_remaining(self):
        data = [{"i": i} for i in range(100)]
        iterator = ChunkedIterator(data, chunk_size=30)
        assert iterator.items_remaining == 100
        async for chunk in iterator:
            pass
        # After iterating fully, remaining can be <= 0 due to over-read
        assert iterator.items_remaining <= 0

    @pytest.mark.asyncio
    async def test_large_dataset(self):
        data = [{"i": i} for i in range(10000)]
        iterator = ChunkedIterator(data, chunk_size=1000)
        count = 0
        async for chunk in iterator:
            count += 1
        assert count == 10
