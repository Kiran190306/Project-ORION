"""Validation rules for raw and canonical market-data records."""

from __future__ import annotations

from datetime import timezone
from decimal import Decimal

from .models import RawTick, Tick, ValidationIssue, ValidationReport


class ValidationEngine:
    """Applies deterministic record-level market-data validation rules."""

    def validate_raw_tick(self, tick: RawTick) -> ValidationReport:
        """Validate externally supplied tick data without raising.

        All observed issues are returned together so a provider integration can
        correct an entire payload rather than fail one field at a time.
        """
        issues: list[ValidationIssue] = []
        if not tick.symbol.strip():
            issues.append(ValidationIssue("symbol", "symbol is required"))
        if not tick.source.strip():
            issues.append(ValidationIssue("source", "source is required"))
        if tick.timestamp.tzinfo is None or tick.timestamp.utcoffset() is None:
            issues.append(ValidationIssue("timestamp", "timestamp must be timezone-aware"))
        if tick.bid <= Decimal("0"):
            issues.append(ValidationIssue("bid", "bid must be positive"))
        if tick.ask <= Decimal("0"):
            issues.append(ValidationIssue("ask", "ask must be positive"))
        if tick.bid > tick.ask:
            issues.append(ValidationIssue("bid", "bid cannot exceed ask"))
        if tick.bid_size is not None and tick.bid_size < Decimal("0"):
            issues.append(ValidationIssue("bid_size", "bid_size cannot be negative"))
        if tick.ask_size is not None and tick.ask_size < Decimal("0"):
            issues.append(ValidationIssue("ask_size", "ask_size cannot be negative"))
        if tick.sequence is not None and tick.sequence < 0:
            issues.append(ValidationIssue("sequence", "sequence cannot be negative"))
        return ValidationReport(tuple(issues))

    def validate_tick(self, tick: Tick) -> ValidationReport:
        """Validate invariants that remain relevant after normalization."""
        issues: list[ValidationIssue] = []
        if tick.timestamp.utcoffset() != timezone.utc.utcoffset(tick.timestamp):
            issues.append(ValidationIssue("timestamp", "timestamp must be UTC"))
        if tick.bid > tick.ask:
            issues.append(ValidationIssue("bid", "bid cannot exceed ask"))
        return ValidationReport(tuple(issues))
