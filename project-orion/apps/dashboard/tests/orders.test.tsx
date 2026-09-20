import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { OrdersPage } from '../src/pages/OrdersPage';
import { ToastProvider } from '../src/components/common/Toast';
import type { PaginatedResponse, OrderResponse } from '../src/api/types';

const mockOrdersList: PaginatedResponse<OrderResponse> = {
  items: [
    {
      id: 'ord-11112222',
      account_id: 'acc-1',
      symbol: 'EUR/USD',
      side: 'BUY',
      order_type: 'MARKET',
      quantity: 10000,
      price: null,
      status: 'FILLED',
      filled_quantity: 10000,
      is_paper: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: 'ord-33334444',
      account_id: 'acc-1',
      symbol: 'GBP/USD',
      side: 'SELL',
      order_type: 'LIMIT',
      quantity: 20000,
      price: 1.305,
      status: 'PENDING',
      filled_quantity: 0,
      is_paper: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ],
  total: 2,
  limit: 15,
  offset: 0,
  has_more: false,
};

describe('OrdersPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders order list and action buttons', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve(mockOrdersList),
    });

    render(
      <ToastProvider>
        <OrdersPage />
      </ToastProvider>
    );

    expect(await screen.findByText('ORDER MANAGEMENT')).toBeInTheDocument();
    expect(screen.getByText('EUR/USD')).toBeInTheDocument();
    expect(screen.getByText('GBP/USD')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /place paper order/i })).toBeInTheDocument();
  });

  it('opens order modal and validates positive quantity', async () => {
    const user = userEvent.setup();

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve(mockOrdersList),
    });

    render(
      <ToastProvider>
        <OrdersPage />
      </ToastProvider>
    );

    await user.click(await screen.findByRole('button', { name: /place paper order/i }));
    expect(screen.getByRole('heading', { name: /place paper order/i })).toBeInTheDocument();

    const volumeInput = screen.getByPlaceholderText('10000');
    await user.clear(volumeInput);
    await user.type(volumeInput, '-500');

    await user.click(screen.getByRole('button', { name: /confirm & submit paper order/i }));
    expect(
      await screen.findByText(/order quantity must be a strictly positive number/i)
    ).toBeInTheDocument();
  });

  it('submits a paper market order successfully', async () => {
    const user = userEvent.setup();

    const createdOrder: OrderResponse = {
      id: 'ord-new-uuid',
      account_id: 'acc-1',
      symbol: 'EUR/USD',
      side: 'BUY',
      order_type: 'MARKET',
      quantity: 10000,
      status: 'FILLED',
      filled_quantity: 10000,
      is_paper: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    global.fetch = vi.fn().mockImplementation((url: string, opts: RequestInit) => {
      if (opts?.method === 'POST' && url.includes('/api/v1/orders/')) {
        return Promise.resolve({
          ok: true,
          status: 201,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(createdOrder),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve(mockOrdersList),
      });
    });

    render(
      <ToastProvider>
        <OrdersPage />
      </ToastProvider>
    );

    await user.click(await screen.findByRole('button', { name: /place paper order/i }));
    await user.click(screen.getByRole('button', { name: /confirm & submit paper order/i }));

    expect(await screen.findByText(/order created: EUR\/USD BUY \(FILLED\)/i)).toBeInTheDocument();
  });

  it('cancels a pending order after confirmation', async () => {
    const user = userEvent.setup();

    global.fetch = vi.fn().mockImplementation((url: string, opts: RequestInit) => {
      if (opts?.method === 'POST' && url.includes('/cancel')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve({ order_id: 'ord-33334444', status: 'CANCELLED', message: 'Success' }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve(mockOrdersList),
      });
    });

    render(
      <ToastProvider>
        <OrdersPage />
      </ToastProvider>
    );

    const cancelButtons = await screen.findAllByRole('button', { name: /cancel/i });
    await user.click(cancelButtons[0]);

    expect(screen.getByText(/confirm order cancellation/i)).toBeInTheDocument();

    const confirmBtn = screen.getByRole('button', { name: /cancel order/i });
    await user.click(confirmBtn);

    expect(await screen.findByText(/order ord-3333 cancelled\./i)).toBeInTheDocument();
  });
});
