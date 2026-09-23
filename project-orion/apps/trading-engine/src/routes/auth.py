"""Authentication endpoints for login, logout, identity verification, and account lifecycles."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.organization.models import MembershipStatus, OrganizationRole
from libraries.domain.security.rate_limit import RateLimitPolicies
from libraries.infrastructure.communication.email_service import get_email_service
from libraries.infrastructure.persistence.models import (
    AuditLogModel,
    AuthTokenModel,
    OrganizationMemberModel,
    OrganizationModel,
    TokenType,
    UserModel,
    UserStatus,
)

from ..dependencies import get_current_user, get_db_session, rate_limit
from ..schemas import (
    DeactivateAccountRequest,
    ForgotPasswordRequest,
    GenericMessageResponse,
    LoginRequest,
    LoginResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    UserResponse,
    VerifyEmailRequest,
)
from ..services.auth import (
    create_access_token,
    generate_secure_token,
    get_password_hash,
    hash_security_token,
    validate_password_strength,
    verify_password,
)

logger = logging.getLogger("trading_engine.routes.auth")

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def mask_email(email: str) -> str:
    """Mask email for privacy-safe storage in audit logs."""
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "***"
    else:
        masked_local = local[0] + "***" + local[-1]
    return f"{masked_local}@{domain}"


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login",
    description="Authenticate with username and password to receive a JWT access token.",
    dependencies=[Depends(rate_limit(RateLimitPolicies.AUTH_LOGIN))],
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
            # Prevent user enumeration with generic 401 error
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active or user.status == UserStatus.DEACTIVATED.value:
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

        # Create access token with issuance timestamp
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
    description="Logout endpoint (client discards local access token).",
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
        status=str(current_user.get("status", "ACTIVE")),
        email_verified=bool(current_user.get("email_verified", False)),
        password_changed_at=current_user.get("password_changed_at"),
        created_at=current_user["created_at"],
        updated_at=current_user["updated_at"],
    )


@router.post(
    "/forgot-password",
    response_model=GenericMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Forgot Password",
    description="Request password reset instructions. Returns generic message to prevent account enumeration.",
    dependencies=[Depends(rate_limit(RateLimitPolicies.AUTH_FORGOT_PASSWORD))],
)
async def forgot_password(
    request: ForgotPasswordRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GenericMessageResponse:
    """Initiate password recovery with time-limited cryptographic token."""
    generic_msg = "If the account exists, password reset instructions have been sent."
    clean_email = request.email.strip().lower()

    try:
        result = await session.execute(
            select(UserModel).where(UserModel.email == clean_email)
        )
        user = result.scalar_one_or_none()

        if user is None or not user.is_active or user.status == UserStatus.DEACTIVATED.value:
            # Return same generic response to prevent user enumeration
            return GenericMessageResponse(message=generic_msg)

        now = datetime.now(timezone.utc)

        # 1. Invalidate any existing unused reset tokens for this user
        existing_tokens = await session.execute(
            select(AuthTokenModel).where(
                AuthTokenModel.user_id == user.id,
                AuthTokenModel.token_type == TokenType.PASSWORD_RESET.value,
                AuthTokenModel.used_at.is_(None),
            )
        )
        for t in existing_tokens.scalars().all():
            t.used_at = now

        # 2. Generate and hash secure single-use token (15-minute expiration)
        raw_token = generate_secure_token()
        token_hash = hash_security_token(raw_token)
        expires_at = now + timedelta(minutes=15)

        token_record = AuthTokenModel(
            id=f"tok_{uuid.uuid4().hex[:16]}",
            user_id=user.id,
            token_hash=token_hash,
            token_type=TokenType.PASSWORD_RESET.value,
            expires_at=expires_at,
            used_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(token_record)

        # 3. Record audit event
        audit = AuditLogModel(
            id=f"aud_{uuid.uuid4().hex[:16]}",
            organization_id=None,
            event_type="PASSWORD_RESET_REQUESTED",
            component="auth",
            actor=user.id,
            details={"email": mask_email(user.email)},
            timestamp=now,
        )
        session.add(audit)

        await session.commit()

        # 4. Dispatch email instructions (token never logged; delivery failure must not leak existence)
        try:
            email_svc = get_email_service()
            sent = await email_svc.send_password_reset_email(user.email, raw_token, user.username)
            if not sent:
                logger.warning(
                    "Email provider reported failure dispatching password reset for user_id=%s",
                    user.id,
                )
        except Exception as email_exc:  # noqa: BLE001
            logger.error(
                "Exception during password reset email dispatch for user_id=%s: %s",
                user.id,
                email_exc.__class__.__name__,
            )

        logger.info("Password reset requested for user_id=%s", user.id)
        return GenericMessageResponse(message=generic_msg)

    except Exception as exc:
        await session.rollback()
        logger.error("Error processing forgot-password request: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error",
        ) from exc


@router.post(
    "/reset-password",
    response_model=GenericMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset Password",
    description="Complete password reset using a cryptographic token.",
)
async def reset_password(
    request: ResetPasswordRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GenericMessageResponse:
    """Validate reset token and update password hash."""
    # 1. Validate password strength
    is_valid, reason = validate_password_strength(request.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=reason,
        )

    token_hash = hash_security_token(request.token.strip())
    now = datetime.now(timezone.utc)

    try:
        # 2. Query token record
        result = await session.execute(
            select(AuthTokenModel).where(
                AuthTokenModel.token_hash == token_hash,
                AuthTokenModel.token_type == TokenType.PASSWORD_RESET.value,
            )
        )
        token_record = result.scalar_one_or_none()

        if token_record is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset token.",
            )

        # 3. Check single-use and expiration
        if token_record.used_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset token has already been used.",
            )

        token_exp = token_record.expires_at
        if token_exp.tzinfo is None:
            token_exp = token_exp.replace(tzinfo=timezone.utc)

        if token_exp < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset token has expired.",
            )

        # 4. Fetch user
        user_result = await session.execute(
            select(UserModel).where(UserModel.id == token_record.user_id)
        )
        user = user_result.scalar_one_or_none()
        if user is None or not user.is_active or user.status == UserStatus.DEACTIVATED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset token.",
            )

        # 5. Invalidate token and update password
        token_record.used_at = now
        user.hashed_password = get_password_hash(request.new_password)
        user.password_changed_at = now
        user.updated_at = now

        # 6. Record audit log
        audit = AuditLogModel(
            id=f"aud_{uuid.uuid4().hex[:16]}",
            organization_id=None,
            event_type="PASSWORD_RESET_COMPLETED",
            component="auth",
            actor=user.id,
            details={"username": user.username},
            timestamp=now,
        )
        session.add(audit)

        await session.commit()
        logger.info("Password successfully reset for user_id=%s", user.id)

        return GenericMessageResponse(
            message="Password has been successfully reset. Please log in with your new credentials."
        )

    except HTTPException:
        raise
    except Exception as exc:
        await session.rollback()
        logger.error("Error processing password reset: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error",
        ) from exc


@router.post(
    "/verify-email",
    response_model=GenericMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Email",
    description="Verify email address using a cryptographic token.",
)
async def verify_email(
    request: VerifyEmailRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GenericMessageResponse:
    """Validate email verification token and activate verified status."""
    token_hash = hash_security_token(request.token.strip())
    now = datetime.now(timezone.utc)

    try:
        result = await session.execute(
            select(AuthTokenModel).where(
                AuthTokenModel.token_hash == token_hash,
                AuthTokenModel.token_type == TokenType.EMAIL_VERIFICATION.value,
            )
        )
        token_record = result.scalar_one_or_none()

        if token_record is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired email verification token.",
            )

        if token_record.used_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email verification token has already been used.",
            )

        token_exp = token_record.expires_at
        if token_exp.tzinfo is None:
            token_exp = token_exp.replace(tzinfo=timezone.utc)

        if token_exp < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email verification token has expired.",
            )

        user_result = await session.execute(
            select(UserModel).where(UserModel.id == token_record.user_id)
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired email verification token.",
            )

        token_record.used_at = now
        user.email_verified = True
        user.updated_at = now

        audit = AuditLogModel(
            id=f"aud_{uuid.uuid4().hex[:16]}",
            organization_id=None,
            event_type="EMAIL_VERIFIED",
            component="auth",
            actor=user.id,
            details={"email": mask_email(user.email)},
            timestamp=now,
        )
        session.add(audit)

        await session.commit()
        logger.info("Email verified for user_id=%s", user.id)

        return GenericMessageResponse(message="Email address has been successfully verified.")

    except HTTPException:
        raise
    except Exception as exc:
        await session.rollback()
        logger.error("Error verifying email: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error",
        ) from exc


@router.post(
    "/resend-verification",
    response_model=GenericMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Resend Email Verification",
    description="Resend email verification token. Generic response prevents account enumeration.",
    dependencies=[Depends(rate_limit(RateLimitPolicies.AUTH_RESEND_VERIFICATION))],
)
async def resend_verification(
    request: ResendVerificationRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GenericMessageResponse:
    """Dispatch a new email verification token and invalidate prior tokens."""
    generic_msg = "If the account exists and is unverified, a new verification link has been sent."
    clean_email = request.email.strip().lower()
    now = datetime.now(timezone.utc)

    try:
        result = await session.execute(
            select(UserModel).where(UserModel.email == clean_email)
        )
        user = result.scalar_one_or_none()

        if user is None or not user.is_active or user.status == UserStatus.DEACTIVATED.value:
            return GenericMessageResponse(message=generic_msg)

        if user.email_verified:
            return GenericMessageResponse(message="Email is already verified.")

        # Invalidate existing verification tokens
        existing_tokens = await session.execute(
            select(AuthTokenModel).where(
                AuthTokenModel.user_id == user.id,
                AuthTokenModel.token_type == TokenType.EMAIL_VERIFICATION.value,
                AuthTokenModel.used_at.is_(None),
            )
        )
        for t in existing_tokens.scalars().all():
            t.used_at = now

        # Generate new 24-hour verification token
        raw_token = generate_secure_token()
        token_hash = hash_security_token(raw_token)
        expires_at = now + timedelta(hours=24)

        token_record = AuthTokenModel(
            id=f"tok_{uuid.uuid4().hex[:16]}",
            user_id=user.id,
            token_hash=token_hash,
            token_type=TokenType.EMAIL_VERIFICATION.value,
            expires_at=expires_at,
            used_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(token_record)

        audit = AuditLogModel(
            id=f"aud_{uuid.uuid4().hex[:16]}",
            organization_id=None,
            event_type="EMAIL_VERIFICATION_SENT",
            component="auth",
            actor=user.id,
            details={"email": mask_email(user.email)},
            timestamp=now,
        )
        session.add(audit)

        await session.commit()

        # Dispatch email verification (token never logged; delivery failure must not leak existence)
        try:
            email_svc = get_email_service()
            sent = await email_svc.send_verification_email(user.email, raw_token, user.username)
            if not sent:
                logger.warning(
                    "Email provider reported failure dispatching verification email for user_id=%s",
                    user.id,
                )
        except Exception as email_exc:  # noqa: BLE001
            logger.error(
                "Exception during email verification dispatch for user_id=%s: %s",
                user.id,
                email_exc.__class__.__name__,
            )

        return GenericMessageResponse(message=generic_msg)

    except Exception as exc:
        await session.rollback()
        logger.error("Error resending email verification: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error",
        ) from exc


@router.post(
    "/deactivate",
    response_model=GenericMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate Account",
    description="Deactivate authenticated user account with sole-owner protection safeguards.",
)
async def deactivate_account(
    request: DeactivateAccountRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GenericMessageResponse:
    """Deactivate the user account while preventing creation of ownerless organizations."""
    if request.confirmation != "DEACTIVATE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation phrase must be strictly 'DEACTIVATE'.",
        )

    user_id = str(current_user["id"])
    now = datetime.now(timezone.utc)

    try:
        result = await session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # 1. Verify password
        if not verify_password(request.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password",
            )

        # 2. Ownership safeguard: Check if user is sole active owner of any organization
        owned_orgs_query = await session.execute(
            select(OrganizationMemberModel.organization_id).where(
                OrganizationMemberModel.user_id == user_id,
                OrganizationMemberModel.role == OrganizationRole.OWNER.value,
                OrganizationMemberModel.status == MembershipStatus.ACTIVE.value,
            )
        )
        owned_org_ids = owned_orgs_query.scalars().all()

        for org_id in owned_org_ids:
            # Count other active owners
            other_owners_query = await session.execute(
                select(func.count()).select_from(OrganizationMemberModel).where(
                    OrganizationMemberModel.organization_id == org_id,
                    OrganizationMemberModel.user_id != user_id,
                    OrganizationMemberModel.role == OrganizationRole.OWNER.value,
                    OrganizationMemberModel.status == MembershipStatus.ACTIVE.value,
                )
            )
            other_owner_count = other_owners_query.scalar_one()

            if other_owner_count == 0:
                # Fetch organization name for actionable rejection message
                org_query = await session.execute(
                    select(OrganizationModel).where(OrganizationModel.id == org_id)
                )
                org = org_query.scalar_one_or_none()
                org_name = org.name if org else org_id
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Cannot deactivate account. You are the sole active OWNER of organization '{org_name}'. "
                        "Please transfer ownership to another member before deactivating your account."
                    ),
                )

        # 3. Apply deactivation
        user.is_active = False
        user.status = UserStatus.DEACTIVATED.value
        user.password_changed_at = now
        user.updated_at = now

        # 4. Record audit event
        audit = AuditLogModel(
            id=f"aud_{uuid.uuid4().hex[:16]}",
            organization_id=None,
            event_type="USER_DEACTIVATED",
            component="auth",
            actor=user.id,
            details={"username": user.username},
            timestamp=now,
        )
        session.add(audit)

        await session.commit()
        logger.info("Account deactivated for user_id=%s (%s)", user.id, user.username)

        return GenericMessageResponse(message="Account has been successfully deactivated.")

    except HTTPException:
        raise
    except Exception as exc:
        await session.rollback()
        logger.error("Error deactivating account: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error",
        ) from exc


@router.post(
    "/users/{target_user_id}/reactivate",
    response_model=GenericMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Reactivate Account",
    description="Reactivate a deactivated account (platform administrator only).",
)
async def reactivate_account(
    target_user_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GenericMessageResponse:
    """Reactivate a deactivated user account under administrative control."""
    if not current_user.get("is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only platform administrators can reactivate user accounts.",
        )

    now = datetime.now(timezone.utc)

    try:
        result = await session.execute(
            select(UserModel).where(UserModel.id == target_user_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user.is_active and user.status == UserStatus.ACTIVE.value:
            return GenericMessageResponse(message="Account is already active.")

        user.is_active = True
        user.status = UserStatus.ACTIVE.value
        user.updated_at = now

        audit = AuditLogModel(
            id=f"aud_{uuid.uuid4().hex[:16]}",
            organization_id=None,
            event_type="USER_REACTIVATED",
            component="auth",
            actor=str(current_user["id"]),
            details={"target_user_id": user.id, "target_username": user.username},
            timestamp=now,
        )
        session.add(audit)

        await session.commit()
        logger.info(
            "Account reactivated for user_id=%s by admin=%s",
            user.id,
            current_user["id"],
        )

        return GenericMessageResponse(
            message=f"User '{user.username}' has been successfully reactivated."
        )

    except HTTPException:
        raise
    except Exception as exc:
        await session.rollback()
        logger.error("Error reactivating account: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error",
        ) from exc