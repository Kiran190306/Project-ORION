import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { MarketingHomePage } from '../src/pages/MarketingHomePage';
import { PricingPage } from '../src/pages/PricingPage';
import { PublicHeader } from '../src/components/layout/PublicHeader';
import { PRICING_PLANS } from '../src/config/pricing';
import { AppRoutes } from '../src/App';
import { AuthProvider } from '../src/auth/AuthContext';
import { OrganizationProvider } from '../src/auth/OrganizationContext';

describe('EPIC-027 Phase 4C: Public Marketing Website & Pricing', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    sessionStorage.clear();
  });

  describe('PublicHeader Component', () => {
    it('renders logo, brand title, desktop navigation links, and primary/secondary CTAs', () => {
      render(
        <MemoryRouter>
          <PublicHeader />
        </MemoryRouter>
      );

      // Brand
      expect(screen.getByText('PROJECT ORION')).toBeInTheDocument();
      expect(screen.getByText(/quantitative research • paper trading/i)).toBeInTheDocument();

      // Navigation links
      const overviewLinks = screen.getAllByRole('link', { name: /overview/i });
      expect(overviewLinks[0]).toHaveAttribute('href', '/');

      const pricingLinks = screen.getAllByRole('link', { name: /pricing/i });
      expect(pricingLinks[0]).toHaveAttribute('href', '/pricing');

      const securityLinks = screen.getAllByRole('link', { name: /security & trust/i });
      expect(securityLinks[0]).toHaveAttribute('href', '/security');

      // CTAs
      const signInLinks = screen.getAllByRole('link', { name: /sign in/i });
      expect(signInLinks[0]).toHaveAttribute('href', '/login');

      const registerLinks = screen.getAllByRole('link', { name: /start paper trading/i });
      expect(registerLinks[0]).toHaveAttribute('href', '/register');
    });

    it('toggles mobile navigation drawer on hamburger button click', async () => {
      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <PublicHeader />
        </MemoryRouter>
      );

      const toggleBtn = screen.getByRole('button', { name: /open navigation menu/i });
      expect(toggleBtn).toBeInTheDocument();

      await user.click(toggleBtn);
      expect(screen.getByRole('button', { name: /close navigation menu/i })).toBeInTheDocument();

      // Mobile nav has rendered
      expect(screen.getByRole('navigation', { name: /mobile navigation/i })).toBeInTheDocument();
    });
  });

  describe('MarketingHomePage Component', () => {
    it('renders hero with quantitative value proposition and paper mode safety badge', () => {
      render(
        <MemoryRouter>
          <MarketingHomePage />
        </MemoryRouter>
      );

      // Hero headline
      expect(
        screen.getByRole('heading', { level: 1, name: /quantitative research & algorithmic paper trading/i })
      ).toBeInTheDocument();

      // Paper mode safety badges
      const safetyBadges = screen.getAllByText(/strictly simulated paper mode • \$0\.00 capital at risk/i);
      expect(safetyBadges.length).toBeGreaterThanOrEqual(1);

      // Hero CTAs
      const startPaperBtn = screen.getByRole('link', { name: /start paper trading — free sandbox/i });
      expect(startPaperBtn).toHaveAttribute('href', '/register');

      const explorePricingBtn = screen.getByRole('link', { name: /explore pricing tiers/i });
      expect(explorePricingBtn).toHaveAttribute('href', '/pricing');
    });

    it('renders quantitative research capabilities and strategy validation pipeline', () => {
      render(
        <MemoryRouter>
          <MarketingHomePage />
        </MemoryRouter>
      );

      expect(screen.getByRole('heading', { level: 2, name: /built for mathematical rigor and strategy evaluation/i })).toBeInTheDocument();
      expect(screen.getByText(/multi-timeframe market data/i)).toBeInTheDocument();
      expect(screen.getByText(/walk-forward optimization/i)).toBeInTheDocument();
      expect(screen.getByText(/quantitative statistical tearsheets/i)).toBeInTheDocument();
      expect(screen.getByText(/the 5-stage strategy validation pipeline/i)).toBeInTheDocument();
    });

    it('renders paper trading telemetry and risk guardrails without real-money claims', () => {
      render(
        <MemoryRouter>
          <MarketingHomePage />
        </MemoryRouter>
      );

      expect(screen.getByText(/high-fidelity simulated matching with zero real-capital risk/i)).toBeInTheDocument();
      expect(screen.getByText(/systematic risk guardrails enforced at the engine level/i)).toBeInTheDocument();
      expect(screen.getByText(/pre-trade order validation/i)).toBeInTheDocument();
      expect(screen.getByText(/drawdown circuit breakers/i)).toBeInTheDocument();
      expect(screen.getByText(/strictly \$0\.00 \(forbidden\)/i)).toBeInTheDocument();
    });

    it('renders security by design section and public FAQ', () => {
      render(
        <MemoryRouter>
          <MarketingHomePage />
        </MemoryRouter>
      );

      expect(screen.getByRole('heading', { level: 2, name: /institutional security & data isolation/i })).toBeInTheDocument();
      expect(screen.getByText(/tenant idor isolation/i)).toBeInTheDocument();
      expect(screen.getByText(/role-based access control/i)).toBeInTheDocument();
      expect(screen.getByText(/is project orion a live financial broker\?/i)).toBeInTheDocument();
      expect(screen.getByText(/how much real capital is at risk\?/i)).toBeInTheDocument();
    });

    it('renders final CTA linking to /register', () => {
      render(
        <MemoryRouter>
          <MarketingHomePage />
        </MemoryRouter>
      );

      const finalCta = screen.getByRole('link', { name: /create paper trading account/i });
      expect(finalCta).toHaveAttribute('href', '/register');
    });
  });

  describe('PricingPage Component', () => {
    it('renders all canonical pricing tiers directly from shared configuration', () => {
      render(
        <MemoryRouter>
          <PricingPage />
        </MemoryRouter>
      );

      expect(screen.getByRole('heading', { level: 1, name: /transparent institutional pricing/i })).toBeInTheDocument();

      // Check each tier from PRICING_PLANS
      for (const plan of PRICING_PLANS) {
        expect(screen.getByRole('heading', { level: 2, name: plan.name })).toBeInTheDocument();
        expect(screen.getAllByText(plan.price).length).toBeGreaterThanOrEqual(1);
      }
    });

    it('displays Enterprise tier as Custom without an invented numerical price', () => {
      render(
        <MemoryRouter>
          <PricingPage />
        </MemoryRouter>
      );

      const enterprisePlan = PRICING_PLANS.find((p) => p.code === 'ENTERPRISE');
      expect(enterprisePlan).toBeDefined();
      expect(enterprisePlan?.price).toBe('Custom');

      // Ensure no invented prices exist in document
      expect(screen.queryByText('$499')).not.toBeInTheDocument();
      expect(screen.queryByText('$999')).not.toBeInTheDocument();
      expect(screen.queryByText('$1999')).not.toBeInTheDocument();

      // Enterprise CTA triggers inquiry notice modal
      const enterpriseBtn = screen.getByRole('button', { name: /contact enterprise/i });
      expect(enterpriseBtn).toBeInTheDocument();
    });

    it('renders detailed quota matrix table with authoritative values', () => {
      render(
        <MemoryRouter>
          <PricingPage />
        </MemoryRouter>
      );

      expect(screen.getByRole('heading', { level: 2, name: /detailed tier quota matrix/i })).toBeInTheDocument();
      expect(screen.getByText(/daily orders limit/i)).toBeInTheDocument();
      expect(screen.getByText(/100 \/ day/i)).toBeInTheDocument();
      expect(screen.getByText(/2,500 \/ day/i)).toBeInTheDocument();
      expect(screen.getByText(/50,000 \/ day/i)).toBeInTheDocument();
      expect(screen.getAllByText(/historical data retention/i).length).toBeGreaterThanOrEqual(1);
    });

    it('shows Stripe Test Mode notice and simulated execution disclaimers', () => {
      render(
        <MemoryRouter>
          <PricingPage />
        </MemoryRouter>
      );

      expect(screen.getByText(/beta environment: commercial subscription checkouts are simulated via stripe test mode/i)).toBeInTheDocument();
      expect(screen.getAllByText(/strictly simulated paper mode • \$0\.00 capital at risk/i).length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('Route Architecture & Code Splitting (AppRoutes)', () => {
    it('renders MarketingHomePage at / without requiring authentication', async () => {
      render(
        <MemoryRouter initialEntries={['/']}>
          <AuthProvider>
            <OrganizationProvider>
              <AppRoutes />
            </OrganizationProvider>
          </AuthProvider>
        </MemoryRouter>
      );

      expect(
        await screen.findByRole('heading', { level: 1, name: /quantitative research & algorithmic paper trading/i })
      ).toBeInTheDocument();
    });

    it('renders PricingPage at /pricing without requiring authentication', async () => {
      render(
        <MemoryRouter initialEntries={['/pricing']}>
          <AuthProvider>
            <OrganizationProvider>
              <AppRoutes />
            </OrganizationProvider>
          </AuthProvider>
        </MemoryRouter>
      );

      expect(
        await screen.findByRole('heading', { level: 1, name: /transparent institutional pricing/i })
      ).toBeInTheDocument();
    });

    it('intercepts unauthenticated access to /dashboard and redirects to /login', async () => {
      render(
        <MemoryRouter initialEntries={['/dashboard']}>
          <AuthProvider>
            <OrganizationProvider>
              <AppRoutes />
            </OrganizationProvider>
          </AuthProvider>
        </MemoryRouter>
      );

      // ProtectedRoute intercepts and renders LoginPage
      expect(await screen.findByRole('heading', { name: /trading terminal sign in/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /authenticate session/i })).toBeInTheDocument();
    });
  });
});
