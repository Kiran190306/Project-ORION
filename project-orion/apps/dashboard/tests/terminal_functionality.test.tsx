import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
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
    getPatterns: vi.fn().mockResolvedValue({ symbol: 'EUR/USD', timeframe: 'H1', provider: 'mock', patterns: [], total_detected: 0 }),
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
    vi.mocked(marketDataApi.getPatterns).mockResolvedValue({
      symbol: 'EUR/USD',
      timeframe: 'H1',
      provider: 'mock',
      patterns: [],
      total_detected: 0,
    });
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

  describe('TerminalMarketChart: Auto-Refresh & Data Freshness Hardening', () => {
    beforeEach(() => {
      vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    });

    afterEach(() => {
      vi.useRealTimers();
      Object.defineProperty(document, 'visibilityState', {
        value: 'visible',
        configurable: true,
      });
    });

    it('periodically refreshes candles at 10-second intervals', async () => {
      vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandlesData);

      render(<TerminalMarketChart symbol="EUR/USD" />);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      // Initial call
      expect(marketDataApi.getCandles).toHaveBeenCalledTimes(1);

      // Advance by 10s
      await act(async () => {
        await vi.advanceTimersByTimeAsync(10000);
      });
      expect(marketDataApi.getCandles).toHaveBeenCalledTimes(2);

      // Advance by another 10s
      await act(async () => {
        await vi.advanceTimersByTimeAsync(10000);
      });
      expect(marketDataApi.getCandles).toHaveBeenCalledTimes(3);
    });

    it('resets timer and fetches new candles when symbol prop changes', async () => {
      vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandlesData);

      const { rerender } = render(<TerminalMarketChart symbol="EUR/USD" />);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(marketDataApi.getCandles).toHaveBeenCalledWith('EUR/USD', expect.objectContaining({ timeframe: 'H1' }));
      expect(marketDataApi.getCandles).toHaveBeenCalledTimes(1);

      // Rerender with GBP/USD
      rerender(<TerminalMarketChart symbol="GBP/USD" />);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(marketDataApi.getCandles).toHaveBeenCalledWith('GBP/USD', expect.objectContaining({ timeframe: 'H1' }));
      expect(marketDataApi.getCandles).toHaveBeenCalledTimes(2);

      // Next tick refreshes the new symbol
      await act(async () => {
        await vi.advanceTimersByTimeAsync(10000);
      });
      expect(marketDataApi.getCandles).toHaveBeenCalledWith('GBP/USD', expect.objectContaining({ timeframe: 'H1' }));
      expect(marketDataApi.getCandles).toHaveBeenCalledTimes(3);
    });

    it('resets timer and fetches new candles when timeframe changes', async () => {
      vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandlesData);

      render(<TerminalMarketChart symbol="EUR/USD" />);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(marketDataApi.getCandles).toHaveBeenCalledWith('EUR/USD', { timeframe: 'H1', limit: 60 });
      expect(marketDataApi.getCandles).toHaveBeenCalledTimes(1);

      // Click M15 timeframe button
      const m15Btn = screen.getByRole('button', { name: 'M15' });
      await act(async () => {
        fireEvent.click(m15Btn);
        await vi.advanceTimersByTimeAsync(0);
      });

      expect(marketDataApi.getCandles).toHaveBeenCalledWith('EUR/USD', { timeframe: 'M15', limit: 60 });
      expect(marketDataApi.getCandles).toHaveBeenCalledTimes(2);

      // Next tick refreshes M15
      await act(async () => {
        await vi.advanceTimersByTimeAsync(10000);
      });
      expect(marketDataApi.getCandles).toHaveBeenCalledWith('EUR/USD', { timeframe: 'M15', limit: 60 });
      expect(marketDataApi.getCandles).toHaveBeenCalledTimes(3);
    });

    it('cleans up interval on component unmount', async () => {
      vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandlesData);

      const { unmount } = render(<TerminalMarketChart symbol="EUR/USD" />);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(marketDataApi.getCandles).toHaveBeenCalledTimes(1);

      unmount();

      // Advancing timer after unmount should NOT trigger any new calls
      await act(async () => {
        await vi.advanceTimersByTimeAsync(30000);
      });
      expect(marketDataApi.getCandles).toHaveBeenCalledTimes(1);
    });

    it('preserves existing candles and does not blank chart when background refresh fails', async () => {
      vi.mocked(marketDataApi.getCandles).mockResolvedValueOnce(mockCandlesData);

      render(<TerminalMarketChart symbol="EUR/USD" />);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(marketDataApi.getCandles).toHaveBeenCalledTimes(1);

      // Verify initial price rendered
      expect(screen.getAllByText('1.08800').length).toBeGreaterThanOrEqual(1);

      // Next periodic refresh fails
      vi.mocked(marketDataApi.getCandles).mockRejectedValueOnce(new Error('Temporary network drop'));
      await act(async () => {
        await vi.advanceTimersByTimeAsync(10000);
      });

      // Verify candles are NOT blanked and no blocking error overlay is displayed
      expect(screen.queryByText('Failed to load market data')).not.toBeInTheDocument();
      expect(screen.getAllByText('1.08800').length).toBeGreaterThanOrEqual(1);
    });

    it('pauses periodic refresh when document is hidden and resumes when visible', async () => {
      vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandlesData);

      render(<TerminalMarketChart symbol="EUR/USD" />);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(marketDataApi.getCandles).toHaveBeenCalledTimes(1);

      // Simulate document becoming hidden
      Object.defineProperty(document, 'visibilityState', {
        value: 'hidden',
        configurable: true,
      });

      // Advance timer while hidden - should skip refresh
      await act(async () => {
        await vi.advanceTimersByTimeAsync(20000);
      });
      expect(marketDataApi.getCandles).toHaveBeenCalledTimes(1);

      // Restore visible state and fire visibilitychange
      Object.defineProperty(document, 'visibilityState', {
        value: 'visible',
        configurable: true,
      });
      await act(async () => {
        document.dispatchEvent(new Event('visibilitychange'));
      });

      // Resumes immediate refresh
      expect(marketDataApi.getCandles).toHaveBeenCalledTimes(2);

      // Regular polling continues while visible
      await act(async () => {
        await vi.advanceTimersByTimeAsync(10000);
      });
      expect(marketDataApi.getCandles).toHaveBeenCalledTimes(3);
    });

    it('prevents duplicate timers and clears interval on symbol change', async () => {
      const setIntervalSpy = vi.spyOn(window, 'setInterval');
      const clearIntervalSpy = vi.spyOn(window, 'clearInterval');
      vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandlesData);

      const { rerender } = render(<TerminalMarketChart symbol="EUR/USD" />);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      expect(setIntervalSpy).toHaveBeenCalledTimes(1);
      expect(clearIntervalSpy).toHaveBeenCalledTimes(0);

      // Change symbol
      rerender(<TerminalMarketChart symbol="USD/JPY" />);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      // Old timer cleared, new timer established
      expect(clearIntervalSpy).toHaveBeenCalledTimes(1);
      expect(setIntervalSpy).toHaveBeenCalledTimes(2);

      setIntervalSpy.mockRestore();
      clearIntervalSpy.mockRestore();
    });

    it('maintains technical indicators and order overlays across periodic refreshes', async () => {
      const mockManyCandles = {
        ...mockCandlesData,
        candles: Array.from({ length: 15 }, (_, i) => ({
          timestamp: `2026-09-26T12:${String(i).padStart(2, '0')}:00Z`,
          open: 1.0850 + i * 0.0001,
          high: 1.0860 + i * 0.0001,
          low: 1.0840 + i * 0.0001,
          close: 1.0855 + i * 0.0001,
          volume: 1000 + i * 100,
        })),
      };
      vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockManyCandles);

      render(<TerminalMarketChart symbol="EUR/USD" />);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      // Indicators present initially
      expect(screen.getByText(/EMA\(20\):/)).toBeInTheDocument();
      expect(screen.getByText(/ATR:/)).toBeInTheDocument();
      expect(screen.getByText(/TP /)).toBeInTheDocument();
      expect(screen.getByText(/SL /)).toBeInTheDocument();

      // Trigger periodic refresh with updated price data
      const updatedCandlesData = {
        ...mockManyCandles,
        candles: [
          ...mockManyCandles.candles,
          {
            timestamp: '2026-09-26T14:00:00Z',
            open: 1.0880,
            high: 1.0910,
            low: 1.0870,
            close: 1.0905,
            volume: 18000,
          },
        ],
      };
      vi.mocked(marketDataApi.getCandles).mockResolvedValue(updatedCandlesData);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(10000);
      });

      // Updated price and indicators remain active
      expect(screen.getAllByText('1.09050').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/EMA\(20\):/)).toBeInTheDocument();
      expect(screen.getByText(/ATR:/)).toBeInTheDocument();
    });
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
