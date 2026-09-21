"""Institutional Strategy Deployment Pipeline & Paper Incubator domain package.

Provides domain models, lifecycle state machine, quality gate evaluation,
and configurable incubation policy for deploying optimized strategies
into managed paper trading incubation.

EPIC-025 terminates at PAPER_VALIDATED or PROMOTION_CANDIDATE.
No live trading pathways exist.
"""

from libraries.domain.deployment.incubation_policy import (
    IncubationEvaluationResult,
    IncubationPolicy,
    IncubationPolicyViolation,
)
from libraries.domain.deployment.lifecycle import (
    DeploymentLifecycle,
    InvalidTransitionError,
    SeparationOfDutiesError,
    TerminalStateError,
)
from libraries.domain.deployment.models import (
    BenchmarkComparison,
    DeploymentStatus,
    DeploymentTransitionRecord,
    EvidenceChain,
    IncubationConfig,
    IncubationMetrics,
    PromotionVerdict,
    QualityGateReport,
    QualityGateResult,
    QualityGateType,
    QualityGateVerdict,
    StrategyDeployment,
)
from libraries.domain.deployment.quality_gates import (
    QualityGateEvaluator,
    QualityGatePolicy,
)

__all__ = [
    "BenchmarkComparison",
    "DeploymentLifecycle",
    "DeploymentStatus",
    "DeploymentTransitionRecord",
    "EvidenceChain",
    "IncubationConfig",
    "IncubationEvaluationResult",
    "IncubationMetrics",
    "IncubationPolicy",
    "IncubationPolicyViolation",
    "InvalidTransitionError",
    "PromotionVerdict",
    "QualityGateEvaluator",
    "QualityGatePolicy",
    "QualityGateReport",
    "QualityGateResult",
    "QualityGateType",
    "QualityGateVerdict",
    "SeparationOfDutiesError",
    "StrategyDeployment",
    "TerminalStateError",
]
