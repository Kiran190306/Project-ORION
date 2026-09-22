# EPIC-027 Phase 4C: Public Marketing Website & Pricing â€” Implementation Report

**Document Version:** 1.1 (Post-Verification Remediation)
**Phase:** EPIC-027 Phase 4C â€” Public Marketing Website & Pricing
**Date:** 2026-09-23
**Authors / Roles:** Principal Software Architect, Senior React Engineer, Product UX Architect, Application Security Engineer, SEO Engineer, QA Lead, Release Gatekeeper
**Baseline Commit:** `c9da2a7 feat(onboarding): implement EPIC-027 phase 4B registration funnel`
**Classification:** **`B â€” COMPLETE WITH EXTERNAL DEPENDENCY`**

---

## 1. Executive Summary

This report documents the implementation and verification of **EPIC-027 Phase 4C: Public Marketing Website & Pricing** for Project ORION.

Prior to Phase 4C, Project ORION possessed institutional-grade backend research engines, paper-trading simulation, an onboarding legal assent registry, and a self-service registration funnel (Phase 4B). However, the root path (`/`) was strictly guarded behind `<ProtectedRoute>`, immediately redirecting any unauthenticated public visitor to `/login`. There was no marketing landing page, no public showcase of quantitative research capabilities, and no publicly accessible pricing page (`/pricing`). Furthermore, subscription plan definitions were hardcoded directly within the authenticated `BillingPage.tsx`, creating potential for pricing drift.

Phase 4C resolves these gaps by delivering:
1. **Shared Pricing Configuration (`pricing.ts`):** A single source of truth for all subscription tiers (`FREE`, `PRO`, `BUSINESS`, `ENTERPRISE`), features, quotas, and regulatory disclaimers, consumed uniformly by both public `/pricing` and authenticated `/billing`.
2. **Public Navigation Header (`PublicHeader.tsx`):** A fully responsive, modern dark-theme header featuring brand identity, prominent "SIMULATION ENVIRONMENT" paper-trading status badges, desktop navigation links, mobile hamburger menu drawer, and clear CTAs ("Sign In" and "Get Started").
3. **Public Marketing Homepage (`MarketingHomePage.tsx`):** An institutional, high-credibility presentation of Project ORIONâ€™s quantitative research platform. It features eight structured sections: Hero with value proposition, Interactive Research Lab Showcase, Absolute Paper Trading Invariant Banner, Four-Layer Real-Time Risk Engine, Five-Stage Strategy Validation Pipeline, Security & Data Isolation Grid, FAQ with Accordions, and High-Conversion Bottom CTA.
4. **Public Pricing Page (`PricingPage.tsx`):** A comprehensive pricing presentation featuring 4 tier cards (monthly test pricing matching backend capabilities), an exhaustive Quota & Capability Comparison Matrix, Stripe Test Mode regulatory badge, and an Enterprise Inquiry modal (with neutral contact notice and zero fabricated custom pricing).
5. **Billing Page Refactoring (`BillingPage.tsx`):** Complete refactor to import and consume `PRICING_PLANS` from the shared configuration, eliminating pricing drift and maintaining active plan state.
6. **Route Architecture & Dynamic Code Splitting (`App.tsx`):** Route-level code splitting using `React.lazy()` and `Suspense` with an accessible `PageLoadingFallback`. Reclaimed `/` as the public landing page, exposed `/pricing` publicly, and nested all authenticated application views under a pathless `<ProtectedRoute><AppShell /></ProtectedRoute>` layout.
7. **SEO & Static Crawler Infrastructure:** Configured `apps/dashboard/index.html` with title, meta description, keywords, Open Graph, and Twitter card tags; created `public/robots.txt` and `public/sitemap.xml`.
8. **Automated Quality & Verification Gates:** 12 new automated unit and integration tests (`marketing_pages.test.tsx`), full Vitest suite passing with **22 test files / 94 tests passed (100%)**, zero TypeScript compilation errors with Vite production bundling passing (`npm run build`), and **73 backend regression tests passed (100%)**.

All development adhered strictly to Project ORION's core safety invariants: **$0.00 capital at risk, paper-trading simulation only, autonomous worker disabled (`ORION_WORKER_ENABLED=false`), and Stripe in Test Mode**.

