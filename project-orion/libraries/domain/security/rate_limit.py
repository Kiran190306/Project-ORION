"""Rate limiting domain models and centralized policy definitions for Project ORION.

All policies represent abuse-prevention burst controls and operate independently
from business subscription quotas enforced by EntitlementService.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RateLimitScope(StrEnum):
    """Dimensional scope applied for rate limit keys."""

    IP = "ip"
    USER = "user"
    ORGANIZATION = "org"
    USER_AND_ORG = "user_org"


class FallbackMode(StrEnum):
    """Strategy when distributed Redis store is temporarily unavailable."""

    BOUNDED_FALLBACK = "bounded_fallback"
    FAIL_CLOSED = "fail_closed"


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    """Immutable rate limiting policy configuration."""

    name: str
    limit: int
    window_seconds: int
    scope: RateLimitScope
    fallback_mode: FallbackMode = FallbackMode.BOUNDED_FALLBACK
    description: str = ""

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError(f"RateLimitPolicy limit must be positive, got {self.limit}")
        if self.window_seconds <= 0:
            raise ValueError(
                f"RateLimitPolicy window_seconds must be positive, got {self.window_seconds}"
            )


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    """Result of an evaluated rate limit check."""

    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int
    reset_after_seconds: int
    reset_timestamp: int
    source: str  # "redis" or "memory_fallback"


class RateLimitPolicies:
    """Canonical, centralized rate limit policies for Project ORION.

    Public authentication endpoints protect against brute-force and enumeration.
    Authenticated resource endpoints protect compute, external APIs, and database resources.
    Health checks and Prometheus metrics are strictly excluded from rate limiting.
    """

    # ─── Public Authentication & Onboarding ───────────────────────────────────
    AUTH_LOGIN = RateLimitPolicy(
        name="auth_login",
        limit=5,
        window_seconds=60,
        scope=RateLimitScope.IP,
        fallback_mode=FallbackMode.BOUNDED_FALLBACK,
        description="Public login rate limit: 5 requests / minute / IP",
    )

    AUTH_FORGOT_PASSWORD = RateLimitPolicy(
        name="auth_forgot_password",
        limit=3,
        window_seconds=3600,
        scope=RateLimitScope.IP,
        fallback_mode=FallbackMode.BOUNDED_FALLBACK,
        description="Password reset dispatch rate limit: 3 requests / hour / IP",
    )

    AUTH_RESEND_VERIFICATION = RateLimitPolicy(
        name="auth_resend_verification",
        limit=3,
        window_seconds=3600,
        scope=RateLimitScope.IP,
        fallback_mode=FallbackMode.BOUNDED_FALLBACK,
        description="Email verification resend rate limit: 3 requests / hour / IP",
    )

    ONBOARDING_REGISTER = RateLimitPolicy(
        name="onboarding_register",
        limit=5,
        window_seconds=3600,
        scope=RateLimitScope.IP,
        fallback_mode=FallbackMode.BOUNDED_FALLBACK,
        description="Account & organization registration rate limit: 5 requests / hour / IP",
    )

    INVITATION_ACCEPT = RateLimitPolicy(
        name="invitation_accept",
        limit=10,
        window_seconds=3600,
        scope=RateLimitScope.IP,
        fallback_mode=FallbackMode.BOUNDED_FALLBACK,
        description="Invitation acceptance rate limit: 10 requests / hour / IP",
    )

    # ─── Authenticated Resource Endpoints ─────────────────────────────────────
    ORDERS_CREATE = RateLimitPolicy(
        name="orders_create",
        limit=60,
        window_seconds=60,
        scope=RateLimitScope.USER_AND_ORG,
        fallback_mode=FallbackMode.BOUNDED_FALLBACK,
        description="Paper order submission rate limit: 60 requests / minute / tenant",
    )

    RESEARCH_EXECUTE = RateLimitPolicy(
        name="research_execute",
        limit=10,
        window_seconds=60,
        scope=RateLimitScope.USER_AND_ORG,
        fallback_mode=FallbackMode.BOUNDED_FALLBACK,
        description="Backtest simulation execution rate limit: 10 requests / minute / tenant",
    )

    OPTIMIZATION_EXECUTE = RateLimitPolicy(
        name="optimization_execute",
        limit=5,
        window_seconds=60,
        scope=RateLimitScope.USER_AND_ORG,
        fallback_mode=FallbackMode.BOUNDED_FALLBACK,
        description="Optimization & WFA sweep rate limit: 5 requests / minute / tenant",
    )

    DATA_EXPORT = RateLimitPolicy(
        name="data_export",
        limit=10,
        window_seconds=60,
        scope=RateLimitScope.USER_AND_ORG,
        fallback_mode=FallbackMode.BOUNDED_FALLBACK,
        description="Report & audit data export rate limit: 10 requests / minute / tenant",
    )

    BILLING_CHECKOUT = RateLimitPolicy(
        name="billing_checkout",
        limit=5,
        window_seconds=60,
        scope=RateLimitScope.USER_AND_ORG,
        fallback_mode=FallbackMode.BOUNDED_FALLBACK,
        description="Stripe checkout session creation rate limit: 5 requests / minute / tenant",
    )

    AUDIT_QUERY = RateLimitPolicy(
        name="audit_query",
        limit=30,
        window_seconds=60,
        scope=RateLimitScope.USER_AND_ORG,
        fallback_mode=FallbackMode.BOUNDED_FALLBACK,
        description="Audit log query rate limit: 30 requests / minute / tenant",
    )
