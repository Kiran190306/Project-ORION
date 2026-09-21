"""FastAPI Dependency Injection providers for the Trading Engine.

Provides clean dependencies for:
- AppSettings
- AsyncSession (database session)
- RedisClient
- PaperExecutionAdapter
- PaperTradingService
- MetricsRegistry
- HealthCheckRegistry
- Authentication

No service-locator anti-patterns. Everything is retrieved cleanly
from request.app.state and injected into routes.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.organization.permissions import Permission, has_permission
from libraries.infrastructure.caching.client import RedisClient
from libraries.infrastructure.execution.paper_execution import PaperExecutionAdapter
from libraries.infrastructure.health import HealthCheckRegistry
from libraries.infrastructure.persistence.config import DatabaseManager
from libraries.infrastructure.persistence.models import AccountModel, UserModel
from libraries.observability.metrics import MetricsRegistry

from .config import AppSettings
from .schemas import PaginationParams
from .services.auth import decode_access_token
from .services.paper_trading import PaperTradingService

if TYPE_CHECKING:
    from .services.market_data_service import MarketDataService
    from .workers.coordinator import AutonomousWorkerCoordinator


def get_settings(request: Request) -> AppSettings:
    """Provide strongly-typed application settings from app state."""
    settings: AppSettings = request.app.state.settings
    return settings


def get_db_manager(request: Request) -> DatabaseManager:
    """Provide DatabaseManager from app state."""
    db_manager: DatabaseManager | None = getattr(request.app.state, "db_manager", None)
    if db_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )
    return db_manager


async def get_db_session(
    db_manager: Annotated[DatabaseManager, Depends(get_db_manager)],
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a scoped async database session that cleans up properly.

    Commits on successful completion, rolls back on exception,
    and always closes the session to prevent connection leaks.
    """
    async with db_manager.session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_redis(request: Request) -> RedisClient:
    """Provide async RedisClient from app state."""
    redis_client: RedisClient = request.app.state.redis_client
    return redis_client


def get_paper_adapter(request: Request) -> PaperExecutionAdapter:
    """Provide PaperExecutionAdapter from app state."""
    adapter: PaperExecutionAdapter = request.app.state.paper_adapter
    return adapter


def get_metrics_registry(request: Request) -> MetricsRegistry:
    """Provide MetricsRegistry from app state."""
    registry: MetricsRegistry = request.app.state.metrics_registry
    return registry


def get_health_registry(request: Request) -> HealthCheckRegistry:
    """Provide HealthCheckRegistry from app state."""
    registry: HealthCheckRegistry = request.app.state.health_registry
    return registry


def get_paper_trading_service(
    adapter: Annotated[PaperExecutionAdapter, Depends(get_paper_adapter)],
) -> PaperTradingService:
    """Provide PaperTradingService with injected paper execution adapter."""
    return PaperTradingService(adapter=adapter)


def get_worker_coordinator(request: Request) -> AutonomousWorkerCoordinator | None:
    """Provide AutonomousWorkerCoordinator from app state if available."""
    return getattr(request.app.state, "worker", None)


def get_market_data_service(request: Request) -> MarketDataService:
    """Provide MarketDataService from app state."""
    service: MarketDataService | None = getattr(request.app.state, "market_data_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Market data service is unavailable",
        )
    return service



async def get_current_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Any:
    """Dependency to get the current authenticated user from JWT token.

    Raises HTTPException if authentication fails.
    """
    try:
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)

        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user from database
        from sqlalchemy import select

        result = await session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error",
        ) from exc


async def get_current_active_user(
    current_user: Annotated[Any, Depends(get_current_user)],
) -> Any:
    """Dependency to get the current active user.

    Raises HTTPException if user is not active.
    """
    if not current_user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    return current_user


