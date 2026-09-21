import React, { useState, useEffect, useCallback } from 'react';
import { Filter, Eye, ShieldCheck, RefreshCw } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { useOrganization } from '../auth/OrganizationContext';
import { hasPermission, Permission } from '../auth/permissions';
import { organizationApi } from '../api/endpoints';
import type { AuditLogResponse } from '../api/types';
import { PageHeader } from '../components/common/PageHeader';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Table, Column } from '../components/common/Table';
import { Modal } from '../components/common/Modal';
import { ErrorState } from '../components/common/ErrorState';

export const AuditPage: React.FC = () => {
  const { user } = useAuth();
  const { currentOrg, currentRole, isLoading: isOrgLoading } = useOrganization();

  const [logs, setLogs] = useState<AuditLogResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEventType, setSelectedEventType] = useState<string>('');
  const [selectedLogForDetails, setSelectedLogForDetails] = useState<AuditLogResponse | null>(null);

  const canReadAudit = hasPermission(currentRole, Permission.AUDIT_READ, user?.is_superuser);

  const loadAuditLogs = useCallback(async () => {
    if (!currentOrg || !canReadAudit) {
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      const auditEntries = await organizationApi.listAuditLogs(currentOrg.id, {
        limit: 50,
        offset: 0,
        event_type: selectedEventType || undefined,
      });
      setLogs(auditEntries);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve compliance audit logs';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [currentOrg, canReadAudit, selectedEventType]);

  useEffect(() => {
    if (!isOrgLoading) {
      loadAuditLogs();
    }
  }, [loadAuditLogs, isOrgLoading]);

  if (isOrgLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Compliance Audit Trail"
          subtitle="Loading organizational context..."
          breadcrumbs={[{ label: 'Audit Trail' }]}
        />
        <div className="space-y-4">
          <div className="h-20 bg-slate-800/40 rounded-xl animate-pulse" />
          <div className="h-64 bg-slate-800/40 rounded-xl animate-pulse" />
        </div>
      </div>
    );
  }

  if (!canReadAudit) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Compliance Audit Trail"
          subtitle="Immutable compliance records for institutional governance."
          breadcrumbs={[{ label: 'Audit Trail' }]}
        />
        <Card>
          <div className="p-8 text-center space-y-3">
            <ShieldCheck className="w-12 h-12 text-slate-500 mx-auto" />
            <h3 className="text-base font-semibold text-slate-200 font-mono">
              Access Restricted
            </h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Your active institutional role ({currentRole || 'VIEWER'}) does not grant <code>AUDIT_READ</code> permission. Contact an Administrator or Owner for access.
            </p>
          </div>
        </Card>
      </div>
    );
  }

  const auditColumns: Column<AuditLogResponse>[] = [
    {
      header: 'Timestamp (UTC)',
      accessor: 'timestamp',
      render: (log) => (
        <span className="font-mono text-xs text-slate-300">
          {new Date(log.timestamp).toISOString().replace('T', ' ').substring(0, 19)}
        </span>
      ),
    },
    {
      header: 'Event Type',
      accessor: 'event_type',
      render: (log) => {
        let variant: 'default' | 'info' | 'warning' | 'danger' | 'success' = 'default';
        if (log.event_type.includes('CREATE') || log.event_type.includes('PLACED')) variant = 'success';
        else if (log.event_type.includes('UPDATE') || log.event_type.includes('ROLE')) variant = 'info';
        else if (log.event_type.includes('CANCEL') || log.event_type.includes('CLOSE')) variant = 'warning';
        else if (log.event_type.includes('FAIL') || log.event_type.includes('ERROR')) variant = 'danger';

        return <Badge variant={variant}>{log.event_type}</Badge>;
      },
    },
    {
      header: 'Actor',
      accessor: 'actor',
      render: (log) => (
        <span className="font-mono text-xs text-slate-200">
          {log.actor || 'SYSTEM'}
        </span>
      ),
    },
    {
      header: 'Component',
      accessor: 'component',
      render: (log) => (
        <span className="font-mono text-xs text-slate-400 uppercase tracking-wider">
          {log.component}
        </span>
      ),
    },
    {
      header: 'Payload Details',
      render: (log) => (
        <Button
          size="sm"
          variant="ghost"
          onClick={() => setSelectedLogForDetails(log)}
          className="text-xs px-2 py-1 text-sky-400 hover:text-sky-300"
        >
          <Eye className="w-3.5 h-3.5 mr-1" />
          View Payload
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Compliance Audit Trail"
        subtitle="Immutable ledger of operational, algorithmic, and governance actions with automated secret redaction."
        breadcrumbs={[{ label: 'Audit Trail' }]}
        actions={
          <Button
            size="sm"
            variant="outline"
            onClick={loadAuditLogs}
            disabled={isLoading}
            className="inline-flex items-center gap-2 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </Button>
        }
      />

      {/* Audit Telemetry & Filter Bar */}
      <Card>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3">
            <Filter className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-mono text-slate-300 uppercase">Filter by Event:</span>
            <select
              value={selectedEventType}
              onChange={(e) => setSelectedEventType(e.target.value)}
              className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-xs font-mono text-slate-200 focus:outline-none focus:border-sky-500"
            >
              <option value="">All Events ({logs.length})</option>
              <option value="ORDER_PLACED">ORDER_PLACED</option>
              <option value="ORDER_CANCELLED">ORDER_CANCELLED</option>
              <option value="POSITION_CLOSED">POSITION_CLOSED</option>
              <option value="STRATEGY_CONFIGURED">STRATEGY_CONFIGURED</option>
              <option value="MEMBER_INVITED">MEMBER_INVITED</option>
              <option value="MEMBER_ROLE_UPDATED">MEMBER_ROLE_UPDATED</option>
              <option value="BILLING_CHECKOUT_CREATED">BILLING_CHECKOUT_CREATED</option>
              <option value="SUBSCRIPTION_CANCELLED">SUBSCRIPTION_CANCELLED</option>
            </select>
          </div>

          <div className="text-xs font-mono text-slate-400">
            Tenant ID: <span className="text-slate-200">{currentOrg?.id || '—'}</span>
          </div>
        </div>
      </Card>

      {/* Audit Log Table */}
      <Card title="Audit Event Log" badge={<Badge variant="default">{logs.length} Events</Badge>}>
        {error ? (
          <ErrorState
            title="Failed to Load Audit Logs"
            message={error}
            onRetry={loadAuditLogs}
          />
        ) : (
          <Table
            columns={auditColumns}
            data={logs}
            isLoading={isLoading}
            emptyMessage="No audit trail entries matching filter criteria."
            keyExtractor={(log) => log.id}
          />
        )}
      </Card>

      {/* Payload Modal */}
      <Modal
        isOpen={!!selectedLogForDetails}
        onClose={() => setSelectedLogForDetails(null)}
        title="Audit Payload Details"
        size="md"
        footer={
          <Button variant="ghost" size="sm" onClick={() => setSelectedLogForDetails(null)}>
            Close
          </Button>
        }
      >
        {selectedLogForDetails && (
          <div className="space-y-4 font-mono text-xs">
            <div className="grid grid-cols-2 gap-2 text-slate-400 p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <div>Event: <span className="text-slate-200 font-bold">{selectedLogForDetails.event_type}</span></div>
              <div>Component: <span className="text-slate-200">{selectedLogForDetails.component}</span></div>
              <div>Actor: <span className="text-slate-200">{selectedLogForDetails.actor}</span></div>
              <div>Time: <span className="text-slate-200">{new Date(selectedLogForDetails.timestamp).toISOString()}</span></div>
            </div>

            <div>
              <div className="text-[11px] text-slate-400 mb-1">Payload JSON (Secrets Redacted)</div>
              <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-emerald-400 overflow-x-auto max-h-64">
                {JSON.stringify(selectedLogForDetails.details, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};
