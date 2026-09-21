"""Domain exceptions for Subscription and Entitlement enforcement."""

from __future__ import annotations


class EntitlementError(Exception):
    """Base exception for entitlement and quota violations."""

    def __init__(self, message: str, code: str = "ENTITLEMENT_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class QuotaExceededError(EntitlementError):
    """Base exception when a tenant quota limit is exceeded."""

    def __init__(self, message: str, code: str = "QUOTA_EXCEEDED") -> None:
        super().__init__(message, code=code)


class AccountQuotaExceededError(QuotaExceededError):
    """Raised when organization exceeds maximum allowed paper trading accounts."""

    def __init__(self, current: int, limit: int) -> None:
        super().__init__(
            f"Account quota exceeded: Organization has {current} accounts (plan limit: {limit}).",
            code="ACCOUNT_QUOTA_EXCEEDED",
        )
        self.current = current
        self.limit = limit


class DailyOrderQuotaExceededError(QuotaExceededError):
    """Raised when organization exceeds maximum allowed daily orders."""

    def __init__(self, current: int, limit: int) -> None:
        super().__init__(
            f"Daily order quota exceeded: Organization has placed {current} orders today (plan limit: {limit}).",
            code="DAILY_ORDER_QUOTA_EXCEEDED",
        )
        self.current = current
        self.limit = limit


class WorkerQuotaExceededError(QuotaExceededError):
    """Raised when organization is not entitled to enable autonomous trading workers."""

    def __init__(self, plan_name: str, limit: int) -> None:
        super().__init__(
            f"Autonomous worker not permitted on plan '{plan_name}' (worker limit: {limit}).",
            code="WORKER_QUOTA_EXCEEDED",
        )
        self.plan_name = plan_name
        self.limit = limit


class AssetNotEntitledError(EntitlementError):
    """Raised when an instrument is not permitted under the organization's plan."""

    def __init__(self, symbol: str, plan_name: str) -> None:
        super().__init__(
            f"Trading symbol '{symbol}' is not entitled under plan '{plan_name}'.",
            code="ASSET_NOT_ENTITLED",
        )
        self.symbol = symbol
        self.plan_name = plan_name


class SubscriptionInactiveError(EntitlementError):
    """Raised when organization subscription is suspended, cancelled, or expired."""

    def __init__(self, status: str) -> None:
        super().__init__(
            f"Subscription is inactive (status: '{status}'). Operation not permitted.",
            code="SUBSCRIPTION_INACTIVE",
        )
        self.status = status


class SubscriptionRequiredError(EntitlementError):
    """Raised when an operation requires an active subscription but none exists."""

    def __init__(self) -> None:
        super().__init__(
            "An active subscription is required to perform this operation.",
            code="SUBSCRIPTION_REQUIRED",
        )


class DailyResearchQuotaExceededError(QuotaExceededError):
    """Raised when organization exceeds maximum allowed daily research backtests."""

    def __init__(self, current: int, limit: int) -> None:
        super().__init__(
            f"Daily research quota exceeded: Organization has executed {current} backtests today (plan limit: {limit}).",
            code="DAILY_RESEARCH_QUOTA_EXCEEDED",
        )
        self.current = current
        self.limit = limit


class ResearchHistoryLimitExceededError(EntitlementError):
    """Raised when requested historical date range exceeds plan limits."""

    def __init__(self, requested_days: int, limit_days: int) -> None:
        super().__init__(
            f"Historical date range ({requested_days} days) exceeds plan limit of {limit_days} days.",
            code="RESEARCH_HISTORY_LIMIT_EXCEEDED",
        )
        self.requested_days = requested_days
        self.limit_days = limit_days
