import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PositionsPage } from '../src/pages/PositionsPage';
import { ToastProvider } from '../src/components/common/Toast';
import type { PaginatedResponse, PositionResponse, ClosePositionResponse } from '../src/api/types';

const mockPositionsList: PaginatedResponse<PositionResponse> = {
  items: [
    {
      id: 'pos-11112222',
      account_id: 'acc-1',
      symbol: 'EUR/USD',
      side: 'BUY',
      quantity: 10000,
      open_price: 1.085,
      current_price: 1.0885,
      realized_pnl: 0,
      unrealized_pnl: 35.0,
      commission: 0,
      swap: 0,
      is_open: true,
      opened_at: new Date().toISOString(),
    },
  ],
  total: 1,
  limit: 15,
  offset: 0,
  has_more: false,
};

describe('PositionsPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders positions table with formatted values and P&L', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve(mockPositionsList),
    });

    render(
      <ToastProvider>
        <PositionsPage />
      </ToastProvider>
    );

    expect(await screen.findByText('POSITIONS MONITOR')).toBeInTheDocument();
    expect(screen.getByText('EUR/USD')).toBeInTheDocument();
    expect(screen.getByText('+$35.00')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /close/i })).toBeInTheDocument();
  });

  it('closes open position with confirmation modal', async () => {
    const user = userEvent.setup();

    const closeResponse: ClosePositionResponse = {
      position_id: 'pos-11112222',
      symbol: 'EUR/USD',
      closed_quantity: 10000,
      close_price: 1.0885,
      realized_pnl: 35.0,
      closed_at: new Date().toISOString(),
      message: 'Position closed successfully',
    };

    global.fetch = vi.fn().mockImplementation((url: string, opts: RequestInit) => {
      if (opts?.method === 'POST' && url.includes('/close')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(closeResponse),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve(mockPositionsList),
      });
    });

    render(
      <ToastProvider>
        <PositionsPage />
      </ToastProvider>
    );

    const closeBtn = await screen.findByRole('button', { name: /close/i });
    await user.click(closeBtn);

    expect(screen.getByRole('heading', { name: /close paper position/i })).toBeInTheDocument();

    const confirmBtn = screen.getByRole('button', { name: /confirm close position/i });
    await user.click(confirmBtn);

    expect(await screen.findByText(/position closed: EUR\/USD \(\+\$35\.00 realized\)/i)).toBeInTheDocument();
  });
});
