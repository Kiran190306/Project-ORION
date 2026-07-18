"""
Data Validators Module

Module Description:
This module provides validation logic for data quality checks.
It includes validators for tick data, OHLC data, metadata, and quality checks.

Implementation Checklist:
- [ ] Tick data validator
- [ ] OHLC data validator
- [ ] Symbol metadata validator
- [ ] Session metadata validator
- [ ] Holiday calendar validator
- [ ] Missing candle check
- [ ] Duplicate record check
- [ ] Timestamp consistency check
- [ ] Outlier detection check
- [ ] Corrupted file check
- [ ] Gap detection check
- [ ] Session validation check
- [ ] Timezone normalization check
- [ ] Symbol consistency check
- [ ] Checksum validation check

Dependency Notes:
- Depends on: shared/ (errors), libraries/data/schemas/
- Used by: quality/, pipelines/
"""

import statistics
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple

from libraries.data.schemas import (
    OHLC,
    DataQualityReport,
    Holiday,
    QualityCheck,
    QualityIssue,
    Session,
    SymbolMetadata,
    Tick,
)
from shared.errors import ValidationError


class TickValidator:
    """Validator for tick data."""

    @staticmethod
    def validate_tick(tick: Tick) -> List[str]:
        """Validate a single tick record."""
        errors: List[str] = []

        # Check required fields
        if not tick.tick_id:
            errors.append("Missing tick_id")
        if not tick.symbol:
            errors.append("Missing symbol")
        if not tick.timestamp:
            errors.append("Missing timestamp")
        if tick.bid_price is None or tick.bid_price <= 0:
            errors.append("Invalid bid_price")
        if tick.ask_price is None or tick.ask_price <= 0:
            errors.append("Invalid ask_price")

        # Check timestamp is UTC
        if tick.timestamp and tick.timestamp.tzinfo is not None:
            errors.append("Timestamp must be naive UTC")

        # Check bid < ask
        if tick.bid_price and tick.ask_price and tick.bid_price >= tick.ask_price:
            errors.append("bid_price must be less than ask_price")

        return errors

    @staticmethod
    def validate_tick_sequence(ticks: List[Tick]) -> List[str]:
        """Validate tick sequence ordering."""
        errors: List[str] = []

        if not ticks:
            return errors

        # Check timestamps are ascending
        for i in range(1, len(ticks)):
            if ticks[i].timestamp < ticks[i - 1].timestamp:
                errors.append(f"Timestamp out of order at index {i}")

        return errors


class OHLCValidator:
    """Validator for OHLC data."""

    @staticmethod
    def validate_ohlc(ohlc: OHLC) -> List[str]:
        """Validate a single OHLC record."""
        errors: List[str] = []

        # Check required fields
        if not ohlc.candle_id:
            errors.append("Missing candle_id")
        if not ohlc.symbol:
            errors.append("Missing symbol")
        if not ohlc.timeframe:
            errors.append("Missing timeframe")
        if not ohlc.timestamp:
            errors.append("Missing timestamp")

        # Check OHLC values
        if ohlc.open is None or ohlc.open <= 0:
            errors.append("Invalid open")
        if ohlc.high is None or ohlc.high <= 0:
            errors.append("Invalid high")
        if ohlc.low is None or ohlc.low <= 0:
            errors.append("Invalid low")
        if ohlc.close is None or ohlc.close <= 0:
            errors.append("Invalid close")

        # Check OHLC relationships
        if ohlc.high and ohlc.low and ohlc.high < ohlc.low:
            errors.append("high must be >= low")
        if ohlc.open and ohlc.high and ohlc.open > ohlc.high:
            errors.append("open must be <= high")
        if ohlc.open and ohlc.low and ohlc.open < ohlc.low:
            errors.append("open must be >= low")
        if ohlc.close and ohlc.high and ohlc.close > ohlc.high:
            errors.append("close must be <= high")
        if ohlc.close and ohlc.low and ohlc.close < ohlc.low:
            errors.append("close must be >= low")

        # Check volume
        if ohlc.volume is None or ohlc.volume < 0:
            errors.append("Invalid volume")

        # Check tick count
        if ohlc.tick_count is None or ohlc.tick_count < 1:
            errors.append("Invalid tick_count")

        return errors

    @staticmethod
    def validate_ohlc_alignment(ohlc: OHLC, timeframe: str) -> List[str]:
        """Validate OHLC timestamp alignment to timeframe."""
        errors: List[str] = []

        if not ohlc.timestamp:
            return errors

        # TODO: Implement timeframe-specific alignment checks
        # For now, just check timestamp is not None
        pass

        return errors


