import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PaperSimulationWidget } from '../src/components/paper/PaperSimulationWidget';
import { paperApi } from '../src/api/endpoints';

vi.mock('../src/api/endpoints', () => ({
  paperApi: {
    getConfig: vi.fn(),
    reset: vi.fn(),
    updateConfig: vi.fn(),
  },
}));

vi.mock('../src/components/common/Toast', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
    showToast: vi.fn(),
  }),
}));

describe('PaperSimulationWidget', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockConfig = {
    default_spread_pips: '1.2',
    slippage_bps: '0.8',
    latency_ms: 25.0,
    partial_fill_probability: 0.1,
    deterministic: false,
    fill_probability: 1.0,
  };

  it('renders paper microstructure metrics correctly', async () => {
    vi.mocked(paperApi.getConfig).mockResolvedValue(mockConfig);

    render(<PaperSimulationWidget />);

    expect(await screen.findByText('Institutional Paper Execution Engine')).toBeInTheDocument();
    expect(screen.getByText('DYNAMIC (GAUSSIAN)')).toBeInTheDocument();
    expect(screen.getByText('1.2 pips')).toBeInTheDocument();
    expect(screen.getByText('0.8 bps')).toBeInTheDocument();
    expect(screen.getByText('25 ms')).toBeInTheDocument();
    expect(screen.getByText('10%')).toBeInTheDocument();
    expect(screen.getByText(/Zero Capital Risk/i)).toBeInTheDocument();
  });

  it('opens reset modal and calls reset API with confirmed balance', async () => {
    const user = userEvent.setup();
    vi.mocked(paperApi.getConfig).mockResolvedValue(mockConfig);
    vi.mocked(paperApi.reset).mockResolvedValue({
      account_id: 'acc-test',
      new_balance: 100000.0,
      cancelled_orders_count: 2,
      closed_positions_count: 1,
      message: 'Account reset successful',
      timestamp: new Date().toISOString(),
    });

    const mockOnReset = vi.fn();
    render(<PaperSimulationWidget onResetSuccess={mockOnReset} />);

    // Click Reset Account button
    const resetBtn = await screen.findByRole('button', { name: /Reset Account/i });
    await user.click(resetBtn);

    // Modal opens
    expect(screen.getByText('Reset Paper Trading Account')).toBeInTheDocument();
    expect(screen.getByText(/Warning: Irreversible Paper Account Reset/i)).toBeInTheDocument();

    // Confirm reset
    const confirmBtn = screen.getByRole('button', { name: /Confirm Reset Account/i });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(paperApi.reset).toHaveBeenCalledWith({ initial_balance: 100000 });
      expect(mockOnReset).toHaveBeenCalledTimes(1);
    });
  });

  it('opens config modal and updates simulation parameters', async () => {
    const user = userEvent.setup();
    vi.mocked(paperApi.getConfig).mockResolvedValue(mockConfig);
    vi.mocked(paperApi.updateConfig).mockResolvedValue({
      ...mockConfig,
      default_spread_pips: '2.0',
      deterministic: true,
    });

    render(<PaperSimulationWidget />);

    // Click Config button
    const configBtn = await screen.findByRole('button', { name: /Config/i });
    await user.click(configBtn);

    // Modal opens
    expect(screen.getByText('Configure Paper Microstructure')).toBeInTheDocument();

    // Submit configuration update
    const saveBtn = screen.getByRole('button', { name: /Save Configuration/i });
    await user.click(saveBtn);

    await waitFor(() => {
      expect(paperApi.updateConfig).toHaveBeenCalled();
    });
  });
});
