"""RateLimitService orchestrating policy evaluation, key generation, and fallback strategy.

Integrates:
- RedisRateLimiter for distributed atomic sliding-window limiting
- InMemoryRateLimiter for bounded local fallback during Redis outages
- Prometheus metrics recording for telemetry
- Structured security logging
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from libraries.domain.security.rate_limit import (
    FallbackMode,
    RateLimitPolicy,
    RateLimitResult,
    RateLimitScope,
)
from libraries.infrastructure.caching.exceptions import RedisError
from libraries.infrastructure.security.ip_resolver import ClientIpResolver
from libraries.infrastructure.security.rate_limiter import (
    InMemoryRateLimiter,
    RedisRateLimiter,
)

if TYPE_CHECKING:
    from libraries.observability.metrics import MetricsRegistry

logger = logging.getLogger("trading_engine.security.rate_limit_service")


class RateLimitService:
    """Evaluates rate limiting policies using primary Redis and bounded memory fallback."""

    def __init__(
        self,
        redis_limiter: RedisRateLimiter | None = None,
        fallback_limiter: InMemoryRateLimiter | None = None,
        ip_resolver: ClientIpResolver | None = None,
        metrics_registry: MetricsRegistry | None = None,
        enabled: bool = True,
        redis_client: Any = None,
        trusted_proxies: tuple[str, ...] | None = None,
    ) -> None:
        if redis_limiter is None and redis_client is not None:
            redis_limiter = RedisRateLimiter(redis_client=redis_client)
        if ip_resolver is None and trusted_proxies is not None:
            ip_resolver = ClientIpResolver(trusted_proxies=trusted_proxies)

        self._redis_limiter = redis_limiter
        self._fallback_limiter = fallback_limiter or InMemoryRateLimiter(max_keys=10000)
        self._ip_resolver = ip_resolver or ClientIpResolver()
        self._metrics = metrics_registry
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def ip_resolver(self) -> ClientIpResolver:
        return self._ip_resolver

    def build_key(
        self,
        policy: RateLimitPolicy,
        ip: str,
        user_id: str | None = None,
        org_id: str | None = None,
    ) -> str:
        """Construct structured, safe rate limit key without sensitive data."""
        clean_ip = ip.strip().replace(":", "_")

        match policy.scope:
            case RateLimitScope.IP:
                return f"rl:v1:{policy.name}:ip:{clean_ip}"
            case RateLimitScope.USER:
                u_id = (user_id or "anon").strip()
                return f"rl:v1:{policy.name}:user:{u_id}"
            case RateLimitScope.ORGANIZATION:
                o_id = (org_id or "anon").strip()
                return f"rl:v1:{policy.name}:org:{o_id}"
            case RateLimitScope.USER_AND_ORG:
                u_id = (user_id or "anon").strip()
                o_id = (org_id or "anon").strip()
                return f"rl:v1:{policy.name}:u:{u_id}:o:{o_id}"
            case _:
                return f"rl:v1:{policy.name}:ip:{clean_ip}"

    def _record_metric(self, metric_name: str) -> None:
        """Helper to increment Prometheus metric safely."""
        if self._metrics is not None:
            try:
                self._metrics.inc(metric_name)
            except (KeyError, ValueError, AttributeError, RuntimeError) as exc:
                logger.debug("Failed to record metric %s: %s", metric_name, exc)

    async def check_rate_limit(
        self,
        policy: RateLimitPolicy,
        ip: str,
        user_id: str | None = None,
        org_id: str | None = None,
    ) -> RateLimitResult:
        """Check rate limit against policy with automatic fail-safe fallback."""
        now_ts = int(time.time())

        # If rate limiting is globally disabled via configuration
        if not self._enabled:
            return RateLimitResult(
                allowed=True,
                limit=policy.limit,
                remaining=policy.limit,
                retry_after_seconds=0,
                reset_after_seconds=policy.window_seconds,
                reset_timestamp=now_ts + policy.window_seconds,
                source="disabled",
            )

        key = self.build_key(policy=policy, ip=ip, user_id=user_id, org_id=org_id)
        result: RateLimitResult | None = None

        # 1. Attempt evaluation via distributed Redis
        if self._redis_limiter is not None:
            try:
                result = await self._redis_limiter.check_rate_limit(
                    key=key,
                    limit=policy.limit,
                    window_seconds=policy.window_seconds,
                )
            except (RedisError, ConnectionError, TimeoutError, OSError) as exc:
                self._record_metric("rate_limit_redis_errors_total")
                logger.warning(
                    "Redis rate limit check failed for policy %s [key=%s]: %s. Invoking fallback.",
                    policy.name,
                    key,
                    exc,
                )

                if policy.fallback_mode == FallbackMode.FAIL_CLOSED:
                    self._record_metric("rate_limit_rejected_total")
                    logger.error(
                        "Policy %s configured as FAIL_CLOSED and Redis unavailable. Rejecting request.",
                        policy.name,
                    )
                    return RateLimitResult(
                        allowed=False,
                        limit=policy.limit,
                        remaining=0,
                        retry_after_seconds=policy.window_seconds,
                        reset_after_seconds=policy.window_seconds,
                        reset_timestamp=now_ts + policy.window_seconds,
                        source="fail_closed",
                    )

        # 2. Fall back to bounded in-memory sliding window limiter
        if result is None:
            self._record_metric("rate_limit_fallback_total")
            result = await self._fallback_limiter.check_rate_limit(
                key=key,
                limit=policy.limit,
                window_seconds=policy.window_seconds,
            )

        # 3. Telemetry and audit logging
        if result.allowed:
            self._record_metric("rate_limit_allowed_total")
        else:
            self._record_metric("rate_limit_rejected_total")
            logger.warning(
                "Rate limit exceeded: policy=%s key=%s limit=%d retry_after=%ds source=%s",
                policy.name,
                key,
                policy.limit,
                result.retry_after_seconds,
                result.source,
            )

        return result
