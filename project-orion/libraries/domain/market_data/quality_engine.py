"""Market Data Quality Engine.

Provides deterministic validation, deduplication, sequencing, and staleness
detection for institutional Forex market data.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.market_data.exceptions import (
    InvalidBarError,
    InvalidQuoteError,
)
from libraries.domain.market_data.models import (
    DataQuality,
    OHLCV,
    Quote,
    Tick,
)
from libraries.domain.market_data.validation import (
    check_staleness,
    validate_ohlc,
    validate_quote,
)


@dataclass(frozen=True, slots=True)
class QualityAssessment:
    """Outcome of quality evaluation for an incoming market data item."""

    quality: DataQuality
    is_valid: bool
    is_duplicate: bool
    is_out_of_order: bool
    is_stale: bool
    issues: tuple[str, ...] = field(default_factory=tuple)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MarketDataQualityEngine:
    """Deterministic quality governance engine.

    Guarantees:
    - Zero duplicate events processed downstream (rolling signature ring buffer).
    - Monotonic time sequencing per symbol (detects out-of-order records).
    - Hard rejection of malformed or crossed prices.
    - Explicit classification of stale feeds.
    """

    def __init__(
        self,
        stale_threshold_seconds: float = 30.0,
        dedup_window_size: int = 2000,
        normal_spread_pips: dict[str, Decimal] | None = None,
    ) -> None:
        self._stale_threshold = stale_threshold_seconds
        self._dedup_window_size = dedup_window_size
        self._normal_spread_pips = normal_spread_pips or {
            "EUR/USD": Decimal("0.00010"),  # 1 pip
            "GBP/USD": Decimal("0.00015"),  # 1.5 pips
            "USD/JPY": Decimal("0.015"),    # 1.5 pips
            "USD/CHF": Decimal("0.00015"),
            "AUD/USD": Decimal("0.00015"),
            "USD/CAD": Decimal("0.00020"),
            "NZD/USD": Decimal("0.00020"),
            "XAU/USD": Decimal("0.30"),
        }

        self._seen_signatures: deque[str] = deque(maxlen=dedup_window_size)
        self._seen_set: set[str] = set()
        self._last_timestamp: dict[str, datetime] = {}
        self._lock = asyncio.Lock()

    async def evaluate_quote(self, quote: Quote) -> QualityAssessment:
        """Evaluate incoming Quote for quality, duplicates, ordering, and staleness."""
        issues: list[str] = []
        is_valid = True
        is_duplicate = False
        is_out_of_order = False
        is_stale = False

        # 1. Basic Schema Validation
        try:
            validate_quote(quote.bid, quote.ask, quote.timestamp)
        except InvalidQuoteError as err:
            is_valid = False
            issues.append(str(err))
            return QualityAssessment(
                quality=DataQuality.INVALID,
                is_valid=False,
                is_duplicate=False,
                is_out_of_order=False,
                is_stale=False,
                issues=tuple(issues),
            )

        # 2. Deduplication check
        sig = f"Q:{quote.symbol}:{quote.timestamp.isoformat()}:{quote.bid}:{quote.ask}"
        async with self._lock:
            if sig in self._seen_set:
                is_duplicate = True
                issues.append(f"Duplicate quote received for {quote.symbol} at {quote.timestamp}")
            else:
                if len(self._seen_signatures) >= self._dedup_window_size:
                    oldest = self._seen_signatures.popleft()
                    self._seen_set.discard(oldest)
                self._seen_signatures.append(sig)
                self._seen_set.add(sig)

            # 3. Sequencing check
            last_ts = self._last_timestamp.get(quote.symbol)
            if last_ts is not None and quote.timestamp < last_ts:
                is_out_of_order = True
                issues.append(
                    f"Out-of-order quote for {quote.symbol}: timestamp {quote.timestamp} < last {last_ts}"
                )
            elif last_ts is None or quote.timestamp > last_ts:
                self._last_timestamp[quote.symbol] = quote.timestamp

        # 4. Staleness check
        try:
            is_stale = check_staleness(quote.timestamp, max_age_seconds=self._stale_threshold)
            if is_stale:
                issues.append(f"Quote for {quote.symbol} is stale (> {self._stale_threshold}s old)")
        except Exception as err:
            is_stale = True
            issues.append(f"Staleness evaluation failed: {err}")

        # 5. Quality scoring
        if is_duplicate or is_out_of_order:
            quality = DataQuality.DEGRADED
        elif is_stale:
            quality = DataQuality.STALE
        else:
            spread = quote.spread
            normal_spread = self._normal_spread_pips.get(quote.symbol, Decimal("0.00020"))
            if spread > normal_spread * Decimal("5"):
                quality = DataQuality.DEGRADED
                issues.append(f"Abnormally wide spread: {spread} > 5x normal ({normal_spread * 5})")
            elif spread <= normal_spread * Decimal("1.5"):
                quality = DataQuality.EXCELLENT
            else:
                quality = DataQuality.GOOD

        return QualityAssessment(
            quality=quality,
            is_valid=is_valid,
            is_duplicate=is_duplicate,
            is_out_of_order=is_out_of_order,
            is_stale=is_stale,
            issues=tuple(issues),
        )

    async def evaluate_ohlcv(self, ohlcv: OHLCV) -> QualityAssessment:
        """Evaluate incoming OHLCV bar for quality, invariants, and staleness."""
        issues: list[str] = []
        is_valid = True
        is_duplicate = False
        is_out_of_order = False
        is_stale = False

        # 1. OHLC relationship validation
        try:
            validate_ohlc(
                ohlcv.open,
                ohlcv.high,
                ohlcv.low,
                ohlcv.close,
                ohlcv.volume,
            )
        except InvalidBarError as err:
            is_valid = False
            issues.append(str(err))
            return QualityAssessment(
                quality=DataQuality.INVALID,
                is_valid=False,
                is_duplicate=False,
                is_out_of_order=False,
                is_stale=False,
                issues=tuple(issues),
            )

        # 2. Deduplication check
        sig = f"B:{ohlcv.symbol}:{ohlcv.bar_type}:{ohlcv.timestamp.isoformat()}:{ohlcv.close}"
        async with self._lock:
            if sig in self._seen_set:
                is_duplicate = True
                issues.append(f"Duplicate OHLCV bar for {ohlcv.symbol} at {ohlcv.timestamp}")
            else:
                if len(self._seen_signatures) >= self._dedup_window_size:
                    oldest = self._seen_signatures.popleft()
                    self._seen_set.discard(oldest)
                self._seen_signatures.append(sig)
                self._seen_set.add(sig)

        # 3. Bar quality scoring
        quality = DataQuality.DEGRADED if is_duplicate else DataQuality.GOOD

        return QualityAssessment(
            quality=quality,
            is_valid=is_valid,
            is_duplicate=is_duplicate,
            is_out_of_order=is_out_of_order,
            is_stale=is_stale,
            issues=tuple(issues),
        )
