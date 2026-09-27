import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { TerminalMarketChart } from '../src/components/market/TerminalMarketChart';
import { TerminalWatchlist } from '../src/components/market/TerminalWatchlist';
import { OrionIntelligencePanel } from '../src/components/market/OrionIntelligencePanel';
import { DashboardPage } from '../src/pages/DashboardPage';
import { ordersApi, marketDataApi, dashboardApi } from '../src/api/endpoints';

const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();

vi.mock('../src/components/common/Toast', () => ({
  useToast: () => ({
    success: mockToastSuccess,
    error: mockToastError,
    warning: vi.fn(),
    info: vi.fn(),
    showToast: vi.fn(),
  }),
}));

vi.mock('../src/api/endpoints', () => ({
  ordersApi: {
    create: vi.fn(),
    cancel: vi.fn(),
    list: vi.fn(),
    getById: vi.fn(),
  },
  marketDataApi: {
    getCandles: vi.fn(),
    getQuote: vi.fn(),
    getHealth: vi.fn(),
    listInstruments: vi.fn(),
  },
  dashboardApi: {
    get: vi.fn(),
  },
  paperApi: {
    getConfig: vi.fn().mockResolvedValue({
      default_spread_pips: '1.2',
      slippage_bps: '0.8',
      latency_ms: 25.0,
      partial_fill_probability: 0.1,
      deterministic: false,
      fill_probability: 1.0,
    }),
    reset: vi.fn(),
    updateConfig: vi.fn(),
  },
}));

