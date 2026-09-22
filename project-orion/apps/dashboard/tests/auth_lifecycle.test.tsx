import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ForgotPasswordPage } from '../src/pages/ForgotPasswordPage';
import { ResetPasswordPage } from '../src/pages/ResetPasswordPage';
import { VerifyEmailPage } from '../src/pages/VerifyEmailPage';
import { AppRoutes } from '../src/App';
import { AuthProvider } from '../src/auth/AuthContext';
import { OrganizationProvider } from '../src/auth/OrganizationContext';

describe('Auth Lifecycle Pages (EPIC-027 Phase 1)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('ForgotPasswordPage', () => {
    it('renders the forgot password form correctly', () => {
      render(
        <MemoryRouter>
          <ForgotPasswordPage />
        </MemoryRouter>
      );

      expect(screen.getByRole('heading', { name: /reset your password/i })).toBeInTheDocument();
      expect(screen.getByLabelText(/registered email/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /send recovery link/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /back to sign in/i })).toBeInTheDocument();
    });

    it('validates email format before sending', async () => {
      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <ForgotPasswordPage />
        </MemoryRouter>
      );

      const submitBtn = screen.getByRole('button', { name: /send recovery link/i });
      await user.click(submitBtn);

      expect(await screen.findByText(/please enter a valid email address/i)).toBeInTheDocument();

      const input = screen.getByLabelText(/registered email/i);
      await user.type(input, 'invalid-email');
      await user.click(submitBtn);

      expect(await screen.findByText(/please enter a valid email address/i)).toBeInTheDocument();
    });

    it('submits forgot password request and displays anti-enumeration generic message', async () => {
      const user = userEvent.setup();

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () =>
          Promise.resolve({
            message: 'If the email is registered, password reset instructions have been dispatched.',
          }),
      });

      render(
        <MemoryRouter>
          <ForgotPasswordPage />
        </MemoryRouter>
      );

      await user.type(screen.getByLabelText(/registered email/i), 'trader@example.com');
      await user.click(screen.getByRole('button', { name: /send recovery link/i }));

      expect(
        await screen.findByText(/if the email is registered, password reset instructions have been dispatched/i)
      ).toBeInTheDocument();
      expect(screen.getByText(/instructions dispatched/i)).toBeInTheDocument();
    });

    it('displays error message when endpoint fails', async () => {
      const user = userEvent.setup();

      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve({ message: 'Internal server error' }),
      });

      render(
        <MemoryRouter>
          <ForgotPasswordPage />
        </MemoryRouter>
      );

      await user.type(screen.getByLabelText(/registered email/i), 'trader@example.com');
      await user.click(screen.getByRole('button', { name: /send recovery link/i }));

      expect(await screen.findByText(/trading service is temporarily unavailable/i)).toBeInTheDocument();
    });
  });

  describe('ResetPasswordPage', () => {
    it('populates token from URL search parameter', () => {
      render(
        <MemoryRouter initialEntries={['/reset-password?token=secret-token-123']}>
          <ResetPasswordPage />
        </MemoryRouter>
      );

      const tokenInput = screen.getByLabelText(/reset token/i) as HTMLInputElement;
      expect(tokenInput.value).toBe('secret-token-123');
    });

    it('validates password requirements and matching inputs', async () => {
      const user = userEvent.setup();
      render(
        <MemoryRouter initialEntries={['/reset-password?token=valid-token']}>
          <ResetPasswordPage />
        </MemoryRouter>
      );

      const submitBtn = screen.getByRole('button', { name: /save new password/i });

      // Password too short
      await user.type(screen.getByLabelText(/new password \(min 8 chars\)/i), 'short');
      await user.type(screen.getByLabelText(/confirm new password/i), 'short');
      await user.click(submitBtn);
      expect(await screen.findByText(/new password must be at least 8 characters long/i)).toBeInTheDocument();

      // Password mismatch
      await user.clear(screen.getByLabelText(/new password \(min 8 chars\)/i));
      await user.clear(screen.getByLabelText(/confirm new password/i));
      await user.type(screen.getByLabelText(/new password \(min 8 chars\)/i), 'StrongPass123!');
      await user.type(screen.getByLabelText(/confirm new password/i), 'DifferentPass123!');
      await user.click(submitBtn);
      expect(await screen.findByText(/passwords do not match\. please verify both inputs\./i)).toBeInTheDocument();
    });

    it('successfully resets password and shows login redirect', async () => {
      const user = userEvent.setup();

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () =>
          Promise.resolve({
            message: 'Password successfully reset. All previous sessions have been revoked. Please sign in.',
          }),
      });

      render(
        <MemoryRouter initialEntries={['/reset-password?token=valid-token']}>
          <ResetPasswordPage />
        </MemoryRouter>
      );

      await user.type(screen.getByLabelText(/new password \(min 8 chars\)/i), 'SecurePass123!');
      await user.type(screen.getByLabelText(/confirm new password/i), 'SecurePass123!');
      await user.click(screen.getByRole('button', { name: /save new password/i }));

      expect(
        await screen.findByText(/password successfully reset\. all previous sessions have been revoked\. please sign in\./i)
      ).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /proceed to sign in/i })).toBeInTheDocument();
    });
  });

  describe('VerifyEmailPage', () => {
    it('automatically triggers verification when token is in search params', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () =>
          Promise.resolve({
            message: 'Email successfully verified. You may now sign in to Project ORION.',
          }),
      });

      render(
        <MemoryRouter initialEntries={['/verify-email?token=email-verify-token-abc']}>
          <VerifyEmailPage />
        </MemoryRouter>
      );

      expect(
        await screen.findByText(/email successfully verified\. you may now sign in to project orion\./i)
      ).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /proceed to sign in/i })).toBeInTheDocument();
    });

    it('handles invalid or expired verification token and displays resend form', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () =>
          Promise.resolve({
            message: 'Invalid or expired verification token.',
          }),
      });

      render(
        <MemoryRouter initialEntries={['/verify-email?token=expired-token']}>
          <VerifyEmailPage />
        </MemoryRouter>
      );

      expect(await screen.findByText(/invalid or expired verification token/i)).toBeInTheDocument();
      expect(screen.getByText(/the verification token was invalid or has expired\. you can request a new verification link below\./i)).toBeInTheDocument();
    });

    it('allows resending verification email with anti-enumeration message', async () => {
      const user = userEvent.setup();

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () =>
          Promise.resolve({
            message: 'If the account exists and is unverified, a verification email has been sent.',
          }),
      });

      render(
        <MemoryRouter initialEntries={['/verify-email']}>
          <VerifyEmailPage />
        </MemoryRouter>
      );

      expect(screen.getByRole('heading', { name: /verify your email/i })).toBeInTheDocument();

      await user.type(screen.getByLabelText(/registered email/i), 'unverified@example.com');
      await user.click(screen.getByRole('button', { name: /resend verification link/i }));

      expect(
        await screen.findByText(/if the account exists and is unverified, a verification email has been sent/i)
      ).toBeInTheDocument();
    });
  });

  describe('Routing Integration in AppRoutes', () => {
    it('renders /forgot-password route', () => {
      render(
        <MemoryRouter initialEntries={['/forgot-password']}>
          <AuthProvider>
            <OrganizationProvider>
              <AppRoutes />
            </OrganizationProvider>
          </AuthProvider>
        </MemoryRouter>
      );

      expect(screen.getByRole('heading', { name: /reset your password/i })).toBeInTheDocument();
    });

    it('renders /reset-password route', () => {
      render(
        <MemoryRouter initialEntries={['/reset-password']}>
          <AuthProvider>
            <OrganizationProvider>
              <AppRoutes />
            </OrganizationProvider>
          </AuthProvider>
        </MemoryRouter>
      );

      expect(screen.getByRole('heading', { name: /set new password/i })).toBeInTheDocument();
    });

    it('renders /verify-email route', () => {
      render(
        <MemoryRouter initialEntries={['/verify-email']}>
          <AuthProvider>
            <OrganizationProvider>
              <AppRoutes />
            </OrganizationProvider>
          </AuthProvider>
        </MemoryRouter>
      );

      expect(screen.getByRole('heading', { name: /verify your email/i })).toBeInTheDocument();
    });
  });
});
