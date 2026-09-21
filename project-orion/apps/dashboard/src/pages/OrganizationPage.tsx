import React, { useState, useEffect, useCallback } from 'react';
import {
  UserPlus,
  Shield,
  Trash2,
  Edit2,
  CheckCircle,
  Copy,
  AlertCircle,
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { useOrganization } from '../auth/OrganizationContext';
import { hasPermission, Permission, OrganizationRole } from '../auth/permissions';
import { organizationApi } from '../api/endpoints';
import type {
  OrganizationMemberResponse,
  InvitationResponse,
} from '../api/types';
import { PageHeader } from '../components/common/PageHeader';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { Table, Column } from '../components/common/Table';
import { ConfirmationDialog } from '../components/common/ConfirmationDialog';
import { CardSkeleton } from '../components/common/Skeleton';
import { useToast } from '../components/common/Toast';

export const OrganizationPage: React.FC = () => {
  const { user } = useAuth();
  const { currentOrg, currentRole, refreshOrganizations } = useOrganization();
  const { showToast } = useToast();

  const [members, setMembers] = useState<OrganizationMemberResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Edit Org modal state
  const [isEditOrgOpen, setIsEditOrgOpen] = useState(false);
  const [orgNameInput, setOrgNameInput] = useState('');
  const [isUpdatingOrg, setIsUpdatingOrg] = useState(false);

  // Invite modal state
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<string>(OrganizationRole.TRADER);
  const [isInviting, setIsInviting] = useState(false);
  const [issuedInvitation, setIssuedInvitation] = useState<InvitationResponse | null>(null);

  // Remove member state
  const [memberToRemove, setMemberToRemove] = useState<OrganizationMemberResponse | null>(null);
  const [isRemovingMember, setIsRemovingMember] = useState(false);

  // Role update state
  const [memberToUpdateRole, setMemberToUpdateRole] = useState<OrganizationMemberResponse | null>(null);
  const [selectedNewRole, setSelectedNewRole] = useState<string>('');
  const [isUpdatingRole, setIsUpdatingRole] = useState(false);

  const canUpdateOrg = hasPermission(currentRole, Permission.ORGANIZATION_UPDATE, user?.is_superuser);
  const canInvite = hasPermission(currentRole, Permission.MEMBER_INVITE, user?.is_superuser);
  const canUpdateMember = hasPermission(currentRole, Permission.MEMBER_UPDATE, user?.is_superuser);
  const canRemoveMember = hasPermission(currentRole, Permission.MEMBER_REMOVE, user?.is_superuser);

  const loadMembers = useCallback(async () => {
    if (!currentOrg) {
      setIsLoading(false);
      return;
    }
    try {
      setIsLoading(true);
      setError(null);
      const mems = await organizationApi.listMembers(currentOrg.id);
      setMembers(mems);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load members';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [currentOrg]);

  useEffect(() => {
    loadMembers();
    if (currentOrg) {
      setOrgNameInput(currentOrg.name);
    }
  }, [loadMembers, currentOrg]);

  const handleUpdateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentOrg || !orgNameInput.trim()) return;
    setIsUpdatingOrg(true);
    try {
      await organizationApi.update(currentOrg.id, { name: orgNameInput.trim() });
      showToast('Organization profile updated successfully', 'success');
      setIsEditOrgOpen(false);
      await refreshOrganizations();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Update failed';
      showToast(msg, 'error');
    } finally {
      setIsUpdatingOrg(false);
    }
  };

  const handleSendInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentOrg || !inviteEmail.trim()) return;
    setIsInviting(true);
    try {
      const inv = await organizationApi.inviteMember(currentOrg.id, {
        email: inviteEmail.trim(),
        role: inviteRole,
      });
      setIssuedInvitation(inv);
      showToast(`Invitation issued to ${inviteEmail}`, 'success');
      setInviteEmail('');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Invitation failed';
      showToast(msg, 'error');
    } finally {
      setIsInviting(false);
    }
  };

  const handleConfirmRoleUpdate = async () => {
    if (!currentOrg || !memberToUpdateRole || !selectedNewRole) return;
    setIsUpdatingRole(true);
    try {
      await organizationApi.updateMemberRole(currentOrg.id, memberToUpdateRole.user_id, selectedNewRole);
      showToast(`Role updated to ${selectedNewRole}`, 'success');
      setMemberToUpdateRole(null);
      await loadMembers();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update role';
      showToast(msg, 'error');
    } finally {
      setIsUpdatingRole(false);
    }
  };

  const handleConfirmRemoveMember = async () => {
    if (!currentOrg || !memberToRemove) return;
    setIsRemovingMember(true);
    try {
      await organizationApi.removeMember(currentOrg.id, memberToRemove.user_id);
      showToast('Member removed from organization', 'success');
      setMemberToRemove(null);
      await loadMembers();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to remove member';
      showToast(msg, 'error');
    } finally {
      setIsRemovingMember(false);
    }
  };

  const memberColumns: Column<OrganizationMemberResponse>[] = [
    {
      header: 'User ID',
      accessor: 'user_id',
      render: (m) => (
        <div className="font-mono text-xs text-slate-200">
          <span>{m.user_id}</span>
          {m.user_id === user?.id && (
            <span className="ml-2 px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300 text-[10px] font-mono">
              YOU
            </span>
          )}
        </div>
      ),
    },
    {
      header: 'Assigned Role',
      accessor: 'role',
      render: (m) => {
        const roleVariant = {
          OWNER: 'warning',
          ADMINISTRATOR: 'info',
          PORTFOLIO_MANAGER: 'buy',
          RISK_OFFICER: 'danger',
          TRADER: 'success',
          AUDITOR: 'default',
          VIEWER: 'default',
        }[m.role] || 'default';

        return (
          <Badge variant={roleVariant as any} dot>
            {m.role}
          </Badge>
        );
      },
    },
    {
      header: 'Status',
      accessor: 'status',
      render: (m) => (
        <Badge variant={m.status === 'ACTIVE' ? 'success' : 'warning'}>
          {m.status}
        </Badge>
      ),
    },
    {
      header: 'Joined Date',
      accessor: 'created_at',
      render: (m) => (
        <span className="font-mono text-xs text-slate-400">
          {new Date(m.created_at).toLocaleDateString()}
        </span>
      ),
    },
    {
      header: 'Actions',
      render: (m) => {
        if (m.user_id === user?.id) {
          return <span className="text-xs text-slate-500 italic">Self</span>;
        }

        return (
          <div className="flex items-center gap-2">
            {canUpdateMember && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setMemberToUpdateRole(m);
                  setSelectedNewRole(m.role);
                }}
                className="text-xs px-2 py-1 text-slate-300 hover:text-white"
                title="Change member role"
              >
                <Edit2 className="w-3.5 h-3.5 mr-1" />
                Role
              </Button>
            )}
            {canRemoveMember && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setMemberToRemove(m)}
                className="text-xs px-2 py-1 text-rose-400 hover:text-rose-300 hover:bg-rose-950/20"
                title="Remove member"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </Button>
            )}
          </div>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Organization Governance"
        subtitle="Manage multi-tenant institution profile, team memberships, and RBAC operational permissions."
        breadcrumbs={[{ label: 'Organization' }]}
        actions={
          canInvite && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                setIssuedInvitation(null);
                setIsInviteOpen(true);
              }}
              className="inline-flex items-center gap-2 cursor-pointer"
            >
              <UserPlus className="w-4 h-4" />
              <span>Invite Member</span>
            </Button>
          )
        }
      />

      {/* Organization Details Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <Card
          title="Tenant Profile"
          badge={<Badge variant="info">{currentOrg?.status || 'ACTIVE'}</Badge>}
          action={
            canUpdateOrg && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setIsEditOrgOpen(true)}
                className="text-xs text-sky-400 hover:text-sky-300"
              >
                <Edit2 className="w-3.5 h-3.5 mr-1" />
                Edit
              </Button>
            )
          }
        >
          {currentOrg ? (
            <div className="space-y-3 font-mono text-xs">
              <div>
                <span className="text-slate-400">Firm Name:</span>
                <p className="text-sm font-bold text-slate-100 mt-0.5">{currentOrg.name}</p>
              </div>
              <div>
                <span className="text-slate-400">Slug Identifier:</span>
                <p className="text-slate-200 mt-0.5">{currentOrg.slug}</p>
              </div>
              <div>
                <span className="text-slate-400">Organization ID:</span>
                <p className="text-slate-400 text-[10px] break-all mt-0.5">{currentOrg.id}</p>
              </div>
            </div>
          ) : (
            <CardSkeleton rows={2} />
          )}
        </Card>

        <Card title="Active Membership" badge={<Badge variant="warning">{currentRole || 'TRADER'}</Badge>}>
          <div className="space-y-3 font-mono text-xs">
            <div>
              <span className="text-slate-400">Your Operating Role:</span>
              <p className="text-sm font-bold text-slate-100 mt-0.5">{currentRole || 'TRADER'}</p>
            </div>
            <div>
              <span className="text-slate-400">Institutional Authority:</span>
              <p className="text-slate-300 mt-0.5">
                {currentRole === 'OWNER'
                  ? 'Full Administrative & Executive Governance'
                  : currentRole === 'ADMINISTRATOR'
                  ? 'Operations & Team Management'
                  : currentRole === 'PORTFOLIO_MANAGER'
                  ? 'Trading & Strategy Execution'
                  : currentRole === 'RISK_OFFICER'
                  ? 'Risk Constraints & Telemetry Oversight'
                  : currentRole === 'TRADER'
                  ? 'Paper Order Execution & Position Close'
                  : currentRole === 'AUDITOR'
                  ? 'Compliance Audit & Verification'
                  : 'Read-Only Telemetry Viewer'}
              </p>
            </div>
          </div>
        </Card>

        <Card title="Security & Multi-Tenancy">
          <div className="space-y-2 text-xs font-mono text-slate-300">
            <div className="flex items-center gap-2 text-emerald-400">
              <CheckCircle className="w-4 h-4 flex-shrink-0" />
              <span>Cryptographic Header Scoping</span>
            </div>
            <div className="flex items-center gap-2 text-emerald-400">
              <CheckCircle className="w-4 h-4 flex-shrink-0" />
              <span>Strict IDOR Tenant Boundaries</span>
            </div>
            <div className="flex items-center gap-2 text-emerald-400">
              <CheckCircle className="w-4 h-4 flex-shrink-0" />
              <span>Server-Authoritative RBAC Matrix</span>
            </div>
            <div className="flex items-center gap-2 text-amber-400 pt-1">
              <Shield className="w-4 h-4 flex-shrink-0" />
              <span>100% Paper Simulated Trading</span>
            </div>
          </div>
        </Card>
      </div>

      {/* Members Management Table */}
      <Card
        title="Team Members & Role Assignments"
        subtitle="Manage access permissions across all registered institution users."
      >
        {error ? (
          <div className="p-4 rounded-lg bg-rose-950/20 border border-rose-900/40 text-xs text-rose-300 flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            <span>{error}</span>
          </div>
        ) : (
          <Table
            columns={memberColumns}
            data={members}
            isLoading={isLoading}
            emptyMessage="No members found in this organization."
            keyExtractor={(m) => m.id}
          />
        )}
      </Card>

      {/* Institutional Role Matrix Guide */}
      <Card title="Role Capability & Permissions Reference">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-xs font-mono">
          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
            <div className="font-bold text-amber-400 mb-1">OWNER</div>
            <p className="text-slate-400">Total institutional governance, billing, member invites/roles, trading, and audit.</p>
          </div>
          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
            <div className="font-bold text-purple-400 mb-1">ADMINISTRATOR</div>
            <p className="text-slate-400">Member management, account administration, strategy config, and subscription governance.</p>
          </div>
          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
            <div className="font-bold text-sky-400 mb-1">PORTFOLIO_MANAGER</div>
            <p className="text-slate-400">Full paper order placement, position closing, strategy parameters, and trade journal.</p>
          </div>
          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
            <div className="font-bold text-rose-400 mb-1">RISK_OFFICER</div>
            <p className="text-slate-400">Risk parameter configuration, circuit breaker oversight, exposure monitoring, audit logs.</p>
          </div>
          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
            <div className="font-bold text-emerald-400 mb-1">TRADER</div>
            <p className="text-slate-400">Paper order execution, position closing, and real-time execution telemetry.</p>
          </div>
          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
            <div className="font-bold text-indigo-400 mb-1">AUDITOR</div>
            <p className="text-slate-400">Read-only access to trading records, portfolio snapshots, and compliance audit trail.</p>
          </div>
          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
            <div className="font-bold text-slate-400 mb-1">VIEWER</div>
            <p className="text-slate-400">Read-only visibility into portfolio summaries and public market states.</p>
          </div>
        </div>
      </Card>

      {/* Edit Organization Modal */}
      <Modal
        isOpen={isEditOrgOpen}
        onClose={() => setIsEditOrgOpen(false)}
        title="Update Organization Profile"
        size="sm"
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setIsEditOrgOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleUpdateOrg} isLoading={isUpdatingOrg}>
              Save Changes
            </Button>
          </>
        }
      >
        <form onSubmit={handleUpdateOrg} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1.5">Organization Firm Name</label>
            <input
              type="text"
              value={orgNameInput}
              onChange={(e) => setOrgNameInput(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-xs font-mono text-slate-100 focus:border-sky-500 focus:outline-none"
              placeholder="Firm Name"
              required
            />
          </div>
        </form>
      </Modal>

      {/* Member Invite Modal */}
      <Modal
        isOpen={isInviteOpen}
        onClose={() => setIsInviteOpen(false)}
        title="Invite New Organization Member"
        size="md"
        footer={
          <Button variant="ghost" size="sm" onClick={() => setIsInviteOpen(false)}>
            Close
          </Button>
        }
      >
        {issuedInvitation ? (
          <div className="space-y-4 font-mono text-xs">
            <div className="p-4 rounded-lg bg-emerald-950/30 border border-emerald-800/60 text-emerald-300 space-y-2">
              <div className="flex items-center gap-2 font-bold text-sm">
                <CheckCircle className="w-5 h-5 text-emerald-400" />
                <span>Invitation Successfully Created</span>
              </div>
              <p className="text-xs text-slate-300">
                A single-use cryptographic invitation has been issued for <strong>{issuedInvitation.email}</strong>.
              </p>
            </div>

            {issuedInvitation.invitation_token && (
              <div>
                <label className="block text-[11px] text-slate-400 mb-1">Invitation Secret Token</label>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    readOnly
                    value={issuedInvitation.invitation_token}
                    className="flex-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-xs text-slate-200 font-mono"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      navigator.clipboard.writeText(issuedInvitation.invitation_token || '');
                      showToast('Token copied to clipboard', 'info');
                    }}
                    title="Copy token"
                  >
                    <Copy className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            )}

            <Button
              size="sm"
              variant="outline"
              onClick={() => setIssuedInvitation(null)}
              className="w-full mt-2"
            >
              Invite Another Member
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSendInvite} className="space-y-4">
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1.5">Member Corporate Email</label>
              <input
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="colleague@institution.com"
                required
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-xs font-mono text-slate-100 focus:border-sky-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1.5">Assign Institutional Role</label>
              <select
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-xs font-mono text-slate-100 focus:border-sky-500 focus:outline-none"
              >
                <option value={OrganizationRole.TRADER}>TRADER (Paper Order Execution)</option>
                <option value={OrganizationRole.PORTFOLIO_MANAGER}>PORTFOLIO_MANAGER (Positions & Strategies)</option>
                <option value={OrganizationRole.RISK_OFFICER}>RISK_OFFICER (Risk Limits & Circuit Breakers)</option>
                <option value={OrganizationRole.ADMINISTRATOR}>ADMINISTRATOR (Member & Account Governance)</option>
                <option value={OrganizationRole.AUDITOR}>AUDITOR (Compliance & Audit Trails)</option>
                <option value={OrganizationRole.VIEWER}>VIEWER (Read-Only Telemetry)</option>
              </select>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isInviting}
              className="w-full cursor-pointer"
            >
              Generate Cryptographic Invitation
            </Button>
          </form>
        )}
      </Modal>

      {/* Role Change Modal */}
      <Modal
        isOpen={!!memberToUpdateRole}
        onClose={() => setMemberToUpdateRole(null)}
        title="Update Member Role"
        size="sm"
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setMemberToUpdateRole(null)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleConfirmRoleUpdate}
              isLoading={isUpdatingRole}
            >
              Save Role
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-300 font-mono">
            Modifying RBAC privileges for user <span className="text-slate-100 font-bold">{memberToUpdateRole?.user_id}</span>.
          </p>

          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1.5">Select New Role</label>
            <select
              value={selectedNewRole}
              onChange={(e) => setSelectedNewRole(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-xs font-mono text-slate-100 focus:border-sky-500 focus:outline-none"
            >
              {Object.values(OrganizationRole).map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Modal>

      {/* Remove Member Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={!!memberToRemove}
        onClose={() => setMemberToRemove(null)}
        onConfirm={handleConfirmRemoveMember}
        title="Remove Organization Member"
        message={
          <>
            Are you sure you want to remove user{' '}
            <strong className="text-white">{memberToRemove?.user_id}</strong> from this organization?
            They will immediately lose access to all tenant trading accounts and telemetry.
          </>
        }
        variant="danger"
        confirmLabel="Remove Member"
        isLoading={isRemovingMember}
        isPaperModeNotice={false}
      />
    </div>
  );
};
