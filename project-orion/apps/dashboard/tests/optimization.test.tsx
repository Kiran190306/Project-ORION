import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { OptimizationStudioPage } from '../src/pages/OptimizationStudioPage';
import { ToastProvider } from '../src/components/common/Toast';
import type {
  StrategyDefaultSpaceResponse,
  OptimizationJobSummary,
  OptimizationJobDetail,
  StrategyCatalogueItem,
} from '../src/api/types';

const mockStrategies: StrategyCatalogueItem[] = [
  {
    strategy_id: 'TrendFollowing',
    name: 'Trend Following',
    description: 'Dual MA trend strategy.',
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
        description: 'Fast MA',
      },
      {
        name: 'slow_period',
        type: 'integer',
        default: 30,
        min: 5,
        max: 300,
        description: 'Slow MA',
      },
    ],
  },
];

const mockDefaultSpace: StrategyDefaultSpaceResponse = {
  strategy_id: 'TrendFollowing',
  ranges: [
    {
      name: 'fast_period',
      param_type: 'int',
      min_value: 5,
      max_value: 30,
      step: 5,
    },
    {
      name: 'slow_period',
      param_type: 'int',
      min_value: 20,
      max_value: 100,
      step: 10,
    },
  ],
  estimated_combinations: 54,
};

const mockJobs: OptimizationJobSummary[] = [
  {
    id: 'opt-job-001',
    organization_id: 'org-test',
    strategy_id: 'TrendFollowing',
    symbol: 'EUR/USD',
    timeframe: 'H1',
    optimization_type: 'GRID_SEARCH',
    fitness_objective: 'SHARPE_RATIO',
    status: 'COMPLETED',
    total_combinations: 50,
    completed_combinations: 50,
    execution_time_seconds: 1.25,
    best_fitness_score: 2.15,
    best_sharpe: 2.15,
    best_return: 0.085,
    created_at: '2025-01-16T12:00:00Z',
    completed_at: '2025-01-16T12:00:01Z',
  },
];

const mockJobDetail: OptimizationJobDetail = {
  id: 'opt-job-001',
  organization_id: 'org-test',
  strategy_id: 'TrendFollowing',
  symbol: 'EUR/USD',
  timeframe: 'H1',
  start_date: '2025-01-01T00:00:00Z',
  end_date: '2025-01-15T00:00:00Z',
  initial_capital: 10000.0,
  optimization_type: 'GRID_SEARCH',
  fitness_objective: 'SHARPE_RATIO',
  parameter_space: {
    ranges: mockDefaultSpace.ranges,
  },
  optimization_config: {},
  status: 'COMPLETED',
  total_combinations: 50,
  completed_combinations: 50,
  execution_time_seconds: 1.25,
  best_parameters: { fast_period: 10, slow_period: 40 },
  best_metrics: {
    sharpe_ratio: 2.15,
    sortino_ratio: 3.1,
    total_return: 0.085,
    max_drawdown: 0.048,
    win_rate: 0.65,
    profit_factor: 3.42,
    total_trades: 20,
    net_pnl: 850.0,
  },
  top_candidates: [
    {
      rank: 1,
      parameters: { fast_period: 10, slow_period: 40 },
      fitness_score: 2.15,
      total_return: 0.085,
      sharpe_ratio: 2.15,
      sortino_ratio: 3.1,
      calmar_ratio: 1.77,
      max_drawdown: 0.048,
      win_rate: 0.65,
      profit_factor: 3.42,
      total_trades: 20,
      net_pnl: 850.0,
    },
    {
      rank: 2,
      parameters: { fast_period: 15, slow_period: 50 },
      fitness_score: 1.85,
      total_return: 0.055,
      sharpe_ratio: 1.85,
      sortino_ratio: 2.4,
      calmar_ratio: 1.45,
      max_drawdown: 0.038,
      win_rate: 0.58,
      profit_factor: 2.55,
      total_trades: 18,
      net_pnl: 550.0,
    },
  ],
  heatmap: {
    param1_name: 'fast_period',
    param2_name: 'slow_period',
    min_fitness: 0.5,
    max_fitness: 2.15,
    points: [
      { param1_value: 10, param2_value: 40, fitness_score: 2.15 },
      { param1_value: 15, param2_value: 50, fitness_score: 1.85 },
    ],
  },
  stability_analysis: {
    optimal_parameters: { fast_period: 10, slow_period: 40 },
    plateau_stability_score: 82.5,
    max_neighbor_drop_pct: 12.0,
    is_cliff: false,
    cliff_details: 'Parameter neighborhood forms a robust plateau.',
    adjacent_evaluations: [],
  },
  regime_breakdowns: [
    {
      regime_name: 'TRENDING_BULL',
      trade_count: 12,
      win_rate: 0.75,
      profit_factor: 4.2,
      total_return: 0.065,
      sharpe_ratio: 2.4,
      drawdown: 0.025,
    },
  ],
  created_at: '2025-01-16T12:00:00Z',
  completed_at: '2025-01-16T12:00:01Z',
};

