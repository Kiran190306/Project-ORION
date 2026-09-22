import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { BillingPage } from '../src/pages/BillingPage';
import { billingApi } from '../src/api/endpoints';
import type { BillingOverviewResponse } from '../src/api/types';

vi.mock('../src/api/endpoints', () => ({
  billingApi: {
    getOverview: vi.fn(),
    createCheckout: vi.fn(),
    cancelSubscription: vi.fn(),
    listInvoices: vi.fn(),
  },
}));

const mockOverview: BillingOverviewResponse = {
  customer: {
    id: 'bcust_123',
    organization_id: 'org_test_1',
    provider_customer_id: 'cus_test_123',
    email: 'trader@orion.internal',
    name: 'Institutional Trader',
  },
  subscription: {
    id: 'bsub_123',
    organization_id: 'org_test_1',
    provider_subscription_id: 'sub_test_123',
    plan_code: 'PRO',
    status: 'active',
    current_period_start: new Date().toISOString(),
    current_period_end: new Date(Date.now() + 30 * 86400000).toISOString(),
    cancel_at_period_end: false,
  },
  recent_invoices: [
    {
      id: 'binv_123',
      provider_invoice_id: 'in_test_123',
      amount_due: 99.0,
      amount_paid: 99.0,
      currency: 'usd',
      status: 'paid',
      hosted_invoice_url: 'https://stripe.com/invoice/test',
      invoice_pdf: 'https://stripe.com/invoice/test.pdf',
      created_at: new Date().toISOString(),
    },
  ],
};

describe('BillingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(billingApi.getOverview).mockResolvedValue(mockOverview);
  });

  it('renders active plan tier, billing cycle, and strict paper-trading warning', async () => {
    render(
      <MemoryRouter>
        <BillingPage />
      </MemoryRouter>
    );

    expect(await screen.findByText('COMMERCIAL BILLING & PLANS')).toBeDefined();
    expect(await screen.findByText('PRO')).toBeDefined();
    expect(screen.getByText('ACTIVE')).toBeDefined();
    expect(screen.getByText(/Stripe Test Mode Only — Strict Paper-Trading Invariant/i)).toBeDefined();
    expect(screen.getByText('Free Sandbox')).toBeDefined();
    expect(screen.getByText('Pro Trader')).toBeDefined();
    expect(screen.getByText('Business Prop Desk')).toBeDefined();
    expect(screen.getByText('Enterprise Institutional')).toBeDefined();
    expect(screen.getByText(/Long-term system audit log retention \(subject to data agreement\)/i)).toBeDefined();

    // Verify Commercial Terms & Billing Notice
    expect(screen.getByText('COMMERCIAL TERMS & BILLING NOTICE')).toBeDefined();
    const refundLink = screen.getByRole('link', { name: /Refund & Cancellation Policy/i });
    expect(refundLink.getAttribute('href')).toBe('/refund-policy');
  });

  it('displays invoice history table with formatted values and receipt link', async () => {
    render(
      <MemoryRouter>
        <BillingPage />
      </MemoryRouter>
    );

    expect(await screen.findByText('in_test_123')).toBeDefined();
    expect(screen.getByText('PAID')).toBeDefined();
    expect(screen.getByText('$99.00')).toBeDefined();
    const receiptLink = screen.getByRole('link', { name: /View/i });
    expect(receiptLink.getAttribute('href')).toBe('https://stripe.com/invoice/test');
  });

  it('triggers server-side checkout session creation on upgrade click', async () => {
    vi.mocked(billingApi.createCheckout).mockResolvedValue({
      session_id: 'cs_test_abc123',
      url: 'https://checkout.stripe.com/c/pay/cs_test_abc123',
      plan_code: 'BUSINESS',
      customer_id: 'cus_test_123',
    });

    render(
      <MemoryRouter>
        <BillingPage />
      </MemoryRouter>
    );

    const upgradeButton = await screen.findByRole('button', { name: /Upgrade to Business Prop Desk/i });
    fireEvent.click(upgradeButton);

    await waitFor(() => {
      expect(billingApi.createCheckout).toHaveBeenCalledWith('BUSINESS');
    });
  });
});