---

## 2. Baseline Commit & Repository Safety

- **Baseline Commit:** `c9da2a75e937442f9a78715c408a4b013c5ddf72` (`c9da2a7`)
- **Commit Message:** `feat(onboarding): implement EPIC-027 phase 4B registration funnel`
- **Branch:** `main`
- **Repository Safety:**
  - All changes are strictly confined to `project-orion/apps/dashboard/` and documentation in `project-orion/docs/`.
  - Zero parent repository files (`../`) were modified or touched.
  - Zero broker execution engine, strategy runner, risk limits, database schemas, or backend API contracts were modified.
  - No tracking libraries, analytics scripts, marketing cookies, or external CDN dependencies were added.

---

## 3. Shared Pricing Architecture

To prevent pricing drift between public marketing collateral and authenticated billing workflows, a single immutable configuration file was established.

### 3.1 Implementation: `apps/dashboard/src/config/pricing.ts`
- **Tiers Defined (Monthly Billing Only):**
  - `FREE` ($0/mo): 1 Paper Account, 100 Orders/Day, 0 Autonomous Workers, 4 Major FX Pairs, 30-day History, Community Support.
  - `PRO` ($99/mo): 3 Paper Accounts, 2,500 Orders/Day, 1 Autonomous Worker, 12 FX Pairs, 365-day History, Standard SLA.
  - `BUSINESS` ($299/mo): 10 Paper Accounts, 50,000 Orders/Day, 5 Autonomous Workers, All Currency Pairs Supported (*), 5-Year History, Dedicated Account Manager.
  - `ENTERPRISE` ("Custom"): Unlimited Accounts, Unlimited Orders, Unlimited Workers, All Currency Pairs Supported (*), 7-Year History, Dedicated SRE Account Manager. No artificial numerical price is invented.
- **Quota Comparison Matrix:** Explicitly maps account limits, order frequency, worker limits, data retention, and asset coverage across all 4 tiers.
- **Regulatory Disclaimers (`PRICING_DISCLAIMERS`):** Standardizes platform invariants across the entire application:
  - *Simulation Disclaimer:* "All tiers operate strictly within a simulated paper trading environment with $0.00 capital at risk."
  - *Billing Behavior:* "Subscription tiers entitle organizations to software compute quotas and paper-trading accounts. Payment processing is conducted via Stripe Test Mode."
  - *Enterprise Notice:* "Contact details coming soon. For institutional bespoke deployment inquiries, reach out through your assigned account representative."

### 3.2 Refactoring: `apps/dashboard/src/pages/BillingPage.tsx`
- Removed duplicated static plan definitions.
- Imported `PRICING_PLANS` from `../config/pricing`.
- Preserved existing Stripe checkout creation logic (`POST /api/v1/billing/create-checkout-session`) and subscription status synchronization.

---

## 4. Public Marketing Homepage Architecture

### 4.1 Implementation: `apps/dashboard/src/pages/MarketingHomePage.tsx`
Designed with institutional aesthetic (Tailwind slate-900 / cyan / indigo palette) and dark mode fidelity. Organized into eight logical sections:

1. **Hero Section:**
   - Visual badge: `Strictly Simulated Paper Mode â€¢ $0.00 Capital at Risk`.
   - Title: "Quantitative Research & Algorithmic Paper Trading".
   - Subtitle: Clearly delineates ORION as a research laboratory and execution simulator for systematic strategies.
   - Dual CTAs: Primary "Start Paper Trading â€” Free Sandbox" (`/register`) and Secondary "Explore Pricing Tiers" (`/pricing`).
   - Platform assurances: $100,000 Initial Paper Balance, No Credit Card Required for Sandbox, Instant Provisioning.
   - Simulated Terminal Mockup: Real-time paper execution telemetry, walk-forward optimization regime, and nominal risk circuit telemetry.

2. **Interactive Research Lab Section (`#research`):**
   - Highlights 4 core research modules: Multi-Timeframe Market Data, Walk-Forward Optimization, Quantitative Statistical Tearsheets, and Strategy Incubator & Pipeline.

