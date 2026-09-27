import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ToastProvider } from '../src/components/common/Toast';
import { OrdersPage } from '../src/pages/OrdersPage';
import { StrategiesPage } from '../src/pages/StrategiesPage';
import { PortfolioPage } from '../src/pages/PortfolioPage';
import { ordersApi, positionsApi, strategiesApi, portfolioApi } from '../src/api/endpoints';

describe('Phase 4: Position Sizing & Multi-Strategy Execution Integration', () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    vi.restoreAllMocks();
  });

  const mockStrategiesCatalogue = {
    strategies: [
      {
        id: 'trend_following_v1',
        name: 'Trend Following Momentum',
        type: 'trend',
        description: 'Dual EMA crossover with volatility filter',
        timeframes: ['M15', 'H1'],
        symbols: ['EUR/USD', 'GBP/USD'],
        is_active: true,
      },
      {
        id: 'mean_reversion_v1',
        name: 'Statistical Mean Reversion',
        type: 'mean_reversion',
        description: 'Bollinger Band and RSI mean reversion',
        timeframes: ['M5', 'M15'],
        symbols: ['USD/JPY', 'EUR/USD'],
        is_active: true,
      },
    ],
    total: 2,
    updated_at: new Date().toISOString(),
  };

  const mockAccountConfigs = [
    {
      account_id: 'acc_01',
      strategy_id: 'trend_following_v1',
      name: 'Trend Following Momentum',
      timeframe: 'M15',
      symbols: ['EUR/USD', 'GBP/USD'],
      parameters: { fast_ema: 9, slow_ema: 21 },
      is_active: true,
      deployment_status: 'INCUBATING',
      updated_at: new Date().toISOString(),
    },
  ];

  const mockOrdersResponse = {
    items: [
      {
        id: 'ord_phase4_01',
        account_id: 'acc_01',
        symbol: 'EUR/USD',
        side: 'BUY',
        order_type: 'MARKET',
        quantity: 15000,
        price: 1.0850,
        status: 'FILLED',
        filled_quantity: 15000,
        average_fill_price: 1.0850,
        strategy_id: 'trend_following_v1',
        is_paper: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ],
    total: 1,
    limit: 15,
    offset: 0,
    has_more: false,
  };

  const mockSizingResponse = {
    symbol: 'EUR/USD',
    method: 'risk_percent',
    account_balance: 100000,
    account_equity: 100000,
    requested_risk_pct: 1.0,
    confidence: 1.0,
    entry_price: 1.085,
    stop_loss: 1.08,
    stop_distance: 0.005,
    calculated_units: 20000,
    notional_value: 21700,
    monetary_risk: 100,
    account_risk_pct: 0.1,
    required_margin: 217,
    available_margin: 100000,
    market_data_status: 'REALTIME' as const,
    constraints_applied: [],
    warnings: [],
    is_valid: true,
    validation_errors: [],
  };

  const mockStrategyBreakdown = {
    account_id: 'acc_01',
    strategies: [
      {
        strategy_id: 'trend_following_v1',
        strategy_name: 'Trend Following Momentum',
        is_active: true,
        deployment_status: 'INCUBATING',
        timeframe: 'M15',
        symbols: ['EUR/USD', 'GBP/USD'],
        open_positions_count: 1,
        total_orders_count: 3,
        gross_exposure: 21700,
        unrealized_pnl: 145.5,
        realized_pnl: 320.0,
        win_rate: 0.6667,
      },
    ],
    total_active_strategies: 1,
    total_open_positions: 1,
    total_gross_exposure: 21700,
    total_unrealized_pnl: 145.5,
    total_realized_pnl: 320.0,
    currency: 'USD',
    is_paper: true,
    updated_at: new Date().toISOString(),
  };

  it('renders OrdersPage with multi-strategy filter and handles real position sizing', async () => {
    vi.spyOn(strategiesApi, 'listAccountConfigs').mockResolvedValue(mockAccountConfigs);
    vi.spyOn(ordersApi, 'list').mockResolvedValue(mockOrdersResponse);
    vi.spyOn(positionsApi, 'calculateSizing').mockResolvedValue(mockSizingResponse);

    render(
      <MemoryRouter>
        <ToastProvider>
          <OrdersPage />
        </ToastProvider>
      </MemoryRouter>
    );

    // Verify Strategy column is present in the table
    await waitFor(() => {
      expect(screen.getByText('ORDER MANAGEMENT')).toBeInTheDocument();
      expect(screen.getByText('trend_following_v1')).toBeInTheDocument();
    });

    // Open Place Paper Order Modal
    const placeOrderBtn = screen.getByRole('button', { name: /Place Paper Order/i });
    await userEvent.click(placeOrderBtn);

    // Check Executing Strategy selector exists
    expect(screen.getByText(/Executing Strategy \(Optional\)/i)).toBeInTheDocument();

    // Toggle Quantitative Position Sizer
    const sizerToggle = screen.getByRole('button', { name: /Open Calculator/i });
    await userEvent.click(sizerToggle);

    expect(screen.getByText(/Quantitative Position Sizer/i)).toBeInTheDocument();
    expect(screen.getByText(/Calculate Recommended Size/i)).toBeInTheDocument();

    // Click Calculate
    const calcBtn = screen.getByRole('button', { name: /Calculate Recommended Size/i });
    await userEvent.click(calcBtn);

    // Verify calculation results displayed
    await waitFor(() => {
      expect(screen.getByText(/Recommended: 20,000 units/i)).toBeInTheDocument();
      expect(screen.getByText(/REALTIME PRICE/i)).toBeInTheDocument();
    });

    // Apply Sizing to Volume
    const applyBtn = screen.getByRole('button', { name: /Apply 20,000 Units to Volume/i });
    await userEvent.click(applyBtn);

    // Check volume input value updated to 20000
    const volumeInput = screen.getByPlaceholderText('10000') as HTMLInputElement;
    expect(volumeInput.value).toBe('20000');
  });

  it('renders StrategiesPage with multi-strategy deployments and lifecycle statuses', async () => {
    vi.spyOn(strategiesApi, 'list').mockResolvedValue(mockStrategiesCatalogue);
    vi.spyOn(strategiesApi, 'listAccountConfigs').mockResolvedValue(mockAccountConfigs);

    render(
      <MemoryRouter>
        <ToastProvider>
          <StrategiesPage />
        </ToastProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/STRATEGY REGISTRY & CONTROL/i)).toBeInTheDocument();
      expect(screen.getByText(/Active Strategy Deployments \(1\)/i)).toBeInTheDocument();
      expect(screen.getByText('INCUBATING')).toBeInTheDocument();
      expect(screen.getByText('DEPLOYED')).toBeInTheDocument();
    });
  });

  it('renders PortfolioPage with Multi-Strategy Portfolio Allocation table', async () => {
    vi.spyOn(portfolioApi, 'getOverview').mockResolvedValue({
      balance: 100000,
      equity: 100145.5,
      used_margin: 217,
      free_margin: 99928.5,
      margin_level: 461.5,
      unrealized_pnl: 145.5,
      realized_pnl: 320.0,
      net_exposure: 21700,
      gross_exposure: 21700,
      open_positions_count: 1,
      currency: 'USD',
      is_paper: true,
      updated_at: new Date().toISOString(),
    });
    vi.spyOn(portfolioApi, 'getEquityCurve').mockResolvedValue({
      balance: 100000,
      equity: 100145.5,
      peak_equity: 100500,
      current_drawdown: 0.35,
      max_drawdown: 1.2,
      currency: 'USD',
      updated_at: new Date().toISOString(),
    });
    vi.spyOn(portfolioApi, 'getPnL').mockResolvedValue({
      realized_pnl: 320,
      unrealized_pnl: 145.5,
      gross_profit: 450,
      gross_loss: -130,
      commission: 0,
      swap: 0,
      fees: 0,
      net_pnl: 320,
      currency: 'USD',
      updated_at: new Date().toISOString(),
    });
    vi.spyOn(portfolioApi, 'getExposure').mockResolvedValue({
      net_exposure: 21700,
      gross_exposure: 21700,
      long_exposure: 21700,
      short_exposure: 0,
      currency_exposures: [],
      updated_at: new Date().toISOString(),
    });
    vi.spyOn(portfolioApi, 'getStrategyBreakdown').mockResolvedValue(mockStrategyBreakdown);

    render(
      <MemoryRouter>
        <ToastProvider>
          <PortfolioPage />
        </ToastProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('PORTFOLIO ANALYTICS')).toBeInTheDocument();
      expect(
        screen.getByText(/Multi-Strategy Portfolio Allocation & Attribution/i)
      ).toBeInTheDocument();
      expect(screen.getByText('Trend Following Momentum')).toBeInTheDocument();
      expect(screen.getByText('INCUBATING')).toBeInTheDocument();
      expect(screen.getByText(/66.7%/i)).toBeInTheDocument();
    });
  });
});
