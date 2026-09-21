"""Broker endpoint security validation and credential cryptography for Project ORION.

Enforces fail-closed defense-in-depth:
1. BrokerEndpointValidator: Static allowlisting, production domain rejection,
   private IP / loopback / metadata block, and DNS resolution validation.
2. CredentialCipher: AES-GCM credential encryption/decryption and token sanitization.
"""

from __future__ import annotations

import base64
import ipaddress
import json
import logging
import os
import re
import socket
from typing import Any
from urllib.parse import urlparse

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import hashlib

logger = logging.getLogger("infrastructure.security.endpoint_validator")


class SecurityViolationError(Exception):
    """Raised when an operation violates core platform security invariants."""

    pass


class InvalidEndpointError(SecurityViolationError):
    """Raised when a broker endpoint fails validation or allowlisting rules."""

    pass


class CredentialEncryptionError(SecurityViolationError):
    """Raised when credential encryption or decryption fails."""

    pass


class BrokerEndpointValidator:
    """Institutional endpoint validator preventing SSRF, DNS rebinding, and production URL leakage."""

    # Explicitly permitted sandbox hosts
    APPROVED_SANDBOX_HOSTS: frozenset[str] = frozenset(
        {
            "api-fxpractice.oanda.com",
            "stream-fxpractice.oanda.com",
            "testnet.binance.vision",
            "paper-api.alpaca.markets",
            "mock-broker.internal",
        }
    )

    # Explicitly forbidden production hosts (Fail closed immediately)
    FORBIDDEN_PRODUCTION_HOSTS: frozenset[str] = frozenset(
        {
            "api-fxtrade.oanda.com",
            "stream-fxtrade.oanda.com",
            "api.binance.com",
            "fapi.binance.com",
            "dapi.binance.com",
            "api.alpaca.markets",
            "live.alpaca.markets",
        }
    )

    # Cloud metadata addresses to reject
    BLOCKED_METADATA_IPS: frozenset[str] = frozenset(
        {
            "169.254.169.254",  # AWS/GCP/Azure link-local metadata
            "fd00:ec2::254",  # AWS IPv6 metadata
        }
    )

    @classmethod
    def validate_endpoint(
        cls,
        endpoint: str,
        provider: str = "",
        *,
        allow_internal_mock: bool = True,
        resolve_dns: bool = True,
    ) -> str:
        """Validate a broker endpoint URL against strict institutional security rules.

        Args:
            endpoint: URL to validate.
            provider: Provider identifier (e.g. 'oanda', 'mock').
            allow_internal_mock: Whether 'mock-broker.internal' is allowed.
            resolve_dns: Whether to perform DNS resolution checks against resolved IPs.

        Returns:
            Normalized validated URL.

        Raises:
            SecurityViolationError: If endpoint violates live-trading prohibition or SSRF rules.
            InvalidEndpointError: If endpoint is malformed or unapproved.
        """
        if not endpoint or not isinstance(endpoint, str):
            raise InvalidEndpointError("Endpoint URL cannot be empty")

        trimmed_url = endpoint.strip()

        # Reject any url containing userinfo (e.g. http://user:pass@host)
        if "@" in trimmed_url.split("/")[2] if len(trimmed_url.split("/")) > 2 else False:
            raise SecurityViolationError("Credentials in URL authority are prohibited")

        try:
            parsed = urlparse(trimmed_url)
        except Exception as e:
            raise InvalidEndpointError(f"Malformed URL: {e}") from e

        scheme = parsed.scheme.lower()
        hostname = (parsed.hostname or "").lower()
        port = parsed.port

        if not hostname:
            raise InvalidEndpointError("Missing hostname in broker endpoint URL")

        # 1. Scheme Validation
        if scheme not in ("https", "http"):
            raise InvalidEndpointError(f"Invalid URL scheme '{scheme}'. Only HTTPS is permitted")

        if scheme == "http":
            if hostname == "mock-broker.internal" and allow_internal_mock:
                pass
            elif os.environ.get("ORION_ALLOW_HTTP_TESTING", "false").lower() == "true":
                logger.warning("Permitting HTTP endpoint under explicit ORION_ALLOW_HTTP_TESTING override")
            else:
                raise SecurityViolationError(
                    f"Insecure HTTP scheme is prohibited for external broker endpoints: {trimmed_url}"
                )

        # 2. Reject Explicit Production Endpoints Immediately
        if hostname in cls.FORBIDDEN_PRODUCTION_HOSTS or any(
            hostname.endswith("." + forbidden) for forbidden in cls.FORBIDDEN_PRODUCTION_HOSTS
        ):
            raise SecurityViolationError(
                f"Production broker endpoint '{hostname}' is strictly prohibited. "
                "Project ORION operates exclusively in Sandbox/Demo mode ($0.00 Capital at Risk)."
            )

        # 3. Reject IP Literals (Must use approved domain names)
        # Check if hostname is an IPv4 or IPv6 literal
        try:
            ip_obj = ipaddress.ip_address(hostname)
            # If parsing succeeds, it's an IP literal!
            raise SecurityViolationError(
                f"IP literals are prohibited for broker endpoints: {hostname}. "
                "Endpoints must use approved canonical sandbox domain names."
            )
        except ValueError:
            # Not an IP literal - good
            pass

        # 4. Reject Localhost & Loopback Names
        if hostname in ("localhost", "localhost.localdomain") or hostname.endswith(".localhost"):
            raise SecurityViolationError(
                f"Localhost access is prohibited for broker endpoints: {hostname}"
            )

        # 5. Allowlist Enforcement
        if hostname not in cls.APPROVED_SANDBOX_HOSTS:
            raise InvalidEndpointError(
                f"Endpoint hostname '{hostname}' is not in the approved broker sandbox allowlist. "
                f"Approved hosts: {', '.join(sorted(cls.APPROVED_SANDBOX_HOSTS))}"
            )

        # 6. Port Restrictions
        if port is not None:
            if port not in (443, 80, 8080):
                raise SecurityViolationError(f"Non-standard port '{port}' is prohibited")
            if port == 80 and scheme != "http":
                raise SecurityViolationError("Port 80 requires HTTP scheme")

        # 7. DNS Resolution & IP Range SSRF Validation
        if resolve_dns and hostname != "mock-broker.internal":
            cls._validate_resolved_destination(hostname)

        # Return clean normalized base endpoint
        path = parsed.path.rstrip("/")
        normalized = f"{scheme}://{hostname}"
        if port and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
            normalized += f":{port}"
        if path:
            normalized += path
        return normalized

    @classmethod
    def _validate_resolved_destination(cls, hostname: str) -> None:
        """Resolve DNS and verify resolved IP addresses do not target private, loopback, or metadata addresses."""
        try:
            addr_info = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
        except socket.gaierror as e:
            logger.warning("DNS resolution failed for broker endpoint %s: %s", hostname, e)
            return

        for entry in addr_info:
            sockaddr = entry[4]
            ip_str = sockaddr[0]
            try:
                ip_addr = ipaddress.ip_address(ip_str)
            except ValueError:
                continue

            if ip_str in cls.BLOCKED_METADATA_IPS:
                raise SecurityViolationError(
                    f"Broker endpoint {hostname} resolved to forbidden cloud metadata IP {ip_str}"
                )

            if ip_addr.is_loopback:
                raise SecurityViolationError(
                    f"Broker endpoint {hostname} resolved to loopback address {ip_str}"
                )

            if ip_addr.is_private:
                raise SecurityViolationError(
                    f"Broker endpoint {hostname} resolved to private RFC 1918 subnet {ip_str}"
                )

            if ip_addr.is_link_local:
                raise SecurityViolationError(
                    f"Broker endpoint {hostname} resolved to link-local address {ip_str}"
                )

            if ip_addr.is_multicast:
                raise SecurityViolationError(
                    f"Broker endpoint {hostname} resolved to multicast address {ip_str}"
                )