3. **Absolute Paper-Trading Invariant Banner:**
   - Prominent alert box with `ShieldAlert` icon emphasizing that ORION connects exclusively to simulated paper execution engines with no client fund custody or live market routing.

4. **Automated Risk Controls (`#risk-controls`):**
   - Visual cards detailing ORION's multi-layered pre-trade risk safeguards: Pre-Trade Order Validation, Drawdown Circuit Breakers, Automated Position Protection, and Account Isolation & Quota Limits.

5. **Strategy Validation Pipeline Section:**
   - Five-stage scientific workflow: 01 Formulate & Research â†’ 02 Historical Backtest â†’ 03 Walk-Forward Analysis â†’ 04 Paper Incubation â†’ 05 Audit & Review.

6. **Institutional Trust & Security Section:**
   - High-trust grid detailing Cryptographic Credentials (Bcrypt password hashing with 72-byte input boundary), Tenant IDOR Isolation (row-level multi-tenant boundaries), Role-Based Access Control, and Immutable Audit Logging.

7. **Frequently Asked Questions (FAQ) Section:**
   - Public FAQ addressing key user queries: non-broker software status, $0.00 real capital at risk, sandbox provisioning, and Stripe Test Mode commercial upgrades.

8. **High-Conversion Bottom CTA Section:**
   - Final call to action directing institutional researchers and algorithmic traders to register for sandbox access, complete with safety assurances.

---

## 5. Public Pricing Page Architecture

### 5.1 Implementation: `apps/dashboard/src/pages/PricingPage.tsx`
- **Header & Disclaimers:**
  - Clear heading and description emphasizing simulated paper trading with zero capital at risk.
  - Notice indicating commercial checkouts are simulated via Stripe Test Mode.
- **Tier Cards:**
  - 4 responsive cards rendering Free Sandbox ($0), Pro Trader ($99/mo), Business Prop Desk ($299/mo), and Enterprise Custom.
  - Clear CTA buttons routing `/register` for self-service tiers, or triggering the Enterprise Inquiry modal.
- **Quota Comparison Matrix:**
  - Detailed feature-by-feature table contrasting all 4 tiers across Monthly Price, Paper Trading Accounts, Daily Orders Limit, Autonomous Workers, FX Asset Coverage, Historical Data Retention, and Support Level.
- **Enterprise Contact Modal:**
  - Accessible modal dialog presenting neutral inquiry instructions: *"Contact details coming soon. For institutional bespoke deployment inquiries, reach out through your assigned account representative."* (with an Acknowledge button; no fabricated email addresses).

---

## 6. Shared Header & Footer Integration

### 6.1 Public Header (`apps/dashboard/src/components/layout/PublicHeader.tsx`)
- Persistent brand logo with quantitative symbol icon and Project ORION wordmark.
- Active route highlighting for `Overview` (`/`), `Research Lab` (`/#research`), `Risk Controls` (`/#risk-controls`), `Pricing` (`/pricing`), and `Security & Trust` (`/security`).
- Embedded `SIMULATION ENVIRONMENT` status badge.
- Action buttons: "Sign In" (`/login`) and "Get Started" (`/register`).
- Fully accessible mobile hamburger drawer with slide-in navigation.

### 6.2 Public Footer (`apps/dashboard/src/components/layout/PublicFooter.tsx`)
- Structured four-column footer: Product Navigation, Legal & Trust, Resources, and Platform Status.
- Mandatory legal disclosure links: Terms of Service (`/terms`), Privacy Policy (`/privacy`), Risk Disclosure (`/risk-disclosure`), and Refund Policy (`/refund-policy`).
- Explicit non-custodial and regulatory disclaimer text.

---

## 7. Router Architecture & Code Splitting

