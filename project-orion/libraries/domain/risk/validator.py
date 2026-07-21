"""Risk Validator - pre-engine validation checks.

Validates the integrity of the risk evaluation pipeline before policies
are executed. Checks context completeness, engine readiness, and
basic preconditions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from libraries.domain.risk.context import RiskContext
from libraries.domain.risk.exceptions import ContextError
from libraries.domain.risk.models import RiskDecision, RiskResult


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Report of pre-engine validation."""

    is_valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


class RiskValidator:
    """Validates risk evaluation inputs and state.

    Performs:
    - Context completeness checks
    - Account data sanity checks
    - Market data consistency checks
    - Engine readiness checks
    """

    def __init__(
        self,
        min_balance: float = 0.0,
        max_leverage: float = 500.0,
        max_spread_pips: float = 100.0,
        require_market_open: bool = False,
    ) -> None:
        self._min_balance = min_balance
        self._max_leverage = max_leverage
        self._max_spread_pips = max_spread_pips
        self._require_market_open = require_market_open

    async def validate_context(self, context: RiskContext) -> ValidationReport:
        """Validate a RiskContext before policy evaluation.

        Args:
            context: The risk context to validate.

        Returns:
            ValidationReport with any errors or warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Basic field validation
        if not context.symbol:
            errors.append("Symbol is required")

        if context.account_balance < 0:
            errors.append(f"Negative account balance: {context.account_balance}")

        if context.account_equity < 0:
            errors.append(f"Negative account equity: {context.account_equity}")

        if context.margin_used < 0:
            errors.append(f"Negative margin used: {context.margin_used}")

        if context.leverage <= 0:
            errors.append(f"Leverage must be positive: {context.leverage}")
        elif context.leverage > self._max_leverage:
            warnings.append(
                f"Leverage {context.leverage:.1f}x exceeds maximum {self._max_leverage:.1f}x"
            )

        # Position data validation
        if context.position_size is not None and context.position_size < 0:
            errors.append(f"Negative position size: {context.position_size}")

        if context.account_balance > 0 and context.position_size is not None:
            if context.position_size > context.account_balance:
                warnings.append(
                    f"Position size {context.position_size} exceeds account balance "
                    f"{context.account_balance}"
                )

        # Market data validation
        if context.spread_pips < 0:
            errors.append(f"Negative spread: {context.spread_pips}")
        elif context.spread_pips > self._max_spread_pips:
            warnings.append(
                f"Spread {context.spread_pips:.1f} pips exceeds max {self._max_spread_pips:.1f} pips"
            )

        if not 0.0 <= context.liquidity_score <= 1.0:
            warnings.append(f"Liquidity score out of range [0,1]: {context.liquidity_score}")

        if context.volatility < 0:
            errors.append(f"Negative volatility: {context.volatility}")

        # Market hours
        if self._require_market_open and not context.market_open:
            errors.append("Market is closed and require_market_open is enabled")

        # Broker health
        if not context.broker_connected:
            warnings.append("Broker is not connected")

        if not context.data_feed_active:
            warnings.append("Data feed is not active")

        # Drawdown validation
        if context.drawdown is not None:
            if not 0.0 <= context.drawdown.current_drawdown <= 100.0:
                warnings.append(
                    f"Drawdown {context.drawdown.current_drawdown:.1f}% out of expected range"
                )

        # Protection status validation
        if context.protection_status is not None and context.protection_status.is_locked:
            warnings.append("Account is currently locked")

        return ValidationReport(
            is_valid=len(errors) == 0,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    async def validate_trade_decision(self, decision: Any) -> ValidationReport:
        """Validate a TradeDecision before risk evaluation.

        Args:
            decision: The TradeDecision to validate.

        Returns:
            ValidationReport with any errors or warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Check required attributes
        if not hasattr(decision, "symbol"):
            errors.append("TradeDecision missing 'symbol' attribute")
        elif not decision.symbol:
            errors.append("TradeDecision symbol is empty")

        if hasattr(decision, "outcome") and not decision.outcome:
            warnings.append("TradeDecision outcome is empty")

        if hasattr(decision, "position_size") and decision.position_size is not None:
            if decision.position_size < 0:
                errors.append(f"TradeDecision negative position size: {decision.position_size}")

        if hasattr(decision, "direction") and decision.direction is not None:
            valid_directions = {"buy", "sell", "long", "short"}
            if decision.direction.lower() not in valid_directions:
                warnings.append(
                    f"Unusual direction: {decision.direction} "
                    f"(expected one of {valid_directions})"
                )

        return ValidationReport(
            is_valid=len(errors) == 0,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    async def is_context_valid(self, context: RiskContext) -> bool:
        """Quick check if context is valid for evaluation.

        Args:
            context: The risk context.

        Returns:
            True if context has no critical errors.
        """
        report = await self.validate_context(context)
        return report.is_valid

    async def check_balance_non_negative(self, balance: float) -> bool:
        """Verify account balance is non-negative.

        Args:
            balance: Account balance to check.

        Returns:
            True if balance is >= 0.
        """
        return balance >= self._min_balance

    async def check_leverage_within_limits(self, leverage: float) -> bool:
        """Verify leverage is within configured limits.

        Args:
            leverage: Current leverage.

        Returns:
            True if leverage is within limits.
        """
        return 0 < leverage <= self._max_leverage