async def get_current_superuser(
    current_user: Annotated[Any, Depends(get_current_user)],
) -> Any:
    """Dependency to get the current superuser.

    Raises HTTPException if user is not a superuser.
    """
    if not current_user["is_superuser"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


@dataclass(frozen=True, slots=True)
class TenantContext:
    """Carries tenant isolation context across requests."""

    user_id: str
    organization_id: str | None = None
    role: str | None = None
    is_superuser: bool = False


async def get_tenant_context(
    request: Request,
    current_user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TenantContext:
    """Resolve and validate the active tenant organization context.

    If X-Organization-ID header is provided:
      - Validates that the active user is an active member of that organization
        (or a superuser).
      - If valid, sets organization_id and role.
      - If invalid, raises 403 Forbidden.
    If X-Organization-ID header is not provided:
      - Resolves user's active membership (primary/first active organization).
      - If user has no active memberships, falls back to organization_id=None (legacy compatibility).
    """
    user_id = str(current_user["id"])
    is_superuser = bool(current_user.get("is_superuser", False))
    requested_org_id = request.headers.get("X-Organization-ID") or request.headers.get("x-organization-id")

    if requested_org_id:
        requested_org_id = requested_org_id.strip()
        from libraries.infrastructure.persistence.models.organization import (
            OrganizationMemberModel,
            OrganizationModel,
        )

        stmt = select(OrganizationMemberModel).where(
            OrganizationMemberModel.user_id == user_id,
            OrganizationMemberModel.organization_id == requested_org_id,
            OrganizationMemberModel.status == "ACTIVE",
        )
        res = await session.execute(stmt)
        member = res.scalar_one_or_none()

        if member is not None:
            # Enforce active organization status fail-closed
            org_res = await session.execute(
                select(OrganizationModel).where(OrganizationModel.id == requested_org_id)
            )
            org = org_res.scalar_one_or_none()
            if org is not None and org.status != "ACTIVE":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Forbidden: Organization '{requested_org_id}' is {org.status.lower()}",
                )

            return TenantContext(
                user_id=user_id,
                organization_id=requested_org_id,
                role=member.role,
                is_superuser=is_superuser,
            )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Access denied to requested organization",
        )

    # Header not provided: resolve default/active membership
    from libraries.infrastructure.persistence.models.organization import (
        OrganizationMemberModel,
        OrganizationModel,
    )

    stmt = (
        select(OrganizationMemberModel)
        .where(
            OrganizationMemberModel.user_id == user_id,
            OrganizationMemberModel.status == "ACTIVE",
        )
        .order_by(OrganizationMemberModel.created_at.asc())
    )
    res = await session.execute(stmt)
    members = list(res.scalars().all())
    primary_member = members[0] if members else None

    if primary_member is not None and isinstance(getattr(primary_member, "organization_id", None), str):
        # Enforce active organization status fail-closed
        org_res = await session.execute(
            select(OrganizationModel).where(OrganizationModel.id == primary_member.organization_id)
        )
        org = org_res.scalar_one_or_none()
        if org is not None and org.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Organization '{primary_member.organization_id}' is {org.status.lower()}",
            )

        return TenantContext(
            user_id=user_id,
            organization_id=primary_member.organization_id,
            role=primary_member.role,
            is_superuser=is_superuser,
        )

    return TenantContext(
        user_id=user_id,
        organization_id=None,
        role=None,
        is_superuser=is_superuser,
    )


