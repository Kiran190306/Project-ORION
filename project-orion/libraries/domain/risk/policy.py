"""Risk Policy Implementations - 24 independent risk policies.

Each policy implements the RiskPolicy protocol with:
- evaluate()       → PolicyResult
- name / description / category / severity / priority
- enabled property
- statistics()     → dict of stats
- initialize() / dispose()
"""

from __future__ import annotations

import asyncio
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.risk.context import RiskContext
from libraries.domain.risk.models import (
    PolicyCategory,
    PolicyResult,
    PolicySeverity,
)
from libraries.domain.risk.profile import RiskProfileConfig


# ─── Base Policy ────────────────────────────────────────────────────────────


class BaseRiskPolicy(ABC):
    """Abstract base for all risk policies.

    Provides common statistics tracking and lifecycle management.
    """

    def __init__(
        self,
        name: str,
        description: str,
        category: PolicyCategory,
        severity: PolicySeverity = PolicySeverity.MEDIUM,
        priority: int = 100,
        enabled: bool = True,
    ) -> None:
        self._name = name
        self._description = description
        self._category = category
        self._severity = severity
        self._priority = priority
        self._enabled = enabled
        self._initialized = False
        self._evaluation_count = 0
        self._pass_count = 0
        self._fail_count = 0
        self._total_score = 0.0
        self._lock = asyncio.Lock()

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def category(self) -> PolicyCategory:
        return self._category

    @property
    def severity(self) -> PolicySeverity:
        return self._severity

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def priority(self) -> int:
        return self._priority

    async def initialize(self) -> None:
        """Initialize the policy."""
        async with self._lock:
            self._initialized = True

    async def dispose(self) -> None:
        """Clean up resources."""
        async with self._lock:
            self._initialized = False

    @abstractmethod
    async def evaluate(self, context: RiskContext) -> PolicyResult:
        """Evaluate the policy against the risk context."""
        ...

    async def statistics(self) -> dict[str, Any]:
        """Return current statistics."""
        async with self._lock:
            total = self._evaluation_count
            avg_score = self._total_score / total if total > 0 else 100.0
            pass_rate = self._pass_count / total if total > 0 else 1.0
            return {
                "policy_name": self._name,
                "evaluation_count": self._evaluation_count,
                "pass_count": self._pass_count,
                "fail_count": self._fail_count,
                "pass_rate": round(pass_rate, 4),
                "average_score": round(avg_score, 2),
                "enabled": self._enabled,
                "initialized": self._initialized,
            }

    async def _record_result(self, result: PolicyResult) -> PolicyResult:
        """Record evaluation result for statistics."""
        async with self._lock:
            self._evaluation_count += 1
            self._total_score += result.score
            if result.passed:
                self._pass_count += 1
            else:
                self._fail_count += 1
        return result

    def _make_result(
        self,
        passed: bool,
        score: float,
        message: str,
        details: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> PolicyResult:
        """Create a PolicyResult."""
        return PolicyResult(
            policy_name=self._name,
            policy_category=self._category,
            severity=self._severity,
            passed=passed,
            score=max(0.0, min(100.0, score)),
            message=message,
            details=details,
            metadata=metadata or {},
        )

    def _apply_profile_threshold(
        self,
        value: float,
        max_value: float,
        invert: bool = False,
        min_score: float = 0.0,
    ) -> tuple[bool, float]:
        """Apply a profile threshold and return (passed, score).

        Args:
            value: The current value (e.g., current loss %).
            max_value: The maximum allowed value.
            invert: If True, lower values are worse (e.g., liquidity).
            min_score: Minimum score to return even when passing.

        Returns:
            (passed, score) where score is 0–100.
        """
        if max_value <= 0:
            return True, 100.0

        if invert:
            # Lower is worse: score = (value / max_value) * 100
            ratio = min(1.0, value / max_value)
            score = max(min_score, ratio * 100.0)
            passed = value >= max_value * 0.5  # Allow at 50% of max
        else:
            # Higher is worse: score = (1 - value/max_value) * 100
            ratio = min(1.0, value / max_value)
            score = max(min_score, (1.0 - ratio) * 100.0)
            passed = value <= max_value

        return passed, round(score, 2)


# ============================================================================
# Category 1: POSITION_SIZING
# ============================================================================


class MaximumPositionSizePolicy(BaseRiskPolicy):
    """Ensures position size does not exceed configured maximum."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="maximum_position_size",
            description="Ensures position size does not exceed configured maximum as % of account",
            category=PolicyCategory.POSITION_SIZING,
            severity=PolicySeverity.HIGH,
            priority=10,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        max_pct = self._config.max_position_size_pct
        if max_pct <= 0 or not context.account_balance:
            return await self._record_result(
                self._make_result(True, 100.0, "Position sizing check skipped (no limit)")
            )

        if context.notional_value and context.account_balance > 0:
            current_pct = float(context.notional_value / context.account_balance * 100)
            passed, score = self._apply_profile_threshold(current_pct, max_pct)
            if not passed:
                return await self._record_result(
                    self._make_result(
                        False, score,
                        f"Position size {current_pct:.2f}% exceeds maximum {max_pct:.1f}%",
                        details=f"Notional: {context.notional_value}, Balance: {context.account_balance}, "
                                f"Current: {current_pct:.2f}%, Max: {max_pct:.1f}%",
                    )
                )
            return await self._record_result(
                self._make_result(
                    True, score,
                    f"Position size {current_pct:.2f}% within {max_pct:.1f}% limit",
                )
            )

        return await self._record_result(
            self._make_result(True, 100.0, "No position size data available")
        )


# ============================================================================
# Category 2: LOSS_LIMITS
# ============================================================================


class MaximumDailyLossPolicy(BaseRiskPolicy):
    """Ensures daily loss does not exceed configured maximum."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="maximum_daily_loss",
            description="Ensures daily loss does not exceed configured maximum as % of account",
            category=PolicyCategory.LOSS_LIMITS,
            severity=PolicySeverity.HIGH,
            priority=20,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        max_loss = self._config.max_daily_loss_pct
        if max_loss <= 0:
            return await self._record_result(self._make_result(True, 100.0, "Daily loss limit disabled"))

        current_loss = context.daily_loss_pct
        passed, score = self._apply_profile_threshold(current_loss, max_loss)
        if not passed:
            return await self._record_result(
                self._make_result(
                    False, score,
                    f"Daily loss {current_loss:.2f}% exceeds {max_loss:.1f}% limit",
                    details=f"Daily PnL: {context.daily_pnl:.2f}, Balance: {context.account_balance}, "
                            f"Loss: {current_loss:.2f}%, Limit: {max_loss:.1f}%",
                )
            )
        return await self._record_result(
            self._make_result(
                True, score,
                f"Daily loss {current_loss:.2f}% within {max_loss:.1f}% limit",
            )
        )


class MaximumWeeklyLossPolicy(BaseRiskPolicy):
    """Ensures weekly loss does not exceed configured maximum."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="maximum_weekly_loss",
            description="Ensures weekly loss does not exceed configured maximum as % of account",
            category=PolicyCategory.LOSS_LIMITS,
            severity=PolicySeverity.HIGH,
            priority=21,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        max_loss = self._config.max_weekly_loss_pct
        if max_loss <= 0:
            return await self._record_result(self._make_result(True, 100.0, "Weekly loss limit disabled"))

        current_loss = context.weekly_loss_pct
        passed, score = self._apply_profile_threshold(current_loss, max_loss)
        if not passed:
            return await self._record_result(
                self._make_result(
                    False, score,
                    f"Weekly loss {current_loss:.2f}% exceeds {max_loss:.1f}% limit",
                    details=f"Weekly PnL: {context.weekly_pnl:.2f}, Loss: {current_loss:.2f}%, Limit: {max_loss:.1f}%",
                )
            )
        return await self._record_result(
            self._make_result(
                True, score,
                f"Weekly loss {current_loss:.2f}% within {max_loss:.1f}% limit",
            )
        )


class MaximumMonthlyLossPolicy(BaseRiskPolicy):
    """Ensures monthly loss does not exceed configured maximum."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="maximum_monthly_loss",
            description="Ensures monthly loss does not exceed configured maximum as % of account",
            category=PolicyCategory.LOSS_LIMITS,
            severity=PolicySeverity.CRITICAL,
            priority=22,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        max_loss = self._config.max_monthly_loss_pct
        if max_loss <= 0:
            return await self._record_result(self._make_result(True, 100.0, "Monthly loss limit disabled"))

        current_loss = context.monthly_loss_pct
        passed, score = self._apply_profile_threshold(current_loss, max_loss)
        if not passed:
            return await self._record_result(
                self._make_result(
                    False, score,
                    f"Monthly loss {current_loss:.2f}% exceeds {max_loss:.1f}% limit",
                    details=f"Monthly PnL: {context.monthly_pnl:.2f}, Loss: {current_loss:.2f}%, Limit: {max_loss:.1f}%",
                )
            )
        return await self._record_result(
            self._make_result(
                True, score,
                f"Monthly loss {current_loss:.2f}% within {max_loss:.1f}% limit",
            )
        )


class MaximumDrawdownPolicy(BaseRiskPolicy):
    """Ensures drawdown does not exceed configured maximum."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="maximum_drawdown",
            description="Ensures drawdown does not exceed configured maximum % from peak",
            category=PolicyCategory.LOSS_LIMITS,
            severity=PolicySeverity.CRITICAL,
            priority=23,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        max_dd = self._config.max_drawdown_pct
        if max_dd <= 0:
            return await self._record_result(self._make_result(True, 100.0, "Drawdown limit disabled"))

        current_dd = context.drawdown.current_drawdown if context.drawdown else 0.0
        passed, score = self._apply_profile_threshold(current_dd, max_dd)
        if not passed:
            return await self._record_result(
                self._make_result(
                    False, score,
                    f"Drawdown {current_dd:.2f}% exceeds {max_dd:.1f}% limit",
                    details=f"Current DD: {current_dd:.2f}%, Max Allowed: {max_dd:.1f}%",
                )
            )
        return await self._record_result(
            self._make_result(
                True, score,
                f"Drawdown {current_dd:.2f}% within {max_dd:.1f}% limit",
            )
        )


class MaximumConsecutiveLossesPolicy(BaseRiskPolicy):
    """Ensures consecutive losses do not exceed configured maximum."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="maximum_consecutive_losses",
            description="Ensures consecutive losing trades do not exceed configured maximum",
            category=PolicyCategory.LOSS_LIMITS,
            severity=PolicySeverity.HIGH,
            priority=24,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        max_losses = self._config.max_consecutive_losses
        if max_losses <= 0:
            return await self._record_result(self._make_result(True, 100.0, "Consecutive losses check disabled"))

        current = context.consecutive_losses
        if current >= max_losses:
            score = max(0.0, 100.0 - (current / max_losses) * 100.0)
            return await self._record_result(
                self._make_result(
                    False, score,
                    f"Consecutive losses {current} meets/exceeds limit {max_losses}",
                    details=f"Current streak: {current}, Maximum allowed: {max_losses}",
                )
            )

        score = 100.0 - (current / max_losses) * 50.0 if current > 0 else 100.0
        return await self._record_result(
            self._make_result(
                True, score,
                f"Consecutive losses {current} below limit {max_losses}",
            )
        )


# ============================================================================
# Category 3: EXPOSURE
# ============================================================================


class MaximumExposurePolicy(BaseRiskPolicy):
    """Ensures total portfolio exposure does not exceed configured maximum."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="maximum_exposure",
            description="Ensures total portfolio exposure does not exceed configured maximum as % of account",
            category=PolicyCategory.EXPOSURE,
            severity=PolicySeverity.HIGH,
            priority=30,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        max_exposure = self._config.max_total_exposure_pct
        if max_exposure <= 0:
            return await self._record_result(self._make_result(True, 100.0, "Exposure check disabled"))

        if context.portfolio_risk is not None:
            total_exposure = float(context.portfolio_risk.gross_exposure)
        elif context.account_balance > 0:
            total_exposure = float(
                sum(p.notional_value for p in context.current_positions)
            ) / float(context.account_balance) * 100.0
        else:
            return await self._record_result(self._make_result(True, 100.0, "No exposure data"))

        passed, score = self._apply_profile_threshold(total_exposure, max_exposure)
        if not passed:
            return await self._record_result(
                self._make_result(
                    False, score,
                    f"Total exposure {total_exposure:.2f}% exceeds {max_exposure:.1f}%",
                    details=f"Exposure: {total_exposure:.2f}%, Limit: {max_exposure:.1f}%",
                )
            )
        return await self._record_result(
            self._make_result(
                True, score,
                f"Total exposure {total_exposure:.2f}% within {max_exposure:.1f}%",
            )
        )


class MaximumSymbolExposurePolicy(BaseRiskPolicy):
    """Ensures per-symbol exposure does not exceed configured maximum."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="maximum_symbol_exposure",
            description="Ensures per-symbol exposure does not exceed configured maximum as % of account",
            category=PolicyCategory.EXPOSURE,
            severity=PolicySeverity.MEDIUM,
            priority=31,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        max_sym = self._config.max_symbol_exposure_pct
        if max_sym <= 0:
            return await self._record_result(self._make_result(True, 100.0, "Symbol exposure check disabled"))

        if context.symbol_position_size and context.account_balance > 0:
            symbol_exposure = float(context.symbol_position_size / context.account_balance * 100)
        elif context.notional_value and context.account_balance > 0:
            symbol_exposure = float(context.notional_value / context.account_balance * 100)
        else:
            return await self._record_result(self._make_result(True, 100.0, "No symbol data"))

        passed, score = self._apply_profile_threshold(symbol_exposure, max_sym)
        if not passed:
            return await self._record_result(
                self._make_result(
                    False, score,
                    f"Symbol {context.symbol} exposure {symbol_exposure:.2f}% exceeds {max_sym:.1f}%",
                    details=f"Symbol: {context.symbol}, Exposure: {symbol_exposure:.2f}%, Limit: {max_sym:.1f}%",
                )
            )
        return await self._record_result(
            self._make_result(
                True, score,
                f"Symbol {context.symbol} exposure {symbol_exposure:.2f}% within {max_sym:.1f}%",
            )
        )


class MaximumCurrencyExposurePolicy(BaseRiskPolicy):
    """Ensures per-currency exposure does not exceed configured maximum."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="maximum_currency_exposure",
            description="Ensures per-currency exposure does not exceed configured maximum as % of account",
            category=PolicyCategory.EXPOSURE,
            severity=PolicySeverity.MEDIUM,
            priority=32,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        max_ccy = self._config.max_currency_exposure_pct
        if max_ccy <= 0:
            return await self._record_result(self._make_result(True, 100.0, "Currency exposure check disabled"))

        if context.portfolio_risk and context.portfolio_risk.currency_exposure:
            exposures = context.portfolio_risk.currency_exposure
            violations = []
            for currency, exposure in exposures.items():
                exp_pct = float(exposure)
                if exp_pct > max_ccy:
                    violations.append(f"{currency}: {exp_pct:.2f}%")
            if violations:
                score = max(0.0, 100.0 - (len(violations) * 20.0))
                return await self._record_result(
                    self._make_result(
                        False, score,
                        f"Currency exposure limit exceeded for: {', '.join(violations)}",
                        details=f"Violations: {violations}, Limit: {max_ccy:.1f}%",
                    )
                )
            return await self._record_result(
                self._make_result(True, 100.0, "All currency exposures within limits")
            )

        return await self._record_result(self._make_result(True, 100.0, "No currency exposure data"))


# ============================================================================
# Category 4: LEVERAGE
# ============================================================================


class MaximumLeveragePolicy(BaseRiskPolicy):
    """Ensures leverage does not exceed configured maximum."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="maximum_leverage",
            description="Ensures account leverage does not exceed configured maximum",
            category=PolicyCategory.LEVERAGE,
            severity=PolicySeverity.HIGH,
            priority=40,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        max_lev = self._config.max_leverage
        if max_lev <= 0:
            return await self._record_result(self._make_result(True, 100.0, "Leverage check disabled"))

        current_leverage = context.leverage
        passed, score = self._apply_profile_threshold(current_leverage, max_lev)
        if not passed:
            return await self._record_result(
                self._make_result(
                    False, score,
                    f"Leverage {current_leverage:.1f}x exceeds {max_lev:.1f}x limit",
                    details=f"Current: {current_leverage:.1f}x, Max: {max_lev:.1f}x",
                )
            )
        return await self._record_result(
            self._make_result(
                True, score,
                f"Leverage {current_leverage:.1f}x within {max_lev:.1f}x limit",
            )
        )


class MaximumOpenPositionsPolicy(BaseRiskPolicy):
    """Ensures number of open positions does not exceed maximum."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="maximum_open_positions",
            description="Ensures number of open positions does not exceed configured maximum",
            category=PolicyCategory.LEVERAGE,
            severity=PolicySeverity.MEDIUM,
            priority=41,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        max_positions = self._config.max_open_positions
        if max_positions <= 0:
            return await self._record_result(self._make_result(True, 100.0, "Open positions check disabled"))

        current = context.open_positions_count
        if current >= max_positions:
            score = max(0.0, 100.0 - (current / max_positions) * 100.0)
            return await self._record_result(
                self._make_result(
                    False, score,
                    f"Open positions {current} meets/exceeds limit {max_positions}",
                    details=f"Current: {current}, Max: {max_positions}",
                )
            )

        score = 100.0 - (current / max_positions) * 30.0
        return await self._record_result(
            self._make_result(
                True, score,
                f"Open positions {current} below limit {max_positions}",
            )
        )


# ============================================================================
# Category 5: MARKET_CONDITIONS
# ============================================================================


class MarginProtectionPolicy(BaseRiskPolicy):
    """Ensures margin level is safe."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="margin_protection",
            description="Ensures margin level is above configured threshold",
            category=PolicyCategory.MARKET_CONDITIONS,
            severity=PolicySeverity.CRITICAL,
            priority=50,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        threshold = self._config.margin_call_threshold_pct
        if threshold <= 0:
            return await self._record_result(self._make_result(True, 100.0, "Margin check disabled"))

        margin_level = context.margin_level_pct
        if math.isinf(margin_level):
            return await self._record_result(self._make_result(True, 100.0, "No margin used"))

        passed, score = self._apply_profile_threshold(margin_level, threshold, invert=True)
        if not passed:
            return await self._record_result(
                self._make_result(
                    False, score,
                    f"Margin level {margin_level:.1f}% below threshold {threshold:.1f}%",
                    details=f"Equity: {context.account_equity}, Margin: {context.margin_used}, "
                            f"Level: {margin_level:.1f}%, Threshold: {threshold:.1f}%",
                )
            )
        return await self._record_result(
            self._make_result(
                True, score,
                f"Margin level {margin_level:.1f}% above threshold {threshold:.1f}%",
            )
        )


class SpreadProtectionPolicy(BaseRiskPolicy):
    """Ensures spread is within acceptable range."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="spread_protection",
            description="Ensures current spread does not exceed configured maximum",
            category=PolicyCategory.MARKET_CONDITIONS,
            severity=PolicySeverity.MEDIUM,
            priority=51,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        max_spread = self._config.max_spread_pips
        if max_spread <= 0:
            return await self._record_result(self._make_result(True, 100.0, "Spread check disabled"))

        current_spread = context.spread_pips
        passed, score = self._apply_profile_threshold(current_spread, max_spread)
        if not passed:
            return await self._record_result(
                self._make_result(
                    False, score,
                    f"Spread {current_spread:.2f} pips exceeds {max_spread:.1f} pips limit",
                    details=f"Current spread: {current_spread:.2f}, Max: {max_spread:.1f}",
                )
            )
        return await self._record_result(
            self._make_result(
                True, score,
                f"Spread {current_spread:.2f} pips within {max_spread:.1f} pips limit",
            )
        )


class VolatilityProtectionPolicy(BaseRiskPolicy):
    """Ensures volatility is within acceptable range."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="volatility_protection",
            description="Ensures current volatility does not exceed configured maximum",
            category=PolicyCategory.MARKET_CONDITIONS,
            severity=PolicySeverity.MEDIUM,
            priority=52,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        max_vol = self._config.max_volatility
        if max_vol <= 0:
            return await self._record_result(self._make_result(True, 100.0, "Volatility check disabled"))

        current_vol = context.volatility
        passed, score = self._apply_profile_threshold(current_vol, max_vol)
        if not passed:
            return await self._record_result(
                self._make_result(
                    False, score,
                    f"Volatility {current_vol:.3f} exceeds {max_vol:.2f} limit",
                    details=f"Current volatility: {current_vol:.3f}, Max: {max_vol:.2f}",
                )
            )
        return await self._record_result(
            self._make_result(
                True, score,
                f"Volatility {current_vol:.3f} within {max_vol:.2f} limit",
            )
        )


class LiquidityProtectionPolicy(BaseRiskPolicy):
    """Ensures liquidity is above minimum threshold."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="liquidity_protection",
            description="Ensures liquidity score is above configured minimum",
            category=PolicyCategory.MARKET_CONDITIONS,
            severity=PolicySeverity.MEDIUM,
            priority=53,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        min_liquidity = self._config.min_liquidity_score
        if min_liquidity <= 0:
            return await self._record_result(self._make_result(True, 100.0, "Liquidity check disabled"))

        current = context.liquidity_score
        passed, score = self._apply_profile_threshold(current, min_liquidity, invert=True)
        if not passed:
            return await self._record_result(
                self._make_result(
                    False, score,
                    f"Liquidity score {current:.3f} below minimum {min_liquidity:.2f}",
                    details=f"Current liquidity: {current:.3f}, Minimum: {min_liquidity:.2f}",
                )
            )
        return await self._record_result(
            self._make_result(
                True, score,
                f"Liquidity score {current:.3f} above minimum {min_liquidity:.2f}",
            )
        )


class SlippageProtectionPolicy(BaseRiskPolicy):
    """Ensures slippage estimate is within acceptable range."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="slippage_protection",
            description="Ensures estimated slippage does not exceed configured maximum",
            category=PolicyCategory.MARKET_CONDITIONS,
            severity=PolicySeverity.LOW,
            priority=54,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        max_slip = self._config.max_slippage_pips
        if max_slip <= 0:
            return await self._record_result(self._make_result(True, 100.0, "Slippage check disabled"))

        current = context.slippage_estimate
        passed, score = self._apply_profile_threshold(current, max_slip)
        if not passed:
            return await self._record_result(
                self._make_result(
                    False, score,
                    f"Slippage estimate {current:.2f} pips exceeds {max_slip:.1f} pips limit",
                    details=f"Slippage: {current:.2f}, Max: {max_slip:.1f}",
                )
            )
        return await self._record_result(
            self._make_result(
                True, score,
                f"Slippage {current:.2f} pips within {max_slip:.1f} pips limit",
            )
        )


# ============================================================================
# Category 6: TRADING_HOURS
# ============================================================================


class NewsProtectionPolicy(BaseRiskPolicy):
    """Blocks or restricts trading during high-impact news periods."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="news_protection",
            description="Blocks or restricts trading during high-impact news periods",
            category=PolicyCategory.TRADING_HOURS,
            severity=PolicySeverity.MEDIUM,
            priority=60,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        if context.is_news_hour:
            return await self._record_result(
                self._make_result(
                    False, 30.0,
                    "Trading restricted during high-impact news period",
                    details="High-impact news event in progress. Trading deferred until news impact subsides.",
                )
            )
        return await self._record_result(
            self._make_result(True, 100.0, "No active news events")
        )


class TradingHoursProtectionPolicy(BaseRiskPolicy):
    """Ensures trading only occurs during market hours."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="trading_hours_protection",
            description="Ensures trading only occurs during market open hours",
            category=PolicyCategory.TRADING_HOURS,
            severity=PolicySeverity.MEDIUM,
            priority=61,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        if not context.market_open and self._config.require_market_open:
            return await self._record_result(
                self._make_result(
                    False, 10.0,
                    "Market is closed - trading not allowed",
                    details=f"Symbol: {context.symbol}, Market open: {context.market_open}, "
                            f"Require market open: {self._config.require_market_open}",
                )
            )
        return await self._record_result(
            self._make_result(
                True, 100.0 if context.market_open else 70.0,
                "Market is open" if context.market_open else "Market closed but weekend/holiday trading allowed",
            )
        )


class WeekendProtectionPolicy(BaseRiskPolicy):
    """Blocks trading during weekends unless configured otherwise."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="weekend_protection",
            description="Blocks trading during weekends unless configured otherwise",
            category=PolicyCategory.TRADING_HOURS,
            severity=PolicySeverity.LOW,
            priority=62,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        if not context.is_weekend:
            return await self._record_result(
                self._make_result(True, 100.0, "Not a weekend")
            )

        if self._config.allow_weekend_trading:
            return await self._record_result(
                self._make_result(
                    True, 50.0,
                    "Weekend trading allowed by profile - proceed with caution",
                    details="Weekend trading carries higher risk due to lower liquidity",
                )
            )

        return await self._record_result(
            self._make_result(
                False, 10.0,
                "Weekend trading is not allowed",
                details="Weekend trading blocked by risk profile. Set allow_weekend_trading=True to enable.",
            )
        )


class HolidayProtectionPolicy(BaseRiskPolicy):
    """Blocks trading during holidays unless configured otherwise."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="holiday_protection",
            description="Blocks trading during holidays unless configured otherwise",
            category=PolicyCategory.TRADING_HOURS,
            severity=PolicySeverity.LOW,
            priority=63,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        if not context.is_holiday:
            return await self._record_result(
                self._make_result(True, 100.0, "Not a holiday")
            )

        if self._config.allow_holiday_trading:
            return await self._record_result(
                self._make_result(
                    True, 50.0,
                    "Holiday trading allowed by profile - proceed with caution",
                    details="Holiday trading carries higher risk due to lower liquidity and thinner markets",
                )
            )

        return await self._record_result(
            self._make_result(
                False, 10.0,
                "Holiday trading is not allowed",
                details="Holiday trading blocked by risk profile. Set allow_holiday_trading=True to enable.",
            )
        )


# ============================================================================
# Category 7: ACCOUNT_PROTECTION
# ============================================================================


class SoftStopPolicy(BaseRiskPolicy):
    """Soft stop - warns when loss exceeds threshold, may reduce position sizes."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="soft_stop",
            description="Soft stop protection - warns and may reduce position sizes when loss exceeds threshold",
            category=PolicyCategory.ACCOUNT_PROTECTION,
            severity=PolicySeverity.HIGH,
            priority=70,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        soft_stop = self._config.soft_stop_loss_pct
        if soft_stop <= 0:
            return await self._record_result(self._make_result(True, 100.0, "Soft stop disabled"))

        if context.drawdown is not None:
            current_dd = context.drawdown.current_drawdown
        else:
            current_dd = context.daily_loss_pct

        if current_dd >= soft_stop * 0.8:
            score = max(0.0, 100.0 - (current_dd / soft_stop) * 100.0)
            if current_dd >= soft_stop:
                return await self._record_result(
                    self._make_result(
                        False, score,
                        f"Soft stop triggered at {current_dd:.2f}% loss (threshold: {soft_stop:.1f}%)",
                        details=f"Reducing position sizes. Current loss: {current_dd:.2f}%, Soft stop: {soft_stop:.1f}%",
                    )
                )
            return await self._record_result(
                self._make_result(
                    True, score,
                    f"Approaching soft stop: {current_dd:.2f}% / {soft_stop:.1f}%",
                    details="Warning: loss approaching soft stop threshold",
                )
            )

        return await self._record_result(
            self._make_result(True, 100.0, f"Loss {current_dd:.2f}% well below soft stop {soft_stop:.1f}%")
        )


class HardStopPolicy(BaseRiskPolicy):
    """Hard stop - immediately stops all trading when loss exceeds threshold."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="hard_stop",
            description="Hard stop protection - immediately stops all trading when loss exceeds threshold",
            category=PolicyCategory.ACCOUNT_PROTECTION,
            severity=PolicySeverity.CRITICAL,
            priority=71,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        hard_stop = self._config.hard_stop_loss_pct
        if hard_stop <= 0:
            return await self._record_result(self._make_result(True, 100.0, "Hard stop disabled"))

        if context.drawdown is not None:
            current_dd = context.drawdown.current_drawdown
        else:
            current_dd = context.daily_loss_pct

        if current_dd >= hard_stop:
            score = max(0.0, 100.0 - (current_dd / hard_stop) * 100.0)
            return await self._record_result(
                self._make_result(
                    False, score,
                    f"HARD STOP TRIGGERED at {current_dd:.2f}% loss (limit: {hard_stop:.1f}%)",
                    details=f"All trading stopped. Current loss: {current_dd:.2f}%, Hard stop: {hard_stop:.1f}%. "
                            f"Account protection level: HARD_STOP",
                )
            )

        return await self._record_result(
            self._make_result(True, 100.0, f"Loss {current_dd:.2f}% within hard stop {hard_stop:.1f}%")
        )


class TradingLockPolicy(BaseRiskPolicy):
    """Locks trading when certain conditions are met (e.g., margin call, hard stop)."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="trading_lock",
            description="Locks trading when critical conditions are met",
            category=PolicyCategory.ACCOUNT_PROTECTION,
            severity=PolicySeverity.CRITICAL,
            priority=72,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        if context.is_trading_locked:
            return await self._record_result(
                self._make_result(
                    False, 0.0,
                    "Trading is locked - no new trades allowed",
                    details="Account is in locked state. Check protection status for details.",
                )
            )
        return await self._record_result(
            self._make_result(True, 100.0, "Trading is not locked")
        )


class CooldownTimerPolicy(BaseRiskPolicy):
    """Enforces a cooldown period after consecutive losses."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="cooldown_timer",
            description="Enforces a cooldown period after losses or high-risk events",
            category=PolicyCategory.ACCOUNT_PROTECTION,
            severity=PolicySeverity.MEDIUM,
            priority=73,
        )
        self._config = config or RiskProfileConfig()
        self._cooldown_end: datetime | None = None

    async def initialize(self) -> None:
        await super().initialize()
        self._cooldown_end = None

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        cooldown_minutes = self._config.cooldown_after_loss_minutes
        if cooldown_minutes <= 0:
            return await self._record_result(self._make_result(True, 100.0, "Cooldown disabled"))

        # Check if in cooldown
        now = datetime.now(timezone.utc)

        if self._cooldown_end and now < self._cooldown_end:
            remaining = (self._cooldown_end - now).total_seconds()
            return await self._record_result(
                self._make_result(
                    False, 10.0,
                    f"Cooldown active - {remaining:.0f}s remaining",
                    details=f"Cooldown until {self._cooldown_end.isoformat()}, "
                            f"remaining: {remaining:.0f}s",
                )
            )

        # Trigger cooldown if consecutive losses reached threshold
        if context.consecutive_losses >= self._config.max_consecutive_losses:
            self._cooldown_end = now.replace(tzinfo=timezone.utc) + __import__(
                "datetime"
            ).timedelta(minutes=cooldown_minutes)
            return await self._record_result(
                self._make_result(
                    False, 20.0,
                    f"Cooldown triggered after {context.consecutive_losses} consecutive losses",
                    details=f"Cooldown for {cooldown_minutes:.0f} minutes until {self._cooldown_end.isoformat()}",
                )
            )

        return await self._record_result(
            self._make_result(True, 100.0, "No cooldown active")
        )


