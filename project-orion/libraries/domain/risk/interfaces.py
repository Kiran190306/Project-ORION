"""Protocol/port definitions for the Risk Management Engine.

Defines:
- RiskPolicy protocol (all policies must implement this)
- RiskEnginePort for the engine's public API
- RiskManagerPort for the manager's public API
- PortfolioDataPort for Portfolio Engine integration
- AccountDataPort for account information
- MarketDataPort for market data access
- BrokerHealthPort for broker connectivity
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from libraries.domain.risk.models import (
    AccountProtectionLevel,
    AccountProtectionStatus,
    EmergencyModeStatus,
    EmergencyTrigger,
    PolicyCategory,
    PolicyResult,
    PolicySeverity,
    PositionSizingMethod,
    RiskProfileType,
    RiskResult,
)

# ─── RiskPolicy Protocol ──────────────────────────────────────────────────


@runtime_checkable
class RiskPolicy(Protocol):
    """Protocol that every risk policy must implement.

    Policies are stateless evaluators. State is managed by the
    RiskManager and RiskEngine.
    """

    @property
    def name(self) -> str:
        """Unique policy name."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description of what this policy checks."""
        ...

    @property
    def category(self) -> PolicyCategory:
        """Logical category for grouping."""
        ...

    @property
    def severity(self) -> PolicySeverity:
        """Severity level for policy chaining priority."""
        ...

    @property
    def enabled(self) -> bool:
        """Whether this policy is currently enabled."""
        ...

    @property
    def priority(self) -> int:
        """Execution priority (lower = executed first)."""
        ...

    async def evaluate(self, context: Any) -> PolicyResult:
        """Evaluate the policy against the given risk context.

        Args:
            context: RiskContext containing all evaluation inputs.

        Returns:
            PolicyResult with pass/fail, score, and explanation.
        """
        ...

    async def statistics(self) -> dict[str, Any]:
        """Return current statistics for this policy.

        Returns:
            Dict with stats like evaluation_count, pass_count,
            fail_count, avg_score, etc.
        """
        ...

    async def initialize(self) -> None:
        """Initialize the policy (load config, set up state)."""
        ...

    async def dispose(self) -> None:
        """Clean up resources when policy is removed."""
        ...


# ─── Engine Ports ─────────────────────────────────────────────────────────


@runtime_checkable
class RiskEnginePort(Protocol):
    """Public API of the RiskEngine."""

    async def evaluate(self, decision: Any) -> RiskResult:
        """Evaluate a TradeDecision against all enabled risk policies.

        Args:
            decision: TradeDecision from the DecisionEngine.

        Returns:
            RiskResult with final decision and detailed breakdown.
        """
        ...

    async def health_check(self) -> dict[str, Any]:
        """Return health status of the risk engine."""
        ...


@runtime_checkable
class RiskManagerPort(Protocol):
    """Public API of the RiskManager."""

    async def start(self) -> None:
        """Start the risk manager."""
        ...

    async def stop(self) -> None:
        """Stop the risk manager."""
        ...

    async def is_emergency_mode(self) -> bool:
        """Return whether emergency mode is active."""
        ...

    async def get_protection_status(self) -> AccountProtectionStatus:
        """Return current account protection status."""
        ...

    async def get_emergency_status(self) -> EmergencyModeStatus:
        """Return current emergency mode status."""
        ...


# ─── Data Ports ───────────────────────────────────────────────────────────


@runtime_checkable
class PortfolioDataPort(Protocol):
    """Port for querying portfolio-level data.

    Designed for future Portfolio Engine integration.
    """

    async def get_portfolio_heat(self) -> float:
        """Return current portfolio heat (0–100)."""
        ...

    async def get_net_exposure(self) -> float:
        """Return net exposure as % of account."""
        ...

    async def get_long_exposure(self) -> float:
        """Return long exposure as % of account."""
        ...

    async def get_short_exposure(self) -> float:
        """Return short exposure as % of account."""
        ...

    async def get_currency_exposure(self, currency: str) -> float:
        """Return exposure to a specific currency as % of account."""
        ...

    async def get_correlation_matrix(self) -> dict[str, dict[str, float]]:
        """Return correlation matrix of current positions."""
        ...

    async def get_sector_exposure(self, sector: str) -> float:
        """Return exposure to a sector as % of account (future-ready)."""
        ...


