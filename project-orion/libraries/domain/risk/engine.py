"""Risk Engine - the final approval authority before any order reaches
the Execution Engine.

The RiskEngine:
1. Receives a TradeDecision from the DecisionEngine
2. Validates the input and builds a RiskContext
3. Executes every enabled risk policy
4. Aggregates policy results via the RiskEvaluator
5. Calculates overall risk score
6. Returns RiskDecision: APPROVED / REJECTED / DEFERRED

NO trade should execute without passing every enabled risk policy.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.risk.context import RiskContext
from libraries.domain.risk.evaluator import RiskEvaluator
from libraries.domain.risk.exceptions import EngineError, EngineNotReadyError, EngineShutdownError
from libraries.domain.risk.models import (
    AccountProtectionStatus,
    DrawdownMetrics,
    EmergencyModeStatus,
    PolicyCategory,
    PolicyResult,
    PolicySeverity,
    PortfolioRisk,
    PositionRisk,
    RiskDecision,
    RiskResult,
    RiskScore,
)
from libraries.domain.risk.registry import RiskPolicyRegistry
from libraries.domain.risk.statistics import RiskStatistics
from libraries.domain.risk.validator import RiskValidator


@dataclass(frozen=True, slots=True)
class RiskEngineConfig:
    """Configuration for the RiskEngine."""

    max_evaluation_time_ms: float = 5000.0
    fail_open: bool = False  # If True, approve if engine itself fails
    strict_mode: bool = True  # If True, reject on validation errors
    log_policy_execution: bool = True


class RiskEngine:
    """Enterprise Risk Engine - final approval authority for trades.

    Thread-safe via asyncio.Lock. Supports dependency injection of all
    components for testing.

    Performance: O(number_of_enabled_policies)
    """

    def __init__(
        self,
        registry: RiskPolicyRegistry | None = None,
        evaluator: RiskEvaluator | None = None,
        validator: RiskValidator | None = None,
        statistics: RiskStatistics | None = None,
        config: RiskEngineConfig | None = None,
    ) -> None:
        self._registry = registry or RiskPolicyRegistry()
        self._evaluator = evaluator or RiskEvaluator()
        self._validator = validator or RiskValidator()
        self._statistics = statistics
        self._config = config or RiskEngineConfig()

        self._lock = asyncio.Lock()
        self._initialized = False
        self._shutdown = False
        self._evaluation_count = 0

    @property
    def config(self) -> RiskEngineConfig:
        return self._config

    @property
    def registry(self) -> RiskPolicyRegistry:
        return self._registry

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def is_shutdown(self) -> bool:
        return self._shutdown

    # ─── Lifecycle ────────────────────────────────────────────

    async def initialize(self) -> None:
        """Initialize the risk engine.

        Initializes all registered policies.
        """
        async with self._lock:
            if self._initialized:
                return

            # Initialize all policies
            policies = await self._registry.get_all()
            init_tasks = []
            for policy in policies:
                if hasattr(policy, "initialize") and callable(policy.initialize):
                    init_tasks.append(policy.initialize())

            if init_tasks:
                async with asyncio.TaskGroup() as tg:
                    for task in init_tasks:
                        tg.create_task(task)

            self._initialized = True
            self._shutdown = False

    async def shutdown(self) -> None:
        """Shutdown the risk engine.

        Disposes all registered policies.
        """
        async with self._lock:
            if self._shutdown:
                return

            # Dispose all policies
            policies = await self._registry.get_all()
            dispose_tasks = []
            for policy in policies:
                if hasattr(policy, "dispose") and callable(policy.dispose):
                    dispose_tasks.append(policy.dispose())

            if dispose_tasks:
                async with asyncio.TaskGroup() as tg:
                    for task in dispose_tasks:
                        tg.create_task(task)

            self._shutdown = True
            self._initialized = False

    # ─── Main Evaluation ──────────────────────────────────────

    async def evaluate(
        self,
        decision: Any,
        context: RiskContext | None = None,
    ) -> RiskResult:
        """Evaluate a TradeDecision against all enabled risk policies.

        This is the main entry point. The pipeline:
        1. Check engine readiness
        2. Validate input decision
        3. Build RiskContext (or use provided one)
        4. Execute every enabled policy (respecting priority order)
        5. Aggregate results via RiskEvaluator
        6. Calculate overall risk score
        7. Return RiskResult

        Args:
            decision: TradeDecision from the DecisionEngine.
            context: Optional pre-built RiskContext. If None, one is
                     built from the decision.

        Returns:
            RiskResult with final decision.

        Raises:
            EngineNotReadyError: If engine is not initialized.
            EngineShutdownError: If engine has been shutdown.
        """
        start_time = time.monotonic()

        async with self._lock:
            if self._shutdown:
                raise EngineShutdownError("RiskEngine has been shutdown")
            if not self._initialized:
                # Auto-initialize if not already done
                await self.initialize()

            self._evaluation_count += 1

        try:
            # Build context if not provided
            if context is None:
                context = self._build_context(decision)

            # Validate decision
            validation = await self._validator.validate_trade_decision(decision)
            if not validation.is_valid:
                if self._config.strict_mode:
                    return self._build_error_result(
                        RiskDecision.REJECTED,
                        100.0,
                        tuple(validation.errors),
                    )

            # Validate context
            ctx_validation = await self._validator.validate_context(context)
            if not ctx_validation.is_valid and self._config.strict_mode:
                return self._build_error_result(
                    RiskDecision.REJECTED,
                    100.0,
                    tuple(ctx_validation.errors),
                )

            # Get enabled policies in execution order
            enabled_policies = await self._registry.list_enabled()
            if not enabled_policies:
                return self._build_result(
                    RiskDecision.APPROVED,
                    0.0,
                    (),
                    warnings=("No risk policies enabled - trade approved by default",),
                )

            # Execute all policies using TaskGroup for concurrent evaluation
            policy_results: list[PolicyResult] = []
            evaluations: list[Any] = []

            async with asyncio.TaskGroup() as tg:
                eval_tasks = {}
                for policy in enabled_policies:
                    if hasattr(policy, "evaluate") and callable(policy.evaluate):
                        task = tg.create_task(self._safe_evaluate(policy, context))
                        eval_tasks[policy.name] = task

                # Collect results
                for policy_name, task in eval_tasks.items():
                    try:
                        result = task.result()
                        if result is not None:
                            policy_results.append(result)
                    except Exception:
                        if self._config.fail_open:
                            policy_results.append(
                                PolicyResult(
                                    policy_name=policy_name,
                                    policy_category=PolicyCategory.SYSTEM_HEALTH,
                                    severity=PolicySeverity.CRITICAL,
                                    passed=True,
                                    score=100.0,
                                    message=f"Policy '{policy_name}' evaluation failed (fail-open mode)",
                                )
                            )
                        else:
                            policy_results.append(
                                PolicyResult(
                                    policy_name=policy_name,
                                    policy_category=PolicyCategory.SYSTEM_HEALTH,
                                    severity=PolicySeverity.CRITICAL,
                                    passed=False,
                                    score=0.0,
                                    message=f"Policy '{policy_name}' evaluation error",
                                    details="Policy execution failed. See engine logs for details.",
                                )
                            )

            # Convert to evaluations and aggregate
            evaluations = [pr.to_evaluation() for pr in policy_results]

            # Aggregate via evaluator
            result = await self._evaluator.evaluate(
                evaluations,
                is_emergency_mode=context.is_emergency if hasattr(context, "is_emergency") else False,
            )

            # Enrich result
            enriched = RiskResult(
                decision=result.decision,
                risk_score=result.risk_score,
                policy_results=result.policy_results + tuple(
                    pr for pr in policy_results if pr.policy_name not in {p.policy_name for p in result.policy_results}
                ),
                evaluations=result.evaluations,
                rejection_reasons=result.rejection_reasons,
                deferred_reasons=result.deferred_reasons,
                warnings=result.warnings + tuple(ctx_validation.warnings),
                is_emergency_mode=result.is_emergency_mode,
                account_protection_level=result.account_protection_level,
                risk_profile=context.risk_profile.value if hasattr(context, "risk_profile") else "",
                evaluated_policies_count=len(policy_results),
                enabled_policies_count=len(enabled_policies),
            )

            # Record statistics
            if self._statistics is not None:
                violations = {pr.policy_name: pr.passed for pr in policy_results}
                categories = {pr.policy_name: pr.policy_category for pr in policy_results}
                await self._statistics.record_evaluation(
                    decision=enriched.decision,
                    risk_score=enriched.risk_score,
                    policy_violations=violations,
                    policy_categories=categories,
                )

            return enriched

        except asyncio.CancelledError:
            raise
        except Exception as e:
            if self._config.fail_open:
                return self._build_error_result(
                    RiskDecision.APPROVED,
                    0.0,
                    (f"Engine error (fail-open): {e!s}",),
                )
            raise EngineError(f"RiskEngine evaluation failed: {e!s}") from e

    # ─── Health ───────────────────────────────────────────────

    async def health_check(self) -> dict[str, Any]:
        """Return health status of the risk engine.

        Returns:
            Dict with health metrics.
        """
        async with self._lock:
            enabled_count = await self._registry.enabled_count()
            total_count = await self._registry.count()

            return {
                "initialized": self._initialized,
                "shutdown": self._shutdown,
                "evaluation_count": self._evaluation_count,
                "total_policies": total_count,
                "enabled_policies": enabled_count,
                "config": {
                    "max_evaluation_time_ms": self._config.max_evaluation_time_ms,
                    "fail_open": self._config.fail_open,
                    "strict_mode": self._config.strict_mode,
                },
            }

    async def get_risk_score(self, context: RiskContext) -> RiskScore:
        """Compute a risk score for a given context without making a decision.

        Useful for monitoring and reporting.

        Args:
            context: RiskContext to evaluate.

        Returns:
            RiskScore breakdown.
        """
        enabled_policies = await self._registry.list_enabled()
        evaluations = []
        for policy in enabled_policies:
            if hasattr(policy, "evaluate") and callable(policy.evaluate):
                try:
                    result = await policy.evaluate(context)
                    evaluations.append(result.to_evaluation())
                except Exception:
                    pass
        return await self._evaluator.compute_risk_score(evaluations)

    # ─── Internal Helpers ─────────────────────────────────────

    async def _safe_evaluate(self, policy: Any, context: RiskContext) -> PolicyResult | None:
        """Safely evaluate a single policy, catching exceptions.

        Args:
            policy: RiskPolicy to evaluate.
            context: RiskContext.

        Returns:
            PolicyResult or None if policy doesn't have evaluate.
        """
        try:
            if hasattr(policy, "evaluate") and callable(policy.evaluate):
                result = await policy.evaluate(context)
                return result
        except asyncio.CancelledError:
            raise
        except Exception:
            return PolicyResult(
                policy_name=getattr(policy, "name", "unknown"),
                policy_category=getattr(policy, "category", PolicyCategory.SYSTEM_HEALTH),
                severity=PolicySeverity.CRITICAL,
                passed=False,
                score=0.0,
                message=f"Policy execution error",
                details=f"Policy '{getattr(policy, 'name', 'unknown')}' threw an exception during evaluation.",
            )
        return None

    def _build_context(self, decision: Any) -> RiskContext:
        """Build a RiskContext from a TradeDecision.

        Args:
            decision: TradeDecision object.

        Returns:
            Populated RiskContext.
        """
        kwargs: dict[str, Any] = {}

        # Extract decision attributes safely
        if hasattr(decision, "symbol"):
            kwargs["symbol"] = decision.symbol
        if hasattr(decision, "direction"):
            kwargs["direction"] = decision.direction.value if hasattr(decision.direction, "value") else str(decision.direction)
        if hasattr(decision, "entry_price"):
            kwargs["entry_price"] = decision.entry_price
        if hasattr(decision, "stop_loss"):
            kwargs["stop_loss"] = decision.stop_loss
        if hasattr(decision, "take_profit"):
            kwargs["take_profit"] = decision.take_profit
        if hasattr(decision, "position_size"):
            kwargs["position_size"] = decision.position_size
        if hasattr(decision, "confidence"):
            kwargs["confidence"] = decision.confidence
        if hasattr(decision, "strategy"):
            kwargs["strategy"] = decision.strategy.value if hasattr(decision.strategy, "value") else str(decision.strategy)
        if hasattr(decision, "notional_value"):
            kwargs["notional_value"] = decision.notional_value

        # Add metadata
        metadata = {}
        if hasattr(decision, "metadata"):
            metadata = dict(getattr(decision, "metadata", {}))

        return RiskContext(
            **kwargs,
            metadata=metadata,
        )

    def _build_result(
        self,
        decision: RiskDecision,
        risk_score: float,
        results: tuple[PolicyResult, ...],
        rejection_reasons: tuple[str, ...] = (),
        deferred_reasons: tuple[str, ...] = (),
        warnings: tuple[str, ...] = (),
    ) -> RiskResult:
        """Build a RiskResult."""
        return RiskResult(
            decision=decision,
            risk_score=risk_score,
            policy_results=results,
            rejection_reasons=rejection_reasons,
            deferred_reasons=deferred_reasons,
            warnings=warnings,
            evaluated_policies_count=len(results),
            enabled_policies_count=len(results),
        )

    def _build_error_result(
        self,
        decision: RiskDecision,
        risk_score: float,
        errors: tuple[str, ...],
    ) -> RiskResult:
        """Build a RiskResult for error conditions."""
        return RiskResult(
            decision=decision,
            risk_score=risk_score,
            rejection_reasons=errors if decision != RiskDecision.APPROVED else (),
            warnings=errors if decision == RiskDecision.APPROVED else (),
        )