class RecoveryModePolicy(BaseRiskPolicy):
    """Manages recovery mode after significant losses."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="recovery_mode",
            description="Manages recovery mode after significant losses - reduces position sizes",
            category=PolicyCategory.ACCOUNT_PROTECTION,
            severity=PolicySeverity.HIGH,
            priority=74,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        if not context.drawdown:
            return await self._record_result(self._make_result(True, 100.0, "No drawdown data"))

        is_recovery = context.drawdown.is_recovery_mode
        current_dd = context.drawdown.current_drawdown
        max_dd = context.drawdown.max_drawdown

        if is_recovery:
            score = max(0.0, 50.0 - current_dd)
            return await self._record_result(
                self._make_result(
                    True, score,
                    "Recovery mode active - reduced position sizes",
                    details=f"Current DD: {current_dd:.2f}%, Max DD: {max_dd:.2f}%. "
                            f"Trading with reduced risk until recovery.",
                )
            )

        # Check if we should enter recovery mode
        if current_dd >= self._config.max_drawdown_pct * 0.7:
            score = 100.0 - (current_dd / self._config.max_drawdown_pct) * 50.0
            return await self._record_result(
                self._make_result(
                    True, max(0.0, score),
                    "Approaching recovery mode trigger level",
                    details=f"Current DD: {current_dd:.2f}%, Recovery trigger: {self._config.max_drawdown_pct * 0.7:.1f}%",
                )
            )

        return await self._record_result(
            self._make_result(True, 100.0, "Drawdown within normal range")
        )


# ============================================================================
# Category 8: SYSTEM_HEALTH
# ============================================================================


class BrokerHealthProtectionPolicy(BaseRiskPolicy):
    """Ensures broker connection is healthy before allowing trades."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="broker_health_protection",
            description="Ensures broker connection is healthy before allowing trades",
            category=PolicyCategory.SYSTEM_HEALTH,
            severity=PolicySeverity.CRITICAL,
            priority=80,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        if not context.broker_connected:
            return await self._record_result(
                self._make_result(
                    False, 0.0,
                    "Broker is disconnected - trading not allowed",
                    details="No broker connection available. Cannot execute trades.",
                )
            )

        if context.broker_latency_ms > 1000:
            return await self._record_result(
                self._make_result(
                    False, 30.0,
                    f"Broker latency too high: {context.broker_latency_ms:.0f}ms",
                    details=f"Latency: {context.broker_latency_ms:.0f}ms, Maximum recommended: 1000ms",
                )
            )

        if context.broker_uptime_pct < 95.0:
            return await self._record_result(
                self._make_result(
                    True, 50.0,
                    f"Broker uptime {context.broker_uptime_pct:.1f}% below 95% threshold",
                    details="Broker reliability is concerning but connection is active",
                )
            )

        return await self._record_result(
            self._make_result(
                True, 100.0,
                f"Broker healthy (latency: {context.broker_latency_ms:.0f}ms, uptime: {context.broker_uptime_pct:.1f}%)"
            )
        )