@runtime_checkable
class AccountDataPort(Protocol):
    """Port for querying account-level data."""

    async def get_balance(self) -> float:
        """Return current account balance."""
        ...

    async def get_equity(self) -> float:
        """Return current account equity."""
        ...

    async def get_margin_used(self) -> float:
        """Return currently used margin."""
        ...

    async def get_margin_free(self) -> float:
        """Return free margin."""
        ...

    async def get_leverage(self) -> float:
        """Return current leverage ratio."""
        ...

    async def get_daily_pnl(self) -> float:
        """Return today's profit/loss."""
        ...

    async def get_weekly_pnl(self) -> float:
        """Return this week's profit/loss."""
        ...

    async def get_monthly_pnl(self) -> float:
        """Return this month's profit/loss."""
        ...

    async def get_consecutive_losses(self) -> int:
        """Return number of consecutive losing trades."""
        ...

    async def get_drawdown(self) -> float:
        """Return current drawdown as % from peak."""
        ...

    async def get_max_drawdown(self) -> float:
        """Return historical maximum drawdown."""
        ...


@runtime_checkable
class MarketDataPort(Protocol):
    """Port for querying market data relevant to risk evaluation."""

    async def get_spread(self, symbol: str) -> float:
        """Return current spread in pips."""
        ...

    async def get_volatility(self, symbol: str) -> float:
        """Return current volatility measure."""
        ...

    async def get_liquidity(self, symbol: str) -> float:
        """Return liquidity score (0–1)."""
        ...

    async def get_slippage(self, symbol: str) -> float:
        """Return estimated slippage in pips."""
        ...

    async def is_market_open(self, symbol: str) -> bool:
        """Return whether the market is currently open."""
        ...

    async def is_news_hour(self) -> bool:
        """Return whether we are in a high-impact news period."""
        ...


@runtime_checkable
class BrokerHealthPort(Protocol):
    """Port for querying broker connectivity health."""

    async def is_connected(self) -> bool:
        """Return whether the broker is connected."""
        ...

    async def get_latency_ms(self) -> float:
        """Return current connection latency in ms."""
        ...

    async def get_uptime_percent(self) -> float:
        """Return broker uptime percentage."""
        ...

    async def is_data_feed_active(self) -> bool:
        """Return whether the market data feed is active."""
        ...


@runtime_checkable
class MarketIntelligencePort(Protocol):
    """Port for querying market intelligence data.

    Integration point with EPIC-005 Sprint-4 Market Intelligence Engine.
    """

    async def get_consensus_quality(self, symbol: str) -> float:
        """Return consensus quality score (0–1)."""
        ...

    async def get_provider_health(self, symbol: str) -> float:
        """Return aggregated provider health score (0–1)."""
        ...

    async def get_liquidity_score(self, symbol: str) -> float:
        """Return liquidity score (0–1)."""
        ...

    async def get_spread_analysis(self, symbol: str) -> dict[str, Any]:
        """Return detailed spread analysis."""
        ...


# ─── Emergency Handler Port ───────────────────────────────────────────────


@runtime_checkable
class EmergencyHandlerPort(Protocol):
    """Port for handling emergency mode activation.

    Designed for future Execution Engine integration.
    """

    async def on_emergency_activated(self, trigger: EmergencyTrigger, details: str) -> None:
        """Called when emergency mode is activated.

        Args:
            trigger: What triggered the emergency.
            details: Human-readable explanation.
        """
        ...

    async def on_emergency_resolved(self) -> None:
        """Called when emergency mode is resolved."""
        ...

    async def on_trading_lock(self, reason: str, duration_seconds: float) -> None:
        """Called when trading is locked.

        Args:
            reason: Why trading was locked.
            duration_seconds: Lock duration.
        """
        ...


# ─── Risk Profile Port ────────────────────────────────────────────────────


@runtime_checkable
class RiskProfilePort(Protocol):
    """Port for managing risk profiles."""

    async def get_profile(self, profile_type: RiskProfileType) -> dict[str, Any]:
        """Return configuration for a risk profile."""
        ...

    async def apply_profile(self, profile_type: RiskProfileType) -> None:
        """Apply a risk profile to the engine.

        Args:
            profile_type: Profile to apply.
        """
        ...

    async def customize_profile(
        self,
        base: RiskProfileType,
        overrides: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a custom profile from a base profile with overrides.

        Args:
            base: Base profile type.
            overrides: Config overrides.

        Returns:
            The resulting profile configuration.
        """
        ...