async def get_user_account(
    current_user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[AppSettings, Depends(get_settings)],
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
) -> AccountModel:
    """Ensure and return the user's paper trading account scoped to active tenant.
    
    Provisions a new paper account if one does not exist for the user/organization yet.
    """
    user_id = str(current_user["id"])
    org_id = tenant_context.organization_id

    if org_id is not None:
        # Organization-scoped account
        result = await session.execute(
            select(AccountModel).where(AccountModel.organization_id == org_id)
        )
        account = result.scalar_one_or_none()
        if account is None:
            # Check if user has an existing unassigned account and associate it
            user_acc_result = await session.execute(
                select(AccountModel).where(
                    AccountModel.user_id == user_id,
                    AccountModel.organization_id.is_(None),
                )
            )
            existing_user_acc = user_acc_result.scalar_one_or_none()
            if existing_user_acc is not None:
                existing_user_acc.organization_id = org_id
                await session.flush()
                return existing_user_acc

            # Check account quota before creating an additional paper account for organization
            from libraries.domain.subscription.exceptions import (
                AccountQuotaExceededError,
            )

            from .services.entitlement_service import EntitlementService

            entitlement_svc = EntitlementService(session)
            try:
                await entitlement_svc.check_account_quota(org_id)
            except AccountQuotaExceededError as exc:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=exc.message,
                ) from exc

            username = str(current_user.get("username", "USER")).upper()[:10]
            account = AccountModel(
                id=f"acc-{org_id[:8]}-{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                organization_id=org_id,
                broker_name="paper",
                account_number=f"PAPER-ORG-{org_id[:6].upper()}-{uuid.uuid4().hex[:4].upper()}",
                currency="USD",
                balance=settings.paper_balance,
                equity=settings.paper_balance,
                margin=Decimal(0),
                margin_free=settings.paper_balance,
                margin_level=0.0,
                leverage=100,
                is_live=False,
                is_active=True,
                meta_data={"created_by": "auto_paper_provisioning", "organization_id": org_id},
            )
            session.add(account)
            await session.flush()
        return account

    # Legacy / personal account without organization
    result = await session.execute(
        select(AccountModel).where(AccountModel.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if account is None:
        username = str(current_user.get("username", "USER")).upper()[:10]
        account = AccountModel(
            id=f"acc-{user_id[:8]}-{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            organization_id=None,
            broker_name="paper",
            account_number=f"PAPER-{username}-{uuid.uuid4().hex[:4].upper()}",
            currency="USD",
            balance=settings.paper_balance,
            equity=settings.paper_balance,
            margin=Decimal(0),
            margin_free=settings.paper_balance,
            margin_level=0.0,
            leverage=100,
            is_live=False,
            is_active=True,
            meta_data={"created_by": "auto_paper_provisioning"},
        )
        session.add(account)
        await session.flush()
    return account


def get_pagination_params(
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page (1..100)")] = 20,
    offset: Annotated[int, Query(ge=0, description="Offset index")] = 0,
    sort_by: Annotated[str, Query(description="Field to sort by")] = "created_at",
    order: Annotated[str, Query(pattern="^(asc|desc)$", description="Sort order: asc or desc")] = "desc",
    date_from: Annotated[datetime | None, Query(description="Start date filter (UTC)")] = None,
    date_to: Annotated[datetime | None, Query(description="End date filter (UTC)")] = None,
) -> PaginationParams:
    """Extract and validate standardized pagination and date range parameters."""
    return PaginationParams(
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        order=order,
        date_from=date_from,
        date_to=date_to,
    )


def get_subscription_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Any:
    """Provide SubscriptionService with injected database session."""
    from .services.subscription_service import SubscriptionService

    return SubscriptionService(session=session)


def get_entitlement_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    subscription_service: Annotated[Any, Depends(get_subscription_service)],
) -> Any:
    """Provide EntitlementService with injected database session and subscription service."""
    from .services.entitlement_service import EntitlementService

    return EntitlementService(session=session, subscription_service=subscription_service)


def get_organization_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Any:
    """Provide OrganizationService with injected database session."""
    from .services.organization_service import OrganizationService

    return OrganizationService(session=session)


def get_invitation_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Any:
    """Provide InvitationService with injected database session."""
    from .services.invitation_service import InvitationService

    return InvitationService(session=session)


def get_onboarding_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Any:
    """Provide OnboardingService with injected database session."""
    from .services.onboarding_service import OnboardingService

    return OnboardingService(session=session)


def require_permission(permission: Permission) -> Callable[..., Any]:
    """FastAPI dependency factory enforcing institutional RBAC permissions.

    1. Personal sandbox mode (organization_id is None):
       Allows standard individual sandbox trading operations while blocking
       multi-tenant organization governance, member management, and audit logs.
    2. Organization mode:
       Validates that the caller has an active role in the organization and that
       the role grants the specified permission. Superuser status does not bypass
       tenant role checks.
    """

    async def _permission_checker(
        tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    ) -> TenantContext:
        if tenant_context.organization_id is None:
            # Personal sandbox mode
            SANDBOX_ALLOWED_PERMISSIONS = {
                Permission.ACCOUNT_READ,
                Permission.ACCOUNT_UPDATE,
                Permission.ORDER_READ,
                Permission.ORDER_CREATE,
                Permission.ORDER_CANCEL,
                Permission.POSITION_READ,
                Permission.POSITION_CLOSE,
                Permission.TRADE_READ,
                Permission.STRATEGY_READ,
                Permission.STRATEGY_CONFIGURE,
                Permission.RISK_READ,
                Permission.RISK_CONFIGURE,
                Permission.WORKER_READ,
                Permission.WORKER_START,
                Permission.WORKER_STOP,
                Permission.SUBSCRIPTION_READ,
                Permission.RESEARCH_READ,
                Permission.RESEARCH_EXECUTE,
                Permission.RESEARCH_CANCEL,
                Permission.RESEARCH_EXPORT,
            }
            if permission in SANDBOX_ALLOWED_PERMISSIONS:
                return tenant_context
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Permission '{permission.value}' requires active organization membership",
            )

        if not tenant_context.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: User has no active role in the organization",
            )

        if not has_permission(tenant_context.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Role '{tenant_context.role}' does not have permission '{permission.value}'",
            )

        return tenant_context

    return _permission_checker


def get_billing_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
) -> Any:
    """Provide BillingService with injected database session and metrics registry."""
    from .services.billing_service import BillingService

    metrics = getattr(request.app.state, "metrics_registry", None)
    return BillingService(session=session, metrics=metrics)


def get_research_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
) -> Any:
    """Provide ResearchService with injected database session, entitlement service, and market data service."""
    from .services.entitlement_service import EntitlementService
    from .services.research_service import ResearchService

    market_data = getattr(request.app.state, "market_data_service", None)
    entitlements = EntitlementService(session=session)
    return ResearchService(
        session=session,
        entitlement_service=entitlements,
        market_data_service=market_data,
    )


