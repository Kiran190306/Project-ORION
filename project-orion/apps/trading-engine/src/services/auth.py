"""Authentication service for JWT token management, password hashing, and token lifecycles."""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

# Configuration sourced from environment with secure defaults
DEFAULT_SECRET_KEY = "insecure-dev-secret-key-change-in-production-institutional-orion-2026"
ALGORITHM = os.environ.get("ORION_JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ORION_JWT_EXPIRE_MINUTES", "30"))


def get_jwt_secret_key() -> str:
    """Retrieve and validate the JWT secret key from the environment.

    Raises RuntimeError if running in production with missing or insecure default key.
    """
    env_name = os.environ.get("ORION_ENVIRONMENT", "development").strip().lower()
    raw_key = os.environ.get("ORION_JWT_SECRET_KEY", "").strip()

    if env_name == "production":
        if not raw_key:
            raise RuntimeError(
                "ORION_JWT_SECRET_KEY is required in production environment but is not set."
            )
        if raw_key == DEFAULT_SECRET_KEY:
            raise RuntimeError(
                "ORION_JWT_SECRET_KEY cannot use the default development secret in production."
            )
        if len(raw_key) < 32:
            raise RuntimeError(
                "ORION_JWT_SECRET_KEY must be at least 32 characters in production."
            )
        return raw_key

    return raw_key if raw_key else DEFAULT_SECRET_KEY


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hashed password.

    Bcrypt has a 72-byte limit on inputs; truncate safely to prevent errors.
    """
    try:
        plain_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hash_bytes)
    except Exception:  # noqa: BLE001
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt with standard salting.

    Bcrypt has a 72-byte limit on inputs; truncate safely.
    """
    plain_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_bytes, salt).decode("utf-8")


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password against institutional security policy.

    Requirements:
    - Minimum length: 8 characters
    - Maximum length: 72 bytes (bcrypt input boundary)
    - At least one letter (a-z or A-Z)
    - At least one non-letter (digit or special character)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(password.encode("utf-8")) > 72:
        return False, "Password cannot exceed 72 bytes."
    has_letter = any(c.isalpha() for c in password)
    has_digit_or_special = any(c.isdigit() or not c.isalnum() for c in password)
    if not (has_letter and has_digit_or_special):
        return False, "Password must contain at least one letter and at least one digit or symbol."
    return True, ""


def generate_secure_token() -> str:
    """Generate a cryptographically secure, URL-safe random token."""
    return secrets.token_urlsafe(32)


def hash_security_token(raw_token: str) -> str:
    """Compute deterministic SHA-256 hash of a raw token for safe persistence."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
    secret_key: str | None = None,
    algorithm: str | None = None,
) -> str:
    """Create a signed JWT access token with expiration and issuance timestamp."""
    to_encode = data.copy()
    now_utc = datetime.now(timezone.utc)
    to_encode.setdefault("iat", int(now_utc.timestamp()))

    if expires_delta:
        expire = now_utc + expires_delta
    else:
        expire = now_utc + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    key = secret_key or get_jwt_secret_key()
    alg = algorithm or ALGORITHM
    encoded_jwt: str = jwt.encode(to_encode, key, algorithm=alg)
    return encoded_jwt


def decode_access_token(
    token: str,
    secret_key: str | None = None,
    algorithm: str | None = None,
) -> dict[str, Any] | None:
    """Decode and validate a JWT access token signature and expiration."""
    try:
        key = secret_key or get_jwt_secret_key()
        alg = algorithm or ALGORITHM
        payload: dict[str, Any] = jwt.decode(token, key, algorithms=[alg])
        return payload
    except JWTError:
        return None
