import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { RegisterPage } from '../src/pages/RegisterPage';
import { LoginPage } from '../src/pages/LoginPage';
import { AppRoutes } from '../src/App';
import { AuthProvider } from '../src/auth/AuthContext';
import { OrganizationProvider } from '../src/auth/OrganizationContext';

describe('EPIC-027 Phase 4B: Self-Service Registration & Onboarding Funnel', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    sessionStorage.clear();
  });

  describe('RegisterPage Rendering & Structure', () => {
    it('renders the registration header, badges, and all form inputs', () => {
      render(
        <MemoryRouter>
          <RegisterPage />
        </MemoryRouter>
      );

      expect(screen.getByRole('heading', { level: 1, name: /project orion/i })).toBeInTheDocument();
      expect(screen.getByText(/self-service registration & onboarding/i)).toBeInTheDocument();
      expect(screen.getByText(/simulated execution • \$0\.00 capital at risk/i)).toBeInTheDocument();

      // Form labels and inputs
      expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/corporate email/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/organization name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/org slug/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^password/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();

      // Mandatory legal consents
      expect(screen.getByRole('checkbox', { name: /terms of service/i })).toBeInTheDocument();
      expect(screen.getByRole('checkbox', { name: /privacy policy/i })).toBeInTheDocument();
      expect(screen.getByRole('checkbox', { name: /strictly as a simulated paper trading environment/i })).toBeInTheDocument();

      // Submit and navigation buttons
      expect(screen.getByRole('button', { name: /create paper trading account/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /already have an account\? sign in/i })).toHaveAttribute('href', '/login');
    });

    it('renders external links to all mandatory legal disclosure pages with target=_blank', () => {
      render(
        <MemoryRouter>
          <RegisterPage />
        </MemoryRouter>
      );

      const termsLinks = screen.getAllByRole('link', { name: /terms of service/i });
      expect(termsLinks[0]).toHaveAttribute('href', '/terms');
      expect(termsLinks[0]).toHaveAttribute('target', '_blank');
      expect(termsLinks[0]).toHaveAttribute('rel', 'noopener noreferrer');

      const privacyLinks = screen.getAllByRole('link', { name: /privacy policy/i });
      expect(privacyLinks[0]).toHaveAttribute('href', '/privacy');
      expect(privacyLinks[0]).toHaveAttribute('target', '_blank');
      expect(privacyLinks[0]).toHaveAttribute('rel', 'noopener noreferrer');

      const riskLinks = screen.getAllByRole('link', { name: /risk disclosure/i });
      expect(riskLinks[0]).toHaveAttribute('href', '/risk-disclosure');
      expect(riskLinks[0]).toHaveAttribute('target', '_blank');
      expect(riskLinks[0]).toHaveAttribute('rel', 'noopener noreferrer');
    });
  });

  describe('Client-Side Validation & Live Password Policy', () => {
    it('validates minimum username length', async () => {
      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <RegisterPage />
        </MemoryRouter>
      );

      await user.type(screen.getByLabelText(/username/i), 'ab');
      await user.click(screen.getByRole('button', { name: /create paper trading account/i }));

      expect(await screen.findByText(/username must be at least 3 characters/i)).toBeInTheDocument();
    });

    it('validates corporate email format', async () => {
      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <RegisterPage />
        </MemoryRouter>
      );

      await user.type(screen.getByLabelText(/username/i), 'trader_test');
      await user.type(screen.getByLabelText(/corporate email/i), 'invalid-email-address');
      await user.click(screen.getByRole('button', { name: /create paper trading account/i }));

      expect(await screen.findByText(/a valid corporate email address is required/i)).toBeInTheDocument();
    });

    it('validates organization name length', async () => {
      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <RegisterPage />
        </MemoryRouter>
      );

      await user.type(screen.getByLabelText(/username/i), 'trader_test');
      await user.type(screen.getByLabelText(/corporate email/i), 'trader@hedgefund.com');
      await user.type(screen.getByLabelText(/organization name/i), 'A');
      await user.click(screen.getByRole('button', { name: /create paper trading account/i }));

      expect(await screen.findByText(/organization name must be at least 2 characters/i)).toBeInTheDocument();
    });

    it('shows live password checklist and validates password strength', async () => {
      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <RegisterPage />
        </MemoryRouter>
      );

      const passwordInput = screen.getByLabelText(/^password/i);
      await user.type(passwordInput, 'weak');

      // Live checklist appears
      expect(screen.getByText(/password policy requirements:/i)).toBeInTheDocument();
      expect(screen.getByText(/between 8 and 72 bytes/i)).toBeInTheDocument();
      expect(screen.getByText(/at least one letter \(a-z, a-z\)/i)).toBeInTheDocument();
      expect(screen.getByText(/at least one number or symbol/i)).toBeInTheDocument();

      // Form submission blocked
      await user.type(screen.getByLabelText(/username/i), 'trader_test');
      await user.type(screen.getByLabelText(/corporate email/i), 'trader@hedgefund.com');
      await user.type(screen.getByLabelText(/organization name/i), 'Alpha Capital');
      await user.click(screen.getByRole('button', { name: /create paper trading account/i }));

      expect(await screen.findByText(/password does not satisfy the security policy requirements/i)).toBeInTheDocument();
    });

    it('enforces password confirmation match', async () => {
      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <RegisterPage />
        </MemoryRouter>
      );

      await user.type(screen.getByLabelText(/username/i), 'trader_test');
      await user.type(screen.getByLabelText(/corporate email/i), 'trader@hedgefund.com');
      await user.type(screen.getByLabelText(/organization name/i), 'Alpha Capital');
      await user.type(screen.getByLabelText(/^password/i), 'ValidPass123!');
      await user.type(screen.getByLabelText(/confirm password/i), 'Mismatch123!');

      await user.click(screen.getByRole('button', { name: /create paper trading account/i }));

      expect(await screen.findByText(/passwords do not match/i)).toBeInTheDocument();
    });

    it('enforces mandatory legal consent checkboxes', async () => {
      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <RegisterPage />
        </MemoryRouter>
      );

      await user.type(screen.getByLabelText(/username/i), 'trader_test');
      await user.type(screen.getByLabelText(/corporate email/i), 'trader@hedgefund.com');
      await user.type(screen.getByLabelText(/organization name/i), 'Alpha Capital');
      await user.type(screen.getByLabelText(/^password/i), 'ValidPass123!');
      await user.type(screen.getByLabelText(/confirm password/i), 'ValidPass123!');

      // Case 1: No checkboxes checked
      await user.click(screen.getByRole('button', { name: /create paper trading account/i }));
      expect(await screen.findByText(/you must accept the terms of service to create an account/i)).toBeInTheDocument();

      // Case 2: Only terms checked
      await user.click(screen.getByRole('checkbox', { name: /terms of service/i }));
      await user.click(screen.getByRole('button', { name: /create paper trading account/i }));
      expect(await screen.findByText(/you must acknowledge the privacy policy to create an account/i)).toBeInTheDocument();

      // Case 3: Terms + Privacy checked, Risk Disclosure unchecked
      await user.click(screen.getByRole('checkbox', { name: /privacy policy/i }));
      await user.click(screen.getByRole('button', { name: /create paper trading account/i }));
      expect(await screen.findByText(/you must acknowledge the paper trading risk disclosure to create an account/i)).toBeInTheDocument();
    });
  });

  describe('Successful Registration & Provisioning State', () => {
    it('calls POST /api/v1/onboarding/register and transitions to the provisioning notice view', async () => {
      const user = userEvent.setup();

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 201,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () =>
          Promise.resolve({
            user_id: 'usr_1234567890abcdef',
            username: 'quant_trader',
            email: 'quant@alphacapital.com',
            organization_id: 'org_1234567890abcdef',
            organization_name: 'Alpha Capital LLC',
            organization_slug: 'alpha-capital',
            role: 'owner',
            subscription_tier: 'FREE',
            account_id: 'acc_1234567890abcdef',
            account_number: 'ORION-PAP-889900',
            initial_balance: 100000.0,
            access_token: 'fake-jwt-token',
            token_type: 'bearer',
            created_at: '2026-09-22T12:00:00Z',
          }),
      });

      render(
        <MemoryRouter>
          <RegisterPage />
        </MemoryRouter>
      );

      await user.type(screen.getByLabelText(/username/i), 'quant_trader');
      await user.type(screen.getByLabelText(/corporate email/i), 'quant@alphacapital.com');
      await user.type(screen.getByLabelText(/organization name/i), 'Alpha Capital LLC');
      await user.type(screen.getByLabelText(/^password/i), 'QuantPass123!');
      await user.type(screen.getByLabelText(/confirm password/i), 'QuantPass123!');

      await user.click(screen.getByRole('checkbox', { name: /terms of service/i }));
      await user.click(screen.getByRole('checkbox', { name: /privacy policy/i }));
      await user.click(screen.getByRole('checkbox', { name: /strictly as a simulated paper trading environment/i }));

      await user.click(screen.getByRole('button', { name: /create paper trading account/i }));

      // Expect fetch to be called with correct endpoint and payload
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/onboarding/register'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            username: 'quant_trader',
            email: 'quant@alphacapital.com',
            organization_name: 'Alpha Capital LLC',
            password: 'QuantPass123!',
            terms_accepted: true,
            privacy_acknowledged: true,
            risk_disclosure_acknowledged: true,
          }),
        })
      );

      // Verify Success View
      expect(await screen.findByRole('heading', { level: 2, name: /organization & account provisioned/i })).toBeInTheDocument();
      expect(screen.getByText(/paper trading account initialized/i)).toBeInTheDocument();
      expect(screen.getByText('ORION-PAP-889900')).toBeInTheDocument();
      expect(screen.getByText('$100,000 USD')).toBeInTheDocument();
      expect(screen.getByText('Alpha Capital LLC')).toBeInTheDocument();
      expect(screen.getByText('FREE')).toBeInTheDocument();

      // Verify email notice
      expect(screen.getByText(/verification email dispatched/i)).toBeInTheDocument();
      expect(screen.getByText('quant@alphacapital.com')).toBeInTheDocument();

      // Verify buttons
      expect(screen.getByRole('button', { name: /proceed to sign in/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /need to enter a verification token\?/i })).toHaveAttribute('href', '/verify-email');
    });
  });

  describe('Error Handling (409 Conflict, 422 Validation, 429 Rate Limit)', () => {
    it('displays 409 conflict message when username or email is already registered', async () => {
      const user = userEvent.setup();

      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 409,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () =>
          Promise.resolve({
            detail: "Username 'trader_existing' is already registered.",
          }),
      });

      render(
        <MemoryRouter>
          <RegisterPage />
        </MemoryRouter>
      );

      await user.type(screen.getByLabelText(/username/i), 'trader_existing');
      await user.type(screen.getByLabelText(/corporate email/i), 'trader@hedgefund.com');
      await user.type(screen.getByLabelText(/organization name/i), 'Alpha Capital');
      await user.type(screen.getByLabelText(/^password/i), 'ValidPass123!');
      await user.type(screen.getByLabelText(/confirm password/i), 'ValidPass123!');

      await user.click(screen.getByRole('checkbox', { name: /terms of service/i }));
      await user.click(screen.getByRole('checkbox', { name: /privacy policy/i }));
      await user.click(screen.getByRole('checkbox', { name: /strictly as a simulated paper trading environment/i }));

      await user.click(screen.getByRole('button', { name: /create paper trading account/i }));

      expect(await screen.findByText(/username 'trader_existing' is already registered/i)).toBeInTheDocument();
    });

    it('displays 429 rate limit exceeded message', async () => {
      const user = userEvent.setup();

      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 429,
        headers: new Headers({
          'content-type': 'application/json',
          'retry-after': '3600',
        }),
        json: () =>
          Promise.resolve({
            detail: 'Rate limit exceeded: 5 requests per 1 hour.',
          }),
      });

      render(
        <MemoryRouter>
          <RegisterPage />
        </MemoryRouter>
      );

      await user.type(screen.getByLabelText(/username/i), 'trader_spam');
      await user.type(screen.getByLabelText(/corporate email/i), 'trader@spam.com');
      await user.type(screen.getByLabelText(/organization name/i), 'Spam Capital');
      await user.type(screen.getByLabelText(/^password/i), 'ValidPass123!');
      await user.type(screen.getByLabelText(/confirm password/i), 'ValidPass123!');

      await user.click(screen.getByRole('checkbox', { name: /terms of service/i }));
      await user.click(screen.getByRole('checkbox', { name: /privacy policy/i }));
      await user.click(screen.getByRole('checkbox', { name: /strictly as a simulated paper trading environment/i }));

      await user.click(screen.getByRole('button', { name: /create paper trading account/i }));

      expect(await screen.findByText(/rate limit exceeded\. please retry after 3600 seconds/i)).toBeInTheDocument();
    });
  });

  describe('Integration with LoginPage & AppRoutes', () => {
    it('LoginPage has a direct navigation link to /register', () => {
      render(
        <MemoryRouter>
          <AuthProvider>
            <OrganizationProvider>
              <LoginPage />
            </OrganizationProvider>
          </AuthProvider>
        </MemoryRouter>
      );

      const registerLink = screen.getByRole('link', { name: /sign up for paper trading/i });
      expect(registerLink).toBeInTheDocument();
      expect(registerLink).toHaveAttribute('href', '/register');
    });

    it('AppRoutes renders RegisterPage when path is /register', async () => {
      render(
        <MemoryRouter initialEntries={['/register']}>
          <AuthProvider>
            <OrganizationProvider>
              <AppRoutes />
            </OrganizationProvider>
          </AuthProvider>
        </MemoryRouter>
      );

      expect(await screen.findByRole('heading', { level: 1, name: /project orion/i })).toBeInTheDocument();
      expect(screen.getByText(/self-service registration & onboarding/i)).toBeInTheDocument();
    });
  });
});
