"""Unit tests for BrokerEndpointValidator and CredentialCipher."""

from __future__ import annotations

import os
import pytest

from libraries.infrastructure.security.endpoint_validator import (
    BrokerEndpointValidator,
    CredentialCipher,
    CredentialEncryptionError,
    InvalidEndpointError,
    SecurityViolationError,
)


def test_approved_sandbox_endpoints_pass() -> None:
    # OANDA fxPractice
    url1 = BrokerEndpointValidator.validate_endpoint(
        "https://api-fxpractice.oanda.com", resolve_dns=False
    )
    assert url1 == "https://api-fxpractice.oanda.com"

    # With trailing slash and path
    url2 = BrokerEndpointValidator.validate_endpoint(
        "https://api-fxpractice.oanda.com/v3/accounts/", resolve_dns=False
    )
    assert url2 == "https://api-fxpractice.oanda.com/v3/accounts"

    # Mock internal
    url3 = BrokerEndpointValidator.validate_endpoint(
        "http://mock-broker.internal", resolve_dns=False
    )
    assert url3 == "http://mock-broker.internal"


def test_production_endpoints_strictly_fail_closed() -> None:
    # OANDA production
    with pytest.raises(SecurityViolationError, match="Production broker endpoint"):
        BrokerEndpointValidator.validate_endpoint(
            "https://api-fxtrade.oanda.com", resolve_dns=False
        )

    # Binance production
    with pytest.raises(SecurityViolationError, match="Production broker endpoint"):
        BrokerEndpointValidator.validate_endpoint(
            "https://api.binance.com", resolve_dns=False
        )

    # Alpaca production
    with pytest.raises(SecurityViolationError, match="Production broker endpoint"):
        BrokerEndpointValidator.validate_endpoint(
            "https://api.alpaca.markets", resolve_dns=False
        )


def test_ip_literals_rejected() -> None:
    # IPv4 literal
    with pytest.raises(SecurityViolationError, match="IP literals are prohibited"):
        BrokerEndpointValidator.validate_endpoint("https://192.168.1.1", resolve_dns=False)

    # IPv6 literal
    with pytest.raises(SecurityViolationError, match="IP literals are prohibited"):
        BrokerEndpointValidator.validate_endpoint("https://[2001:db8::1]", resolve_dns=False)


def test_localhost_and_loopback_rejected() -> None:
    with pytest.raises(SecurityViolationError, match="Localhost access is prohibited"):
        BrokerEndpointValidator.validate_endpoint("https://localhost", resolve_dns=False)

    with pytest.raises(SecurityViolationError, match="Localhost access is prohibited"):
        BrokerEndpointValidator.validate_endpoint("https://localhost:8443", resolve_dns=False)


def test_unallowlisted_arbitrary_domain_rejected() -> None:
    with pytest.raises(InvalidEndpointError, match="not in the approved broker sandbox allowlist"):
        BrokerEndpointValidator.validate_endpoint("https://evil-hacker.com", resolve_dns=False)


def test_insecure_http_rejected_for_external() -> None:
    with pytest.raises(SecurityViolationError, match="Insecure HTTP scheme is prohibited"):
        BrokerEndpointValidator.validate_endpoint(
            "http://api-fxpractice.oanda.com", resolve_dns=False
        )


def test_credentials_in_url_rejected() -> None:
    with pytest.raises(SecurityViolationError, match="Credentials in URL authority"):
        BrokerEndpointValidator.validate_endpoint(
            "https://user:pass@api-fxpractice.oanda.com", resolve_dns=False
        )


def test_credential_cipher_roundtrip() -> None:
    payload = {
        "api_key": "secret-oanda-token-123",
        "account_id": "001-004-1234567-001",
        "nested": {"api_secret": "my-secret-key"},
    }

    encrypted = CredentialCipher.encrypt(payload)
    assert "ciphertext" in encrypted
    assert "nonce" in encrypted
    assert "secret-oanda-token-123" not in str(encrypted)

    decrypted = CredentialCipher.decrypt(encrypted)
    assert decrypted == payload


def test_credential_masking() -> None:
    payload = {
        "api_key": "secret-123",
        "token": "token-456",
        "account_id": "001-004",
        "broker": "oanda",
        "details": {"password": "pass", "server": "practice"},
    }
    masked = CredentialCipher.mask_credentials(payload)
    assert masked["api_key"] == "***"
    assert masked["token"] == "***"
    assert masked["account_id"] == "001-004"
    assert masked["broker"] == "oanda"
    assert masked["details"]["password"] == "***"
    assert masked["details"]["server"] == "practice"


def test_credential_cipher_fail_closed_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("ORION_CREDENTIAL_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("ORION_SECRET_CREDENTIAL_KEY", raising=False)

    with pytest.raises(CredentialEncryptionError, match="Encryption configuration missing"):
        CredentialCipher.encrypt({"api_key": "test"})
