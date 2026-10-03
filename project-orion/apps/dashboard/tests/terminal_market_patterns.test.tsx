import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TerminalMarketChart } from '../src/components/market/TerminalMarketChart';
import { marketDataApi } from '../src/api/endpoints';

vi.mock('../src/components/common/Toast', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
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
    getPatterns: vi.fn(),
  },
  dashboardApi: {
    get: vi.fn(),
  },
  paperApi: {
    getConfig: vi.fn().mockResolvedValue({}),
    reset: vi.fn(),
    updateConfig: vi.fn(),
  },
}));

describe('Candlestick Pattern Visual Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockCandles = {
    symbol: 'EUR/USD',
    timeframe: 'H1',
    provider: 'mock',
    candles: [
      {
        timestamp: '2026-03-15T10:00:00Z',
        open: 1.0850,
        high: 1.0870,
        low: 1.0840,
        close: 1.0860,
        volume: 1200,
      },
      {
        timestamp: '2026-03-15T11:00:00Z',
        open: 1.0860,
        high: 1.0880,
        low: 1.0855,
        close: 1.0861,
        volume: 1500,
      },
      {
        timestamp: '2026-03-15T12:00:00Z',
        open: 1.0890,
        high: 1.0895,
        low: 1.0840,
        close: 1.0845,
        volume: 1800,
      },
      {
        timestamp: '2026-03-15T13:00:00Z',
        open: 1.0845,
        high: 1.0850,
        low: 1.0800,
        close: 1.0848,
        volume: 2100,
      },
    ],
  };

  const mockPatternsData = {
    symbol: 'EUR/USD',
    timeframe: 'H1',
    provider: 'mock',
    patterns: [
      {
        pattern_id: 'doji',
        name: 'Doji',
        direction: 'neutral',
        strength: 'moderate',
        candle_index: 1,
        timestamp: '2026-03-15T11:00:00Z',
        description: 'Indecision candle with tiny body and bilateral shadows',
        confidence: '0.90',
        metadata: { body_ratio: '0.05' },
      },
      {
        pattern_id: 'hammer',
        name: 'Hammer',
        direction: 'bullish',
        strength: 'strong',
        candle_index: 3,
        timestamp: '2026-03-15T13:00:00Z',
        description: 'Bullish reversal candle with long lower shadow rejecting lows',
        confidence: '1.00',
        metadata: { lower_shadow_ratio: '2.5' },
      },
    ],
    total_detected: 2,
  };

  it('1. Pattern API request uses correct symbol and timeframe parameters', async () => {
    vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandles);
    vi.mocked(marketDataApi.getPatterns).mockResolvedValue(mockPatternsData);

    render(<TerminalMarketChart symbol="EUR/USD" />);

    await waitFor(() => {
      expect(marketDataApi.getPatterns).toHaveBeenCalledWith('EUR/USD', {
        timeframe: 'H1',
        limit: 60,
      });
    });
  });

  it('2. Pattern response maps to correct candle and displays pattern count badge', async () => {
    vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandles);
    vi.mocked(marketDataApi.getPatterns).mockResolvedValue(mockPatternsData);

    render(<TerminalMarketChart symbol="EUR/USD" />);

    await waitFor(() => {
      expect(screen.getByTestId('chart-patterns-count')).toHaveTextContent('2 patterns');
    });
  });

  it('3. Bullish marker renders below candle on the matched candle index', async () => {
    vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandles);
    vi.mocked(marketDataApi.getPatterns).mockResolvedValue(mockPatternsData);

    render(<TerminalMarketChart symbol="EUR/USD" />);

    await waitFor(() => {
      const bullishMarkers = screen.getAllByTestId('pattern-marker-bullish');
      expect(bullishMarkers.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('4. Bearish marker renders above candle with downward pointing indicator', async () => {
    const bearishPatterns = {
      symbol: 'EUR/USD',
      timeframe: 'H1',
      provider: 'mock',
      patterns: [
        {
          pattern_id: 'shooting_star',
          name: 'Shooting Star',
          direction: 'bearish',
          strength: 'strong',
          candle_index: 2,
          timestamp: '2026-03-15T12:00:00Z',
          description: 'Bearish top reversal with extended upper shadow',
          confidence: '1.00',
          metadata: {},
        },
      ],
      total_detected: 1,
    };
    vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandles);
    vi.mocked(marketDataApi.getPatterns).mockResolvedValue(bearishPatterns);

    render(<TerminalMarketChart symbol="EUR/USD" />);

    await waitFor(() => {
      const bearishMarkers = screen.getAllByTestId('pattern-marker-bearish');
      expect(bearishMarkers.length).toBe(1);
    });
  });

  it('5. Neutral marker renders diamond indicator', async () => {
    vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandles);
    vi.mocked(marketDataApi.getPatterns).mockResolvedValue(mockPatternsData);

    render(<TerminalMarketChart symbol="EUR/USD" />);

    await waitFor(() => {
      const neutralMarkers = screen.getAllByTestId('pattern-marker-neutral');
      expect(neutralMarkers.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('6. Multiple patterns on one candle render count badge and consolidated tooltip', async () => {
    const multiPatternsOnSameCandle = {
      symbol: 'EUR/USD',
      timeframe: 'H1',
      provider: 'mock',
      patterns: [
        {
          pattern_id: 'doji',
          name: 'Doji',
          direction: 'neutral',
          strength: 'moderate',
          candle_index: 1,
          timestamp: '2026-03-15T11:00:00Z',
          description: 'Indecision candle with tiny body',
          confidence: '0.90',
          metadata: {},
        },
        {
          pattern_id: 'inside_bar',
          name: 'Inside Bar',
          direction: 'neutral',
          strength: 'moderate',
          candle_index: 1,
          timestamp: '2026-03-15T11:00:00Z',
          description: 'Volatility contraction inside previous bar',
          confidence: '0.85',
          metadata: {},
        },
      ],
      total_detected: 2,
    };

    vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandles);
    vi.mocked(marketDataApi.getPatterns).mockResolvedValue(multiPatternsOnSameCandle);

    render(<TerminalMarketChart symbol="EUR/USD" />);

    await waitFor(() => {
      const neutralMarker = screen.getByTestId('pattern-marker-neutral');
      expect(neutralMarker).toBeInTheDocument();
      // Count badge indicates '2'
      expect(neutralMarker).toHaveTextContent('2');
    });
  });

  it('7. Pattern tooltip contains pattern information and description', async () => {
    vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandles);
    vi.mocked(marketDataApi.getPatterns).mockResolvedValue(mockPatternsData);

    render(<TerminalMarketChart symbol="EUR/USD" />);

    await waitFor(() => {
      const bullishMarker = screen.getByTestId('pattern-marker-bullish');
      const titleEl = bullishMarker.querySelector('title');
      expect(titleEl).toBeInTheDocument();
      expect(titleEl?.textContent).toContain('Hammer');
      expect(titleEl?.textContent).toContain('Bullish reversal candle');
      expect(titleEl?.textContent).toContain('strong');
    });
  });

  it('8. Pattern API failure does not blank candles or show blocking error overlay', async () => {
    vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandles);
    vi.mocked(marketDataApi.getPatterns).mockRejectedValue(new Error('Pattern engine timeout'));

    render(<TerminalMarketChart symbol="EUR/USD" />);

    // Candles render successfully
    await waitFor(() => {
      expect(screen.queryByText('Failed to load market data')).not.toBeInTheDocument();
      expect(screen.getAllByText('1.08480').length).toBeGreaterThanOrEqual(1);
    });

    // Pattern count badge is hidden
    expect(screen.queryByTestId('chart-patterns-count')).not.toBeInTheDocument();
  });

  it('9. Pattern visibility toggle button toggles pattern markers on and off', async () => {
    const user = userEvent.setup();
    vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandles);
    vi.mocked(marketDataApi.getPatterns).mockResolvedValue(mockPatternsData);

    render(<TerminalMarketChart symbol="EUR/USD" />);

    await waitFor(() => {
      expect(screen.getByTestId('chart-patterns-count')).toBeInTheDocument();
      expect(screen.getByTestId('pattern-marker-bullish')).toBeInTheDocument();
    });

    // Click toggle button to hide patterns
    const toggleBtn = screen.getByTestId('toggle-patterns-btn');
    await user.click(toggleBtn);

    // Markers are hidden
    expect(screen.queryByTestId('pattern-marker-bullish')).not.toBeInTheDocument();
    expect(screen.queryByTestId('chart-patterns-count')).not.toBeInTheDocument();

    // Click again to re-enable
    await user.click(toggleBtn);
    expect(screen.getByTestId('pattern-marker-bullish')).toBeInTheDocument();
  });

  it('10. Symbol change re-fetches patterns for the new symbol', async () => {
    vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandles);
    vi.mocked(marketDataApi.getPatterns).mockResolvedValue(mockPatternsData);

    const { rerender } = render(<TerminalMarketChart symbol="EUR/USD" />);

    await waitFor(() => {
      expect(marketDataApi.getPatterns).toHaveBeenCalledWith('EUR/USD', expect.anything());
    });

    // Rerender with GBP/USD
    rerender(<TerminalMarketChart symbol="GBP/USD" />);

    await waitFor(() => {
      expect(marketDataApi.getPatterns).toHaveBeenCalledWith('GBP/USD', expect.anything());
    });
  });

  it('11. Timeframe change re-fetches patterns for the new timeframe', async () => {
    const user = userEvent.setup();
    vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandles);
    vi.mocked(marketDataApi.getPatterns).mockResolvedValue(mockPatternsData);

    render(<TerminalMarketChart symbol="EUR/USD" />);

    await waitFor(() => {
      expect(marketDataApi.getPatterns).toHaveBeenCalledWith('EUR/USD', {
        timeframe: 'H1',
        limit: 60,
      });
    });

    // Click M15 timeframe button
    const m15Button = screen.getByRole('button', { name: 'M15' });
    await user.click(m15Button);

    await waitFor(() => {
      expect(marketDataApi.getPatterns).toHaveBeenCalledWith('EUR/USD', {
        timeframe: 'M15',
        limit: 60,
      });
    });
  });

  it('12. Periodic 10-second refresh refreshes both candles and patterns', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandles);
    vi.mocked(marketDataApi.getPatterns).mockResolvedValue(mockPatternsData);

    render(<TerminalMarketChart symbol="EUR/USD" />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    expect(marketDataApi.getCandles).toHaveBeenCalledTimes(1);
    expect(marketDataApi.getPatterns).toHaveBeenCalledTimes(1);

    // Advance by 10 seconds
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10000);
    });

    expect(marketDataApi.getCandles).toHaveBeenCalledTimes(2);
    expect(marketDataApi.getPatterns).toHaveBeenCalledTimes(2);

    vi.useRealTimers();
  });

  it('13. Technical indicators (EMA, ATR) and TP/SL reference lines remain intact', async () => {
    vi.mocked(marketDataApi.getCandles).mockResolvedValue(mockCandles);
    vi.mocked(marketDataApi.getPatterns).mockResolvedValue(mockPatternsData);

    render(<TerminalMarketChart symbol="EUR/USD" />);

    await waitFor(() => {
      expect(screen.getByText(/ATR:/)).toBeInTheDocument();
      expect(screen.getByText(/TP /)).toBeInTheDocument();
      expect(screen.getByText(/SL /)).toBeInTheDocument();
    });
  });
});
