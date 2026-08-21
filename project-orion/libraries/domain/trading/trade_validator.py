"""Trade validator for the Trading Decision Engine.

Final validation gate that combines spread, risk, confidence, market
quality, liquidity, and provider health checks before a trade is approved.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone

from libraries.domain.trading.decision_result import TradeDecision
from libraries.domain.trading.models import TradingSignal


@dataclass(frozen=True, slots=True)
class TradeValidationReport:
    """Comprehensive validation report for a trade decision."""

    valid: bool
    spread_check: tuple[bool, str] = (True, "")
    risk_check: tuple[bool, str] = (True, "")
    confidence_check: tuple[bool, str] = (True, "")
    market_quality_check: tuple[bool, str] = (True, "")
    liquidity_check: tuple[bool, str] = (True, "")
    provider_health_check: tuple[bool, str] = (True, "")
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    validated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_valid(self) -> bool:
        return self.valid


class TradeValidator:
    """Final validation gate before trade execution.

    Thread-safe via asyncio.Lock.
    """

    def __init__(
        self,
        max_spread_pips: float = 5.0,
        min_confidence: float = 30.0,
        min_liquidity: float = 0.3,
        min_market_quality: float = 0.3,
        min_provider_health: float = 0.4,
    ) -> None:
        if max_spread_pips <= 0:
            raise ValueError("max_spread_pips must be positive")
        if not 0 <= min_confidence <= 100:
            raise ValueError("min_confidence must be between 0 and 100")
        if not 0 <= min_liquidity <= 1:
            raise ValueError("min_liquidity must be between 0 and 1")

        self._max_spread_pips = max_spread_pips
        self._min_confidence = min_confidence
        self._min_liquidity = min_liquidity
        self._min_market_quality = min_market_quality
        self._min_provider_health = min_provider_health
        self._lock = asyncio.Lock()

    async def validate(
        self,
        signal: TradingSignal,
        decision: TradeDecision,
        spread_pips: float = 0.0,
        liquidity_score: float = 0.5,
        market_quality: float = 0.5,
        provider_health: float = 0.7,
    ) -> TradeValidationReport:
        """Validate a trade decision for execution.

        Args:
            signal: The original trading signal.
            decision: The proposed trade decision.
            spread_pips: Current spread in pips.
            liquidity_score: 0.0-1.0 liquidity score.
            market_quality: 0.0-1.0 market quality score.
            provider_health: 0.0-1.0 provider health score.

        Returns:
            TradeValidationReport with all check results.
        """
        async with self._lock:
            errors: list[str] = []
            warnings: list[str] = []

            # Spread check
            spread_ok = spread_pips <= self._max_spread_pips
            spread_reason = ""
            if not spread_ok:
                spread_reason = (
                    f"Spread {spread_pips:.1f}pips exceeds max {self._max_spread_pips}pips"
                )
                errors.append(spread_reason)

            # Confidence check
            confidence_ok = decision.confidence >= self._min_confidence
            confidence_reason = ""
            if not confidence_ok:
                confidence_reason = (
                    f"Confidence {decision.confidence:.1f} below min {self._min_confidence}"
                )
                errors.append(confidence_reason)

            # Liquidity check
            liquidity_ok = liquidity_score >= self._min_liquidity
            liquidity_reason = ""
            if not liquidity_ok:
                liquidity_reason = (
                    f"Liquidity {liquidity_score:.2f} below min {self._min_liquidity:.2f}"
                )
                errors.append(liquidity_reason)

            # Market quality check
            market_quality_ok = market_quality >= self._min_market_quality
            market_quality_reason = ""
            if not market_quality_ok:
                market_quality_reason = (
                    f"Market quality {market_quality:.2f} below min {self._min_market_quality:.2f}"
                )
                errors.append(market_quality_reason)

            # Provider health check
            provider_health_ok = provider_health >= self._min_provider_health
            provider_health_reason = ""
            if not provider_health_ok:
                provider_health_reason = f"Provider health {provider_health:.2f} below min {self._min_provider_health:.2f}"
                errors.append(provider_health_reason)

            # Risk check
            risk_ok = decision.account_risk_pct <= 5.0  # Max 5% account risk
            risk_reason = ""
            if not risk_ok:
                risk_reason = f"Account risk {decision.account_risk_pct:.2f}% exceeds 5%"
                warnings.append(risk_reason)

            # Add reject reasons from decision
            errors.extend(decision.reject_reasons)

            return TradeValidationReport(
                valid=not bool(errors),
                spread_check=(spread_ok, spread_reason),
                risk_check=(risk_ok, risk_reason),
                confidence_check=(confidence_ok, confidence_reason),
                market_quality_check=(market_quality_ok, market_quality_reason),
                liquidity_check=(liquidity_ok, liquidity_reason),
                provider_health_check=(provider_health_ok, provider_health_reason),
                errors=errors,
                warnings=warnings,
            )
