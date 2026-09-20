"""Domain exceptions for commercial billing operations."""

from __future__ import annotations


class BillingError(Exception):
    """Base exception for all billing domain errors."""


class CustomerNotFoundError(BillingError):
    """Raised when a billing customer cannot be found."""


class SubscriptionNotFoundError(BillingError):
    """Raised when a billing subscription cannot be found."""


class InvalidWebhookSignatureError(BillingError):
    """Raised when an incoming webhook signature fails cryptographic verification."""


class DuplicateWebhookEventError(BillingError):
    """Raised when a webhook event ID has already been recorded."""


class BillingProviderError(BillingError):
    """Raised when the external billing provider fails or returns an unhandled error."""


class LiveCredentialsForbiddenError(BillingError):
    """Raised when live Stripe credentials (sk_live_) are detected in configuration."""


class InvalidPlanCodeError(BillingError):
    """Raised when an invalid or unmappable plan code is requested."""