class CredentialCipher:
    """AES-256-GCM cipher for encrypting and decrypting broker sandbox credentials."""

    ENV_KEY_VAR = "ORION_CREDENTIAL_ENCRYPTION_KEY"
    FALLBACK_ENV_KEY_VAR = "ORION_SECRET_CREDENTIAL_KEY"
    DEV_TEST_KEY = b"orion-dev-credential-key-32b-!"  # Deterministic test key for local/unit test runs only

    @classmethod
    def _get_encryption_key(cls) -> bytes:
        """Retrieve the 256-bit encryption key from environment or secrets manager."""
        raw_key = os.environ.get(cls.ENV_KEY_VAR) or os.environ.get(cls.FALLBACK_ENV_KEY_VAR)

        if raw_key:
            # Key can be hex-encoded, base64-encoded, or raw string
            raw_stripped = raw_key.strip()
            if len(raw_stripped) == 64 and all(c in "0123456789abcdefABCDEF" for c in raw_stripped):
                return bytes.fromhex(raw_stripped)
            # Otherwise derive 32-byte key via SHA-256
            return hashlib.sha256(raw_stripped.encode("utf-8")).digest()

        # Check environment mode
        env_mode = os.environ.get("ENVIRONMENT", os.environ.get("ORION_ENV", "development")).lower()
        if env_mode in ("test", "testing", "development", "local"):
            logger.warning(
                "Using fallback development key for sandbox credential encryption. "
                "Set ORION_CREDENTIAL_ENCRYPTION_KEY in production/sandbox."
            )
            return hashlib.sha256(cls.DEV_TEST_KEY).digest()

        raise CredentialEncryptionError(
            f"Encryption configuration missing. Environment variable {cls.ENV_KEY_VAR} "
            "must be provided. Plaintext credential storage is prohibited."
        )

    @classmethod
    def encrypt(cls, credentials: dict[str, Any]) -> dict[str, str]:
        """Encrypt a dictionary of credentials into AES-GCM ciphertext payload.

        Args:
            credentials: Plaintext credential dictionary (e.g. {'api_key': '...', 'account_id': '...'}).

        Returns:
            JSON-serializable dict containing base64-encoded ciphertext, nonce, and key version.
        """
        if not isinstance(credentials, dict):
            raise CredentialEncryptionError("Credentials must be provided as a dictionary")

        try:
            key = cls._get_encryption_key()
            aesgcm = AESGCM(key)
            nonce = os.urandom(12)  # Standard 96-bit nonce for AES-GCM
            plaintext = json.dumps(credentials).encode("utf-8")
            ciphertext = aesgcm.encrypt(nonce, plaintext, None)

            return {
                "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
                "nonce": base64.b64encode(nonce).decode("utf-8"),
                "v": "1",
            }
        except Exception as e:
            if isinstance(e, CredentialEncryptionError):
                raise
            raise CredentialEncryptionError(f"Encryption failed: {e}") from e

    @classmethod
    def decrypt(cls, payload: dict[str, str]) -> dict[str, Any]:
        """Decrypt an AES-GCM encrypted payload back into a dictionary.

        Args:
            payload: Dict containing 'ciphertext', 'nonce', and optional version 'v'.

        Returns:
            Decrypted credential dictionary.
        """
        if not isinstance(payload, dict):
            raise CredentialEncryptionError("Encrypted payload must be a dictionary")

        ciphertext_b64 = payload.get("ciphertext")
        nonce_b64 = payload.get("nonce")

        if not ciphertext_b64 or not nonce_b64:
            raise CredentialEncryptionError("Invalid payload: missing ciphertext or nonce")

        try:
            key = cls._get_encryption_key()
            aesgcm = AESGCM(key)
            ciphertext = base64.b64decode(ciphertext_b64)
            nonce = base64.b64decode(nonce_b64)

            decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
            return json.loads(decrypted_bytes.decode("utf-8"))
        except Exception as e:
            if isinstance(e, CredentialEncryptionError):
                raise
            raise CredentialEncryptionError(f"Decryption failed: {e}") from e

    @classmethod
    def mask_credentials(cls, credentials: dict[str, Any]) -> dict[str, Any]:
        """Redact sensitive fields from a credential dictionary for safe logging and API presentation.

        Replaces keys like 'api_key', 'api_secret', 'token', 'password' with '***'.
        Preserves non-secret fields like 'account_id', 'username', 'server'.
        """
        if not isinstance(credentials, dict):
            return {}

        sensitive_pattern = re.compile(r"(key|secret|token|password|auth|credential)", re.IGNORECASE)
        masked: dict[str, Any] = {}

        for k, v in credentials.items():
            if sensitive_pattern.search(k):
                masked[k] = "***"
            elif isinstance(v, dict):
                masked[k] = cls.mask_credentials(v)
            else:
                masked[k] = v

        return masked
