"""Historical data providers for backtesting.

Provides data access abstractions for loading historical market data
from various sources including CSV, Parquet, Databases, Compressed files,
and streaming replay. All providers follow the same interface.
"""

from __future__ import annotations

import abc
import calendar
import csv
import hashlib
import random
from collections.abc import AsyncIterator
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any, ClassVar

from libraries.domain.backtesting.exceptions import (
    DataFormatError,
    DataNotFoundError,
    HistoricalDataUnavailableError,
)
from libraries.domain.backtesting.models import Timeframe
from libraries.domain.research.models import DatasetProvenance, DataSourceMode

if TYPE_CHECKING:
    from libraries.domain.market_data.models import BarType


def _sanitize_error_message(msg: str) -> str:
    """Strip API keys, tokens, and credentials from error messages to maintain audit security."""
    import re

    return re.sub(
        r"(?i)(api[_-]?key|token|secret|password|bearer\s+|authorization)\s*[:=]\s*[^\s&,;\"']+",
        r"\1=[REDACTED]",
        msg,
    )



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
            with open(self._file_path, "r", encoding="utf-8") as f:  # noqa: ASYNC230 - local file CSV provider; aiofiles is not an installed dependency
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
        except (csv.Error, ValueError, KeyError, OSError) as e:
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


