"""REST API router for Institutional Broker Sandbox & Demo Broker Integration (EPIC-026)."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.organization.permissions import Permission

from ..dependencies import TenantContext, get_db_session, require_permission
from ..schemas_broker_sandbox import (
    BrokerProviderInfo,
    BrokerSandboxAccountCreateRequest,
    BrokerSandboxAccountResponse,
    BrokerSandboxAccountUpdateRequest,
    BrokerSandboxConnectResponse,
    BrokerSandboxOrderRequest,
    BrokerSandboxOrderResponse,
    BrokerSandboxPositionResponse,
    BrokerSandboxReconciliationResponse,
)
from ..services.broker_sandbox_service import BrokerSandboxService

logger = logging.getLogger("trading_engine.routes.broker_sandbox")

router = APIRouter(prefix="/api/v1/broker-sandbox", tags=["Broker Sandbox"])


def get_broker_sandbox_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BrokerSandboxService:
    """Dependency provider for BrokerSandboxService."""
    return BrokerSandboxService(session=session)


def _resolve_org_id(tenant_context: TenantContext) -> str:
    """Resolve active tenant organization ID or sandbox fallback."""
    if tenant_context.organization_id:
        return tenant_context.organization_id
    return f"personal-{tenant_context.user_id}"


# ── Providers Catalog ─────────────────────────────────────────────────

@router.get(
    "/providers",
    response_model=list[BrokerProviderInfo],
    status_code=status.HTTP_200_OK,
    summary="List Approved Broker Sandbox Providers",
    description="Retrieve approved broker sandbox providers and capabilities ($0 Capital at Risk).",
)
async def list_providers(
    _perm: Annotated[TenantContext, Depends(require_permission(Permission.BROKER_READ))],
    service: Annotated[BrokerSandboxService, Depends(get_broker_sandbox_service)],
) -> list[BrokerProviderInfo]:
    return service.list_providers()


# ── Account Management ────────────────────────────────────────────────

@router.get(
    "/accounts",
    response_model=list[BrokerSandboxAccountResponse],
    status_code=status.HTTP_200_OK,
    summary="List Organization Broker Sandbox Accounts",
    description="List all sandbox accounts configured for the tenant organization. Requires BROKER_READ.",
)
async def list_accounts(
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.BROKER_READ))],
    service: Annotated[BrokerSandboxService, Depends(get_broker_sandbox_service)],
) -> list[BrokerSandboxAccountResponse]:
    org_id = _resolve_org_id(tenant_context)
    return await service.list_accounts(org_id)


@router.post(
    "/accounts",
    response_model=BrokerSandboxAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Broker Sandbox Account",
    description="Register a new broker sandbox connection with encrypted credentials. Requires BROKER_SANDBOX_CONNECT.",
)
async def create_account(
    request: BrokerSandboxAccountCreateRequest,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.BROKER_SANDBOX_CONNECT))],
    service: Annotated[BrokerSandboxService, Depends(get_broker_sandbox_service)],
) -> BrokerSandboxAccountResponse:
    org_id = _resolve_org_id(tenant_context)
    return await service.create_account(
        organization_id=org_id,
        user_id=tenant_context.user_id,
        request=request,
    )


@router.get(
    "/accounts/{account_id}",
    response_model=BrokerSandboxAccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Broker Sandbox Account",
    description="Retrieve details and status for a specific sandbox account. Requires BROKER_READ.",
)
async def get_account(
    account_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.BROKER_READ))],
    service: Annotated[BrokerSandboxService, Depends(get_broker_sandbox_service)],
) -> BrokerSandboxAccountResponse:
    org_id = _resolve_org_id(tenant_context)
    return await service.get_account(organization_id=org_id, account_id=account_id)


@router.patch(
    "/accounts/{account_id}",
    response_model=BrokerSandboxAccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Broker Sandbox Account",
    description="Update configuration or credentials for a sandbox account. Requires BROKER_SANDBOX_CONNECT.",
)
async def update_account(
    account_id: str,
    request: BrokerSandboxAccountUpdateRequest,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.BROKER_SANDBOX_CONNECT))],
    service: Annotated[BrokerSandboxService, Depends(get_broker_sandbox_service)],
) -> BrokerSandboxAccountResponse:
    org_id = _resolve_org_id(tenant_context)
    return await service.update_account(
        organization_id=org_id, account_id=account_id, request=request
    )


@router.delete(
    "/accounts/{account_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Broker Sandbox Account",
    description="Remove a broker sandbox account. Requires BROKER_SANDBOX_CONNECT.",
)
async def delete_account(
    account_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.BROKER_SANDBOX_CONNECT))],
    service: Annotated[BrokerSandboxService, Depends(get_broker_sandbox_service)],
) -> dict[str, str]:
    org_id = _resolve_org_id(tenant_context)
    return await service.delete_account(organization_id=org_id, account_id=account_id)


# ── Connection Controls ───────────────────────────────────────────────

@router.post(
    "/accounts/{account_id}/connect",
    response_model=BrokerSandboxConnectResponse,
    status_code=status.HTTP_200_OK,
    summary="Connect Broker Sandbox Session",
    description="Establish connection to the broker sandbox and query account health. Requires BROKER_SANDBOX_CONNECT.",
)
async def connect_account(
    account_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.BROKER_SANDBOX_CONNECT))],
    service: Annotated[BrokerSandboxService, Depends(get_broker_sandbox_service)],
) -> BrokerSandboxConnectResponse:
    org_id = _resolve_org_id(tenant_context)
    return await service.connect_account(organization_id=org_id, account_id=account_id)


@router.post(
    "/accounts/{account_id}/disconnect",
    response_model=BrokerSandboxConnectResponse,
    status_code=status.HTTP_200_OK,
    summary="Disconnect Broker Sandbox Session",
    description="Disconnect active session to the broker sandbox. Requires BROKER_SANDBOX_CONNECT.",
)
async def disconnect_account(
    account_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.BROKER_SANDBOX_CONNECT))],
    service: Annotated[BrokerSandboxService, Depends(get_broker_sandbox_service)],
) -> BrokerSandboxConnectResponse:
    org_id = _resolve_org_id(tenant_context)
    return await service.disconnect_account(organization_id=org_id, account_id=account_id)


# ── Positions & Orders ────────────────────────────────────────────────

@router.get(
    "/accounts/{account_id}/positions",
    response_model=list[BrokerSandboxPositionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Open Positions from Broker Sandbox",
    description="Query open positions reported directly by the broker sandbox. Requires BROKER_READ.",
)
async def get_positions(
    account_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.BROKER_READ))],
    service: Annotated[BrokerSandboxService, Depends(get_broker_sandbox_service)],
) -> list[BrokerSandboxPositionResponse]:
    org_id = _resolve_org_id(tenant_context)
    return await service.get_positions(organization_id=org_id, account_id=account_id)


@router.post(
    "/accounts/{account_id}/orders",
    response_model=BrokerSandboxOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Order to Broker Sandbox",
    description="Execute an order through the mandatory Risk Engine & OrderValidator pipeline. Requires BROKER_SANDBOX_EXECUTE.",
)
async def submit_order(
    account_id: str,
    request: BrokerSandboxOrderRequest,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.BROKER_SANDBOX_EXECUTE))],
    service: Annotated[BrokerSandboxService, Depends(get_broker_sandbox_service)],
) -> BrokerSandboxOrderResponse:
    org_id = _resolve_org_id(tenant_context)
    return await service.submit_sandbox_order(
        organization_id=org_id,
        account_id=account_id,
        request=request,
    )


@router.post(
    "/accounts/{account_id}/orders/{order_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel Order on Broker Sandbox",
    description="Cancel a resting order on the broker sandbox. Requires BROKER_SANDBOX_EXECUTE.",
)
async def cancel_order(
    account_id: str,
    order_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.BROKER_SANDBOX_EXECUTE))],
    service: Annotated[BrokerSandboxService, Depends(get_broker_sandbox_service)],
) -> dict[str, Any]:
    org_id = _resolve_org_id(tenant_context)
    return await service.cancel_order(
        organization_id=org_id,
        account_id=account_id,
        order_id=order_id,
    )


# ── State Reconciliation Audit ────────────────────────────────────────

@router.post(
    "/accounts/{account_id}/reconcile",
    response_model=BrokerSandboxReconciliationResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger On-Demand State Reconciliation Audit",
    description="Reconcile internal ORION orders, positions, and balances against external broker sandbox. Requires BROKER_SANDBOX_RECONCILE.",
)
async def reconcile_account(
    account_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.BROKER_SANDBOX_RECONCILE))],
    service: Annotated[BrokerSandboxService, Depends(get_broker_sandbox_service)],
) -> BrokerSandboxReconciliationResponse:
    org_id = _resolve_org_id(tenant_context)
    return await service.reconcile_account(
        organization_id=org_id,
        account_id=account_id,
    )


@router.get(
    "/accounts/{account_id}/reconciliations",
    response_model=list[BrokerSandboxReconciliationResponse],
    status_code=status.HTTP_200_OK,
    summary="List Reconciliation Audit Snapshots",
    description="Retrieve historical reconciliation audits and discrepancy logs. Requires BROKER_READ.",
)
async def list_reconciliations(
    account_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.BROKER_READ))],
    service: Annotated[BrokerSandboxService, Depends(get_broker_sandbox_service)],
    limit: int = Query(default=20, ge=1, le=100),
) -> list[BrokerSandboxReconciliationResponse]:
    org_id = _resolve_org_id(tenant_context)
    return await service.list_reconciliations(
        organization_id=org_id,
        account_id=account_id,
        limit=limit,
    )
