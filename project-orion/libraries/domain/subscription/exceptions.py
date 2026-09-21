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


class DailyOptimizationQuotaExceededError(QuotaExceededError):
    """Raised when organization exceeds maximum allowed daily optimization runs."""

    def __init__(self, current: int, limit: int) -> None:
        super().__init__(
            f"Daily optimization quota exceeded: Organization has launched {current} optimization jobs today (plan limit: {limit}).",
            code="DAILY_OPTIMIZATION_QUOTA_EXCEEDED",
        )
        self.current = current
        self.limit = limit


class OptimizationCombinationLimitExceededError(QuotaExceededError):
    """Raised when parameter space combination count exceeds plan limit."""

    def __init__(self, requested: int, limit: int) -> None:
        super().__init__(
            f"Optimization parameter combinations ({requested}) exceeds plan limit of {limit} combinations per job.",
            code="OPTIMIZATION_COMBINATION_LIMIT_EXCEEDED",
        )
        self.requested = requested
        self.limit = limit


class ActiveDeploymentLimitExceededError(QuotaExceededError):
    """Raised when organization exceeds maximum allowed concurrent active deployments."""

    def __init__(self, current: int, limit: int) -> None:
        super().__init__(
            f"Active deployment quota exceeded: Organization has {current} active deployments (plan limit: {limit}).",
            code="ACTIVE_DEPLOYMENT_LIMIT_EXCEEDED",
        )
        self.current = current
        self.limit = limit


class MonthlyDeploymentQuotaExceededError(QuotaExceededError):
    """Raised when organization exceeds maximum monthly deployment promotions."""

    def __init__(self, current: int, limit: int) -> None:
        super().__init__(
            f"Monthly deployment quota exceeded: Organization has launched {current} deployments this month (plan limit: {limit}).",
            code="MONTHLY_DEPLOYMENT_QUOTA_EXCEEDED",
        )
        self.current = current
        self.limit = limit

