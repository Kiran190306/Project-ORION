import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { WorkerPage } from '../src/pages/WorkerPage';
import type { WorkerStatusResponse, WorkerMetricsResponse } from '../src/api/types';

const mockWorkerStatus: WorkerStatusResponse = {
  enabled: true,
  state: 'RUNNING',
  is_running: true,
  last_cycle_at: new Date().toISOString(),
  uptime_seconds: 7200,
  last_error: null,
  updated_at: new Date().toISOString(),
};

const mockWorkerMetrics: WorkerMetricsResponse = {
  cycles_started: 120,
  cycles_completed: 119,
  cycles_failed: 1,
  market_poll_failures: 0,
  orders_submitted: 15,
  risk_rejections: 2,
  execution_failures: 0,
  uptime_seconds: 7200,
  updated_at: new Date().toISOString(),
};

describe('WorkerPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders worker lifecycle telemetry and PAPER mode indicators', async () => {
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/v1/worker/metrics')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockWorkerMetrics),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve(mockWorkerStatus),
      });
    });

    render(<WorkerPage />);

    expect(await screen.findByText('AUTONOMOUS WORKER MONITOR')).toBeInTheDocument();
    expect(screen.getAllByText('PAPER').length).toBeGreaterThan(0);
    expect(screen.getByText('RUNNING')).toBeInTheDocument();
    expect(screen.getByText('119')).toBeInTheDocument();
    expect(screen.getByText('15')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });
});
