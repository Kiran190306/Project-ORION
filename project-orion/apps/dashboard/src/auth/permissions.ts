/**
 * Institutional RBAC permissions matching backend canonical Role -> Permission matrix.
 */

export enum Permission {
  ORGANIZATION_READ = 'ORGANIZATION_READ',
  ORGANIZATION_UPDATE = 'ORGANIZATION_UPDATE',

  MEMBER_READ = 'MEMBER_READ',
  MEMBER_INVITE = 'MEMBER_INVITE',
  MEMBER_UPDATE = 'MEMBER_UPDATE',
  MEMBER_REMOVE = 'MEMBER_REMOVE',

  ACCOUNT_READ = 'ACCOUNT_READ',
  ACCOUNT_CREATE = 'ACCOUNT_CREATE',
  ACCOUNT_UPDATE = 'ACCOUNT_UPDATE',

  ORDER_READ = 'ORDER_READ',
  ORDER_CREATE = 'ORDER_CREATE',
  ORDER_CANCEL = 'ORDER_CANCEL',

  POSITION_READ = 'POSITION_READ',
  POSITION_CLOSE = 'POSITION_CLOSE',

  TRADE_READ = 'TRADE_READ',

  STRATEGY_READ = 'STRATEGY_READ',
  STRATEGY_CONFIGURE = 'STRATEGY_CONFIGURE',

  RISK_READ = 'RISK_READ',
  RISK_CONFIGURE = 'RISK_CONFIGURE',

  WORKER_READ = 'WORKER_READ',
  WORKER_START = 'WORKER_START',
  WORKER_STOP = 'WORKER_STOP',

  SUBSCRIPTION_READ = 'SUBSCRIPTION_READ',
  SUBSCRIPTION_MANAGE = 'SUBSCRIPTION_MANAGE',

  AUDIT_READ = 'AUDIT_READ',
}

export enum OrganizationRole {
  OWNER = 'OWNER',
  ADMINISTRATOR = 'ADMINISTRATOR',
  PORTFOLIO_MANAGER = 'PORTFOLIO_MANAGER',
  RISK_OFFICER = 'RISK_OFFICER',
  TRADER = 'TRADER',
  AUDITOR = 'AUDITOR',
  VIEWER = 'VIEWER',
}

export const ROLE_PERMISSIONS: Record<string, Set<Permission>> = {
  [OrganizationRole.OWNER]: new Set([
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
  ]),
  [OrganizationRole.ADMINISTRATOR]: new Set([
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
  ]),
  [OrganizationRole.PORTFOLIO_MANAGER]: new Set([
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
  ]),
  [OrganizationRole.RISK_OFFICER]: new Set([
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
  ]),
  [OrganizationRole.TRADER]: new Set([
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
  ]),
  [OrganizationRole.AUDITOR]: new Set([
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
  ]),
  [OrganizationRole.VIEWER]: new Set([
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
  ]),
};

export function hasPermission(
  role: string | undefined | null,
  permission: Permission,
  isSuperuser = false
): boolean {
  if (isSuperuser) return true;
  if (!role) return false;
  const upperRole = role.toUpperCase();
  const permissions = ROLE_PERMISSIONS[upperRole];
  if (!permissions) return false;
  return permissions.has(permission);
}
