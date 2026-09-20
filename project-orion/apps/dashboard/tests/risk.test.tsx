import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RiskPage } from '../src/pages/RiskPage';
import type { RiskStatusResponse, RiskLimitsResponse } from '../src/api/types';

const mockRiskStatus: RiskStatusResponse = {
  status: 'healthy',
  position_count: 2,
  total_exposure: '20000.00',
  used_margin: '5000.00',
  free_margin: '95000.00',
  margin_level: 2000.0,
  drawdown: 0.85,
  daily_pnl: '250.00',
  daily_loss_rate: 0.0,
  consecutive_losses: 0,
  emergency_stop_active: false,
  recovery_mode_active: false,
  updated_at: new Date().toISOString(),
};

const mockRiskLimits: RiskLimitsResponse = {
  limits: [
    {
      name: 'maximum_position_size',
      category: 'position',
      description: 'Maximum position size in units',
      is_enabled: true,
      severity: 'warning',
    },
    {
      name: 'maximum_daily_loss',
      category: 'pnl',
      description: 'Maximum daily loss percentage',
      is_enabled: true,
      severity: 'critical',
    },
  ],
  total: 2,
  updated_at: new Date().toISOString(),
};

describe('RiskPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders read-only risk telemetry and limits', async () => {
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/v1/risk/limits')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockRiskLimits),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve(mockRiskStatus),
      });
    });

    render(<RiskPage />);

    expect(await screen.findByText('RISK MANAGEMENT ENGINE')).toBeInTheDocument();
    expect(screen.getByText('Deterministic Invariant Protection:')).toBeInTheDocument();
    expect(screen.getByText('healthy')).toBeInTheDocument();
    expect(screen.getByText('$20,000.00')).toBeInTheDocument();
    expect(screen.getByText('maximum_position_size')).toBeInTheDocument();
    expect(screen.getByText('maximum_daily_loss')).toBeInTheDocument();
  });

  it('verifies that no toggle or delete controls exist that could weaken risk policies', async () => {
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/v1/risk/limits')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockRiskLimits),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve(mockRiskStatus),
      });
    });

    render(<RiskPage />);

    await screen.findByText('RISK MANAGEMENT ENGINE');

    // Verify there are no buttons to disable or override risk
    expect(screen.queryByRole('button', { name: /disable/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /bypass/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument();
  });
});
