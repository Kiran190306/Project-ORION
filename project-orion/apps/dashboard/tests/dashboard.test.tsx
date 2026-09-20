import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { DashboardPage } from '../src/pages/DashboardPage';
import type { DashboardResponse } from '../src/api/types';

const mockDashboardData: DashboardResponse = {
  account: {
    balance: '100000.00',
    equity: '102500.00',
    available_cash: '95000.00',
    used_margin: '5000.00',
    free_margin: '97500.00',
    currency: 'USD',
    is_paper: true,
  },
  performance: {
    realized_pnl: '1500.00',
    unrealized_pnl: '2500.00',
    daily_pnl: '400.00',
    drawdown_pct: 1.25,
  },
  trading: {
    open_positions: [
      {
        id: 'pos-12345678',
        account_id: 'acc-1',
        symbol: 'EUR/USD',
        side: 'BUY',
        quantity: 10000,
        open_price: 1.085,
        current_price: 1.0875,
        realized_pnl: 0,
        unrealized_pnl: 25.0,
        commission: 0,
        swap: 0,
        is_open: true,
        opened_at: new Date().toISOString(),
      },
    ],
    recent_trades: [
      {
        trade_id: 'trd-12345678',
        order_id: 'ord-12345678',
        symbol: 'EUR/USD',
        side: 'BUY',
        quantity: 10000,
        price: 1.085,
        commission: 0,
        timestamp: new Date().toISOString(),
        is_paper: true,
      },
    ],
    pending_orders: [],
  },
  strategy: {
    active_strategy: 'trend_following',
    timeframe: 'M15',
    symbols: ['EUR/USD', 'GBP/USD'],
  },
  risk: {
    status: 'healthy',
    total_exposure: '10000.00',
    margin_level: 2050.0,
    emergency_stop_active: false,
    recovery_mode_active: false,
  },
  worker: {
    enabled: true,
    state: 'RUNNING',
    is_running: true,
    last_cycle_at: new Date().toISOString(),
    uptime_seconds: 3600,
    last_error: null,
  },
  system: {
    status: 'ONLINE',
    market_data_status: 'CONNECTED',
    timestamp: new Date().toISOString(),
  },
};

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders all 7 key sections and financial values accurately', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve(mockDashboardData),
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(await screen.findByText('TRADING DASHBOARD')).toBeInTheDocument();
    expect(screen.getByText('$100,000.00')).toBeInTheDocument();
    expect(screen.getByText('$102,500.00')).toBeInTheDocument();
    expect(screen.getByText('+$2,500.00')).toBeInTheDocument();
    expect(screen.getByText('+$1,500.00')).toBeInTheDocument();
    expect(screen.getByText('trend_following')).toBeInTheDocument();
    expect(screen.getByText('healthy')).toBeInTheDocument();
    expect(screen.getByText('RUNNING')).toBeInTheDocument();
  });

  it('handles empty positions and pending orders gracefully', async () => {
    const emptyData = {
      ...mockDashboardData,
      trading: {
        open_positions: [],
        recent_trades: [],
        pending_orders: [],
      },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve(emptyData),
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(
      await screen.findByText(/no open positions\. use orders page to place a trade\./i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/no active pending orders or recent fills\./i)
    ).toBeInTheDocument();
  });

  it('renders error state and provides retry action on API failure', async () => {
    const user = userEvent.setup();
    global.fetch = vi.fn().mockRejectedValue(new Error('Backend connection refused'));

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(await screen.findByText('Unable to Load Dashboard')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /retry connection/i })).toBeInTheDocument();

    // Mock recovery on retry
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve(mockDashboardData),
    });

    await user.click(screen.getByRole('button', { name: /retry connection/i }));
    expect(await screen.findByText('TRADING DASHBOARD')).toBeInTheDocument();
  });
});
