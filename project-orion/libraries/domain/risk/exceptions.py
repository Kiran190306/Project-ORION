"""Risk Management Engine exception hierarchy.

All exceptions raised by the risk domain library inherit from RiskError,
enabling clean catch-and-handle patterns without exposing internals.
"""

from __future__ import annotations


class RiskError(Exception):
    """Base exception for all risk management errors."""


class PolicyError(RiskError):
    """Raised when a risk policy encounters an error during evaluation."""


class PolicyNotFoundError(RiskError):
    """Raised when a policy is not found in the registry."""


class PolicyRegistrationError(RiskError):
    """Raised when policy registration fails (duplicate, invalid)."""


class PolicyExecutionError(PolicyError):
    """Raised when a policy fails during execution."""


class PolicyConfigurationError(PolicyError):
    """Raised when a policy is misconfigured."""


class EngineError(RiskError):
    """Raised when the RiskEngine encounters a fatal error."""


class EngineNotReadyError(EngineError):
    """Raised when the engine is invoked before being fully initialized."""


class EngineShutdownError(EngineError):
    """Raised when the engine is used after shutdown."""


class RegistryError(RiskError):
    """Raised when the policy registry encounters an error."""


class RegistryFullError(RegistryError):
    """Raised when the registry capacity is exhausted."""


class ProfileError(RiskError):
    """Raised when a risk profile operation fails."""


class ProfileNotFoundError(ProfileError):
    """Raised when a profile is not found."""


class ProfileValidationError(ProfileError):
    """Raised when profile configuration is invalid."""


class ContextError(RiskError):
    """Raised when the risk context is invalid or incomplete."""


class StatisticsError(RiskError):
    """Raised when statistics tracking encounters an error."""


class EmergencyModeError(RiskError):
    """Raised when emergency mode operations fail."""


class EmergencyAlreadyActiveError(EmergencyModeError):
    """Raised when emergency mode is already active."""


class CooldownActiveError(RiskError):
    """Raised when a trade is attempted during cooldown period."""


class TradingLockedError(RiskError):
    """Raised when trading is locked and a trade is attempted."""

