"""Configuration management for commercial billing and Stripe integration."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from libraries.domain.billing.exceptions import (
    InvalidPlanCodeError,
    LiveCredentialsForbiddenError,
)
from libraries.domain.subscription.models import PlanCode


@dataclass(frozen=True)
class BillingConfig:
    """Strongly-typed billing configuration enforcing Stripe Test Mode."""

    secret_key: str = ""
    publishable_key: str = ""
    webhook_secret: str = ""
    price_pro: str = "price_test_pro_monthly"
    price_business: str = "price_test_business_monthly"
    price_enterprise: str = "price_test_enterprise_monthly"
    use_mock: bool = False

    def __post_init__(self) -> None:
        """Validate that live credentials are never supplied."""
        if self.secret_key.strip().startswith("sk_live_"):
            raise LiveCredentialsForbiddenError(
                "Live Stripe secret key (sk_live_...) detected. "
                "Project ORION operates strictly in Stripe TEST MODE only."
            )
        if self.publishable_key.strip().startswith("pk_live_"):
            raise LiveCredentialsForbiddenError(
                "Live Stripe publishable key (pk_live_...) detected. "
                "Project ORION operates strictly in Stripe TEST MODE only."
            )

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> BillingConfig:
        """Load billing settings from environment variables."""
        source = env if env is not None else os.environ

        secret_key = (
            source.get("ORION_STRIPE_SECRET_KEY")
            or source.get("STRIPE_SECRET_KEY")
            or ""
        ).strip()

        publishable_key = (
            source.get("ORION_STRIPE_PUBLISHABLE_KEY")
            or source.get("STRIPE_PUBLISHABLE_KEY")
            or ""
        ).strip()

        webhook_secret = (
            source.get("ORION_STRIPE_WEBHOOK_SECRET")
            or source.get("STRIPE_WEBHOOK_SECRET")
            or ""
        ).strip()

        use_mock_raw = source.get("ORION_BILLING_USE_MOCK", "").lower()
        use_mock = use_mock_raw in ("true", "1", "yes") or not secret_key

        return cls(
            secret_key=secret_key,
            publishable_key=publishable_key,
            webhook_secret=webhook_secret,
            price_pro=source.get("ORION_STRIPE_PRICE_PRO", "price_test_pro_monthly").strip(),
            price_business=source.get(
                "ORION_STRIPE_PRICE_BUSINESS", "price_test_business_monthly"
            ).strip(),
            price_enterprise=source.get(
                "ORION_STRIPE_PRICE_ENTERPRISE", "price_test_enterprise_monthly"
            ).strip(),
            use_mock=use_mock,
        )

    @property
    def is_mock_enabled(self) -> bool:
        """Evaluate if billing operates with deterministic in-memory mock."""
        return self.use_mock or not self.secret_key.startswith("sk_test_")

    def get_price_id_for_plan(self, plan_code: PlanCode) -> str:
        """Resolve Stripe Price ID for a given paid tier."""
        if plan_code == PlanCode.PRO:
            return self.price_pro
        if plan_code == PlanCode.BUSINESS:
            return self.price_business
        if plan_code == PlanCode.ENTERPRISE:
            return self.price_enterprise
        raise InvalidPlanCodeError(
            f"Plan tier '{plan_code.value}' is a free tier and has no Stripe Price ID."
        )

    def get_plan_code_for_price_id(self, price_id: str) -> PlanCode:
        """Resolve canonical PlanCode from a Stripe Price ID."""
        norm = price_id.strip()
        if norm == self.price_pro:
            return PlanCode.PRO
        if norm == self.price_business:
            return PlanCode.BUSINESS
        if norm == self.price_enterprise:
            return PlanCode.ENTERPRISE
        # Allow fallback matching for test mocks
        if "pro" in norm.lower():
            return PlanCode.PRO
        if "business" in norm.lower():
            return PlanCode.BUSINESS
        if "enterprise" in norm.lower():
            return PlanCode.ENTERPRISE
        raise InvalidPlanCodeError(f"Unknown Stripe Price ID: '{price_id}'")
