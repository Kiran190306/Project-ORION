"""Unit tests for Subscription and Entitlement domain models, value objects, and exceptions."""

from __future__ import annotations

import pytest

from libraries.domain.subscription.exceptions import (
    AccountQuotaExceededError,
    AssetNotEntitledError,
    DailyOrderQuotaExceededError,
    EntitlementError,
    QuotaExceededError,
    SubscriptionInactiveError,
    SubscriptionRequiredError,
    WorkerQuotaExceededError,
)
from libraries.domain.subscription.models import (
    Entitlement,
    Plan,
    PlanCode,
    PlanLimits,
    Subscription,
    SubscriptionStatus,
)


class TestPlanCode:
    """Tests for PlanCode enum."""

    def test_enum_values(self) -> None:
        assert PlanCode.FREE.value == "FREE"
        assert PlanCode.PRO.value == "PRO"
        assert PlanCode.BUSINESS.value == "BUSINESS"
        assert PlanCode.ENTERPRISE.value == "ENTERPRISE"

    def test_from_str_case_insensitive(self) -> None:
        assert PlanCode.from_str("free") == PlanCode.FREE
        assert PlanCode.from_str("  PrO ") == PlanCode.PRO
        assert PlanCode.from_str("bUsInEsS") == PlanCode.BUSINESS
        assert PlanCode.from_str("ENTERPRISE") == PlanCode.ENTERPRISE

    def test_from_str_invalid(self) -> None:
        with pytest.raises(ValueError, match="Invalid plan code"):
            PlanCode.from_str("ULTRA")


class TestSubscriptionStatus:
    """Tests for SubscriptionStatus enum."""

    def test_status_values(self) -> None:
        assert SubscriptionStatus.ACTIVE.value == "ACTIVE"
        assert SubscriptionStatus.TRIALING.value == "TRIALING"
        assert SubscriptionStatus.SUSPENDED.value == "SUSPENDED"
        assert SubscriptionStatus.CANCELLED.value == "CANCELLED"
        assert SubscriptionStatus.EXPIRED.value == "EXPIRED"

    def test_from_str_case_insensitive(self) -> None:
        assert SubscriptionStatus.from_str("active") == SubscriptionStatus.ACTIVE
        assert SubscriptionStatus.from_str(" trialing ") == SubscriptionStatus.TRIALING
        assert SubscriptionStatus.from_str("cancelled") == SubscriptionStatus.CANCELLED

    def test_from_str_invalid(self) -> None:
        with pytest.raises(ValueError, match="Invalid subscription status"):
            SubscriptionStatus.from_str("UNKNOWN")


class TestPlanLimits:
    """Tests for PlanLimits value object quota verification."""

    @pytest.fixture
    def free_limits(self) -> PlanLimits:
        return PlanLimits(
            max_accounts=1,
            max_daily_orders=100,
            max_workers=0,
            allowed_assets=("EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF"),
            retention_days=30,
        )

    @pytest.fixture
    def enterprise_limits(self) -> PlanLimits:
        return PlanLimits(
            max_accounts=-1,
            max_daily_orders=-1,
            max_workers=-1,
            allowed_assets=("*",),
            retention_days=2555,
        )

    def test_account_quota_free(self, free_limits: PlanLimits) -> None:
        assert free_limits.is_account_allowed(0) is True
        assert free_limits.is_account_allowed(1) is False
        assert free_limits.is_account_allowed(2) is False

    def test_account_quota_unlimited(self, enterprise_limits: PlanLimits) -> None:
        assert enterprise_limits.is_account_allowed(0) is True
        assert enterprise_limits.is_account_allowed(100) is True
        assert enterprise_limits.is_account_allowed(10000) is True

    def test_daily_order_quota_free(self, free_limits: PlanLimits) -> None:
        assert free_limits.is_daily_order_allowed(0) is True
        assert free_limits.is_daily_order_allowed(99) is True
        assert free_limits.is_daily_order_allowed(100) is False
        assert free_limits.is_daily_order_allowed(101) is False

    def test_daily_order_quota_unlimited(self, enterprise_limits: PlanLimits) -> None:
        assert enterprise_limits.is_daily_order_allowed(50000) is True
        assert enterprise_limits.is_daily_order_allowed(1000000) is True

    def test_worker_quota_free(self, free_limits: PlanLimits) -> None:
        assert free_limits.is_worker_allowed(0) is False
        assert free_limits.is_worker_allowed(1) is False

    def test_worker_quota_pro(self) -> None:
        pro_limits = PlanLimits(
            max_accounts=3,
            max_daily_orders=2500,
            max_workers=1,
            allowed_assets=("EUR/USD",),
            retention_days=365,
        )
        assert pro_limits.is_worker_allowed(0) is True
        assert pro_limits.is_worker_allowed(1) is False

    def test_worker_quota_unlimited(self, enterprise_limits: PlanLimits) -> None:
        assert enterprise_limits.is_worker_allowed(0) is True
        assert enterprise_limits.is_worker_allowed(50) is True

    def test_asset_entitlement_free(self, free_limits: PlanLimits) -> None:
        # Slashed format
        assert free_limits.is_asset_allowed("EUR/USD") is True
        assert free_limits.is_asset_allowed("GBP/USD") is True
        # Unslashed 6-char format
        assert free_limits.is_asset_allowed("EURUSD") is True
        assert free_limits.is_asset_allowed("USDJPY") is True
        # Disallowed pairs
        assert free_limits.is_asset_allowed("AUD/USD") is False
        assert free_limits.is_asset_allowed("AUDUSD") is False
        assert free_limits.is_asset_allowed("BTC/USD") is False

    def test_asset_entitlement_wildcard(self, enterprise_limits: PlanLimits) -> None:
        assert enterprise_limits.is_asset_allowed("EUR/USD") is True
        assert enterprise_limits.is_asset_allowed("NZD/CAD") is True
        assert enterprise_limits.is_asset_allowed("XAU/USD") is True
        assert enterprise_limits.is_asset_allowed("ANYTHING") is True


