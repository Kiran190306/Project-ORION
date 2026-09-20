import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PortfolioPage } from '../src/pages/PortfolioPage';
import type {
  PortfolioOverviewResponse,
  EquityCurveResponse,
  PnLBreakdownResponse,
  ExposureResponse,
} from '../src/api/types';

const mockOverview: PortfolioOverviewResponse = {
  balance: '100000.00',
  equity: '101500.00',
  used_margin: '2500.00',
  free_margin: '99000.00',
  margin_level: 4060.0,
  unrealized_pnl: '1500.00',
  realized_pnl: '500.00',
  net_exposure: '10000.00',
  gross_exposure: '10000.00',
  open_positions_count: 1,
  currency: 'USD',
  is_paper: true,
  updated_at: new Date().toISOString(),
};

const mockEquity: EquityCurveResponse = {
  balance: '100000.00',
  equity: '101500.00',
  peak_equity: '102000.00',
  current_drawdown: 0.49,
  max_drawdown: 1.25,
  currency: 'USD',
  updated_at: new Date().toISOString(),
};

const mockPnl: PnLBreakdownResponse = {
  realized_pnl: '500.00',
  unrealized_pnl: '1500.00',
  gross_profit: '800.00',
  gross_loss: '300.00',
  commission: '0.00',
  swap: '0.00',
  fees: '0.00',
  net_pnl: '500.00',
  currency: 'USD',
  updated_at: new Date().toISOString(),
};

const mockExposure: ExposureResponse = {
  net_exposure: '10000.00',
  gross_exposure: '10000.00',
  long_exposure: '10000.00',
  short_exposure: '0.00',
  currency_exposures: [
    {
      currency: 'EUR',
      long_exposure: '10000.00',
      short_exposure: '0.00',
      net_exposure: '10000.00',
      position_count: 1,
    },
  ],
  updated_at: new Date().toISOString(),
};

describe('PortfolioPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders portfolio balances, equity curve, and P&L breakdown', async () => {
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/v1/portfolio/equity')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockEquity),
        });
      }
      if (url.includes('/api/v1/portfolio/pnl')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockPnl),
        });
      }
      if (url.includes('/api/v1/portfolio/exposure')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockExposure),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve(mockOverview),
      });
    });

    render(<PortfolioPage />);

    expect(await screen.findByText('PORTFOLIO ANALYTICS')).toBeInTheDocument();
    expect(screen.getAllByText('$100,000.00').length).toBeGreaterThan(0);
    expect(screen.getAllByText('$101,500.00').length).toBeGreaterThan(0);
    expect(screen.getByText('$800.00')).toBeInTheDocument();
    expect(screen.getAllByText('EUR').length).toBeGreaterThan(0);
  });
});
