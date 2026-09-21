"""Permission definitions and Role-to-Permission matrix for institutional RBAC."""

from __future__ import annotations

from enum import StrEnum

from libraries.domain.organization.models import OrganizationRole


class Permission(StrEnum):
    """Granular institutional permissions across platform operational domains."""

    # Organization Governance
    ORGANIZATION_READ = "ORGANIZATION_READ"
    ORGANIZATION_UPDATE = "ORGANIZATION_UPDATE"

    # Member Management
    MEMBER_READ = "MEMBER_READ"
    MEMBER_INVITE = "MEMBER_INVITE"
    MEMBER_UPDATE = "MEMBER_UPDATE"
    MEMBER_REMOVE = "MEMBER_REMOVE"

    # Account Administration
    ACCOUNT_READ = "ACCOUNT_READ"
    ACCOUNT_CREATE = "ACCOUNT_CREATE"
    ACCOUNT_UPDATE = "ACCOUNT_UPDATE"

    # Order Operations
    ORDER_READ = "ORDER_READ"
    ORDER_CREATE = "ORDER_CREATE"
    ORDER_CANCEL = "ORDER_CANCEL"

    # Position Operations
    POSITION_READ = "POSITION_READ"
    POSITION_CLOSE = "POSITION_CLOSE"

    # Trade Journal
    TRADE_READ = "TRADE_READ"

    # Strategy Control
    STRATEGY_READ = "STRATEGY_READ"
    STRATEGY_CONFIGURE = "STRATEGY_CONFIGURE"

    # Risk Controls
    RISK_READ = "RISK_READ"
    RISK_CONFIGURE = "RISK_CONFIGURE"

    # Autonomous Worker Operations
    WORKER_READ = "WORKER_READ"
    WORKER_START = "WORKER_START"
    WORKER_STOP = "WORKER_STOP"

    # Subscription Governance
    SUBSCRIPTION_READ = "SUBSCRIPTION_READ"
    SUBSCRIPTION_MANAGE = "SUBSCRIPTION_MANAGE"

    # Compliance Audit
    AUDIT_READ = "AUDIT_READ"

    # Research Lab & Strategy Backtesting
    RESEARCH_READ = "RESEARCH_READ"
    RESEARCH_EXECUTE = "RESEARCH_EXECUTE"
    RESEARCH_CANCEL = "RESEARCH_CANCEL"
    RESEARCH_EXPORT = "RESEARCH_EXPORT"


