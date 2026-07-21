"""Strategy lifecycle management."""

from __future__ import annotations

from enum import StrEnum, auto


class LifecycleState(StrEnum):
    """States in a strategy's lifecycle."""

    CREATED = "created"
    INITIALIZED = "initialized"
    STARTED = "started"
    PAUSED = "paused"
    RESUMED = "resumed"
    STOPPED = "stopped"
    SHUTDOWN = "shutdown"
    ERROR = "error"


class StrategyLifecycle:
    """Manages the lifecycle state machine for a single strategy.

    Valid transitions:
    CREATED -> INITIALIZED -> STARTED <-> PAUSED -> STOPPED -> SHUTDOWN
    Any state -> ERROR -> STOPPED -> SHUTDOWN
    """

    VALID_TRANSITIONS: dict[LifecycleState, set[LifecycleState]] = {
        LifecycleState.CREATED: {LifecycleState.INITIALIZED, LifecycleState.ERROR},
        LifecycleState.INITIALIZED: {
            LifecycleState.STARTED,
            LifecycleState.ERROR,
            LifecycleState.SHUTDOWN,
        },
        LifecycleState.STARTED: {
            LifecycleState.PAUSED,
            LifecycleState.STOPPED,
            LifecycleState.ERROR,
        },
        LifecycleState.PAUSED: {
            LifecycleState.RESUMED,
            LifecycleState.STOPPED,
            LifecycleState.ERROR,
        },
        LifecycleState.RESUMED: {
            LifecycleState.PAUSED,
            LifecycleState.STOPPED,
            LifecycleState.ERROR,
        },
        LifecycleState.STOPPED: {LifecycleState.SHUTDOWN, LifecycleState.ERROR},
        LifecycleState.SHUTDOWN: set(),
        LifecycleState.ERROR: {LifecycleState.STOPPED, LifecycleState.SHUTDOWN},
    }

    def __init__(self) -> None:
        self._state: LifecycleState = LifecycleState.CREATED

    @property
    def state(self) -> LifecycleState:
        """Return the current lifecycle state."""
        return self._state

    def transition_to(self, new_state: LifecycleState) -> None:
        """Attempt to transition to a new state.

        Args:
            new_state: Target state.

        Raises:
            ValueError: If the transition is invalid.
        """
        allowed = self.VALID_TRANSITIONS.get(self._state, set())
        if new_state not in allowed:
            raise ValueError(f"Invalid transition from {self._state.value} to {new_state.value}")
        self._state = new_state

    def can_transition_to(self, new_state: LifecycleState) -> bool:
        """Check if a transition is valid without performing it.

        Args:
            new_state: Target state.

        Returns:
            True if the transition is allowed.
        """
        allowed = self.VALID_TRANSITIONS.get(self._state, set())
        return new_state in allowed

    def is_active(self) -> bool:
        """Return True if the strategy is in an active state."""
        return self._state in {LifecycleState.STARTED, LifecycleState.RESUMED}

    def is_stopped(self) -> bool:
        """Return True if the strategy is stopped."""
        return self._state == LifecycleState.STOPPED

    def is_shutdown(self) -> bool:
        """Return True if the strategy is shut down."""
        return self._state == LifecycleState.SHUTDOWN

    def reset(self) -> None:
        """Reset lifecycle to CREATED (for testing)."""
        self._state = LifecycleState.CREATED
