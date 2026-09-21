import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MarketOverviewWidget } from '../src/components/market/MarketOverviewWidget';
import type { MarketQuote } from '../src/api/types';

const mockEurUsdQuote: MarketQuote = {
  symbol: 'EUR/USD',
  bid: '1.08500',
  ask: '1.08520',
  mid: '1.08510',
  spread: '0.00020',
  spread_pips: '2.0',
  timestamp: new Date().toISOString(),
  provider: 'mock',
  is_stale: false,
  quality: 'EXCELLENT',
};

const mockGbpUsdQuote: MarketQuote = {
  symbol: 'GBP/USD',
  bid: '1.27100',
  ask: '1.27130',
  mid: '1.27115',
  spread: '0.00030',
  spread_pips: '3.0',
  timestamp: new Date().toISOString(),
  provider: 'mock',
  is_stale: false,
  quality: 'EXCELLENT',
};

const mockUsdJpyStaleQuote: MarketQuote = {
  symbol: 'USD/JPY',
  bid: '155.200',
  ask: '155.250',
  mid: '155.225',
  spread: '0.050',
  spread_pips: '5.0',
  timestamp: new Date(Date.now() - 60000).toISOString(),
  provider: 'mock',
  is_stale: true,
  quality: 'STALE',
};

describe('MarketOverviewWidget', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders live market quotes with spreads, bid/ask, and quality badges', async () => {
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('EUR%2FUSD') || url.includes('EUR/USD')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockEurUsdQuote),
        });
      }
      if (url.includes('GBP%2FUSD') || url.includes('GBP/USD')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockGbpUsdQuote),
        });
      }
      if (url.includes('USD%2FJPY') || url.includes('USD/JPY')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockUsdJpyStaleQuote),
        });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    render(<MarketOverviewWidget />);

    expect(screen.getByText('Live Market Feed')).toBeInTheDocument();
    expect(screen.getByText(/PAPER FEED/i)).toBeInTheDocument();

    // Verify symbols rendered
    expect(await screen.findByText('EUR/USD')).toBeInTheDocument();
    expect(await screen.findByText('GBP/USD')).toBeInTheDocument();
    expect(await screen.findByText('USD/JPY')).toBeInTheDocument();

    // Verify mid prices rendered
    expect(screen.getByText('1.08510')).toBeInTheDocument();
    expect(screen.getByText('1.27115')).toBeInTheDocument();
    expect(screen.getByText('155.225')).toBeInTheDocument();

    // Verify spreads
    expect(screen.getByText('2.0 pips')).toBeInTheDocument();
    expect(screen.getByText('3.0 pips')).toBeInTheDocument();
    expect(screen.getByText('5.0 pips')).toBeInTheDocument();

    // Verify stale and quality badges
    expect(screen.getAllByText('EXCELLENT').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('STALE')).toBeInTheDocument();
  });
});