class MetadataValidator:
    """Validator for metadata."""

    @staticmethod
    def validate_symbol_metadata(metadata: SymbolMetadata) -> List[str]:
        """Validate symbol metadata."""
        errors = []

        # Check required fields
        if not metadata.symbol_id:
            errors.append("Missing symbol_id")
        if not metadata.symbol:
            errors.append("Missing symbol")
        if not metadata.base_currency:
            errors.append("Missing base_currency")
        if not metadata.quote_currency:
            errors.append("Missing quote_currency")

        # Check numeric values
        if metadata.pip_size is None or metadata.pip_size <= 0:
            errors.append("Invalid pip_size")
        if metadata.tick_size is None or metadata.tick_size <= 0:
            errors.append("Invalid tick_size")
        if metadata.contract_size is None or metadata.contract_size <= 0:
            errors.append("Invalid contract_size")

        # Check quality score
        if metadata.data_quality_score < 0 or metadata.data_quality_score > 1:
            errors.append("Invalid data_quality_score")

        return errors

    @staticmethod
    def validate_session(session: Session) -> List[str]:
        """Validate session metadata."""
        errors = []

        # Check required fields
        if not session.session_id:
            errors.append("Missing session_id")
        if not session.name:
            errors.append("Missing name")
        if not session.timezone:
            errors.append("Missing timezone")

        # Check times
        if not session.start_time:
            errors.append("Missing start_time")
        if not session.end_time:
            errors.append("Missing end_time")

        # Check days of week
        if session.days_of_week:
            for day in session.days_of_week:
                if day < 0 or day > 6:
                    errors.append(f"Invalid day of week: {day}")

        return errors

    @staticmethod
    def validate_holiday(holiday: Holiday) -> List[str]:
        """Validate holiday calendar."""
        errors = []

        # Check required fields
        if not holiday.holiday_id:
            errors.append("Missing holiday_id")
        if not holiday.name:
            errors.append("Missing name")
        if not holiday.date:
            errors.append("Missing date")

        return errors


class QualityChecker:
    """Quality checker for datasets."""

    @staticmethod
    def check_missing_candles(expected_count: int, actual_count: int) -> QualityCheck:
        """Check for missing candles."""
        if expected_count == 0:
            score = 1.0
        else:
            score = 1.0 - (expected_count - actual_count) / expected_count

        return QualityCheck(
            check_id="missing_candles",
            check_name="Missing Candles",
            check_type="completeness",
            passed=score >= 0.99,
            score=max(0.0, score),
            details={
                "expected_count": expected_count,
                "actual_count": actual_count,
                "missing_count": expected_count - actual_count,
            },
            timestamp=datetime.utcnow(),
        )

    @staticmethod
    def check_duplicates(total_count: int, duplicate_count: int) -> QualityCheck:
        """Check for duplicate records."""
        if total_count == 0:
            score = 1.0
        else:
            score = 1.0 - (duplicate_count / total_count)

        return QualityCheck(
            check_id="duplicates",
            check_name="Duplicate Records",
            check_type="uniqueness",
            passed=score >= 0.99,
            score=max(0.0, score),
            details={"total_count": total_count, "duplicate_count": duplicate_count},
            timestamp=datetime.utcnow(),
        )

    @staticmethod
    def check_timestamp_consistency(
        ordering_score: float,
        alignment_score: float,
        gap_score: float,
        timezone_score: float,
    ) -> QualityCheck:
        """Check timestamp consistency."""
        score = (
            (ordering_score * 0.4)
            + (alignment_score * 0.3)
            + (gap_score * 0.2)
            + (timezone_score * 0.1)
        )

        return QualityCheck(
            check_id="timestamp_consistency",
            check_name="Timestamp Consistency",
            check_type="consistency",
            passed=score >= 0.95,
            score=max(0.0, score),
            details={
                "ordering_score": ordering_score,
                "alignment_score": alignment_score,
                "gap_score": gap_score,
                "timezone_score": timezone_score,
            },
            timestamp=datetime.utcnow(),
        )

    @staticmethod
    def check_outliers(total_count: int, outlier_count: int) -> QualityCheck:
        """Check for outliers."""
        if total_count == 0:
            score = 1.0
        else:
            score = 1.0 - (outlier_count / total_count)

        return QualityCheck(
            check_id="outliers",
            check_name="Outlier Detection",
            check_type="quality",
            passed=score >= 0.98,
            score=max(0.0, score),
            details={"total_count": total_count, "outlier_count": outlier_count},
            timestamp=datetime.utcnow(),
        )

    @staticmethod
    def check_checksum(calculated_checksum: str, stored_checksum: str) -> QualityCheck:
        """Check checksum validation."""
        passed = calculated_checksum == stored_checksum
        score = 1.0 if passed else 0.0

        return QualityCheck(
            check_id="checksum",
            check_name="Checksum Validation",
            check_type="integrity",
            passed=passed,
            score=score,
            details={
                "calculated_checksum": calculated_checksum,
                "stored_checksum": stored_checksum,
            },
            timestamp=datetime.utcnow(),
        )

    @staticmethod
    def calculate_overall_quality_score(
        missing_candle_score: float,
        duplicate_score: float,
        timestamp_score: float,
        outlier_score: float,
        file_score: float,
        gap_score: float,
        session_score: float,
        timezone_score: float,
        symbol_score: float,
        checksum_score: float,
    ) -> float:
        """Calculate overall quality score."""
        return (
            missing_candle_score * 0.20
            + duplicate_score * 0.10
            + timestamp_score * 0.15
            + outlier_score * 0.10
            + file_score * 0.05
            + gap_score * 0.10
            + session_score * 0.10
            + timezone_score * 0.10
            + symbol_score * 0.05
            + checksum_score * 0.05
        )

    @staticmethod
    def get_quality_bucket(score: float) -> str:
        """Get quality bucket from score."""
        if score >= 0.950:
            return "excellent"
        elif score >= 0.900:
            return "good"
        elif score >= 0.800:
            return "acceptable"
        else:
            return "poor"
