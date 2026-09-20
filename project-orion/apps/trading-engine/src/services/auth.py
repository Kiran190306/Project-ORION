"""Authentication service for JWT token management and password hashing."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

# Configuration sourced from environment with secure defaults
DEFAULT_SECRET_KEY = "insecure-dev-secret-key-change-in-production-institutional-orion-2026"
SECRET_KEY = os.environ.get("ORION_JWT_SECRET_KEY", DEFAULT_SECRET_KEY)
ALGORITHM = os.environ.get("ORION_JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ORION_JWT_EXPIRE_MINUTES", "30"))


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


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
    secret_key: str | None = None,
    algorithm: str | None = None,
) -> str:
    """Create a signed JWT access token with expiration."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    key = secret_key or SECRET_KEY
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
        key = secret_key or SECRET_KEY
        alg = algorithm or ALGORITHM
        payload: dict[str, Any] = jwt.decode(token, key, algorithms=[alg])
        return payload
    except JWTError:
        return None
