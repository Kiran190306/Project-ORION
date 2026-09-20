import React, { useState, useCallback } from 'react';
import { RefreshCw, Activity } from 'lucide-react';
import { workerApi } from '../api/endpoints';
import type { WorkerStatusResponse, WorkerMetricsResponse } from '../api/types';
import { usePolling } from '../hooks/usePolling';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge, PaperTradingBadge } from '../components/common/Badge';
import { formatDateTime, formatUnits } from '../utils/formatters';
import { getErrorMessage } from '../utils/errors';

export const WorkerPage: React.FC = () => {
  const [status, setStatus] = useState<WorkerStatusResponse | null>(null);
  const [metrics, setMetrics] = useState<WorkerMetricsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchWorker = useCallback(async () => {
    try {
      const [s, m] = await Promise.all([workerApi.getStatus(), workerApi.getMetrics()]);
      setStatus(s);
      setMetrics(m);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  usePolling(fetchWorker, 8000);

  if (isLoading && !status) {
    return (
      <div className="space-y-6">
        <div className="h-6 bg-slate-800 rounded w-48 animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 bg-slate-900 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100">
              AUTONOMOUS WORKER MONITOR
            </h1>
            <PaperTradingBadge size="sm" />
          </div>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Real-time coordinator lifecycle &bull; Market polling status &bull; Trade cycle metrics
          </p>
        </div>

        <Button variant="outline" size="sm" onClick={() => fetchWorker()}>
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </Button>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300 text-xs font-mono">
          Error retrieving worker status: {error}
        </div>
      )}

      {/* Lifecycle Status Overview */}
      {status && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 font-mono text-xs">
          <Card
            className="p-4 border-l-4 border-l-sky-500"
            title="Lifecycle State"
            badge={
              <Badge variant={status.is_running ? 'success' : 'default'}>
                {status.state}
              </Badge>
            }
          >
            <div className="space-y-1.5 mt-2">
              <div className="flex justify-between">
                <span className="text-slate-400">Worker Enabled:</span>
                <span className="font-bold text-slate-200">
                  {status.enabled ? 'YES' : 'NO'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Execution Mode:</span>
                <span className="font-bold text-amber-400">PAPER</span>
              </div>
            </div>
          </Card>

          <Card className="p-4 border-l-4 border-l-emerald-500" title="Cycle Schedule">
            <div className="space-y-1.5 mt-2">
              <div className="flex justify-between">
                <span className="text-slate-400">Last Execution:</span>
                <span className="text-slate-200">{formatDateTime(status.last_cycle_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Uptime:</span>
                <span className="font-bold text-slate-200">{Math.round(status.uptime_seconds)}s</span>
              </div>
            </div>
          </Card>

          <Card className="p-4 border-l-4 border-l-purple-500" title="Error Telemetry">
            <div className="space-y-1.5 mt-2">
              <div className="flex justify-between">
                <span className="text-slate-400">Last Error:</span>
                <span className={status.last_error ? 'text-rose-400 font-semibold' : 'text-emerald-400'}>
                  {status.last_error || 'None (Normal)'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Heartbeat:</span>
                <span className="text-slate-200">{formatDateTime(status.updated_at)}</span>
              </div>
            </div>
          </Card>

          <Card className="p-4 border-l-4 border-l-amber-500" title="Security Model">
            <div className="space-y-1.5 mt-2 text-slate-400">
              <p className="text-[11px] leading-relaxed">
                Superuser permissions are enforced for lifecycle controls. Read telemetry is active.
              </p>
            </div>
          </Card>
        </div>
      )}

      {/* Operational Metrics Cards */}
      {metrics && (
        <Card
          title={
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-sky-400" />
              <span>Worker Operational Metrics</span>
            </div>
          }
        >
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 font-mono text-center">
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <div className="text-[11px] text-slate-400 mb-1">CYCLES COMPLETED</div>
              <div className="text-lg font-bold text-emerald-400">{formatUnits(metrics.cycles_completed)}</div>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <div className="text-[11px] text-slate-400 mb-1">CYCLES FAILED</div>
              <div className="text-lg font-bold text-rose-400">{formatUnits(metrics.cycles_failed)}</div>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <div className="text-[11px] text-slate-400 mb-1">ORDERS SUBMITTED</div>
              <div className="text-lg font-bold text-sky-400">{formatUnits(metrics.orders_submitted)}</div>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <div className="text-[11px] text-slate-400 mb-1">RISK REJECTIONS</div>
              <div className="text-lg font-bold text-amber-400">{formatUnits(metrics.risk_rejections)}</div>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <div className="text-[11px] text-slate-400 mb-1">EXECUTION FAILS</div>
              <div className="text-lg font-bold text-slate-300">{formatUnits(metrics.execution_failures)}</div>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <div className="text-[11px] text-slate-400 mb-1">MARKET POLL FAILS</div>
              <div className="text-lg font-bold text-slate-300">{formatUnits(metrics.market_poll_failures)}</div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};