describe('Phase 1 Real Terminal Functionality', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockCandlesData = {
    symbol: 'EUR/USD',
    timeframe: 'H1',
    provider: 'market_data_engine',
    candles: [
      {
        timestamp: '2026-09-26T12:00:00Z',
        open: 1.0850,
        high: 1.0875,
        low: 1.0840,
        close: 1.0865,
        volume: 12500,
      },
      {
        timestamp: '2026-09-26T13:00:00Z',
        open: 1.0865,
        high: 1.0890,
        low: 1.0860,
        close: 1.0880,
        volume: 15400,
      },
    ],
  };

  const mockQuoteEur = {
    symbol: 'EUR/USD',
    bid: '1.08500',
    ask: '1.08520',
    mid: '1.08510',
    spread: '0.00020',
    spread_pips: '2.0',
    timestamp: new Date().toISOString(),
    provider: 'paper_stream',
    is_stale: false,
    quality: 'EXCELLENT',
  };

  it('TerminalMarketChart: fetches real candles via marketDataApi.getCandles on mount', async () => {
    vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandlesData);

    render(<TerminalMarketChart symbol="EUR/USD" />);

    await waitFor(() => {
      expect(marketDataApi.getCandles).toHaveBeenCalledWith('EUR/USD', {
        timeframe: 'H1',
        limit: 60,
      });
    });

    // Check rendered current price from the latest candle (1.0880)
    const priceElements = await screen.findAllByText('1.08800');
    expect(priceElements.length).toBeGreaterThanOrEqual(1);
  });

  it('TerminalMarketChart: executes real BUY paper order via ordersApi.create', async () => {
    const user = userEvent.setup();
    vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandlesData);
    vi.mocked(ordersApi.create).mockResolvedValue({
      id: 'ord-test-1234',
      account_id: 'acc-paper-1',
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
    });

    const onPlaceOrderMock = vi.fn();
    render(<TerminalMarketChart symbol="EUR/USD" onPlaceOrder={onPlaceOrderMock} />);

    // Wait for candles to load
    await screen.findAllByText('1.08800');

    // Click BUY button
    const buyButton = screen.getByRole('button', { name: /BUY/i });
    await user.click(buyButton);

    await waitFor(() => {
      expect(ordersApi.create).toHaveBeenCalledWith({
        symbol: 'EUR/USD',
        side: 'BUY',
        order_type: 'MARKET',
        quantity: 10000, // 0.1 lot * 100,000 units
      });
      expect(mockToastSuccess).toHaveBeenCalledWith(
        expect.stringContaining('[PAPER] Order Submitted: EUR/USD BUY (FILLED)')
      );
      expect(onPlaceOrderMock).toHaveBeenCalledWith('BUY', 10000);
    });
  });

  it('TerminalMarketChart: executes real SELL paper order via ordersApi.create', async () => {
    const user = userEvent.setup();
    vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandlesData);
    vi.mocked(ordersApi.create).mockResolvedValue({
      id: 'ord-test-sell',
      account_id: 'acc-paper-1',
      symbol: 'EUR/USD',
      side: 'SELL',
      order_type: 'MARKET',
      quantity: 10000,
      price: null,
      status: 'SUBMITTED',
      filled_quantity: 0,
      is_paper: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    render(<TerminalMarketChart symbol="EUR/USD" />);
    await screen.findAllByText('1.08800');

    const sellButton = screen.getByRole('button', { name: /SELL/i });
    await user.click(sellButton);

    await waitFor(() => {
      expect(ordersApi.create).toHaveBeenCalledWith({
        symbol: 'EUR/USD',
        side: 'SELL',
        order_type: 'MARKET',
        quantity: 10000,
      });
      expect(mockToastSuccess).toHaveBeenCalledWith(
        expect.stringContaining('[PAPER] Order Submitted: EUR/USD SELL (SUBMITTED)')
      );
    });
  });

  it('TerminalMarketChart: shows error state and retry on candle API failure', async () => {
    const user = userEvent.setup();
    vi.mocked(marketDataApi.getCandles).mockRejectedValueOnce(new Error('Network gateway timeout'));

    render(<TerminalMarketChart symbol="EUR/USD" />);

    expect(await screen.findByText('Failed to load market data')).toBeInTheDocument();
    expect(screen.getByText('Network gateway timeout')).toBeInTheDocument();

    // Test retry
    vi.mocked(marketDataApi.getCandles).mockResolvedValueOnce(mockCandlesData);
    const retryBtn = screen.getByRole('button', { name: /Retry/i });
    await user.click(retryBtn);

    const priceElementsAfterRetry = await screen.findAllByText('1.08800');
    expect(priceElementsAfterRetry.length).toBeGreaterThanOrEqual(1);
  });

  it('TerminalWatchlist: polls real market data quotes and renders live spreads', async () => {
    vi.mocked(marketDataApi.getQuote).mockImplementation((symbol: string) => {
      if (symbol === 'EUR/USD') {
        return Promise.resolve(mockQuoteEur);
      }
      return Promise.resolve({
        symbol,
        bid: '1.27100',
        ask: '1.27130',
        mid: '1.27115',
        spread: '0.00030',
        spread_pips: '3.0',
        timestamp: new Date().toISOString(),
        provider: 'paper_stream',
        is_stale: false,
        quality: 'EXCELLENT',
      });
    });

    const onSelectMock = vi.fn();
    render(<TerminalWatchlist selectedSymbol="EUR/USD" onSelectSymbol={onSelectMock} />);

    expect(screen.getByText('FX Watchlist')).toBeInTheDocument();

    await waitFor(() => {
      expect(marketDataApi.getQuote).toHaveBeenCalledWith('EUR/USD');
    });

    expect(await screen.findByText('1.08500')).toBeInTheDocument();
    expect(screen.getByText('2.0p')).toBeInTheDocument();
  });

  it('OrionIntelligencePanel: renders truthful unbacked metrics and honest telemetry state', () => {
    render(<OrionIntelligencePanel selectedSymbol="EUR/USD" />);

    expect(screen.getByText('ORION Intelligence')).toBeInTheDocument();
    expect(screen.getByText('TELEMETRY IDLE')).toBeInTheDocument();
    expect(screen.getByText('Awaiting Analysis')).toBeInTheDocument();
    expect(screen.getByText('No Active Signal')).toBeInTheDocument();
    expect(screen.getByText('N/A (No active signal)')).toBeInTheDocument();
    expect(screen.getByText('Standard Lot Model')).toBeInTheDocument();
    expect(screen.getByText('Risk-Adjusted Sizing: Not Configured')).toBeInTheDocument();
    expect(screen.getByText('UNVALIDATED')).toBeInTheDocument();
    expect(screen.getAllByText('N/A').length).toBeGreaterThanOrEqual(3);
  });

  it('DashboardPage: renders truthful N/A indicators for Sharpe and Win Rate', async () => {
    vi.mocked(dashboardApi.get).mockResolvedValue({
      account: {
        balance: '100000.00',
        equity: '100000.00',
        available_cash: '100000.00',
        used_margin: '0.00',
        free_margin: '100000.00',
        currency: 'USD',
        is_paper: true,
      },
      performance: {
        realized_pnl: '0.00',
        unrealized_pnl: '0.00',
        daily_pnl: '0.00',
        drawdown_pct: 0,
      },
      trading: {
        open_positions: [],
        recent_trades: [],
        pending_orders: [],
      },
      strategy: {
        active_strategy: 'trend_following',
        timeframe: 'M15',
        symbols: ['EUR/USD'],
      },
      risk: {
        status: 'healthy',
        total_exposure: '0.00',
        margin_level: 0,
        emergency_stop_active: false,
        recovery_mode_active: false,
      },
      worker: {
        enabled: true,
        state: 'RUNNING',
        is_running: true,
        last_cycle_at: new Date().toISOString(),
        uptime_seconds: 120,
        last_error: null,
      },
      system: {
        status: 'ONLINE',
        market_data_status: 'CONNECTED',
        timestamp: new Date().toISOString(),
      },
    });
    vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandlesData);
    vi.mocked(marketDataApi.getQuote).mockResolvedValue(mockQuoteEur);

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(await screen.findByText('TRADING DASHBOARD')).toBeInTheDocument();
    expect(screen.getByText('History: < 30 trades')).toBeInTheDocument();
    expect(screen.getByText('PF: N/A')).toBeInTheDocument();
  });
});
