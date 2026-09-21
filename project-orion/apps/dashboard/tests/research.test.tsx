import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ResearchLabPage } from '../src/pages/ResearchLabPage';
import { ToastProvider } from '../src/components/common/Toast';
import type {
  StrategyCatalogueItem,
  ExperimentSummary,
  ExperimentDetail,
  ExperimentEquityResponse,
  ExperimentTradesResponse,
  ExperimentComparisonResponse,
} from '../src/api/types';

const mockStrategies: StrategyCatalogueItem[] = [
  {
    strategy_id: 'trend_following',
    name: 'Trend Following',
    description: 'Dual MA trend strategy with momentum confirmation.',
    category: 'trend',
    version: '1.0.0',
    is_deterministic: true,
    supported_instruments: ['EUR/USD', 'GBP/USD'],
    supported_timeframes: ['M15', 'H1'],
    parameters: [
      {
        name: 'fast_period',
        type: 'integer',
        default: 10,
        min: 2,
        max: 100,
        description: 'Fast moving average period',
      },
      {
        name: 'slow_period',
        type: 'integer',
        default: 30,
        min: 5,
        max: 300,
        description: 'Slow moving average period',
      },
    ],
  },
  {
    strategy_id: 'mean_reversion',
    name: 'Mean Reversion',
    description: 'Statistical mean reversion strategy.',
    category: 'reversion',
    version: '1.0.0',
    is_deterministic: true,
    supported_instruments: ['USD/JPY', 'EUR/USD'],
    supported_timeframes: ['H1', 'H4'],
    parameters: [
      {
        name: 'lookback_period',
        type: 'integer',
        default: 20,
        min: 5,
        max: 100,
        description: 'Lookback window',
      },
      {
        name: 'entry_threshold',
        type: 'float',
        default: 2.0,
        min: 0.5,
        max: 5.0,
        description: 'Z-score entry trigger',
      },
    ],
  },
];

const mockExperiments: ExperimentSummary[] = [
  {
    id: 'exp-test-001',
    organization_id: 'org-test',
    strategy_id: 'trend_following',
    strategy_version: '1.0.0',
    symbol: 'EUR/USD',
    timeframe: 'H1',
    start_date: '2025-01-01T00:00:00Z',
    end_date: '2025-01-15T00:00:00Z',
    initial_capital: 10000.0,
    status: 'COMPLETED',
    execution_time_seconds: 0.42,
    created_at: '2025-01-16T12:00:00Z',
    completed_at: '2025-01-16T12:00:01Z',
    metrics: {
      initial_capital: 10000.0,
      final_balance: 10850.0,
      net_profit: 850.0,
      total_return_pct: 8.5,
      gross_profit: 1200.0,
      gross_loss: 350.0,
      profit_factor: 3.42,
      win_rate_pct: 65.0,
      loss_rate_pct: 35.0,
      total_trades: 20,
      winning_trades: 13,
      losing_trades: 7,
      avg_trade_pnl: 42.5,
      largest_win: 150.0,
      largest_loss: 70.0,
      sharpe_ratio: 2.15,
      sortino_ratio: 3.1,
      max_drawdown_pct: 4.8,
      recovery_factor: 1.77,
      expectancy: 42.5,
    },
    warnings: [
      {
        code: 'SMALL_SAMPLE_SIZE',
        title: 'Small Trade Sample Size',
        description: 'Backtest produced only 20 trades. Statistical validity recommends at least 30 trades.',
        severity: 'WARNING',
      },
    ],
  },
  {
    id: 'exp-test-002',
    organization_id: 'org-test',
    strategy_id: 'mean_reversion',
    strategy_version: '1.0.0',
    symbol: 'EUR/USD',
    timeframe: 'H1',
    start_date: '2025-01-01T00:00:00Z',
    end_date: '2025-01-15T00:00:00Z',
    initial_capital: 10000.0,
    status: 'COMPLETED',
    execution_time_seconds: 0.38,
    created_at: '2025-01-16T12:30:00Z',
    completed_at: '2025-01-16T12:30:01Z',
    metrics: {
      initial_capital: 10000.0,
      final_balance: 10420.0,
      net_profit: 420.0,
      total_return_pct: 4.2,
      gross_profit: 800.0,
      gross_loss: 380.0,
      profit_factor: 2.1,
      win_rate_pct: 58.0,
      loss_rate_pct: 42.0,
      total_trades: 25,
      winning_trades: 14,
      losing_trades: 11,
      avg_trade_pnl: 16.8,
      largest_win: 90.0,
      largest_loss: 50.0,
      sharpe_ratio: 1.85,
      sortino_ratio: 2.4,
      max_drawdown_pct: 3.2,
      recovery_factor: 1.31,
      expectancy: 16.8,
    },
    warnings: [],
  },
];

const mockDetail: ExperimentDetail = {
  ...mockExperiments[0],
  parameters: { fast_period: 10, slow_period: 30 },
  simulation_config: { spread_pips: 1.5, initial_capital: 10000.0 },
};

const mockEquity: ExperimentEquityResponse = {
  experiment_id: 'exp-test-001',
  initial_capital: 10000.0,
  points: [
    { timestamp: '2025-01-01T00:00:00Z', balance: 10000.0, equity: 10000.0, drawdown_pct: 0.0 },
    { timestamp: '2025-01-05T00:00:00Z', balance: 10400.0, equity: 10450.0, drawdown_pct: 0.0 },
    { timestamp: '2025-01-10T00:00:00Z', balance: 10300.0, equity: 10250.0, drawdown_pct: 1.9 },
    { timestamp: '2025-01-15T00:00:00Z', balance: 10850.0, equity: 10850.0, drawdown_pct: 0.0 },
  ],
};

