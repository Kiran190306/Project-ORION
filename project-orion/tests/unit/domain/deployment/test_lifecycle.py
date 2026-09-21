"""Unit tests for DeploymentLifecycle state machine."""

from __future__ import annotations

import pytest

from libraries.domain.deployment.lifecycle import (
    DeploymentLifecycle,
    InvalidTransitionError,
    SeparationOfDutiesError,
    TerminalStateError,
)
from libraries.domain.deployment.models import (
    DeploymentStatus,
    QualityGateVerdict,
)


def test_valid_transitions_coverage():
    """Verify valid transitions succeed and generate transition records."""
    # PENDING_GATES -> GATES_PASSED (with PASS gate verdict)
    rec1 = DeploymentLifecycle.validate_transition(
        current_status=DeploymentStatus.PENDING_GATES,
        target_status=DeploymentStatus.GATES_PASSED,
        actor_id="user-1",
        creator_id="user-1",
        quality_gate_verdict=QualityGateVerdict.PASS,
        authorization="DEPLOYMENT_EXECUTE",
    )
    assert rec1.from_status == DeploymentStatus.PENDING_GATES
    assert rec1.to_status == DeploymentStatus.GATES_PASSED
    assert rec1.validation_passed is True

    # GATES_PASSED -> INCUBATING
    rec2 = DeploymentLifecycle.validate_transition(
        current_status=DeploymentStatus.GATES_PASSED,
        target_status=DeploymentStatus.INCUBATING,
        actor_id="user-1",
        creator_id="user-1",
        authorization="DEPLOYMENT_EXECUTE",
    )
    assert rec2.to_status == DeploymentStatus.INCUBATING

    # INCUBATING -> PAUSED -> INCUBATING
    rec3 = DeploymentLifecycle.validate_transition(
        current_status=DeploymentStatus.INCUBATING,
        target_status=DeploymentStatus.PAUSED,
        actor_id="user-1",
        creator_id="user-1",
        authorization="DEPLOYMENT_CANCEL",
    )
    assert rec3.to_status == DeploymentStatus.PAUSED

    rec4 = DeploymentLifecycle.validate_transition(
        current_status=DeploymentStatus.PAUSED,
        target_status=DeploymentStatus.INCUBATING,
        actor_id="user-1",
        creator_id="user-1",
        authorization="DEPLOYMENT_EXECUTE",
    )
    assert rec4.to_status == DeploymentStatus.INCUBATING

    # INCUBATING -> PAPER_VALIDATED (with incubation_passed=True)
    rec5 = DeploymentLifecycle.validate_transition(
        current_status=DeploymentStatus.INCUBATING,
        target_status=DeploymentStatus.PAPER_VALIDATED,
        actor_id="user-2",
        creator_id="user-1",
        incubation_passed=True,
        authorization="DEPLOYMENT_PROMOTE",
    )
    assert rec5.to_status == DeploymentStatus.PAPER_VALIDATED

    # PAPER_VALIDATED -> PROMOTION_CANDIDATE
    rec6 = DeploymentLifecycle.validate_transition(
        current_status=DeploymentStatus.PAPER_VALIDATED,
        target_status=DeploymentStatus.PROMOTION_CANDIDATE,
        actor_id="user-2",
        creator_id="user-1",
        authorization="DEPLOYMENT_PROMOTE",
    )
    assert rec6.to_status == DeploymentStatus.PROMOTION_CANDIDATE


def test_terminal_states_fail_closed():
    """Verify transitions from terminal states are completely rejected."""
    terminal_states = [
        DeploymentStatus.GATES_FAILED,
        DeploymentStatus.INCUBATION_FAILED,
        DeploymentStatus.CANCELLED,
        DeploymentStatus.SUSPENDED,
        DeploymentStatus.PROMOTION_CANDIDATE,
    ]
    for ts in terminal_states:
        assert DeploymentLifecycle.is_terminal(ts) is True
        with pytest.raises(TerminalStateError, match="Cannot transition from terminal state"):
            DeploymentLifecycle.validate_transition(
                current_status=ts,
                target_status=DeploymentStatus.INCUBATING,
                actor_id="admin-1",
                creator_id="user-1",
            )


def test_invalid_transitions_fail_closed():
    """Verify non-permitted transitions raise InvalidTransitionError."""
    # Cannot jump from PENDING_GATES directly to PAPER_VALIDATED
    with pytest.raises(InvalidTransitionError, match="Invalid lifecycle transition"):
        DeploymentLifecycle.validate_transition(
            current_status=DeploymentStatus.PENDING_GATES,
            target_status=DeploymentStatus.PAPER_VALIDATED,
            actor_id="user-1",
            creator_id="user-1",
        )

    # Cannot jump from GATES_PASSED directly to PROMOTION_CANDIDATE
    with pytest.raises(InvalidTransitionError):
        DeploymentLifecycle.validate_transition(
            current_status=DeploymentStatus.GATES_PASSED,
            target_status=DeploymentStatus.PROMOTION_CANDIDATE,
            actor_id="user-1",
            creator_id="user-1",
        )


def test_separation_of_duties_enforcement():
    """Verify that creator cannot self-approve restricted transitions when enforced."""
    # When separation of duties is enforced, self-approval must raise SeparationOfDutiesError
    with pytest.raises(SeparationOfDutiesError, match="Separation of duties violation"):
        DeploymentLifecycle.validate_transition(
            current_status=DeploymentStatus.INCUBATING,
            target_status=DeploymentStatus.PAPER_VALIDATED,
            actor_id="user-creator",
            creator_id="user-creator",
            enforce_separation_of_duties=True,
            incubation_passed=True,
        )

    # With a distinct reviewer, it must pass
    rec = DeploymentLifecycle.validate_transition(
        current_status=DeploymentStatus.INCUBATING,
        target_status=DeploymentStatus.PAPER_VALIDATED,
        actor_id="user-reviewer",
        creator_id="user-creator",
        enforce_separation_of_duties=True,
        incubation_passed=True,
    )
    assert rec.validation_passed is True


def test_gate_conditions_checked():
    """Verify gate conditions must be met for status advancement."""
    # Cannot advance to GATES_PASSED if verdict is FAIL
    with pytest.raises(InvalidTransitionError, match="Quality gate verdict is 'FAIL'"):
        DeploymentLifecycle.validate_transition(
            current_status=DeploymentStatus.PENDING_GATES,
            target_status=DeploymentStatus.GATES_PASSED,
            actor_id="user-1",
            creator_id="user-1",
            quality_gate_verdict=QualityGateVerdict.FAIL,
        )

    # Cannot advance to GATES_PASSED if verdict is INSUFFICIENT_DATA
    with pytest.raises(InvalidTransitionError, match="Quality gate verdict is 'INSUFFICIENT_DATA'"):
        DeploymentLifecycle.validate_transition(
            current_status=DeploymentStatus.PENDING_GATES,
            target_status=DeploymentStatus.GATES_PASSED,
            actor_id="user-1",
            creator_id="user-1",
            quality_gate_verdict=QualityGateVerdict.INSUFFICIENT_DATA,
        )