class MarketDataQualityProtectionPolicy(BaseRiskPolicy):
    """Ensures market data quality is sufficient for trading."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="market_data_quality_protection",
            description="Ensures market data quality is sufficient for trading",
            category=PolicyCategory.SYSTEM_HEALTH,
            severity=PolicySeverity.HIGH,
            priority=81,
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        if not context.data_feed_active:
            return await self._record_result(
                self._make_result(
                    False, 0.0,
                    "Market data feed is not active",
                    details="Cannot evaluate market conditions without active data feed.",
                )
            )

        issues = []
        score = 100.0

        if context.consensus_quality < 0.5:
            issues.append(f"Low consensus quality: {context.consensus_quality:.2f}")
            score -= 30.0

        if context.provider_health < 0.5:
            issues.append(f"Low provider health: {context.provider_health:.2f}")
            score -= 20.0

        if context.liquidity_score < 0.2:
            issues.append(f"Very low liquidity: {context.liquidity_score:.2f}")
            score -= 30.0

        if issues:
            return await self._record_result(
                self._make_result(
                    score >= 50.0, max(0.0, score),
                    "Market data quality issues detected",
                    details="; ".join(issues),
                )
            )

        return await self._record_result(
            self._make_result(
                True, 100.0,
                f"Market data quality good (consensus: {context.consensus_quality:.2f}, "
                f"provider health: {context.provider_health:.2f})"
            )
        )


class EmergencyStopPolicy(BaseRiskPolicy):
    """Emergency stop - immediately blocks all trading when activated."""

    def __init__(self, config: RiskProfileConfig | None = None) -> None:
        super().__init__(
            name="emergency_stop",
            description="Emergency stop - immediately blocks all trading when emergency mode is active",
            category=PolicyCategory.EMERGENCY,
            severity=PolicySeverity.CRITICAL,
            priority=5,  # Very high priority - runs early
        )
        self._config = config or RiskProfileConfig()

    async def evaluate(self, context: RiskContext) -> PolicyResult:
        if context.is_emergency:
            triggers = []
            if context.emergency_status:
                triggers = [t.value for t in context.emergency_status.triggers]
            trigger_str = ", ".join(triggers) if triggers else "Unknown trigger"

            return await self._record_result(
                self._make_result(
                    False, 0.0,
                    f"EMERGENCY STOP ACTIVE - all trading blocked",
                    details=f"Emergency triggers: {trigger_str}. "
                            f"All trading is suspended until emergency is resolved.",
                    metadata={"emergency_triggers": triggers},
                )
            )

        return await self._record_result(
            self._make_result(True, 100.0, "No emergency mode active")
        )


# ============================================================================
# Policy Factory
# ============================================================================


def create_default_policies(config: RiskProfileConfig | None = None) -> list[BaseRiskPolicy]:
    """Create a list of all 24 default risk policies with the given config.

    Args:
        config: RiskProfileConfig to use for thresholds. If None, uses balanced defaults.

    Returns:
        List of all policy instances ready for registration.
    """
    cfg = config or RiskProfileConfig()
    return [
        # Position Sizing (1)
        MaximumPositionSizePolicy(cfg),
        # Loss Limits (5)
        MaximumDailyLossPolicy(cfg),
        MaximumWeeklyLossPolicy(cfg),
        MaximumMonthlyLossPolicy(cfg),
        MaximumDrawdownPolicy(cfg),
        MaximumConsecutiveLossesPolicy(cfg),
        # Exposure (3)
        MaximumExposurePolicy(cfg),
        MaximumSymbolExposurePolicy(cfg),
        MaximumCurrencyExposurePolicy(cfg),
        # Leverage (2)
        MaximumLeveragePolicy(cfg),
        MaximumOpenPositionsPolicy(cfg),
        # Market Conditions (5)
        MarginProtectionPolicy(cfg),
        SpreadProtectionPolicy(cfg),
        VolatilityProtectionPolicy(cfg),
        LiquidityProtectionPolicy(cfg),
        SlippageProtectionPolicy(cfg),
        # Trading Hours (4)
        NewsProtectionPolicy(cfg),
        TradingHoursProtectionPolicy(cfg),
        WeekendProtectionPolicy(cfg),
        HolidayProtectionPolicy(cfg),
        # Account Protection (5)
        SoftStopPolicy(cfg),
        HardStopPolicy(cfg),
        TradingLockPolicy(cfg),
        CooldownTimerPolicy(cfg),
        RecoveryModePolicy(cfg),
        # System Health (2)
        BrokerHealthProtectionPolicy(cfg),
        MarketDataQualityProtectionPolicy(cfg),
        # Emergency (1)
        EmergencyStopPolicy(cfg),
    ]


# Map policy names to their classes for dynamic instantiation
POLICY_CLASS_MAP: dict[str, type[BaseRiskPolicy]] = {
    "maximum_position_size": MaximumPositionSizePolicy,
    "maximum_daily_loss": MaximumDailyLossPolicy,
    "maximum_weekly_loss": MaximumWeeklyLossPolicy,
    "maximum_monthly_loss": MaximumMonthlyLossPolicy,
    "maximum_drawdown": MaximumDrawdownPolicy,
    "maximum_consecutive_losses": MaximumConsecutiveLossesPolicy,
    "maximum_exposure": MaximumExposurePolicy,
    "maximum_symbol_exposure": MaximumSymbolExposurePolicy,
    "maximum_currency_exposure": MaximumCurrencyExposurePolicy,
    "maximum_leverage": MaximumLeveragePolicy,
    "maximum_open_positions": MaximumOpenPositionsPolicy,
    "margin_protection": MarginProtectionPolicy,
    "spread_protection": SpreadProtectionPolicy,
    "volatility_protection": VolatilityProtectionPolicy,
    "liquidity_protection": LiquidityProtectionPolicy,
    "slippage_protection": SlippageProtectionPolicy,
    "news_protection": NewsProtectionPolicy,
    "trading_hours_protection": TradingHoursProtectionPolicy,
    "weekend_protection": WeekendProtectionPolicy,
    "holiday_protection": HolidayProtectionPolicy,
    "soft_stop": SoftStopPolicy,
    "hard_stop": HardStopPolicy,
    "trading_lock": TradingLockPolicy,
    "cooldown_timer": CooldownTimerPolicy,
    "recovery_mode": RecoveryModePolicy,
    "broker_health_protection": BrokerHealthProtectionPolicy,
    "market_data_quality_protection": MarketDataQualityProtectionPolicy,
    "emergency_stop": EmergencyStopPolicy,
}

