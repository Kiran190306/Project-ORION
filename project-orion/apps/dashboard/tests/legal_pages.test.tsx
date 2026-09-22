import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { TermsPage } from '../src/pages/TermsPage';
import { PrivacyPage } from '../src/pages/PrivacyPage';
import { RiskDisclosurePage } from '../src/pages/RiskDisclosurePage';
import { RefundPolicyPage } from '../src/pages/RefundPolicyPage';
import { SecurityTrustPage } from '../src/pages/SecurityTrustPage';
import { PublicFooter } from '../src/components/layout/PublicFooter';

describe('EPIC-027 Phase 3: Legal, Trust & Risk Disclosure Pages', () => {
  describe('TermsPage', () => {
    it('renders terms title, draft status badge, and key sections', () => {
      render(
        <MemoryRouter>
          <TermsPage />
        </MemoryRouter>
      );

      expect(screen.getByRole('heading', { level: 1, name: /^Terms of Service$/i })).toBeInTheDocument();
      expect(screen.getByText(/Draft for Legal Review/i)).toBeInTheDocument();
      expect(screen.getByText(/Paper Trading Invariant \(\$0\.00 Capital at Risk\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Return to Terminal/i)).toBeInTheDocument();
    });
  });

  describe('PrivacyPage', () => {
    it('renders privacy title, draft status badge, and ephemeral storage disclosures', () => {
      render(
        <MemoryRouter>
          <PrivacyPage />
        </MemoryRouter>
      );

      expect(screen.getByRole('heading', { level: 1, name: /Privacy Policy/i })).toBeInTheDocument();
      expect(screen.getByText(/Draft for Legal Review/i)).toBeInTheDocument();
      expect(screen.getByText(/Zero Tracking Cookies/i)).toBeInTheDocument();
      expect(screen.getByText(/orion_access_token/i)).toBeInTheDocument();
    });
  });

  describe('RiskDisclosurePage', () => {
    it('renders paper trading risk title, simulated execution notice, and $0 capital invariant', () => {
      render(
        <MemoryRouter>
          <RiskDisclosurePage />
        </MemoryRouter>
      );

      expect(screen.getByRole('heading', { level: 1, name: /Paper Trading & Financial Risk Disclosure/i })).toBeInTheDocument();
      expect(screen.getByText(/Strictly Paper Simulation/i)).toBeInTheDocument();
      expect(screen.getByText(/Execution Differences & Simulation Limitations/i)).toBeInTheDocument();
      expect(screen.getByText(/Capital at risk is strictly \$0\.00/i)).toBeInTheDocument();
    });
  });

  describe('RefundPolicyPage', () => {
    it('renders refund policy, Stripe test mode disclaimer, and cancellation terms', () => {
      render(
        <MemoryRouter>
          <RefundPolicyPage />
        </MemoryRouter>
      );

      expect(screen.getByRole('heading', { level: 1, name: /Refund & Subscription Cancellation Policy/i })).toBeInTheDocument();
      expect(screen.getByText(/Draft for Legal Review/i)).toBeInTheDocument();
      expect(screen.getByText(/Beta Testing Environment \(Stripe Test Mode\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Subscription Billing & Auto-Renewal/i)).toBeInTheDocument();
    });
  });

  describe('SecurityTrustPage', () => {
    it('renders security architecture, clear disclaimer on non-certification, and vulnerability disclosure', () => {
      render(
        <MemoryRouter>
          <SecurityTrustPage />
        </MemoryRouter>
      );

      expect(screen.getByRole('heading', { level: 1, name: /Security & Trust Architecture/i })).toBeInTheDocument();
      expect(screen.getByText(/Security Architecture/i)).toBeInTheDocument();
      expect(screen.getByText(/NON-CERTIFICATION DISCLOSURE/i)).toBeInTheDocument();
      expect(screen.getByText(/Coordinated Vulnerability Disclosure/i)).toBeInTheDocument();
    });
  });

  describe('PublicFooter', () => {
    it('renders all legal navigation links and paper trading notice', () => {
      render(
        <MemoryRouter>
          <PublicFooter />
        </MemoryRouter>
      );

      const termsLink = screen.getByRole('link', { name: /Terms of Service/i });
      expect(termsLink).toHaveAttribute('href', '/terms');

      const privacyLink = screen.getByRole('link', { name: /Privacy Policy/i });
      expect(privacyLink).toHaveAttribute('href', '/privacy');

      const riskLink = screen.getByRole('link', { name: /Risk Disclosure/i });
      expect(riskLink).toHaveAttribute('href', '/risk-disclosure');

      const refundLink = screen.getByRole('link', { name: /Refund Policy/i });
      expect(refundLink).toHaveAttribute('href', '/refund-policy');

      const securityLink = screen.getByRole('link', { name: /Security & Trust/i });
      expect(securityLink).toHaveAttribute('href', '/security');

      expect(screen.getByText(/Strictly Simulated Paper Mode • \$0\.00 Capital at Risk/i)).toBeInTheDocument();
    });
  });
});
