import React, { useState, useCallback } from 'react';
import { RefreshCw, CheckCircle2, Lock } from 'lucide-react';
import { riskApi } from '../api/endpoints';
import type { RiskStatusResponse, RiskLimitsResponse } from '../api/types';
import { usePolling } from '../hooks/usePolling';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge, PaperTradingBadge } from '../components/common/Badge';
import { Table, Column } from '../components/common/Table';
import { formatCurrency, formatPercent } from '../utils/formatters';
import { getErrorMessage } from '../utils/errors';
import type { RiskLimitItem } from '../api/types';

export const RiskPage: React.FC = () => {
  const [status, setStatus] = useState<RiskStatusResponse | null>(null);
  const [limits, setLimits] = useState<RiskLimitsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRisk = useCallback(async () => {
    try {
      const [s, l] = await Promise.all([riskApi.getStatus(), riskApi.getLimits()]);
      setStatus(s);
      setLimits(l);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  usePolling(fetchRisk, 10000);

  const limitColumns: Column<RiskLimitItem>[] = [
    {
      header: 'Policy / Limit Rule',
      accessor: 'name',
      render: (item) => (
        <div>
          <div className="font-bold text-slate-100">{item.name}</div>
          <div className="text-[11px] text-slate-400 font-sans mt-0.5">{item.description}</div>
        </div>
      ),
    },
    {
      header: 'Category',
      render: (item) => <Badge variant="default">{item.category}</Badge>,
    },
    {
      header: 'Severity',
      render: (item) => (
        <Badge variant={item.severity === 'critical' ? 'danger' : 'warning'}>
          {item.severity}
        </Badge>
      ),
    },
    {
      header: 'Enforcement Status',
      render: () => (
        <div className="flex items-center gap-1.5 text-emerald-400">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span className="font-semibold">ACTIVE</span>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100">
              RISK MANAGEMENT ENGINE
            </h1>
            <PaperTradingBadge size="sm" />
          </div>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Pre-trade risk filtering &bull; Portfolio limits enforcement &bull; Institutional capital protection
          </p>
        </div>

        <Button variant="outline" size="sm" onClick={() => fetchRisk()}>
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </Button>
      </div>

      {/* Institutional Read-Only Guarantee */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-start gap-3.5 font-mono text-xs text-slate-300">
        <Lock className="w-4 h-4 text-sky-400 mt-0.5 flex-shrink-0" />
        <div>
          <span className="font-semibold text-slate-100">Deterministic Invariant Protection:</span>{' '}
          Institutional risk policies are evaluated directly by the quantitative risk domain engine.
          Risk limits cannot be altered, weakened, or bypassed via user-interface controls.
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300 text-xs font-mono">
          Error retrieving risk status: {error}
        </div>
      )}

      {/* Risk Metrics Cards */}
      {status && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 font-mono text-xs">
          <Card
            className="p-4 border-l-4 border-l-emerald-500"
            title="Engine Health"
            badge={
              <Badge variant={status.status === 'healthy' ? 'success' : 'danger'}>
                {status.status}
              </Badge>
            }
          >
            <div className="space-y-1.5 mt-2">
              <div className="flex justify-between">
                <span className="text-slate-400">Position Count:</span>
                <span className="font-bold text-slate-200">{status.position_count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Total Exposure:</span>
                <span className="font-bold text-slate-200">{formatCurrency(status.total_exposure)}</span>
              </div>
            </div>
          </Card>

          <Card className="p-4 border-l-4 border-l-sky-500" title="Margin Solvency">
            <div className="space-y-1.5 mt-2">
              <div className="flex justify-between">
                <span className="text-slate-400">Margin Level:</span>
                <span className="font-bold text-slate-200">{formatPercent(status.margin_level)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Used Margin:</span>
                <span className="font-bold text-slate-200">{formatCurrency(status.used_margin)}</span>
              </div>
            </div>
          </Card>

          <Card className="p-4 border-l-4 border-l-amber-500" title="Drawdown Guard">
            <div className="space-y-1.5 mt-2">
              <div className="flex justify-between">
                <span className="text-slate-400">Current Drawdown:</span>
                <span className="font-bold text-slate-200">{formatPercent(status.drawdown)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Consecutive Losses:</span>
                <span className="font-bold text-slate-200">{status.consecutive_losses}</span>
              </div>
            </div>
          </Card>

          <Card
            className={`p-4 border-l-4 ${
              status.emergency_stop_active ? 'border-l-rose-500 bg-rose-950/20' : 'border-l-emerald-500'
            }`}
            title="Emergency Circuit Breaker"
          >
            <div className="space-y-1.5 mt-2">
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Emergency Stop:</span>
                <span
                  className={`font-bold ${
                    status.emergency_stop_active ? 'text-rose-400' : 'text-emerald-400'
                  }`}
                >
                  {status.emergency_stop_active ? 'ACTIVE' : 'INACTIVE'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Recovery Mode:</span>
                <span className="text-slate-300">
                  {status.recovery_mode_active ? 'ACTIVE' : 'NORMAL'}
                </span>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Risk Limits Policy Table */}
      <Card title="Active Institutional Risk Limit Policies">
        <Table
          columns={limitColumns}
          data={limits?.limits || []}
          isLoading={isLoading}
          emptyMessage="No risk policies loaded."
          keyExtractor={(item) => item.name}
        />
      </Card>
    </div>
  );
};
