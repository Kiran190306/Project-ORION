"""Authentication endpoints for login, logout, and user information."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.infrastructure.persistence.models import UserModel

from ..dependencies import get_current_user, get_db_session
from ..schemas import LoginRequest, LoginResponse, UserResponse
from ..services.auth import (
    create_access_token,
    verify_password,
)

logger = logging.getLogger("trading_engine.routes.auth")

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login",
    description="Authenticate with username and password to receive an access token.",
)
async def login(
    request: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LoginResponse:
    """Authenticate user and return JWT access token."""
    try:
        # Find user by username
        result = await session.execute(
            select(UserModel).where(UserModel.username == request.username)
        )
        user = result.scalar_one_or_none()

        if user is None:
            # User not found - don't reveal whether username exists
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )

        # Verify password
        if not verify_password(request.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create access token
        access_token = create_access_token(
            data={"sub": user.id, "username": user.username}
        )

        logger.info("User logged in: %s", user.username)

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            username=user.username,
            is_superuser=user.is_superuser,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Login failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error",
        ) from exc


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout",
    description="Logout endpoint (token-based, client should discard token).",
)
async def logout() -> dict[str, str]:
    """Logout endpoint - client should discard the token."""
    return {"message": "Successfully logged out"}


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User",
    description="Get information about the currently authenticated user.",
)
async def get_current_user_info(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> UserResponse:
    """Get current user information from JWT token."""
    return UserResponse(
        id=str(current_user["id"]),
        username=str(current_user["username"]),
        email=str(current_user["email"]),
        full_name=current_user.get("full_name"),
        is_active=bool(current_user["is_active"]),
        is_superuser=bool(current_user["is_superuser"]),
        created_at=current_user["created_at"],
        updated_at=current_user["updated_at"],
    )