class TestPlanEntity:
    """Tests for Plan domain entity validation."""

    def test_plan_instantiation(self) -> None:
        limits = PlanLimits(1, 100, 0, ("EUR/USD",), 30)
        plan = Plan(
            id="plan-1",
            code=PlanCode.FREE,
            name="Free Plan",
            description="Sandbox tier",
            limits=limits,
        )
        assert plan.id == "plan-1"
        assert plan.code == PlanCode.FREE
        assert plan.is_active is True

    def test_plan_validation_empty_id(self) -> None:
        limits = PlanLimits(1, 100, 0, ("EUR/USD",), 30)
        with pytest.raises(ValueError, match="Plan id must not be empty"):
            Plan(id="", code=PlanCode.FREE, name="Free", description="", limits=limits)

    def test_plan_validation_empty_name(self) -> None:
        limits = PlanLimits(1, 100, 0, ("EUR/USD",), 30)
        with pytest.raises(ValueError, match="Plan name must not be empty"):
            Plan(id="p-1", code=PlanCode.FREE, name="  ", description="", limits=limits)


class TestSubscriptionEntity:
    """Tests for Subscription domain entity validation and active state."""

    def test_subscription_active_states(self) -> None:
        sub_active = Subscription(
            id="sub-1",
            organization_id="org-1",
            plan_id="plan-free",
            status=SubscriptionStatus.ACTIVE,
        )
        assert sub_active.is_active is True

        sub_trial = Subscription(
            id="sub-2",
            organization_id="org-1",
            plan_id="plan-pro",
            status=SubscriptionStatus.TRIALING,
        )
        assert sub_trial.is_active is True

        for inactive_status in (
            SubscriptionStatus.SUSPENDED,
            SubscriptionStatus.CANCELLED,
            SubscriptionStatus.EXPIRED,
        ):
            sub_inactive = Subscription(
                id="sub-3",
                organization_id="org-1",
                plan_id="plan-free",
                status=inactive_status,
            )
            assert sub_inactive.is_active is False

    def test_subscription_validation(self) -> None:
        with pytest.raises(ValueError, match="Subscription id must not be empty"):
            Subscription(id="", organization_id="org-1", plan_id="p-1")

        with pytest.raises(ValueError, match="Organization id must not be empty"):
            Subscription(id="s-1", organization_id="", plan_id="p-1")

        with pytest.raises(ValueError, match="Plan id must not be empty"):
            Subscription(id="s-1", organization_id="org-1", plan_id="")


class TestEntitlementAggregate:
    """Tests for Entitlement aggregate snapshot."""

    def test_entitlement_snapshot(self) -> None:
        limits = PlanLimits(1, 100, 0, ("EUR/USD",), 30)
        plan = Plan(id="p-1", code=PlanCode.FREE, name="Free", description="", limits=limits)
        sub = Subscription(id="s-1", organization_id="org-1", plan_id="p-1", status=SubscriptionStatus.ACTIVE)
        ent = Entitlement(organization_id="org-1", plan=plan, subscription=sub, limits=limits)

        assert ent.is_subscription_active is True
        assert ent.limits.max_daily_orders == 100

    def test_entitlement_no_subscription(self) -> None:
        limits = PlanLimits(1, 100, 0, ("EUR/USD",), 30)
        plan = Plan(id="p-1", code=PlanCode.FREE, name="Free", description="", limits=limits)
        ent = Entitlement(organization_id="org-1", plan=plan, subscription=None, limits=limits)

        assert ent.is_subscription_active is False


class TestEntitlementExceptions:
    """Tests for subscription exception inheritance and formatting."""

    def test_exceptions_hierarchy(self) -> None:
        assert issubclass(QuotaExceededError, EntitlementError)
        assert issubclass(AccountQuotaExceededError, QuotaExceededError)
        assert issubclass(DailyOrderQuotaExceededError, QuotaExceededError)
        assert issubclass(WorkerQuotaExceededError, QuotaExceededError)
        assert issubclass(AssetNotEntitledError, EntitlementError)
        assert issubclass(SubscriptionInactiveError, EntitlementError)
        assert issubclass(SubscriptionRequiredError, EntitlementError)

    def test_exception_messages_and_codes(self) -> None:
        acc_err = AccountQuotaExceededError(current=3, limit=3)
        assert acc_err.code == "ACCOUNT_QUOTA_EXCEEDED"
        assert "3 accounts" in acc_err.message

        daily_err = DailyOrderQuotaExceededError(current=100, limit=100)
        assert daily_err.code == "DAILY_ORDER_QUOTA_EXCEEDED"
        assert "100 orders" in daily_err.message

        worker_err = WorkerQuotaExceededError(plan_name="Free Sandbox", limit=0)
        assert worker_err.code == "WORKER_QUOTA_EXCEEDED"
        assert "worker limit: 0" in worker_err.message

        asset_err = AssetNotEntitledError(symbol="GBP/JPY", plan_name="Free Sandbox")
        assert asset_err.code == "ASSET_NOT_ENTITLED"
        assert "GBP/JPY" in asset_err.message

        sub_inact = SubscriptionInactiveError(status="CANCELLED")
        assert sub_inact.code == "SUBSCRIPTION_INACTIVE"
        assert "CANCELLED" in sub_inact.message
