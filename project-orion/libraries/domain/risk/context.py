"""Risk Context - aggregates all inputs for risk policy evaluation.

The RiskContext is an immutable snapshot of all data needed to evaluate
risk policies. It is constructed once per RiskEngine.evaluate() call and
passed to every enabled policy.

Designed for Portfolio Engine integration - accepts portfolio data ports
for future extensibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.risk.models import (
    AccountProtectionStatus,
    DrawdownMetrics,
    EmergencyModeStatus,
    PortfolioRisk,
    PositionRisk,
    RiskProfileType,
)


@dataclass(frozen=True, slots=True)
class RiskContext:
    """Complete context for risk evaluation.

    All fields are read-only. Constructed by the RiskManager or
    RiskEngine before evaluating policies.
    """

    # ─── Trade Decision Input ──────────────────────────────────
    symbol: str = ""
    direction: str = ""  # buy / sell
    entry_price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    position_size: Decimal | None = None
    notional_value: Decimal | None = None
    confidence: float = 0.0
    strategy: str = ""
    signal_strength: str = ""

    # ─── Account Data ──────────────────────────────────────────
    account_balance: Decimal = Decimal(0)
    account_equity: Decimal = Decimal(0)
    margin_used: Decimal = Decimal(0)
    margin_free: Decimal = Decimal(0)
    leverage: float = 1.0
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    monthly_pnl: float = 0.0
    consecutive_losses: int = 0

    # ─── Drawdown ──────────────────────────────────────────────
    drawdown: DrawdownMetrics | None = None

    # ─── Position Data ─────────────────────────────────────────
    current_positions: tuple[PositionRisk, ...] = ()
    open_positions_count: int = 0
    symbol_position_size: Decimal | None = None  # current size for this symbol

    # ─── Portfolio Data ────────────────────────────────────────
    portfolio_risk: PortfolioRisk | None = None

    # ─── Market Data ───────────────────────────────────────────
    spread_pips: float = 0.0
    volatility: float = 0.0
    liquidity_score: float = 1.0
    slippage_estimate: float = 0.0
    market_open: bool = True
    is_news_hour: bool = False
    is_weekend: bool = False
    is_holiday: bool = False

    # ─── Broker Health ─────────────────────────────────────────
    broker_connected: bool = True
    broker_latency_ms: float = 0.0
    broker_uptime_pct: float = 100.0
    data_feed_active: bool = True

    # ─── Market Intelligence ───────────────────────────────────
    consensus_quality: float = 1.0
    provider_health: float = 1.0

    # ─── Account Protection ────────────────────────────────────
    protection_status: AccountProtectionStatus | None = None
    emergency_status: EmergencyModeStatus | None = None

    # ─── Risk Profile ──────────────────────────────────────────
    risk_profile: RiskProfileType = RiskProfileType.BALANCED
    profile_config: dict[str, Any] = field(default_factory=dict)

    # ─── Metadata ─────────────────────────────────────────────
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    # ─── Computed Properties ───────────────────────────────────

    @property
    def margin_level_pct(self) -> float:
        """Return margin level as percentage (equity / margin * 100)."""
        if self.margin_used > 0:
            return float(self.account_equity / self.margin_used * 100)
        return float("inf")

    @property
    def is_margin_call_risk(self) -> bool:
        """Return whether margin level indicates margin call risk."""
        return self.margin_level_pct < 100.0

    @property
    def account_risk_pct(self) -> float:
        """Return the percentage of account at risk on this trade."""
        if self.account_balance > 0 and self.stop_loss and self.entry_price and self.position_size:
            risk_per_unit = abs(self.entry_price - self.stop_loss)
            risk_amount = risk_per_unit * self.position_size
            return float(risk_amount / self.account_balance * 100)
        return 0.0

    @property
    def daily_loss_pct(self) -> float:
        """Return daily loss as percentage of account balance."""
        if self.account_balance > 0 and self.daily_pnl < 0:
            return abs(self.daily_pnl) / float(self.account_balance) * 100
        return 0.0

    @property
    def weekly_loss_pct(self) -> float:
        """Return weekly loss as percentage of account balance."""
        if self.account_balance > 0 and self.weekly_pnl < 0:
            return abs(self.weekly_pnl) / float(self.account_balance) * 100
        return 0.0

    @property
    def monthly_loss_pct(self) -> float:
        """Return monthly loss as percentage of account balance."""
        if self.account_balance > 0 and self.monthly_pnl < 0:
            return abs(self.monthly_pnl) / float(self.account_balance) * 100
        return 0.0

    @property
    def is_emergency(self) -> bool:
        """Return whether emergency mode is active."""
        if self.emergency_status is not None:
            return self.emergency_status.active
        return False

    @property
    def is_trading_locked(self) -> bool:
        """Return whether trading is currently locked."""
        if self.protection_status is not None:
            return not self.protection_status.can_trade
        return False

    @property
    def check_summary(self) -> dict[str, Any]:
        """Return a summary dict of key risk indicators."""
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "account_balance": float(self.account_balance),
            "daily_pnl": self.daily_pnl,
            "consecutive_losses": self.consecutive_losses,
            "open_positions": self.open_positions_count,
            "margin_level_pct": self.margin_level_pct,
            "spread_pips": self.spread_pips,
            "volatility": self.volatility,
            "liquidity_score": self.liquidity_score,
            "market_open": self.market_open,
            "is_news_hour": self.is_news_hour,
            "broker_connected": self.broker_connected,
            "data_feed_active": self.data_feed_active,
            "risk_profile": self.risk_profile.value,
            "is_emergency": self.is_emergency,
            "is_trading_locked": self.is_trading_locked,
        }
