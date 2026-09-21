import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { MetricCard } from '../src/components/common/MetricCard';
import { PageHeader } from '../src/components/common/PageHeader';
import { Breadcrumbs } from '../src/components/common/Breadcrumbs';
import { ConfirmationDialog } from '../src/components/common/ConfirmationDialog';
import { Skeleton } from '../src/components/common/Skeleton';
import { Tabs } from '../src/components/common/Tabs';

describe('Design System Components', () => {
  it('renders MetricCard with labels, values, and trends', () => {
    render(
      <MetricCard
        label="Net Exposure"
        value="$50,000.00"
        change="+2.5%"
        changeDirection="up"
        changeLabel="vs 24h ago"
      />
    );

    expect(screen.getByText('Net Exposure')).toBeInTheDocument();
    expect(screen.getByText('$50,000.00')).toBeInTheDocument();
    expect(screen.getByText('+2.5%')).toBeInTheDocument();
    expect(screen.getByText('vs 24h ago')).toBeInTheDocument();
  });

  it('renders PageHeader with persistent paper-trading badge and breadcrumbs', () => {
    render(
      <MemoryRouter>
        <PageHeader
          title="Portfolio Analytics"
          subtitle="Real-time exposure and equity telemetry"
          breadcrumbs={[{ label: 'Portfolio' }]}
        />
      </MemoryRouter>
    );

    expect(screen.getByText('Portfolio Analytics')).toBeInTheDocument();
    expect(screen.getByText('Real-time exposure and equity telemetry')).toBeInTheDocument();
    expect(screen.getByText('PAPER TRADING ONLY')).toBeInTheDocument();
  });

  it('renders Breadcrumbs and supports links', () => {
    render(
      <MemoryRouter>
        <Breadcrumbs items={[{ label: 'Orders', path: '/orders' }, { label: 'New Order' }]} />
      </MemoryRouter>
    );

    expect(screen.getByText('Orders')).toBeInTheDocument();
    expect(screen.getByText('New Order')).toBeInTheDocument();
  });

  it('renders ConfirmationDialog and calls callbacks', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const onClose = vi.fn();

    render(
      <ConfirmationDialog
        isOpen={true}
        onClose={onClose}
        onConfirm={onConfirm}
        title="Cancel Paper Order"
        message="Are you sure you want to cancel order ORD-123?"
        confirmLabel="Yes, Cancel"
      />
    );

    expect(screen.getByText('Cancel Paper Order')).toBeInTheDocument();
    expect(screen.getByText(/SIMULATED PAPER EXECUTION/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /yes, cancel/i }));
    expect(onConfirm).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole('button', { name: /^cancel$/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('renders Skeleton placeholders', () => {
    const { container } = render(<Skeleton width={100} height={20} />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders Tabs and handles tab switching', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(
      <Tabs
        tabs={[
          { id: 'tab1', label: 'Overview' },
          { id: 'tab2', label: 'History' },
        ]}
        activeTab="tab1"
        onChange={onChange}
      />
    );

    expect(screen.getByText('Overview')).toBeInTheDocument();
    const historyTab = screen.getByText('History');
    await user.click(historyTab);
    expect(onChange).toHaveBeenCalledWith('tab2');
  });
});