const mockTrades: ExperimentTradesResponse = {
  experiment_id: 'exp-test-001',
  total_trades: 2,
  trades: [
    {
      trade_id: 'tr-001',
      symbol: 'EUR/USD',
      side: 'BUY',
      entry_time: '2025-01-02T10:00:00Z',
      exit_time: '2025-01-04T15:00:00Z',
      entry_price: 1.052,
      exit_price: 1.056,
      quantity: 10000.0,
      gross_pnl: 40.0,
      fees: 0.7,
      net_pnl: 39.3,
      duration_seconds: 190800,
      exit_reason: 'SIGNAL_REVERSAL',
    },
    {
      trade_id: 'tr-002',
      symbol: 'EUR/USD',
      side: 'SELL',
      entry_time: '2025-01-06T08:00:00Z',
      exit_time: '2025-01-08T12:00:00Z',
      entry_price: 1.055,
      exit_price: 1.051,
      quantity: 10000.0,
      gross_pnl: 40.0,
      fees: 0.7,
      net_pnl: 39.3,
      duration_seconds: 187200,
      exit_reason: 'TAKE_PROFIT',
    },
  ],
};

const mockComparison: ExperimentComparisonResponse = {
  comparison: [
    {
      experiment_id: 'exp-test-001',
      strategy_id: 'trend_following',
      symbol: 'EUR/USD',
      timeframe: 'H1',
      net_profit: 850.0,
      total_return_pct: 8.5,
      sharpe_ratio: 2.15,
      max_drawdown_pct: 4.8,
      win_rate_pct: 65.0,
      total_trades: 20,
      profit_factor: 3.42,
    },
    {
      experiment_id: 'exp-test-002',
      strategy_id: 'mean_reversion',
      symbol: 'EUR/USD',
      timeframe: 'H1',
      net_profit: 420.0,
      total_return_pct: 4.2,
      sharpe_ratio: 1.85,
      max_drawdown_pct: 3.2,
      win_rate_pct: 58.0,
      total_trades: 25,
      profit_factor: 2.1,
    },
  ],
  normalized_curves: {
    'exp-test-001': [
      { timestamp: '2025-01-01T00:00:00Z', return_pct: 0.0 },
      { timestamp: '2025-01-15T00:00:00Z', return_pct: 8.5 },
    ],
    'exp-test-002': [
      { timestamp: '2025-01-01T00:00:00Z', return_pct: 0.0 },
      { timestamp: '2025-01-15T00:00:00Z', return_pct: 4.2 },
    ],
  },
};

describe('ResearchLabPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();

    global.fetch = vi.fn().mockImplementation((url: string, opts?: any) => {
      const urlStr = url.toString();

      if (urlStr.includes('/research/strategies')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockStrategies),
        });
      }

      if (urlStr.includes('/research/experiments/compare')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockComparison),
        });
      }

      if (urlStr.includes('/equity-curve')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockEquity),
        });
      }

      if (urlStr.includes('/trades')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockTrades),
        });
      }

      if (urlStr.includes('/research/experiments/exp-test-001')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockDetail),
        });
      }

      if (urlStr.includes('/research/experiments') && opts?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          status: 201,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockExperiments[0]),
        });
      }

      if (urlStr.includes('/research/experiments')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockExperiments),
        });
      }

      return Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve({}),
      });
    });
  });

  it('renders Strategy Lab header and strategy parameters in Lab Builder', async () => {
    render(
      <ToastProvider>
        <ResearchLabPage />
      </ToastProvider>
    );

    expect(await screen.findByText(/Institutional Strategy Lab & Research/i)).toBeInTheDocument();
    expect(await screen.findByText(/Strategy & Simulation Parameters/i)).toBeInTheDocument();
    expect(await screen.findByText(/Archetype Specification/i)).toBeInTheDocument();
    expect(await screen.findByText(/Quant Methodological Rules/i)).toBeInTheDocument();
  });

  it('switches to Experiments tab and displays history ledger', async () => {
    const user = userEvent.setup();
    render(
      <ToastProvider>
        <ResearchLabPage />
      </ToastProvider>
    );

    const historyTab = await screen.findByRole('button', { name: /Experiments/i });
    await user.click(historyTab);

    expect(await screen.findByText(/Research Experiment Ledger/i)).toBeInTheDocument();
    expect(await screen.findByText('exp-test-001')).toBeInTheDocument();
    expect(await screen.findByText('exp-test-002')).toBeInTheDocument();
  });

  it('inspects an experiment and displays results, warnings, and trades', async () => {
    const user = userEvent.setup();
    render(
      <ToastProvider>
        <ResearchLabPage />
      </ToastProvider>
    );

    const historyTab = await screen.findByRole('button', { name: /Experiments/i });
    await user.click(historyTab);

    const viewButtons = await screen.findAllByRole('button', { name: /View Results/i });
    await user.click(viewButtons[0]);

    // Check Results tab items
    expect(await screen.findByText(/Simulated Equity Curve/i)).toBeInTheDocument();
    expect(await screen.findByText(/Simulated Trade Execution Ledger/i)).toBeInTheDocument();
    expect(await screen.findByText(/SMALL_SAMPLE_SIZE/i)).toBeInTheDocument();
    expect(await screen.findByText('tr-001')).toBeInTheDocument();
  });
});