# Canonical Role -> Permission Matrix
ROLE_PERMISSIONS: dict[OrganizationRole, set[Permission]] = {
    OrganizationRole.OWNER: {
        Permission.ORGANIZATION_READ,
        Permission.ORGANIZATION_UPDATE,
        Permission.MEMBER_READ,
        Permission.MEMBER_INVITE,
        Permission.MEMBER_UPDATE,
        Permission.MEMBER_REMOVE,
        Permission.ACCOUNT_READ,
        Permission.ACCOUNT_CREATE,
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
        Permission.SUBSCRIPTION_MANAGE,
        Permission.AUDIT_READ,
        Permission.RESEARCH_READ,
        Permission.RESEARCH_EXECUTE,
        Permission.RESEARCH_CANCEL,
        Permission.RESEARCH_EXPORT,
    },
    OrganizationRole.ADMINISTRATOR: {
        Permission.ORGANIZATION_READ,
        Permission.ORGANIZATION_UPDATE,
        Permission.MEMBER_READ,
        Permission.MEMBER_INVITE,
        Permission.MEMBER_UPDATE,
        Permission.MEMBER_REMOVE,
        Permission.ACCOUNT_READ,
        Permission.ACCOUNT_CREATE,
        Permission.ACCOUNT_UPDATE,
        Permission.ORDER_READ,
        Permission.POSITION_READ,
        Permission.TRADE_READ,
        Permission.STRATEGY_READ,
        Permission.STRATEGY_CONFIGURE,
        Permission.RISK_READ,
        Permission.WORKER_READ,
        Permission.WORKER_START,
        Permission.WORKER_STOP,
        Permission.SUBSCRIPTION_READ,
        Permission.SUBSCRIPTION_MANAGE,
        Permission.AUDIT_READ,
        Permission.RESEARCH_READ,
        Permission.RESEARCH_EXECUTE,
        Permission.RESEARCH_CANCEL,
        Permission.RESEARCH_EXPORT,
    },
    OrganizationRole.PORTFOLIO_MANAGER: {
        Permission.ORGANIZATION_READ,
        Permission.MEMBER_READ,
        Permission.ACCOUNT_READ,
        Permission.ACCOUNT_CREATE,
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
        Permission.WORKER_READ,
        Permission.WORKER_START,
        Permission.WORKER_STOP,
        Permission.SUBSCRIPTION_READ,
        Permission.AUDIT_READ,
        Permission.RESEARCH_READ,
        Permission.RESEARCH_EXECUTE,
        Permission.RESEARCH_CANCEL,
        Permission.RESEARCH_EXPORT,
    },
    OrganizationRole.RISK_OFFICER: {
        Permission.ORGANIZATION_READ,
        Permission.MEMBER_READ,
        Permission.ACCOUNT_READ,
        Permission.ORDER_READ,
        Permission.POSITION_READ,
        Permission.TRADE_READ,
        Permission.STRATEGY_READ,
        Permission.RISK_READ,
        Permission.RISK_CONFIGURE,
        Permission.WORKER_READ,
        Permission.SUBSCRIPTION_READ,
        Permission.AUDIT_READ,
        Permission.RESEARCH_READ,
        Permission.RESEARCH_EXPORT,
    },
    OrganizationRole.TRADER: {
        Permission.ORGANIZATION_READ,
        Permission.MEMBER_READ,
        Permission.ACCOUNT_READ,
        Permission.ORDER_READ,
        Permission.ORDER_CREATE,
        Permission.ORDER_CANCEL,
        Permission.POSITION_READ,
        Permission.POSITION_CLOSE,
        Permission.TRADE_READ,
        Permission.STRATEGY_READ,
        Permission.STRATEGY_CONFIGURE,
        Permission.RISK_READ,
        Permission.WORKER_READ,
        Permission.SUBSCRIPTION_READ,
        Permission.RESEARCH_READ,
        Permission.RESEARCH_EXECUTE,
        Permission.RESEARCH_CANCEL,
        Permission.RESEARCH_EXPORT,
    },
    OrganizationRole.AUDITOR: {
        Permission.ORGANIZATION_READ,
        Permission.MEMBER_READ,
        Permission.ACCOUNT_READ,
        Permission.ORDER_READ,
        Permission.POSITION_READ,
        Permission.TRADE_READ,
        Permission.STRATEGY_READ,
        Permission.RISK_READ,
        Permission.WORKER_READ,
        Permission.SUBSCRIPTION_READ,
        Permission.AUDIT_READ,
        Permission.RESEARCH_READ,
        Permission.RESEARCH_EXPORT,
    },
    OrganizationRole.VIEWER: {
        Permission.ORGANIZATION_READ,
        Permission.MEMBER_READ,
        Permission.ACCOUNT_READ,
        Permission.ORDER_READ,
        Permission.POSITION_READ,
        Permission.TRADE_READ,
        Permission.STRATEGY_READ,
        Permission.RISK_READ,
        Permission.WORKER_READ,
        Permission.SUBSCRIPTION_READ,
        Permission.RESEARCH_READ,
    },
}


def has_permission(role: OrganizationRole | str, permission: Permission) -> bool:
    """Evaluate whether an organization role grants a given permission."""
    try:
        resolved_role = role if isinstance(role, OrganizationRole) else OrganizationRole.from_str(role)
    except ValueError:
        return False
    granted = ROLE_PERMISSIONS.get(resolved_role, set())
    return permission in granted
