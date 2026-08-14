"""Risk Manager - orchestrates policy lifecycle, profile management,
emergency mode, and account protection.

Central coordination point for the Risk Management Engine.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Any

from libraries.domain.risk.context import RiskContext
from libraries.domain.risk.engine import RiskEngine
from libraries.domain.risk.evaluator import RiskEvaluator
from libraries.domain.risk.exceptions import EngineNotReadyError, ProfileNotFoundError
from libraries.domain.risk.interfaces import (
    AccountDataPort,
    BrokerHealthPort,
    EmergencyHandlerPort,
    MarketDataPort,
    MarketIntelligencePort,
    PortfolioDataPort,
    RiskPolicy,
)
from libraries.domain.risk.models import (
    AccountProtectionLevel,
    AccountProtectionStatus,
    EmergencyModeStatus,
    EmergencyTrigger,
    RiskDecision,
    RiskProfileType,
    RiskResult,
)
from libraries.domain.risk.policy import BaseRiskPolicy, create_default_policies
from libraries.domain.risk.profile import RiskProfileConfig, RiskProfileManager
from libraries.domain.risk.registry import RiskPolicyRegistry
from libraries.domain.risk.statistics import RiskStatistics
from libraries.domain.risk.validator import RiskValidator

HEALTH_CHECK_ERRORS = (
    ArithmeticError,
    AttributeError,
    KeyError,
    LookupError,
    RuntimeError,
    TypeError,
    ValueError,
)


@dataclass(frozen=True, slots=True)
class RiskManagerConfig:
    """Configuration for the RiskManager."""

    health_check_interval_seconds: float = 60.0
    emergency_auto_resolve_seconds: float = 300.0
    track_statistics: bool = True
    enable_default_policies: bool = True
    default_profile: RiskProfileType = RiskProfileType.BALANCED
    cooldown_default_minutes: float = 15.0
    max_cooldown_minutes: float = 1440.0  # 24 hours


class RiskManager:
    """Orchestrates risk evaluation lifecycle.

    Responsible for:
    - Starting/stopping the risk engine
    - Managing policy registration and profiles
    - Emergency mode detection and handling
    - Account protection monitoring
    - Health checks
    """

    def __init__(
        self,
        registry: RiskPolicyRegistry | None = None,
        engine: RiskEngine | None = None,
        evaluator: RiskEvaluator | None = None,
        validator: RiskValidator | None = None,
        statistics: RiskStatistics | None = None,
        profile_manager: RiskProfileManager | None = None,
        config: RiskManagerConfig | None = None,
        portfolio_port: PortfolioDataPort | None = None,
        account_port: AccountDataPort | None = None,
        market_port: MarketDataPort | None = None,
        broker_port: BrokerHealthPort | None = None,
        intelligence_port: MarketIntelligencePort | None = None,
        emergency_handler: EmergencyHandlerPort | None = None,
        track_statistics: bool | None = None,
    ) -> None:
        self._registry = registry or RiskPolicyRegistry()
        self._evaluator = evaluator or RiskEvaluator()
        self._validator = validator or RiskValidator()
        self._statistics = statistics or RiskStatistics()
        self._profile_manager = profile_manager or RiskProfileManager()
        self._config = config or RiskManagerConfig()
        if track_statistics is not None:
            self._config = replace(self._config, track_statistics=track_statistics)

        # External ports
        self._portfolio_port = portfolio_port
        self._account_port = account_port
        self._market_port = market_port
        self._broker_port = broker_port
        self._intelligence_port = intelligence_port
        self._emergency_handler = emergency_handler

        # Engine
        self._engine = engine

        # State
        self._lock = asyncio.Lock()
        self._running = False
        self._initialized = False

        # Emergency mode
        self._emergency_status = EmergencyModeStatus()
        self._protection_status = AccountProtectionStatus()

        # Profile
        self._active_profile: RiskProfileType = self._config.default_profile
        self._active_profile_config: RiskProfileConfig = RiskProfileConfig()

        # Health monitoring
        self._health_task: asyncio.Task[None] | None = None

    @property
    def running(self) -> bool:
        return self._running

    @property
    def registry(self) -> RiskPolicyRegistry:
        return self._registry

    @property
    def engine(self) -> RiskEngine | None:
        return self._engine

    @property
    def statistics(self) -> RiskStatistics:
        return self._statistics

    @property
    def profile_manager(self) -> RiskProfileManager:
        return self._profile_manager

    @property
    def active_profile(self) -> RiskProfileType:
        return self._active_profile

    @property
    def active_profile_config(self) -> RiskProfileConfig:
        return self._active_profile_config

    # ─── Lifecycle ────────────────────────────────────────────

    async def start(self) -> None:
        """Start the risk manager.

        Initializes the engine, registers default policies, applies
        the default profile, and starts health monitoring.
        """
        async with self._lock:
            if self._running:
                return

        # Initialize engine
        if self._engine is None:
            self._engine = RiskEngine(
                registry=self._registry,
                evaluator=self._evaluator,
                validator=self._validator,
                statistics=self._statistics if self._config.track_statistics else None,
            )
            await self._engine.initialize()

        # Register default policies
        if self._config.enable_default_policies:
            await self._apply_default_profile()

        async with self._lock:
            self._running = True
            self._initialized = True

        # Start health monitoring
        self._health_task = asyncio.create_task(self._health_loop())

    async def stop(self) -> None:
        """Stop the risk manager and clean up resources."""
        async with self._lock:
            if not self._running:
                return
            self._running = False

        if self._health_task is not None:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
            self._health_task = None

        if self._engine is not None:
            await self._engine.shutdown()

    async def initialize_engine(self) -> None:
        """Initialize the engine if not already done."""
        if self._engine is not None:
            await self._engine.initialize()

    # ─── Profile Management ───────────────────────────────────

    async def set_profile(self, profile_type: RiskProfileType | str) -> None:
        """Set the active risk profile.

        Args:
            profile_type: Profile type to activate.
        """
        config = await self._profile_manager.get_profile(profile_type)
        profile_name = (
            profile_type.value if isinstance(profile_type, RiskProfileType) else profile_type
        )

        # Find the matching RiskProfileType
        profile_enum = RiskProfileType.CUSTOM
        for pt in RiskProfileType:
            if pt.value == profile_name:
                profile_enum = pt
                break

        async with self._lock:
            self._active_profile = profile_enum
            self._active_profile_config = config

        # Apply profile config to all policies
        if self._engine is not None:
            # Re-register policies with new config
            self._registry = RiskPolicyRegistry()
            policies = create_default_policies(config)
            for policy in policies:
                await self._registry.register(policy)

            # Re-initialize engine
            self._engine = RiskEngine(
                registry=self._registry,
                evaluator=self._evaluator,
                validator=self._validator,
                statistics=self._statistics if self._config.track_statistics else None,
            )
            await self._engine.initialize()

    async def get_profile_config(self) -> RiskProfileConfig:
        """Get the active profile configuration.

        Returns:
            Current active profile config.
        """
        async with self._lock:
            return self._active_profile_config

    async def customize_and_apply(
        self,
        base: RiskProfileType,
        overrides: dict[str, Any],
        profile_name: str | None = None,
    ) -> RiskProfileConfig:
        """Create and apply a custom profile.

        Args:
            base: Base profile.
            overrides: Config overrides.
            profile_name: Optional custom name.

        Returns:
            The customized config.
        """
        config = await self._profile_manager.customize_profile(base, overrides, profile_name)
        await self.set_profile(RiskProfileType.CUSTOM)
        return config

    # ─── Emergency Mode ───────────────────────────────────────

    async def activate_emergency(
        self,
        trigger: EmergencyTrigger,
        details: str = "",
    ) -> None:
        """Activate emergency mode.

        Args:
            trigger: What triggered the emergency.
            details: Explanation.
        """
        async with self._lock:
            now = datetime.now(timezone.utc)
            triggers = list(self._emergency_status.triggers)
            if trigger not in triggers:
                triggers.append(trigger)

            self._emergency_status = EmergencyModeStatus(
                active=True,
                triggers=tuple(triggers),
                activated_at=self._emergency_status.activated_at or now,
                auto_resolve=True,
                auto_resolve_after_seconds=self._config.emergency_auto_resolve_seconds,
                execution_engine_notified=False,
                broker_disconnected=(
                    self._emergency_status.broker_disconnected
                    or trigger == EmergencyTrigger.BROKER_DISCONNECT
                ),
                market_feed_failed=(
                    self._emergency_status.market_feed_failed
                    or trigger == EmergencyTrigger.MARKET_FEED_FAILURE
                ),
                extreme_spread_detected=(
                    self._emergency_status.extreme_spread_detected
                    or trigger == EmergencyTrigger.EXTREME_SPREAD
                ),
                extreme_slippage_detected=(
                    self._emergency_status.extreme_slippage_detected
                    or trigger == EmergencyTrigger.EXTREME_SLIPPAGE
                ),
                margin_call_risk=(
                    self._emergency_status.margin_call_risk
                    or trigger == EmergencyTrigger.MARGIN_CALL_RISK
                ),
                connection_timeout=(
                    self._emergency_status.connection_timeout
                    or trigger == EmergencyTrigger.CONNECTION_TIMEOUT
                ),
                manual_override=(
                    self._emergency_status.manual_override
                    or trigger == EmergencyTrigger.MANUAL_OVERRIDE
                ),
            )

            await self._statistics.record_emergency_activation()

        # Notify emergency handler
        if self._emergency_handler is not None:
            await self._emergency_handler.on_emergency_activated(trigger, details)

    async def resolve_emergency(self) -> None:
        """Resolve emergency mode."""
        async with self._lock:
            if not self._emergency_status.active:
                return

            self._emergency_status = EmergencyModeStatus(active=False)

        if self._emergency_handler is not None:
            await self._emergency_handler.on_emergency_resolved()

    async def is_emergency_mode(self) -> bool:
        """Check if emergency mode is active."""
        async with self._lock:
            return self._emergency_status.active

    async def get_emergency_status(self) -> EmergencyModeStatus:
        """Get current emergency status."""
        async with self._lock:
            return self._emergency_status

    # ─── Account Protection ───────────────────────────────────

    async def get_protection_status(self) -> AccountProtectionStatus:
        """Get current account protection status."""
        async with self._lock:
            return self._protection_status

    async def update_protection_status(self, status: AccountProtectionStatus) -> None:
        """Update account protection status."""
        async with self._lock:
            self._protection_status = status

    async def set_trading_lock(
        self,
        locked: bool,
        reason: str = "",
        duration_seconds: float = 0.0,
    ) -> None:
        """Lock or unlock trading.

        Args:
            locked: Whether to lock trading.
            reason: Reason for the lock.
            duration_seconds: Lock duration (0 = indefinite).
        """
        async with self._lock:
            cooldown_until = None
            if locked and duration_seconds > 0:
                cooldown_until = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)

            self._protection_status = AccountProtectionStatus(
                level=(
                    AccountProtectionLevel.TRADING_LOCK if locked else AccountProtectionLevel.NONE
                ),
                trading_locked=locked,
                cooldown_active=locked and cooldown_until is not None,
                cooldown_until=cooldown_until,
                cooldown_remaining_seconds=duration_seconds if locked else 0.0,
            )

        if locked and self._emergency_handler is not None:
            await self._emergency_handler.on_trading_lock(reason, duration_seconds)

    # ─── Policy Management ────────────────────────────────────

    async def register_policy(self, policy: BaseRiskPolicy) -> None:
        """Register a policy.

        Args:
            policy: Policy to register.
        """
        await self._registry.register(policy)

    async def unregister_policy(self, policy_name: str) -> None:
        """Unregister a policy.

        Args:
            policy_name: Name of policy to remove.
        """
        await self._registry.unregister(policy_name)

    async def enable_policy(self, policy_name: str) -> None:
        """Enable a policy."""
        policy = await self._registry.get(policy_name)
        if hasattr(policy, "_enabled"):
            policy._enabled = True

    async def disable_policy(self, policy_name: str) -> None:
        """Disable a policy."""
        policy = await self._registry.get(policy_name)
        if hasattr(policy, "_enabled"):
            policy._enabled = False

    async def get_enabled_policies(self) -> list[RiskPolicy]:
        """Get all enabled policies.

        Returns:
            List of enabled policies.
        """
        return await self._registry.list_enabled()

    async def get_policy(self, policy_name: str) -> RiskPolicy:
        """Get a specific policy.

        Args:
            policy_name: Policy name.

        Returns:
            The policy instance.
        """
        return await self._registry.get(policy_name)

    # ─── Engine Evaluation ────────────────────────────────────

    async def evaluate(
        self,
        decision: Any,
        context: RiskContext | None = None,
    ) -> RiskResult:
        """Evaluate a trade decision against all risk policies.

        Args:
            decision: TradeDecision from the DecisionEngine.
            context: Optional pre-built RiskContext.

        Returns:
            RiskResult with final decision.

        Raises:
            EngineNotReadyError: If engine is not initialized.
        """
        if not self._initialized or self._engine is None:
            raise EngineNotReadyError("RiskEngine not initialized. Call start() before evaluate().")

        # Check emergency mode
        if self._emergency_status.active:
            return RiskResult(
                decision=RiskDecision.REJECTED,
                risk_score=100.0,
                rejection_reasons=("Emergency mode active - all trading blocked",),
                is_emergency_mode=True,
                account_protection_level=AccountProtectionLevel.HARD_STOP,
            )

        return await self._engine.evaluate(decision)

    # ─── Health ───────────────────────────────────────────────

    async def health_check(self) -> dict[str, Any]:
        """Perform a health check on the risk manager.

        Returns:
            Dict with health status.
        """
        async with self._lock:
            engine_health = {}
            if self._engine is not None:
                engine_health = await self._engine.health_check()

            stats_snapshot = await self._statistics.get_snapshot()

            return {
                "running": self._running,
                "initialized": self._initialized,
                "active_profile": self._active_profile.value,
                "total_policies": await self._registry.count(),
                "enabled_policies": await self._registry.enabled_count(),
                "emergency_mode": self._emergency_status.active,
                "protection_level": self._protection_status.level.value,
                "trading_locked": self._protection_status.trading_locked,
                "total_evaluations": stats_snapshot.total_evaluations,
                "total_approved": stats_snapshot.total_approved,
                "total_rejected": stats_snapshot.total_rejected,
                "approval_rate": stats_snapshot.approval_rate,
                "average_risk_score": stats_snapshot.average_risk_score,
                **engine_health,
            }

    async def get_statistics_snapshot(self) -> Any:
        """Get statistics snapshot."""
        return await self._statistics.get_snapshot()

    async def reset_statistics(self) -> None:
        """Reset all statistics."""
        await self._statistics.reset()

    # ─── Internal ─────────────────────────────────────────────

    async def _apply_default_profile(self) -> None:
        """Apply the default risk profile."""
        try:
            config = await self._profile_manager.get_profile(self._config.default_profile)
        except ProfileNotFoundError:
            config = RiskProfileConfig()

        async with self._lock:
            self._active_profile_config = config

        policies = create_default_policies(config)
        for policy in policies:
            await self._registry.register(policy)

    async def _health_loop(self) -> None:
        """Background health monitoring loop."""
        while True:
            try:
                await asyncio.sleep(self._config.health_check_interval_seconds)
                if not self._running:
                    break

                # Check self-health by querying engine
                if self._engine is not None:
                    await self._engine.health_check()

            except asyncio.CancelledError:
                break
            except HEALTH_CHECK_ERRORS:
                pass
