import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StrategiesPage } from '../src/pages/StrategiesPage';
import { ToastProvider } from '../src/components/common/Toast';
import type { StrategyListResponse, AccountStrategyConfigResponse } from '../src/api/types';

const mockCatalogue: StrategyListResponse = {
  strategies: [
    {
      id: 'trend_following',
      name: 'Trend Following',
      type: 'trend_following',
      description: 'Follows trends using MA and momentum indicators.',
      timeframes: ['M15', 'H1'],
      symbols: ['EUR/USD', 'GBP/USD'],
      is_active: true,
    },
    {
      id: 'mean_reversion',
      name: 'Mean Reversion',
      type: 'mean_reversion',
      description: 'Reverts to mean when price deviates from average.',
      timeframes: ['M15', 'H1'],
      symbols: ['USD/JPY'],
      is_active: true,
    },
  ],
  total: 2,
  updated_at: new Date().toISOString(),
};

const mockActiveConfig: AccountStrategyConfigResponse = {
  account_id: 'acc-1',
  strategy_id: 'trend_following',
  timeframe: 'M15',
  symbols: ['EUR/USD', 'GBP/USD'],
  parameters: { fast_ma: 10, slow_ma: 30 },
  is_active: true,
  updated_at: new Date().toISOString(),
};

describe('StrategiesPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders strategy catalogue and active strategy banner', async () => {
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/account/config')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockActiveConfig),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve(mockCatalogue),
      });
    });

    render(
      <ToastProvider>
        <StrategiesPage />
      </ToastProvider>
    );

    expect(await screen.findByText('STRATEGY REGISTRY & CONTROL')).toBeInTheDocument();
    expect(screen.getByText('Active Account Strategy')).toBeInTheDocument();
    expect(screen.getAllByText('trend_following').length).toBeGreaterThan(0);
    expect(screen.getByText('Mean Reversion')).toBeInTheDocument();
  });

  it('modifies strategy configuration and calls backend update', async () => {
    const user = userEvent.setup();

    const updatedConfig: AccountStrategyConfigResponse = {
      ...mockActiveConfig,
      timeframe: 'H1',
    };

    global.fetch = vi.fn().mockImplementation((url: string, opts: RequestInit) => {
      if (opts?.method === 'PUT' && url.includes('/account/config')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(updatedConfig),
        });
      }
      if (url.includes('/account/config')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockActiveConfig),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve(mockCatalogue),
      });
    });

    render(
      <ToastProvider>
        <StrategiesPage />
      </ToastProvider>
    );

    const modifyBtn = await screen.findByRole('button', { name: /modify configuration/i });
    await user.click(modifyBtn);

    expect(screen.getByRole('heading', { name: /configure account strategy/i })).toBeInTheDocument();

    const saveBtn = screen.getByRole('button', { name: /save strategy settings/i });
    await user.click(saveBtn);

    expect(
      await screen.findByText(/account strategy updated to trend_following \(H1\)/i)
    ).toBeInTheDocument();
  });
});