### 7.1 Dynamic Code Splitting (`apps/dashboard/src/App.tsx`)
All route components are lazily imported using `React.lazy()` to decouple the public bundle footprint from authenticated modules:
- Public Pages: `MarketingHomePage`, `PricingPage`, `LoginPage`, `RegisterPage`, `ForgotPasswordPage`, `ResetPasswordPage`, `VerifyEmailPage`, `TermsPage`, `PrivacyPage`, `RiskDisclosurePage`, `RefundPolicyPage`, `SecurityTrustPage`.
- Authenticated Pages: `DashboardPage`, `PortfolioPage`, `OrdersPage`, `PositionsPage`, `TradesPage`, `RiskPage`, `StrategiesPage`, `ResearchLabPage`, `OptimizationStudioPage`, `DeploymentPipelinePage`, `BrokerSandboxPage`, `WorkerPage`, `BillingPage`, `OrganizationPage`, `AuditPage`.

### 7.2 Route Separation
```tsx
<Suspense fallback={<PageLoadingFallback />}>
  <Routes>
    {/* Public Marketing & Pricing */}
    <Route path="/" element={<MarketingHomePage />} />
    <Route path="/pricing" element={<PricingPage />} />

    {/* Public Authentication */}
    <Route path="/login" element={<LoginPage />} />
    <Route path="/register" element={<RegisterPage />} />
    ...

    {/* Protected Authenticated Application */}
    <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
      <Route path="dashboard" element={<DashboardPage />} />
      <Route path="orders" element={<OrdersPage />} />
      ...
    </Route>
  </Routes>
</Suspense>
```

---

## 8. SEO & Static Crawler Infrastructure

### 8.1 Index HTML Metadata (`apps/dashboard/index.html`)
- Updated title: `Project ORION â€” Quantitative Financial Research & Algorithmic Paper Trading`.
- Meta description: Highlights institutional-grade quantitative research, backtesting, walk-forward optimization, and simulated paper execution.
- Open Graph tags: `og:title`, `og:description`, `og:type=website`, `og:site_name`, `og:locale`.
- Twitter Card tags: `twitter:card=summary`, `twitter:title`, `twitter:description`.
- *(Note: JSON-LD schema was evaluated and omitted from current scope to avoid unverified corporate schema claims; standard Open Graph and meta headers provide full search crawler discoverability).*

### 8.2 Robots & Sitemap
- `apps/dashboard/public/robots.txt`:
  - Allows public crawling of `/`, `/pricing`, `/terms`, `/privacy`, `/risk-disclosure`, `/refund-policy`, `/security`, `/login`, `/register`.
  - Disallows internal routes (`/dashboard`, `/orders`, `/api/`, etc.).
  - References `Sitemap: /sitemap.xml`.
- `apps/dashboard/public/sitemap.xml`:
  - XML standard compliant map covering all 9 public indexable URLs.

---

## 9. Verification & Automated Test Results

### 9.1 Automated Tests: `apps/dashboard/tests/marketing_pages.test.tsx`
12 comprehensive unit and integration tests are implemented and verified:
1. `PublicHeader`: Renders logo, brand title, navigation links, and CTAs.
2. `PublicHeader`: Renders persistent paper trading simulation badge.
3. `PublicHeader`: Toggles mobile navigation menu on hamburger click.
4. `MarketingHomePage`: Renders hero title, subtitle, and primary/secondary CTAs.
5. `MarketingHomePage`: Renders quantitative research capabilities and strategy validation pipeline.
6. `MarketingHomePage`: Renders paper trading telemetry and risk guardrails without real-money claims.
7. `MarketingHomePage`: Renders security by design section and public FAQ.
8. `MarketingHomePage`: Renders final CTA linking to `/register`.
9. `PricingPage`: Renders all canonical pricing tiers directly from shared configuration.
10. `PricingPage`: Displays Enterprise tier as Custom without an invented numerical price.
11. `PricingPage`: Renders detailed quota matrix table with authoritative values.
12. `PricingPage`: Shows Stripe Test Mode notice and simulated execution disclaimers.

### 9.2 Full Frontend Test Suite
- **Command:** `npm test -- --run`
- **Result:**
  - **Test Files:** 22 passed (22/22)
  - **Tests:** 94 passed (94/94)
  - **Failures:** 0

### 9.3 Frontend Production Build
- **Command:** `npm run build` (`tsc && vite build`)
- **Result:** Code 0.
- **Bundle Chunk Isolation:**
  - Initial load of `/` transfers **~77.25 kB gzipped** (~250.46 kB raw JS), well within high-performance web benchmarks.
  - Protected chunks (`DashboardPage`, `ResearchLabPage`, `OptimizationStudioPage`) are completely excluded from initial public visitor payloads.

