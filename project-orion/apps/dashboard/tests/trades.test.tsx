import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TradesPage } from '../src/pages/TradesPage';
import type { PaginatedResponse, TradeResponse } from '../src/api/types';

const mockTradesList: PaginatedResponse<TradeResponse> = {
  items: [
    {
      trade_id: 'trd-11112222',
      order_id: 'ord-11112222',
      symbol: 'EUR/USD',
      side: 'BUY',
      quantity: 10000,
      price: 1.085,
      commission: 0,
      timestamp: new Date().toISOString(),
      is_paper: true,
    },
  ],
  total: 1,
  limit: 20,
  offset: 0,
  has_more: false,
};

describe('TradesPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders executed trade fills ledger', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve(mockTradesList),
    });

    render(<TradesPage />);

    expect(await screen.findByText('TRADE EXECUTION LEDGER')).toBeInTheDocument();
    expect(screen.getByText('EUR/USD')).toBeInTheDocument();
    expect(screen.getByText('10,000')).toBeInTheDocument();
  });
});
