"""Exception hierarchy for the Portfolio & Position Management Engine."""

from __future__ import annotations


class PortfolioError(Exception):
    """Base exception for all portfolio engine errors."""


class PositionNotFoundError(PortfolioError):
    """Raised when a position is not found."""


class DuplicatePositionError(PortfolioError):
    """Raised when attempting to create a duplicate position."""


class InvalidPositionStateError(PortfolioError):
    """Raised when an operation is attempted in an invalid position state."""


class PositionSizeError(PortfolioError):
    """Raised when position sizing is invalid (e.g., close size > position size)."""


class InvalidTradeError(PortfolioError):
    """Raised when a trade operation is invalid."""


class InsufficientBalanceError(PortfolioError):
    """Raised when account balance is insufficient for a trade."""


class InsufficientMarginError(PortfolioError):
    """Raised when available margin is insufficient for a trade."""


class MarginCallError(PortfolioError):
    """Raised when margin level falls below the margin call threshold."""


class StopOutError(PortfolioError):
    """Raised when margin level falls below the stop-out threshold."""


class ExposureLimitExceededError(PortfolioError):
    """Raised when an exposure limit is exceeded."""


class JournalError(PortfolioError):
    """Raised when a journal operation fails."""


class PersistenceError(PortfolioError):
    """Raised when a persistence operation fails."""


class ManagerNotReadyError(PortfolioError):
    """Raised when the portfolio manager is called before being ready."""


class ManagerShutdownError(PortfolioError):
    """Raised when the portfolio manager is called after shutdown."""


class EngineNotReadyError(PortfolioError):
    """Raised when the portfolio engine is called before being initialized."""


class EngineShutdownError(PortfolioError):
    """Raised when the portfolio engine is called after shutdown."""
