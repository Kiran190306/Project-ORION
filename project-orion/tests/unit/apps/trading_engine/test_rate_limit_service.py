"""Unit tests for RateLimitService orchestration, fallback policies, and metrics."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from apps.trading_engine.src.services.rate_limit_service import RateLimitService

from libraries.domain.security.rate_limit import (
    FallbackMode,
    RateLimitPolicy,
    RateLimitScope,
)


class TestRateLimitService:
    """Test suite for RateLimitService key generation, routing, and degradation strategies."""

    def test_build_key_ip_ipv4(self) -> None:
        """IP scope generates clean IP key for IPv4."""
        service = RateLimitService(redis_client=None)
        policy = RateLimitPolicy(
            name="auth_login",
            limit=5,
            window_seconds=60,
            scope=RateLimitScope.IP,
        )
        key = service.build_key(policy, ip="192.0.2.1")
        assert key == "rl:v1:auth_login:ip:192.0.2.1"

    def test_build_key_ip_ipv6(self) -> None:
        """IP scope sanitizes IPv6 colons to avoid Redis key hierarchy collision."""
        service = RateLimitService(redis_client=None)
        policy = RateLimitPolicy(
            name="auth_login",
            limit=5,
            window_seconds=60,
            scope=RateLimitScope.IP,
        )
        key = service.build_key(policy, ip="2001:db8::1")
        assert key == "rl:v1:auth_login:ip:2001_db8__1"

    def test_build_key_user_and_org(self) -> None:
        """USER_AND_ORG scope incorporates both user and tenant identifiers."""
        service = RateLimitService(redis_client=None)
        policy = RateLimitPolicy(
            name="orders_create",
            limit=60,
            window_seconds=60,
            scope=RateLimitScope.USER_AND_ORG,
        )
        key = service.build_key(
            policy,
            ip="192.0.2.1",
            user_id="usr_abc",
            org_id="org_xyz",
        )
        assert key == "rl:v1:orders_create:u:usr_abc:o:org_xyz"

    def test_build_key_user_and_org_missing_falls_back_to_anon(self) -> None:
        """USER_AND_ORG scope gracefully handles missing user or org with anon tokens."""
        service = RateLimitService(redis_client=None)
        policy = RateLimitPolicy(
            name="orders_create",
            limit=60,
            window_seconds=60,
            scope=RateLimitScope.USER_AND_ORG,
        )
        key = service.build_key(policy, ip="192.0.2.1", user_id=None, org_id=None)
        assert key == "rl:v1:orders_create:u:anon:o:anon"

    @pytest.mark.asyncio
    async def test_disabled_service_bypasses_checks(self) -> None:
        """When rate limiting is disabled globally, all requests pass with source=disabled."""
        service = RateLimitService(redis_client=None, enabled=False)
        policy = RateLimitPolicy(
            name="test",
            limit=5,
            window_seconds=60,
            scope=RateLimitScope.IP,
        )
        res = await service.check_rate_limit(policy, ip="192.0.2.1")
        assert res.allowed is True
        assert res.source == "disabled"
        assert res.remaining == 5

    @pytest.mark.asyncio
    async def test_redis_success_routes_through_redis(self) -> None:
        """When Redis is healthy, rate limit result comes from Redis."""
        mock_redis = MagicMock()
        mock_redis.eval_script = AsyncMock(return_value=[1, 4, 0, 60])
        mock_metrics = MagicMock()

        service = RateLimitService(redis_client=mock_redis, metrics_registry=mock_metrics)
        policy = RateLimitPolicy(
            name="test_redis",
            limit=5,
            window_seconds=60,
            scope=RateLimitScope.IP,
        )

        res = await service.check_rate_limit(policy, ip="192.0.2.1")
        assert res.allowed is True
        assert res.remaining == 4
        assert res.source == "redis"
        mock_metrics.inc.assert_called_with("rate_limit_allowed_total")

    @pytest.mark.asyncio
    async def test_redis_outage_bounded_fallback(self) -> None:
        """When Redis fails and policy is BOUNDED_FALLBACK, gracefully uses in-memory limiter."""
        mock_redis = MagicMock()
        mock_redis.eval_script = AsyncMock(side_effect=ConnectionError("Redis down"))
        mock_metrics = MagicMock()

        service = RateLimitService(redis_client=mock_redis, metrics_registry=mock_metrics)
        policy = RateLimitPolicy(
            name="test_fallback",
            limit=3,
            window_seconds=60,
            scope=RateLimitScope.IP,
            fallback_mode=FallbackMode.BOUNDED_FALLBACK,
        )

        res = await service.check_rate_limit(policy, ip="192.0.2.5")
        assert res.allowed is True
        assert res.source == "memory_fallback"
        # Verify metrics recorded
        assert any(call.args[0] == "rate_limit_redis_errors_total" for call in mock_metrics.inc.mock_calls)
        assert any(call.args[0] == "rate_limit_fallback_total" for call in mock_metrics.inc.mock_calls)

    @pytest.mark.asyncio
    async def test_redis_outage_fail_closed(self) -> None:
        """When Redis fails and policy is FAIL_CLOSED, request is blocked safely."""
        mock_redis = MagicMock()
        mock_redis.eval_script = AsyncMock(side_effect=ConnectionError("Redis down"))
        mock_metrics = MagicMock()

        service = RateLimitService(redis_client=mock_redis, metrics_registry=mock_metrics)
        policy = RateLimitPolicy(
            name="test_fail_closed",
            limit=3,
            window_seconds=60,
            scope=RateLimitScope.IP,
            fallback_mode=FallbackMode.FAIL_CLOSED,
        )

        res = await service.check_rate_limit(policy, ip="192.0.2.6")
        assert res.allowed is False
        assert res.source == "fail_closed"
        assert res.retry_after_seconds == 60
        assert any(call.args[0] == "rate_limit_redis_errors_total" for call in mock_metrics.inc.mock_calls)
        assert any(call.args[0] == "rate_limit_rejected_total" for call in mock_metrics.inc.mock_calls)
