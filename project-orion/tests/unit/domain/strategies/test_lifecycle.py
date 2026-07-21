"""Tests for StrategyLifecycle."""

from __future__ import annotations

import pytest

from libraries.domain.strategies.lifecycle import LifecycleState, StrategyLifecycle


class TestStrategyLifecycle:
    def test_initial_state(self) -> None:
        lifecycle = StrategyLifecycle()
        assert lifecycle.state == LifecycleState.CREATED

    def test_valid_transition(self) -> None:
        lifecycle = StrategyLifecycle()
        lifecycle.transition_to(LifecycleState.INITIALIZED)
        assert lifecycle.state == LifecycleState.INITIALIZED

    def test_invalid_transition_raises(self) -> None:
        lifecycle = StrategyLifecycle()
        with pytest.raises(ValueError, match="Invalid transition"):
            lifecycle.transition_to(LifecycleState.SHUTDOWN)

    def test_full_lifecycle(self) -> None:
        lifecycle = StrategyLifecycle()
        lifecycle.transition_to(LifecycleState.INITIALIZED)
        lifecycle.transition_to(LifecycleState.STARTED)
        lifecycle.transition_to(LifecycleState.PAUSED)
        lifecycle.transition_to(LifecycleState.RESUMED)
        lifecycle.transition_to(LifecycleState.STOPPED)
        lifecycle.transition_to(LifecycleState.SHUTDOWN)
        assert lifecycle.state == LifecycleState.SHUTDOWN

    def test_can_transition_to(self) -> None:
        lifecycle = StrategyLifecycle()
        assert lifecycle.can_transition_to(LifecycleState.INITIALIZED)
        assert not lifecycle.can_transition_to(LifecycleState.SHUTDOWN)

    def test_is_active(self) -> None:
        lifecycle = StrategyLifecycle()
        assert not lifecycle.is_active()
        lifecycle.transition_to(LifecycleState.INITIALIZED)
        lifecycle.transition_to(LifecycleState.STARTED)
        assert lifecycle.is_active()

    def test_is_stopped(self) -> None:
        lifecycle = StrategyLifecycle()
        assert not lifecycle.is_stopped()
        lifecycle.transition_to(LifecycleState.INITIALIZED)
        lifecycle.transition_to(LifecycleState.STARTED)
        lifecycle.transition_to(LifecycleState.STOPPED)
        assert lifecycle.is_stopped()

    def test_is_shutdown(self) -> None:
        lifecycle = StrategyLifecycle()
        lifecycle.transition_to(LifecycleState.INITIALIZED)
        lifecycle.transition_to(LifecycleState.STARTED)
        lifecycle.transition_to(LifecycleState.STOPPED)
        lifecycle.transition_to(LifecycleState.SHUTDOWN)
        assert lifecycle.is_shutdown()

    def test_error_transition(self) -> None:
        lifecycle = StrategyLifecycle()
        lifecycle.transition_to(LifecycleState.ERROR)
        assert lifecycle.state == LifecycleState.ERROR
        lifecycle.transition_to(LifecycleState.STOPPED)
        assert lifecycle.state == LifecycleState.STOPPED

    def test_reset(self) -> None:
        lifecycle = StrategyLifecycle()
        lifecycle.transition_to(LifecycleState.INITIALIZED)
        lifecycle.reset()
        assert lifecycle.state == LifecycleState.CREATED
