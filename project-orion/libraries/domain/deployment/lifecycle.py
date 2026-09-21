"""Institutional Strategy Deployment Lifecycle State Machine.

Enforces strict, fail-closed state transitions, separation-of-duties rules,
auditable transition records, and terminal state invariants for EPIC-025.

EPIC-025 strictly terminates at PAPER_VALIDATED or PROMOTION_CANDIDATE.
No live trading transitions or broker execution pathways exist.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, ClassVar

from libraries.domain.deployment.models import (
    DeploymentStatus,
    DeploymentTransitionRecord,
    QualityGateVerdict,
)


class InvalidTransitionError(ValueError):
    """Raised when an invalid lifecycle state transition is attempted."""


class SeparationOfDutiesError(PermissionError):
    """Raised when an actor attempts an approval/activation action on their own candidate."""


class TerminalStateError(InvalidTransitionError):
    """Raised when attempting a transition from an immutable terminal state."""


class DeploymentLifecycle:
    """State machine governing strategy deployment lifecycle transitions."""

    # Exhaustive dictionary of valid from_status -> set of allowed to_status
    VALID_TRANSITIONS: ClassVar[dict[DeploymentStatus, set[DeploymentStatus]]] = {
        DeploymentStatus.PENDING_GATES: {
            DeploymentStatus.GATES_PASSED,
            DeploymentStatus.GATES_FAILED,
            DeploymentStatus.CANCELLED,
        },
        DeploymentStatus.GATES_PASSED: {
            DeploymentStatus.INCUBATING,
            DeploymentStatus.CANCELLED,
        },
        DeploymentStatus.INCUBATING: {
            DeploymentStatus.PAUSED,
            DeploymentStatus.PAPER_VALIDATED,
            DeploymentStatus.INCUBATION_FAILED,
            DeploymentStatus.SUSPENDED,
            DeploymentStatus.CANCELLED,
        },
        DeploymentStatus.PAUSED: {
            DeploymentStatus.INCUBATING,
            DeploymentStatus.SUSPENDED,
            DeploymentStatus.CANCELLED,
        },
        DeploymentStatus.PAPER_VALIDATED: {
            DeploymentStatus.PROMOTION_CANDIDATE,
            DeploymentStatus.SUSPENDED,
        },
        # Terminal states have NO outgoing transitions:
        DeploymentStatus.GATES_FAILED: set(),
        DeploymentStatus.INCUBATION_FAILED: set(),
        DeploymentStatus.CANCELLED: set(),
        DeploymentStatus.SUSPENDED: set(),
        DeploymentStatus.PROMOTION_CANDIDATE: set(),
    }

    TERMINAL_STATES: ClassVar[set[DeploymentStatus]] = {
        DeploymentStatus.GATES_FAILED,
        DeploymentStatus.INCUBATION_FAILED,
        DeploymentStatus.CANCELLED,
        DeploymentStatus.SUSPENDED,
        DeploymentStatus.PROMOTION_CANDIDATE,
    }

    # Transitions that require Separation of Duties (actor cannot be creator)
    # when enforce_separation_of_duties is True.
    SEPARATION_OF_DUTIES_TRANSITIONS: ClassVar[set[tuple[DeploymentStatus, DeploymentStatus]]] = {
        (DeploymentStatus.PENDING_GATES, DeploymentStatus.GATES_PASSED),
        (DeploymentStatus.GATES_PASSED, DeploymentStatus.INCUBATING),
        (DeploymentStatus.INCUBATING, DeploymentStatus.PAPER_VALIDATED),
        (DeploymentStatus.PAPER_VALIDATED, DeploymentStatus.PROMOTION_CANDIDATE),
    }

    @classmethod
    def is_terminal(cls, status: DeploymentStatus) -> bool:
        """Return True if status represents an immutable terminal state."""
        return status in cls.TERMINAL_STATES

    @classmethod
    def can_transition(
        cls, current_status: DeploymentStatus, target_status: DeploymentStatus
    ) -> bool:
        """Check if transition from current to target is theoretically valid in the matrix."""
        allowed = cls.VALID_TRANSITIONS.get(current_status, set())
        return target_status in allowed

    @classmethod
    def validate_transition(
        cls,
        *,
        current_status: DeploymentStatus,
        target_status: DeploymentStatus,
        actor_id: str,
        creator_id: str,
        actor_role: str | None = None,
        reason: str = "",
        authorization: str = "",
        quality_gate_verdict: QualityGateVerdict | None = None,
        incubation_passed: bool | None = None,
        enforce_separation_of_duties: bool = False,
        details: dict[str, Any] | None = None,
    ) -> DeploymentTransitionRecord:
        """Validate a lifecycle state transition.

        Raises:
            TerminalStateError: If current state is immutable/terminal.
            InvalidTransitionError: If transition is not allowed by matrix or gates.
            SeparationOfDutiesError: If actor is creator on restricted promotion transition.
        """
        now = datetime.now(timezone.utc)

        # 1. Terminal State Check (Fail-closed invariant)
        if cls.is_terminal(current_status):
            raise TerminalStateError(
                f"Cannot transition from terminal state '{current_status.value}'. Deployment is immutable."
            )

        # 2. Transition Matrix Check
        if not cls.can_transition(current_status, target_status):
            raise InvalidTransitionError(
                f"Invalid lifecycle transition: '{current_status.value}' -> '{target_status.value}' is not permitted"
            )

        # 3. Separation of Duties Check
        if (
            enforce_separation_of_duties
            and (current_status, target_status) in cls.SEPARATION_OF_DUTIES_TRANSITIONS
            and actor_id == creator_id
        ):
            raise SeparationOfDutiesError(
                f"Separation of duties violation: Actor '{actor_id}' cannot approve/activate their own deployment ({current_status.value} -> {target_status.value})"
            )

        # 4. Domain Logic & Gate Condition Validations
        if target_status == DeploymentStatus.GATES_PASSED:
            if quality_gate_verdict != QualityGateVerdict.PASS:
                raise InvalidTransitionError(
                    f"Cannot advance to GATES_PASSED: Quality gate verdict is '{quality_gate_verdict}', must be PASS"
                )

        elif target_status == DeploymentStatus.GATES_FAILED:
            if quality_gate_verdict == QualityGateVerdict.PASS:
                raise InvalidTransitionError(
                    "Cannot mark GATES_FAILED when all quality gates passed"
                )

        elif target_status == DeploymentStatus.PAPER_VALIDATED:
            if incubation_passed is not True:
                raise InvalidTransitionError(
                    "Cannot mark PAPER_VALIDATED: Incubation criteria was not passed"
                )

        elif target_status == DeploymentStatus.INCUBATION_FAILED and incubation_passed is True:
            raise InvalidTransitionError(
                "Cannot mark INCUBATION_FAILED: Incubation criteria was passed"
            )

        # 5. Build and return the immutable audit transition record
        return DeploymentTransitionRecord(
            from_status=current_status,
            to_status=target_status,
            actor_id=actor_id,
            actor_role=actor_role,
            timestamp=now,
            reason=reason or f"Transitioned from {current_status.value} to {target_status.value}",
            authorization=authorization,
            validation_passed=True,
            details=details or {},
        )