class MarketDataServiceHistoricalProvider(HistoricalDataProvider):
    """Bridges MarketDataService and canonical market data into BacktestEngine."""

    _BASE_PRICES: ClassVar[dict[str, Decimal]] = {
        "EUR/USD": Decimal("1.08500"),
        "GBP/USD": Decimal("1.26500"),
        "USD/JPY": Decimal("151.200"),
        "AUD/USD": Decimal("0.65500"),
        "USD/CHF": Decimal("0.88500"),
        "EUR/GBP": Decimal("0.85500"),
    }

    def __init__(
        self,
        market_data_service: Any | None = None,
        quality_engine: Any | None = None,
        source_mode: DataSourceMode | str | None = None,
    ) -> None:
        self._service = market_data_service
        self._quality = quality_engine
        if isinstance(source_mode, str):
            sm = source_mode.lower()
            if sm in ("real", "external"):
                self._source_mode: DataSourceMode | None = DataSourceMode.EXTERNAL
            elif sm in ("synthetic", "deterministic"):
                self._source_mode = DataSourceMode.SYNTHETIC
            elif sm == "auto":
                self._source_mode = DataSourceMode.AUTO
            else:
                self._source_mode = DataSourceMode(sm)
        else:
            self._source_mode = source_mode
        self._last_provenance: DatasetProvenance | None = None

    @property
    def last_provenance(self) -> DatasetProvenance | None:
        """Audit provenance of the most recently loaded dataset."""
        return self._last_provenance

    async def load_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_date: date,
        end_date: date,
        source_mode: DataSourceMode | str | None = None,
    ) -> list[dict[str, Any]]:
        from libraries.domain.market_data.normalization import (
            bar_type_to_timeframe,
            normalize_symbol,
        )

        canonical = normalize_symbol(symbol)
        tf_domain = bar_type_to_timeframe(timeframe)
        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)
        tf_str = tf_domain.value

        # Resolve effective source mode
        effective_mode = source_mode or self._source_mode
        if isinstance(effective_mode, str):
            em = effective_mode.lower()
            if em in ("real", "external"):
                effective_mode = DataSourceMode.EXTERNAL
            elif em in ("synthetic", "deterministic"):
                effective_mode = DataSourceMode.SYNTHETIC
            elif em == "auto":
                effective_mode = DataSourceMode.AUTO

        if effective_mode is None or effective_mode == DataSourceMode.AUTO:
            effective_mode = DataSourceMode.EXTERNAL if self._service is not None else DataSourceMode.SYNTHETIC

        # 1. External Real Market Data Path
        if effective_mode == DataSourceMode.EXTERNAL:
            if self._service is None or not hasattr(self._service, "get_candles"):
                raise HistoricalDataUnavailableError(
                    symbol=canonical,
                    timeframe=tf_str,
                    start=start_dt,
                    end=end_dt,
                    provider="external",
                    reason="External historical data requested but no MarketDataService is configured",
                )

            # Extract provider identity safely
            provider_name = "external"
            if hasattr(self._service, "provider") and hasattr(self._service.provider, "provider_name") and isinstance(self._service.provider.provider_name, str):
                provider_name = self._service.provider.provider_name
            elif hasattr(self._service, "provider_name") and isinstance(self._service.provider_name, str):
                provider_name = self._service.provider_name

            try:
                raw_candles = await self._service.get_candles(
                    symbol=canonical,
                    timeframe=tf_str,
                    start=start_dt,
                    end=end_dt,
                    limit=1000,
                )
            except Exception as exc:
                is_rate_limit = (
                    "RateLimit" in type(exc).__name__
                    or "429" in str(exc)
                    or getattr(exc, "status_code", None) == 429
                )
                status_code = 429 if is_rate_limit else getattr(exc, "status_code", None)
                sanitized_reason = _sanitize_error_message(str(exc))
                raise HistoricalDataUnavailableError(
                    symbol=canonical,
                    timeframe=tf_str,
                    start=start_dt,
                    end=end_dt,
                    provider=provider_name,
                    reason=f"External provider failure: {sanitized_reason}",
                    status_code=status_code,
                    cause=exc,
                ) from exc

            if not raw_candles:
                raise HistoricalDataUnavailableError(
                    symbol=canonical,
                    timeframe=tf_str,
                    start=start_dt,
                    end=end_dt,
                    provider=provider_name,
                    reason="External provider returned zero candles for requested range",
                )

            candles = []
            for c in raw_candles:
                candles.append(
                    {
                        "timestamp": c.timestamp if hasattr(c, "timestamp") else c["timestamp"],
                        "open": Decimal(str(c.open if hasattr(c, "open") else c["open"])),
                        "high": Decimal(str(c.high if hasattr(c, "high") else c["high"])),
                        "low": Decimal(str(c.low if hasattr(c, "low") else c["low"])),
                        "close": Decimal(str(c.close if hasattr(c, "close") else c["close"])),
                        "volume": Decimal(
                            str(c.volume if hasattr(c, "volume") else c.get("volume", 100))
                        ),
                    }
                )
            candles.sort(key=lambda x: x["timestamp"])

            # Verify integrity
            for c in candles:
                if (
                    c["high"] < c["low"]
                    or c["high"] < c["open"]
                    or c["high"] < c["close"]
                    or c["low"] > c["open"]
                    or c["low"] > c["close"]
                ):
                    raise HistoricalDataUnavailableError(
                        symbol=canonical,
                        timeframe=tf_str,
                        start=start_dt,
                        end=end_dt,
                        provider=provider_name,
                        reason="Candle integrity violation: high/low bounds invalid",
                    )

            import hashlib

            dataset_hash = None
            if candles:
                fp = f"{len(candles)}:{candles[0]['timestamp']}:{candles[0]['open']}:{candles[-1]['timestamp']}:{candles[-1]['close']}"
                dataset_hash = hashlib.sha256(fp.encode()).hexdigest()[:16]

            self._last_provenance = DatasetProvenance(
                data_source="external",
                provider=provider_name,
                symbol=canonical,
                timeframe=tf_str,
                start=start_dt,
                end=end_dt,
                candle_count=len(candles),
                synthetic=False,
                deterministic=False,
                data_quality="excellent",
                dataset_hash=dataset_hash,
            )
            return candles

        # 2. Deterministic Synthetic Data Path
        elif effective_mode == DataSourceMode.SYNTHETIC:
            candles = self._generate_deterministic_candles(canonical, tf_domain, start_dt, end_dt)
            import hashlib

            dataset_hash = None
            if candles:
                fp = f"{len(candles)}:{candles[0]['timestamp']}:{candles[0]['open']}:{candles[-1]['timestamp']}:{candles[-1]['close']}"
                dataset_hash = hashlib.sha256(fp.encode()).hexdigest()[:16]

            self._last_provenance = DatasetProvenance(
                data_source="synthetic",
                provider="deterministic_prng",
                symbol=canonical,
                timeframe=tf_str,
                start=start_dt,
                end=end_dt,
                candle_count=len(candles),
                synthetic=True,
                deterministic=True,
                data_quality=None,
                dataset_hash=dataset_hash,
            )
            return candles

        else:
            raise ValueError(f"Unsupported data source mode: {effective_mode}")

    def _generate_deterministic_candles(
        self,
        symbol: str,
        timeframe: Timeframe | BarType | str,
        start_dt: datetime,
        end_dt: datetime,
    ) -> list[dict[str, Any]]:
        from libraries.domain.market_data.normalization import bar_type_to_timeframe

        tf_domain = bar_type_to_timeframe(timeframe)
        base = self._BASE_PRICES.get(symbol, Decimal("1.08500"))
        tf_val = tf_domain.value

        step_map: dict[Timeframe, timedelta] = {
            Timeframe.M1: timedelta(minutes=1),
            Timeframe.M5: timedelta(minutes=5),
            Timeframe.M15: timedelta(minutes=15),
            Timeframe.M30: timedelta(minutes=30),
            Timeframe.H1: timedelta(hours=1),
            Timeframe.H4: timedelta(hours=4),
            Timeframe.D1: timedelta(days=1),
            Timeframe.WEEKLY: timedelta(weeks=1),
        }

        seed_str = f"{symbol}_{start_dt.date().isoformat()}_{end_dt.date().isoformat()}_{tf_val}"
        seed_int = int(hashlib.sha256(seed_str.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed_int)

        candles = []
        curr = start_dt
        current_price = float(base)

        if tf_domain == Timeframe.WEEKLY and curr.weekday() >= 5:
            curr += timedelta(days=(7 - curr.weekday()))

        while curr <= end_dt:
            is_active_session = True if tf_domain in (Timeframe.WEEKLY, Timeframe.MONTHLY) else (curr.weekday() < 5)

            if is_active_session:
                drift = (rng.random() - 0.495) * 0.001 * current_price
                open_p = current_price
                close_p = open_p + drift

                high_noise = abs(rng.random() * 0.0015 * current_price)
                low_noise = abs(rng.random() * 0.0015 * current_price)

                high_p = max(open_p, close_p) + high_noise
                low_p = min(open_p, close_p) - low_noise
                volume = Decimal(str(rng.randint(50, 500)))

                candles.append(
                    {
                        "timestamp": curr,
                        "open": Decimal(f"{open_p:.5f}"),
                        "high": Decimal(f"{high_p:.5f}"),
                        "low": Decimal(f"{low_p:.5f}"),
                        "close": Decimal(f"{close_p:.5f}"),
                        "volume": volume,
                    }
                )
                current_price = close_p

            if tf_domain == Timeframe.MONTHLY:
                year = curr.year + 1 if curr.month == 12 else curr.year
                month = 1 if curr.month == 12 else curr.month + 1
                max_day = calendar.monthrange(year, month)[1]
                day = min(curr.day, max_day)
                curr = curr.replace(year=year, month=month, day=day)
            else:
                curr += step_map[tf_domain]

        return candles

    async def load_ticks(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        return []

    async def get_available_symbols(self) -> list[str]:
        from libraries.domain.market_data.normalization import canonical_instruments

        return list(canonical_instruments().keys())

    async def validate_data_available(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> bool:
        from libraries.domain.market_data.exceptions import SymbolNotFoundError
        from libraries.domain.market_data.normalization import (
            canonical_instruments,
            normalize_symbol,
        )

        try:
            canonical = normalize_symbol(symbol)
            return canonical in canonical_instruments() and start_date <= end_date
        except SymbolNotFoundError:
            # Unknown symbol — treat as data unavailable, not a crash.
            return False