describe('OptimizationStudioPage', () => {
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

      if (urlStr.includes('/optimization/spaces')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockDefaultSpace),
        });
      }

      if (urlStr.includes('/optimization/jobs') && (!opts || opts.method === 'GET')) {
        if (urlStr.includes('/opt-job-001')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve(mockJobDetail),
          });
        }
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockJobs),
        });
      }

      if (urlStr.includes('/optimization/run') && opts?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          status: 201,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockJobDetail),
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

  it('renders studio header and default parameters correctly', async () => {
    render(
      <ToastProvider>
        <OptimizationStudioPage />
      </ToastProvider>
    );

    expect(screen.getByText('OPTIMIZATION STUDIO')).toBeInTheDocument();
    expect(screen.getByText(/PAPER TRADING/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('fast_period')).toBeInTheDocument();
      expect(screen.getByText('slow_period')).toBeInTheDocument();
    });
  });

  it('allows switching between tabs', async () => {
    const user = userEvent.setup();
    render(
      <ToastProvider>
        <OptimizationStudioPage />
      </ToastProvider>
    );

    const historyTab = screen.getByRole('button', { name: /Job History/i });
    await user.click(historyTab);

    await waitFor(() => {
      expect(screen.getByText('ORGANIZATION OPTIMIZATION RUNS (1)')).toBeInTheDocument();
      expect(screen.getByText('opt-job-001')).toBeInTheDocument();
    });
  });

  it('loads and displays candidate leaderboard upon selecting past job', async () => {
    const user = userEvent.setup();
    render(
      <ToastProvider>
        <OptimizationStudioPage />
      </ToastProvider>
    );

    const historyTab = screen.getByRole('button', { name: /Job History/i });
    await user.click(historyTab);

    await waitFor(() => {
      expect(screen.getByText('View Results')).toBeInTheDocument();
    });

    const viewBtn = screen.getByText('View Results');
    await user.click(viewBtn);

    await waitFor(() => {
      expect(screen.getByText(/RANKED CANDIDATES/i)).toBeInTheDocument();
      expect(screen.getByText('#1')).toBeInTheDocument();
      expect(screen.getByText('#2')).toBeInTheDocument();
    });
  });

  it('launches optimization run and displays leaderboard', async () => {
    const user = userEvent.setup();
    render(
      <ToastProvider>
        <OptimizationStudioPage />
      </ToastProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Launch Optimization Run/i })).toBeInTheDocument();
    });

    const runBtn = screen.getByRole('button', { name: /Launch Optimization Run/i });
    await user.click(runBtn);

    await waitFor(() => {
      expect(screen.getByText(/RANKED CANDIDATES/i)).toBeInTheDocument();
    });
  });
});