### 9.4 Backend Regression Test Suite
- **Command:**
  `poetry run pytest tests/unit/apps/trading_engine/test_auth_lifecycle.py tests/integration/apps/trading_engine/test_onboarding_legal.py tests/unit/domain/legal tests/integration/apps/trading_engine/test_legal_routes.py tests/integration/apps/trading_engine/test_rate_limiting.py tests/unit/apps/trading_engine/test_rate_limit_service.py tests/integration/apps/trading_engine/test_phase4_rbac.py tests/security/test_broker_security.py`
- **Result:**
  - **Tests:** 73 passed (73/73)
  - **Failures:** 0

### 9.5 Diff Hygiene
- **Command:** `git diff --check apps/ docs/`
- **Result:** Code 0 (0 trailing whitespace or formatting defects).

---

## 10. File Inventory

### 10.1 Created Files
| Path | Purpose |
| :--- | :--- |
| `apps/dashboard/src/config/pricing.ts` | Shared immutable pricing tiers, quotas, and disclaimers |
| `apps/dashboard/src/components/layout/PublicHeader.tsx` | Public responsive header with navigation and badges |
| `apps/dashboard/src/pages/MarketingHomePage.tsx` | Public marketing landing page with 8 structured sections |
| `apps/dashboard/src/pages/PricingPage.tsx` | Public pricing page with quota matrix and Enterprise modal |
| `apps/dashboard/public/robots.txt` | Crawler policy allowing public routes, disallowing dashboard |
| `apps/dashboard/public/sitemap.xml` | Search engine sitemap for public URLs |
| `apps/dashboard/tests/marketing_pages.test.tsx` | 12 unit and integration tests for marketing and pricing |
| `docs/EPIC-027-PHASE-4C-AUDIT.md` | Architectural pre-implementation audit report |
| `docs/EPIC-027-PHASE-4C-FINAL-VERIFICATION.md` | Final verification audit report |
| `docs/EPIC-027-PHASE-4C-IMPLEMENTATION.md` | This technical implementation report |
| `docs/EPIC-027-PHASE-4C-REMEDIATION.md` | Verification remediation log |

### 10.2 Modified Files
| Path | Modifications |
| :--- | :--- |
| `apps/dashboard/src/App.tsx` | Code splitting (`React.lazy`), Suspense fallback, public `/` and `/pricing`, protected app layout |
| `apps/dashboard/src/pages/BillingPage.tsx` | Refactored to consume shared `PRICING_PLANS` from config |
| `apps/dashboard/src/pages/RegisterPage.tsx` | Corrected password hashing badge from Argon2id to Bcrypt |
| `apps/dashboard/src/components/layout/PublicFooter.tsx` | Enhanced navigation links and platform disclaimers |
| `apps/dashboard/index.html` | Added SEO metadata, Open Graph, Twitter cards |
| `apps/dashboard/tests/auth_lifecycle.test.tsx` | Adjusted async expectations for lazy-loaded route resolution |
| `apps/dashboard/tests/registration.test.tsx` | Adjusted async expectations for lazy-loaded route resolution |

---

## 11. External Dependencies & Operational Requirements

1. **Stripe Test Mode:** Subscriptions remain in Stripe Test Mode. Transition to live billing requires Stripe account activation, webhook endpoint secret configuration, and production API keys.
2. **External Legal Counsel Review:** All legal disclosures (Terms, Privacy, Risk Disclosure, Refund Policy) remain designated "Draft for Legal Review".
3. **Domain & DNS Configuration:** Canonical custom domain assignment is pending production DNS rollout.

---

## 12. Production Readiness Classification

Based on exhaustive automated testing, zero-defect production build, clean diff hygiene, remediation of marketing claims, and strict preservation of safety invariants, EPIC-027 Phase 4C is classified as:

### **`B â€” COMPLETE WITH EXTERNAL DEPENDENCY`**

The implementation is technically complete, fully verified, and ready for release verification.
