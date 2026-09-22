# EPIC-027 Phase 4: Public Marketing Website & Product Presentation — Architectural Audit

**Document Version:** 1.0
**Phase:** EPIC-027 Phase 4A (Audit-Only / No-Code Gate)
**Audit Date:** 2026-09-22
**Baseline Commit:** `0ded05f feat(legal): implement EPIC-027 phase 3 legal trust and risk disclosure`
**Branch:** `main`
**Classification:** **`B — IMPLEMENTATION READY WITH EXTERNAL DEPENDENCIES`**

---

## 1. Executive Summary

This audit assesses the current state of Project ORION’s public-facing web presence and defines the architectural blueprint for **EPIC-027 Phase 4: Public Marketing Website & Product Presentation**.

Project ORION currently functions as an institutional-grade quantitative research, walk-forward strategy optimization, and paper-trading platform. While Phase 1 (Authentication & Account Lifecycle Hardening), Phase 2 (Public API Rate Limiting & Abuse Defense), and Phase 3 (Legal, Trust & Risk Disclosures) are technically complete and verified, **the frontend currently lacks any public marketing website**. An unauthenticated visitor navigating to the platform root (`/`) is immediately redirected to a cold "Trading Terminal Sign In" page (`/login`). Furthermore, while the backend exposes a verified onboarding endpoint (`POST /api/v1/onboarding/register`), the frontend possesses **no user registration page (`/register`) or public pricing page (`/pricing`)**.

The objective of Phase 4 is to create a high-credibility, production-grade marketing presentation and user acquisition funnel without compromising ORION's strict safety invariants: **$0.00 capital at risk, paper-trading simulation only, autonomous worker disabled, live broker connections disabled, and Stripe in Test Mode**.

---

## 2. Current Public Experience

An audit of the current visitor entry point reveals:

1. **Root Route Behavior (`/`):**
   - In `apps/dashboard/src/App.tsx`, route `/` is wrapped in `<ProtectedRoute>`.
   - When an unauthenticated visitor accesses `https://<domain>/`, `ProtectedRoute` intercepts the request and issues a client-side redirect (`<Navigate to="/login" replace />`).
2. **First Impression:**
   - The visitor sees `LoginPage.tsx` ("Trading Terminal Sign In").
   - Headline: `PROJECT ORION — QUANTITATIVE PAPER TRADING PLATFORM`.
   - Subtitle: `Simulated Execution • $0.00 Capital at Risk`.
   - Credentials form: Username, Password, "Authenticate Session" button.
   - Links present: "Forgot password?", "Need to verify your email?", and footer links to legal disclosures.
3. **Key Deficiencies:**
   - **No Explanatory Surface:** Unauthenticated visitors cannot see what the product does, its quantitative capabilities, architecture, research lab, or walk-forward optimization features.
   - **Zero Self-Service Signup Path:** The login page provides no "Create Account" or "Sign Up" link. Visitors have no visual mechanism to register or onboard.
   - **No Pricing Visibility:** Commercial subscription tiers (Sandbox, Pro Trader, Business Prop Desk, Enterprise) are locked behind the authenticated `/billing` route.
   - **Funnel Disconnect:** There is no progression from `Visitor → Learn → Trust → Register → Onboard → Terminal`.

---

## 3. Current Route Map

### Frontend Route Table (`apps/dashboard/src/App.tsx`)

| Route Path | Access Type | Component | Current Purpose |
|---|---|---|---|
| `/` | Protected | `<Navigate to="/dashboard" />` | Root redirect (sends unauthenticated users to `/login`) |
| `/login` | Public | `LoginPage` | User authentication form |
| `/forgot-password` | Public | `ForgotPasswordPage` | Account recovery request form |
| `/reset-password` | Public | `ResetPasswordPage` | Cryptographic password reset form |
| `/verify-email` | Public | `VerifyEmailPage` | Email token verification handler |
| `/terms` | Public | `TermsPage` | Terms of Service disclosure |
| `/privacy` | Public | `PrivacyPage` | Privacy policy & data handling disclosure |
| `/risk-disclosure` | Public | `RiskDisclosurePage` | Paper trading & financial risk disclosure |
| `/refund-policy` | Public | `RefundPolicyPage` | Beta billing refund & cancellation policy |
| `/security` | Public | `SecurityTrustPage` | Technical security architecture disclosure |
| `/dashboard` | Protected | `DashboardPage` | Operational terminal overview |
| `/orders` | Protected | `OrdersPage` | Order book & submission |
| `/positions` | Protected | `PositionsPage` | Open position tracking |
| `/trades` | Protected | `TradesPage` | Trade execution ledger |
| `/portfolio` | Protected | `PortfolioPage` | Equity curve & portfolio metrics |
| `/broker-sandbox` | Protected | `BrokerSandboxPage` | Practice broker credentials |
| `/strategies` | Protected | `StrategiesPage` | Strategy catalogue & parameters |
| `/research` | Protected | `ResearchLabPage` | Strategy lab & backtest experiments |
| `/optimization` | Protected | `OptimizationStudioPage` | Walk-forward optimization & heatmap |
| `/deployments` | Protected | `DeploymentPipelinePage` | Strategy incubation & promotion |
| `/risk` | Protected | `RiskPage` | Risk telemetry & hard limits |
| `/worker` | Protected | `WorkerPage` | Autonomous worker telemetry |
| `/billing` | Protected | `BillingPage` | Commercial billing & subscription plans |
| `/organization` | Protected | `OrganizationPage` | Tenant team & RBAC management |
| `/audit` | Protected | `AuditPage` | System audit trail ledger |
| `*` | Catch-All | `<Navigate to="/dashboard" />` | Wildcard fallback (redirects to login) |

---

## 4. Marketing Website Gap Analysis

| Marketing Element | Status | Required Action for Phase 4 |
|---|---|---|
| **Public Homepage (`/`)** | **MISSING** | Create dedicated landing page at `/` decoupling from `ProtectedRoute`. |
| **Hero Section** | **MISSING** | Develop high-impact institutional dark-theme hero with headline, value proposition, and dual CTAs ("Launch Paper Terminal" / "View Capabilities"). |
| **Product Positioning Banner** | **MISSING** | Prominent safety callout: *Strictly Paper Trading / $0.00 Capital at Risk*. |
| **Quantitative Features Showcase** | **MISSING** | Showcase Research Lab, Walk-Forward Optimizer, Risk Engine, and Sandbox Execution. |
| **Live Interactive / Visual Mockups** | **MISSING** | Component-level simulated terminal preview or feature cards illustrating tearsheets and heatmaps. |
| **Workflow Explanation** | **MISSING** | 4-step quantitative lifecycle: *Formulate Strategy → Walk-Forward Validation → Quality Gate Pass → Paper Execution*. |
| **Public Pricing Page (`/pricing`)** | **MISSING** | Expose public plan comparison grid (Free, Pro, Business, Enterprise) derived from `BillingPage.tsx`. |
| **Public Registration (`/register`)** | **MISSING** | Implement self-service onboarding interface integrating `POST /api/v1/onboarding/register` with mandatory Phase 3 consent checkboxes. |
| **FAQ Section** | **MISSING** | Address platform nature, paper trading reality, broker sandbox differences, and subscription mechanics. |
| **Contact / Inquiries Entry** | **MISSING** | Institutional inquiry / enterprise demo request form or designated contact card. |
| **Public Header Navigation** | **MISSING** | Sticky header with links to Features, Research, Pricing, Security, Docs/Legal, and Sign In / Register buttons. |
| **Public Footer** | **PARTIAL** | `PublicFooter.tsx` exists; expand to include marketing sitemap, product links, and copyright notices. |

---

## 5. Product Positioning Audit

Audit of specific marketing terminology across existing copy and public presentation:

| Term | Context in ORION | Classification | Audit Assessment & Copy Guidelines |
|---|---|---|---|
| **"Institutional"** | Used in platform title and plan tiers ("Enterprise Institutional"). | **B. Needs Qualification** | Must be qualified as *"Institutional-Grade Quantitative Software Architecture"*. Must NOT imply ORION is an institutional bank, prime broker, or asset management firm. |
| **"AI"** | Used in Strategy Lab (LLM strategy code generator). | **A. Supported Fact** | Factual capability (integrates with Anthropic/OpenAI code generation models for algorithmic syntax). Describe strictly as code generation and analysis assistance. |
| **"Trading"** | Used across terminal. | **B. Needs Qualification** | Must always be qualified as *"Simulated Paper Trading"* or *"Paper Execution"*. Never describe as live interbank trading. |
| **"Forex"** | Used across market quotes (EUR/USD, GBP/USD, etc.). | **A. Supported Fact** | Factual capability: platform matches orders against simulated major foreign exchange pairs. |
| **"Quantitative"** | Used in analytical metrics. | **A. Supported Fact** | Factual capability: Sharpe ratio, Sortino ratio, max drawdown, Calmar ratio, parametric slippage modeling. |
| **"Research"** | Strategy Lab & Backtesting. | **A. Supported Fact** | Factual capability: historical experiment simulation, parameter sweeps, and tearsheet generation. |
| **"Backtesting"** | Experiment execution. | **A. Supported Fact** | Factual capability: deterministic tick/candle simulation. |
| **"Paper Trading"** | Execution matching engine. | **A. Supported Fact** | Core architectural invariant: $0.00 capital at risk, virtual demo balances. |
| **"Automation"** | Autonomous background worker. | **B. Needs Qualification** | Worker architecture exists in code, but is currently configured as **DISABLED** (`ORION_WORKER_ENABLED=false`). Marketing copy must explicitly describe automation as available in simulated environments and subject to operational limits. |
| **"Profit" / "Returns"** | Strategy metrics. | **C. Potentially Misleading** | Must NEVER be promised or forecasted. Must always be accompanied by the mandatory hypothetical performance warning: *"Simulated or historical performance does not guarantee future results."* |
| **"Prediction"** | Algorithmic forecasting. | **C. Potentially Misleading** | Prohibited in marketing copy. Do not claim predictive certainty or "guaranteed edge". |
| **"Guaranteed"** | Quality gate pass. | **C. Potentially Misleading** | Prohibited. Passing a research Quality Gate indicates mathematical consistency under test conditions, never guaranteed performance. |
| **"Risk-free"** | Virtual paper execution. | **B. Needs Qualification** | While financial capital at risk is $0.00, trading involves cognitive and operational learning curves. Avoid blanket "risk-free" claims outside the factual statement: *"No financial capital at risk in simulated mode."* |
| **"Investment Advice"** | Platform output. | **D. Requires Legal Review** | Strictly disclaimed: ORION provides quantitative software tools, not personalized investment, legal, tax, or financial advice. |
| **"Broker"** | OANDA practice sandbox. | **D. Requires Legal Review** | Strictly disclaimed: ORION is a software developer, not a registered broker-dealer, introducing broker, or custodian. |
| **"Regulated"** | Platform governance. | **D. Requires Legal Review** | Strictly disclaimed: ORION is not registered with the SEC, CFTC, FINRA, FCA, or NFA. |
| **"Certification"** | Security controls. | **D. Requires Legal Review** | Strictly disclaimed: System controls are implemented, but formal third-party SOC 2, ISO 27001, or PCI DSS certifications are pending external audit. |

---

## 6. Legal & Claim Safety Audit

1. **CFTC Rule 4.41:**
   - Cites hypothetical performance disclaimer standards common to algorithmic trading software.
   - *Status:* **LEGAL CLAIM REQUIRING EXTERNAL COUNSEL**. The text should be presented as an industry-standard quantitative disclosure, with formal legal determination of whether Rule 4.41 statutory compliance applies to ORION reserved for external counsel.
2. **Draft Notice Invariant:**
   - Every legal page and link must maintain its *"Draft for legal review"* indicator until external counsel completes formal sign-off.
3. **No Fabricated Business Details:**
   - Marketing text must NOT invent fictitious office locations, registered corporate entities, regulatory license numbers, or partner broker endorsements.
4. **Discretionary Refund Policy:**
   - Marketing website must state that during Public Beta, all billing runs through Stripe Test Mode with $0.00 actual charges, and commercial policies remain subject to final approval.

---

## 7. Privacy & Cookie Audit

1. **Zero Cookie Tracking:**
   - The platform uses **no tracking cookies, no third-party marketing pixels, and no analytics beacons**.
   - Review of `package.json` confirms zero analytics SDKs (no Google Analytics, Mixpanel, Segment, or Facebook Pixel).
2. **Storage Audit:**
   - `localStorage`: Not used.
   - `sessionStorage`: Used strictly for ephemeral authentication session keys (`orion_access_token`, `orion_active_org_id`). Destroyed on tab close or logout.
3. **Cookie Banner Necessity:**
   - **No cookie banner is required or recommended.** Introducing an unneeded cookie consent banner would be misleading because no tracking cookies exist. Transparent disclosure in the Privacy Policy is the correct privacy-by-design approach.

---

## 8. SEO Audit

| SEO Element | Current State | Defect / Gap | Required Phase 4 Enhancement |
|---|---|---|---|
| **Document Title** | Static in `index.html` (`Project ORION — Institutional Trading Platform (Paper Mode)`) | Does not change dynamically per route. | Implement dynamic route title manager (e.g. `Project ORION | Quantitative Paper Trading Architecture`). |
| **Meta Description** | **MISSING** in `index.html` | Search engines generate arbitrary snippets. | Add informative, safety-first meta description emphasizing simulated paper trading and quantitative research. |
| **Canonical URL** | **MISSING** | Potential duplicate content indexing. | Add dynamic or configurable `<link rel="canonical">`. Requires external domain configuration. |
| **Robots Meta Tag** | **MISSING** | Uncontrolled search crawling. | Add `<meta name="robots" content="index, follow">` on public pages; `noindex, nofollow` on authenticated portal routes. |
| **Open Graph (OG)** | **MISSING** | Links shared on social channels (Slack, X, LinkedIn) render no preview. | Add `og:title`, `og:description`, `og:image`, `og:type`, `og:url`. |
| **Twitter / X Card** | **MISSING** | No formatted card preview. | Add `twitter:card` (`summary_large_image`), `twitter:title`, `twitter:description`, `twitter:image`. |
| **Favicon** | Inline SVG data URI in `index.html` | Works in modern browsers, but lacks standard multi-resolution `.ico` and `apple-touch-icon`. | Add dedicated favicon assets. |
| **Sitemap (`sitemap.xml`)** | **MISSING** | Crawlers must discover pages by link traversal alone. | Provide static or dynamically served `sitemap.xml` listing public marketing and legal routes. |
| **Robots File (`robots.txt`)** | **MISSING** | Web crawlers receive default 404/index fallback. | Provide `robots.txt` allowing public routes and disallowing `/dashboard/*`, `/api/*`. |
| **Structured Data** | **MISSING** | No rich search snippet integration. | Add JSON-LD `SoftwareApplication` schema describing ORION as Financial Simulation Software. |

---

## 9. Accessibility Audit (WCAG 2.1 AA)

1. **Color Contrast:**
   - Dark theme palette (`#090d16` background, `#f8fafc` text, `#94a3b8` muted text) achieves contrast ratios exceeding 7:1 for body copy and 4.5:1 for muted text, compliant with WCAG AA standards.
2. **Keyboard Navigation & Focus:**
   - High-contrast focus rings configured in `src/index.css`: `:focus-visible { outline: 2px solid var(--color-brand-light); outline-offset: 2px; }`.
   - All interactive elements must use native `<button>` or `<Link>` elements rather than clickable `<div>` elements.
3. **Screen Readers & ARIA:**
   - Form inputs on login and future registration pages require associated `<label>` elements with `htmlFor` matching input `id`.
   - Modals and mobile menus require `aria-modal="true"`, `aria-expanded`, and focus trap management.
   - Screen-reader text (`sr-only`) required for icon-only action buttons.
4. **Reduced Motion:**
   - Ensure subtle animations (e.g. pulse badges, glows) respect `@media (prefers-reduced-motion: reduce)`.

---

## 10. Responsive Design Audit

1. **Breakpoints Supported:**
   - Tailwind/CSS standard breakpoints: Mobile (`<640px`), Tablet (`640px–1024px`), Desktop (`>1024px`), Large Desktop (`>1280px`).
2. **Current Responsive Patterns:**
   - `PublicFooter.tsx` and `LegalPageLayout.tsx` already utilize flex-col on mobile and flex-row on desktop.
3. **Marketing Website Responsive Requirements:**
   - **Header:** Sticky desktop navigation bar must collapse into a mobile hamburger menu on viewports `<768px`.
   - **Hero:** Text typography must scale fluidly (`text-3xl sm:text-5xl lg:text-6xl`).
   - **Feature Grid:** 1-column layout on mobile, 2-column on tablet, 3-column or 4-column on desktop.
   - **Pricing Table:** Vertical stack on mobile; side-by-side comparison grid on desktop with active tier highlighted.

---

## 11. Performance & Bundle Audit

1. **Bundle Structure:**
   - Current production build: `dist/assets/index-Qu7wq2OM.js` is **525.68 kB** (minified, ~125 kB gzip).
   - Currently, all 24 authenticated dashboard pages (`OptimizationStudioPage`, `ResearchLabPage`, `DeploymentPipelinePage`, etc.) are statically imported into `App.tsx`.
2. **Code-Splitting Requirement:**
   - **Crucial Recommendation:** The marketing homepage and public pages must be code-split using `React.lazy()` and `Suspense`.
   - An unauthenticated visitor landing on the marketing homepage should only download the lightweight marketing bundle (~30–45 kB), preserving near-instant First Contentful Paint (FCP) and Largest Contentful Paint (LCP) under 1.2s.
   - Heavy quantitative dashboard components should only load when the user authenticates and enters `/dashboard`.
3. **CSS Strategy:**
   - `src/index.css` is currently **1.50 kB**, utilizing lightweight CSS variables. No heavy utility bloat exists. Adding marketing component styles will introduce negligible overhead (<5 kB).

---

## 12. Security Audit

The marketing website architecture must strictly enforce defense-in-depth:

1. **XSS Mitigation:**
   - All dynamic text rendered through React JSX; no `dangerouslySetInnerHTML`.
   - Markdown documents are compiled into static React elements or sanitized.
2. **CSP & Security Headers:**
   - Nginx reverse proxy configuration (`apps/dashboard/nginx.conf`) enforces strict headers:
     - `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' http: https: ws: wss:; font-src 'self'; frame-ancestors 'none';`
     - `X-Frame-Options: DENY` (anti-clickjacking)
     - `X-Content-Type-Options: nosniff`
     - `Referrer-Policy: strict-origin-when-cross-origin`
3. **No Third-Party Scripts:**
   - No external tag managers, ad pixels, or external CDNs. All assets bundled self-contained.
4. **Form Security:**
   - Public inquiry or signup forms must submit via JSON API over HTTPS with strict input validation, sanitized error rendering, and Phase 2 rate limiting.

---

## 13. Billing & Pricing Audit

1. **Current Commercial Tiers (derived from `BillingPage.tsx`):**
   - **Free Sandbox ($0/month):** 1 Paper Trading Account, 100 Daily Orders, 0 Autonomous Workers, 4 Major FX Pairs, 30-Day Retention.
   - **Pro Trader ($99/month):** 3 Paper Accounts, 2,500 Daily Orders, 1 Worker Entitled, 12 Liquid FX Pairs, 365-Day Retention, Email Notifications.
   - **Business Prop Desk ($299/month):** 10 Paper Accounts, 50,000 Daily Orders, 5 Workers Entitled, All FX Pairs, 5-Year Retention, Priority SRE Support SLA.
   - **Enterprise Institutional (Custom):** Unlimited Accounts & Orders, Unlimited Workers, All Asset Classes (*), Long-term Audit Log Retention (subject to data agreement), Dedicated SRE Manager.
2. **Public Presentation Boundaries:**
   - The pricing page can safely be made public.
   - Disclaimers must be prominently displayed:
     - *All subscription billing operates strictly through Stripe Test Mode during Public Beta.*
     - *No real monetary charges are incurred in Test Mode.*
     - *Self-service subscription cancellation is accessible at any time.*
3. **CTA Navigation:**
   - CTAs on the public pricing page must direct unauthenticated visitors to `/register?plan={code}`, NOT directly to Stripe checkout. Stripe checkout requires an authenticated tenant session and is initiated from `/billing` after account creation.

---

## 14. Signup & Onboarding Audit

1. **Backend Registration Readiness:**
   - Endpoint: `POST /api/v1/onboarding/register` (in `apps/trading-engine/src/routes/onboarding.py`).
   - Request DTO: `OnboardingRegisterRequest`:
     - `username: str` (min length 3, max length 50)
     - `email: EmailStr`
     - `password: str` (enforced by Phase 1 strength policy: min 12 chars, upper, lower, digit, symbol)
     - `organization_name: str` (min length 2, max length 100)
     - `organization_slug: str | None`
     - `terms_accepted: bool` (mandatory: `true`)
     - `privacy_acknowledged: bool` (mandatory: `true`)
     - `risk_disclosure_acknowledged: bool` (mandatory: `true`)
   - Returns: `OnboardingRegisterResponse` containing user profile, organization details, and JWT `access_token`.
2. **Frontend Onboarding Gap:**
   - **Missing Page:** `/register` does not exist in `apps/dashboard/src/pages/`.
   - **Missing Client Method:** `endpoints.ts` has no `onboardingApi.register()` wrapper.
   - **Missing Types:** `types.ts` has no `OnboardingRegisterRequest` interface.
3. **Required Implementation for Phase 4:**
   - Implement `RegisterPage.tsx` with a multi-step or unified form:
     - Organization / Desk Name
     - Trader Username & Email
     - Secure Password with live strength meter
     - 3 Mandatory Phase 3 Checkboxes (Terms, Privacy, Risk Disclosure) with clickable modal or new-tab links
   - On success: automatically set JWT session token and redirect into `/dashboard`.

---

## 15. Trust & Security Presentation Audit

Factual security controls that can be transparently highlighted on the marketing website:

| Implemented Engineering Control | Factual Marketing Statement |
|---|---|
| **Stateless JWT with Password Revocation** | Cryptographically signed HMAC-SHA256 tokens instantly invalidated upon password modification. |
| **Bcrypt Password Protection** | Strong adaptive hashing with per-user cryptographic salts; zero plaintext storage. |
| **Phase 2 Sliding-Window Abuse Defense** | Atomic Redis rate limiting protecting public API endpoints against automated brute-force attacks. |
| **Multi-Tenant SQL Isolation** | Strict organizational boundary enforcement on every database query, preventing horizontal IDOR. |
| **AES-256-GCM Broker Key Encryption** | Practice broker sandbox API credentials encrypted at rest with authenticated GCM ciphers. |
| **Append-Only Compliance Audit Trail** | Immutable database logging of all administrative, billing, and legal consent actions. |
| **Zero Tracking Cookies** | Privacy-by-design architecture with zero advertising cookies or cross-site behavioral trackers. |
| **Paper-Only Execution Safety** | Architectural barrier ensuring zero live execution facilities and $0.00 capital risk. |

**Prohibited Marketing Claims:**
- Do NOT claim SOC 2 certification.
- Do NOT claim ISO 27001 certification.
- Do NOT claim PCI DSS level 1 compliance (card handling is delegated to Stripe).
- Do NOT claim formal regulatory authorization (SEC, CFTC, FCA, FINRA, SEBI).

---

## 16. Existing Marketing Asset Inventory

1. **Design Tokens & Theme:**
   - Backgrounds: `#090d16` (Deep Dark), `#0f172a` (Slate 900), `#141e33` (Card Dark), `#1a2742` (Card Hover).
   - Accents: `#0284c7` (Brand Blue), `#38bdf8` (Brand Light), `#10b981` (Profit Emerald), `#f59e0b` (Warning Amber), `#f43f5e` (Loss Rose).
   - Typography: `Inter` (sans-serif) for body and headings; `JetBrains Mono` (monospace) for quantitative numbers, badges, and terminal labels.
2. **Brand Icon / Mark:**
   - Greek Omega symbol: `Ω` rendered in square rounded container (`bg-sky-500/10 border border-sky-500/30 text-sky-400 font-bold font-mono`).
3. **Reusable Design Components:**
   - `Button`: Primary, secondary, outline, danger, ghost variants with loading states.
   - `Badge` & `PaperTradingBadge`: Status indicators for live paper status.
   - `Card` & `MetricCard`: Containers for quantitative metrics.
   - `PublicFooter`: Baseline legal links.
   - `LegalPageLayout`: Structured document viewer.
4. **Icons:**
   - Over 400 icons available via `lucide-react` (e.g. `Cpu`, `Activity`, `ShieldCheck`, `TrendingUp`, `BarChart3`, `Database`, `Sliders`, `Lock`, `RefreshCw`).

---

## 17. Testing Gap Analysis

1. **Current Test Suite:**
   - 20 Vitest test files in `apps/dashboard/tests/` (67 tests, 100% pass).
2. **Required Tests for Phase 4:**
   - `tests/marketing_homepage.test.tsx`: Verify rendering of Hero, Feature cards, Workflow section, Trust section, and CTAs.
   - `tests/marketing_navigation.test.tsx`: Verify public header, mobile drawer toggle, and links to `/pricing`, `/login`, `/register`, and legal pages.
   - `tests/public_pricing.test.tsx`: Verify rendering of 4 plan tiers, feature lists, test-mode disclaimers, and CTA navigation.
   - `tests/registration_flow.test.tsx`: Verify `/register` form rendering, password strength validation, mandatory Phase 3 consent checkbox validation, error handling, and API integration.
   - `tests/route_decoupling.test.tsx`: Verify unauthenticated visitors can view `/`, `/pricing`, `/register`, and legal pages without being redirected to `/login`.

---

## 18. Render Deployment Audit

1. **Configuration (`render.yaml`):**
   - Service name: `orion-dashboard`.
   - Environment: Docker (`apps/dashboard/Dockerfile`).
   - Health check path: `/`.
   - Environment variable: `VITE_API_URL` pointing to backend `orion-api`.
2. **Nginx Runtime (`apps/dashboard/nginx.conf`):**
   - `try_files $uri $uri/ /index.html;` ensures seamless client-side routing for newly added public paths (`/`, `/pricing`, `/register`).
   - Gzip compression active for text, CSS, JavaScript, and SVG.
   - Hashed assets (`/assets/`) cached for 1 year (`max-age=31536000, immutable`).
3. **Custom Domain Readiness:**
   - Render supports attaching custom domains with automated TLS certificates.
   - Updating custom domain will require updating `ORION_CORS_ORIGINS` in `render.yaml` to authorize API cross-origin requests.

---

## 19. Phase 4 Architecture Recommendation

To deliver an institutional-grade public marketing website without degrading the trading terminal's security or performance:

1. **Decouple App Routing:**
   - Reconfigure `App.tsx` so `/` renders the `LandingPage` component.
   - Protect dashboard routes under `/app/*` or preserve explicit paths (`/dashboard`, `/orders`, etc.) behind `<ProtectedRoute>`.
2. **Implement Code Splitting (`React.lazy`):**
   - Lazy-load the marketing pages (`LandingPage`, `PricingPage`, `RegisterPage`) and dashboard pages.
   - Wrap routes in `<Suspense fallback={<PageLoadingSpinner />}>`.
3. **Introduce a Shared Public Layout (`PublicLayout.tsx`):**
   - Persistent top navigation bar (Logo, Product, Architecture, Pricing, Security, Docs, Sign In, Register CTA).
   - Persistent footer (`PublicFooter.tsx` enhanced with product sitemap).
4. **Build Dedicated Onboarding Flow (`RegisterPage.tsx`):**
   - Connect to `POST /api/v1/onboarding/register`.
   - Enforce mandatory Phase 3 consent checkboxes for legal adherence.

---

## 20. Proposed Public Route Map

| Proposed Route | Page Component | Access | Description |
|---|---|---|---|
| `/` | `LandingPage` | Public | Comprehensive marketing homepage with hero, quantitative features, workflow, trust, and CTAs |
| `/pricing` | `PricingPage` | Public | Commercial plan comparison, quota limits, test-mode disclaimers, and registration CTAs |
| `/register` | `RegisterPage` | Public | Institutional onboarding registration form with Phase 3 legal consent checkboxes |
| `/login` | `LoginPage` | Public | Terminal session sign-in (enhanced with "Create Account" link) |
| `/forgot-password` | `ForgotPasswordPage` | Public | Password reset request |
| `/reset-password` | `ResetPasswordPage` | Public | Password reset completion |
| `/verify-email` | `VerifyEmailPage` | Public | Email verification handler |
| `/terms` | `TermsPage` | Public | Terms of Service disclosure |
| `/privacy` | `PrivacyPage` | Public | Privacy policy & ephemeral storage disclosure |
| `/risk-disclosure` | `RiskDisclosurePage` | Public | Paper trading & CFTC 4.41 hypothetical performance disclosure |
| `/refund-policy` | `RefundPolicyPage` | Public | Beta billing refund & cancellation policy |
| `/security` | `SecurityTrustPage` | Public | Technical security & trust architecture disclosure |
| `/dashboard` | `DashboardPage` | Protected | Authenticated trading terminal overview |
| `/app/*` (or existing routes) | App Pages | Protected | All 15 existing trading engine feature pages |

---

## 21. Proposed Homepage Information Architecture

A structured, 8-section layout optimized for credibility and conversion:

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Public Top Navigation Bar                                    │
│    [Ω PROJECT ORION]   Features  Architecture  Pricing  Security│
│                        Sign In [Launch Paper Terminal]          │
├─────────────────────────────────────────────────────────────────┤
│ 2. Hero Section                                                 │
│    "Institutional Quantitative Paper Trading Architecture"      │
│    Headline • Subtitle • [Start Free Sandbox] [Explore Terminal]│
│    Persistent Safety Callout: Strict Paper Mode • $0 Capital    │
├─────────────────────────────────────────────────────────────────┤
│ 3. Quantitative Capability Highlights (4 Core Pillars)         │
│    • Strategy Research Lab (Deterministic Python Backtests)     │
│    • Walk-Forward Optimization Studio (Overfitting Defense)     │
│    • Hard Risk Guardrails (Drawdown & Exposure Circuit Breakers)│
│    • Paper Execution Engine (Gaussian Slippage & Spread Modeling│
├─────────────────────────────────────────────────────────────────┤
│ 4. Algorithmic Lifecycle Workflow (4-Step Visual Flow)          │
│    [Formulate Model] → [Walk-Forward Test] → [Quality Gate Pass]│
│    → [Paper Matching Engine]                                    │
├─────────────────────────────────────────────────────────────────┤
│ 5. Technical Architecture & Trust Highlights                    │
│    AES-256 Broker Encryption • Redis Sliding-Window Rate Limits │
│    Multi-Tenant IDOR Isolation • Immutable Audit Trail          │
├─────────────────────────────────────────────────────────────────┤
│ 6. Public Pricing Snapshot (4 Tiers)                           │
│    Sandbox ($0) | Pro ($99) | Business ($299) | Enterprise      │
│    Stripe Test Mode Notice • Clear Quota Breakdown              │
├─────────────────────────────────────────────────────────────────┤
│ 7. Frequently Asked Questions (FAQ Accordion)                   │
│    Paper trading reality • Data retention • Broker sandboxes    │
├─────────────────────────────────────────────────────────────────┤
│ 8. Call to Action & Public Legal Footer                         │
│    "Deploy Your First Quantitative Model in Simulated Mode"     │
│    [Create Sandbox Account]                                     │
│    Full Legal Links • Terms • Privacy • Risk • Security         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 22. Required Components to Implement in Phase 4

1. `apps/dashboard/src/components/layout/PublicHeader.tsx`: Public navigation bar with responsive mobile menu.
2. `apps/dashboard/src/components/layout/PublicLayout.tsx`: Shell wrapping `PublicHeader`, main content area, and `PublicFooter`.
3. `apps/dashboard/src/pages/LandingPage.tsx`: Full marketing homepage containing Hero, Pillars, Workflow, Security, Pricing Preview, and FAQ.
4. `apps/dashboard/src/pages/PricingPage.tsx`: Standalone public pricing comparison page.
5. `apps/dashboard/src/pages/RegisterPage.tsx`: Self-service onboarding page with legal consent checkboxes.
6. `apps/dashboard/src/api/endpoints.ts` update: Add `onboardingApi.register()` endpoint caller.
7. `apps/dashboard/src/api/types.ts` update: Add `OnboardingRegisterRequest` and `OnboardingRegisterResponse` types.

---

## 23. External Dependencies & Configuration

The following items are external dependencies that cannot be invented by code and must be configured or confirmed:

1. **Production Domain Name:** Required for canonical SEO URLs, Open Graph `og:url`, and sitemap generation (defaulting to Render hostname or placeholder if unspecified).
2. **Official Support / Inquiries Email:** Required for contact and enterprise inquiry references (e.g. `support@project-orion.example.com` or custom).
3. **Formal Corporate Entity & Jurisdiction:** Remains subject to external legal counsel review as noted in Phase 3.
4. **Stripe Production Activation:** Currently operates in Stripe Test Mode. Transitioning to live monetary transactions requires business formation, merchant underwriting, and bank account linkage.

---

## 24. Risks & Mitigations

| Risk | Severity | Mitigation Strategy |
|---|---|---|
| **Misleading Visitor Expectations** | High | Prominent, persistent callouts across Hero, Pricing, and Footer that ORION operates in **Paper Trading Mode only with $0.00 capital at risk**. |
| **Performance Degradation of Terminal** | Medium | Implement `React.lazy()` code-splitting. Marketing assets are segregated into independent bundle chunks; authenticated dashboard performance is unaffected. |
| **Registration Consent Bypass** | Critical | Server-side validation already in place (`HTTP 422`). Frontend `RegisterPage` will enforce matching client-side checkbox validation before dispatch. |
| **SEO Indexing of Sensitive Pages** | Medium | Configure `robots.txt` and meta tags to disallow crawling of authenticated routes (`/dashboard/*`, `/api/*`). |
| **XSS from Dynamic Content** | Low | No `dangerouslySetInnerHTML`; all marketing and FAQ text rendered via typed React components. |

---

## 25. Blockers

- **Zero Technical Blockers:** The backend API, database schemas, migration 0014, rate limiting, and frontend build tooling are 100% operational and ready to support Phase 4 frontend implementation.
- **External Non-Technical Blockers:** Formal external legal counsel review of prose remains pending (Class B).

---

## 26. Recommended Implementation Phases

```
Phase 4A: Architectural Audit (CURRENT — COMPLETED)
  └─ Audit current public experience, routes, assets, SEO, positioning, and safety constraints.

Phase 4B: Client API & Registration Onboarding
  ├─ Add TypeScript interfaces (`OnboardingRegisterRequest`) in `types.ts`.
  ├─ Add `onboardingApi.register()` in `endpoints.ts`.
  ├─ Implement `RegisterPage.tsx` with Phase 3 consent enforcement.
  └─ Add "Sign Up" links to `LoginPage.tsx`.

Phase 4C: Public Marketing Website & Pricing
  ├─ Implement `PublicHeader.tsx` (responsive desktop & mobile drawer).
  ├─ Implement `LandingPage.tsx` (Hero, Quantitative Pillars, Workflow, Trust, FAQ).
  ├─ Implement `PricingPage.tsx` (Public tier comparison with test-mode notices).
  └─ Decouple `/` route in `App.tsx` and configure `React.lazy()` code splitting.

Phase 4D: SEO, Assets & Final Quality Gate
  ├─ Update `index.html` with meta tags, Open Graph, Twitter cards, and JSON-LD schema.
  ├─ Create `robots.txt` and `sitemap.xml`.
  ├─ Write comprehensive Vitest test suite (`marketing_pages.test.tsx`, `registration.test.tsx`).
  └─ Run full verification: `tsc && vite build`, `vitest run`, Python backend tests, and secret scan.
```

---

## 27. Verification Strategy

1. **Automated Unit & Integration Tests (Vitest):**
   - Marketing homepage renders all sections and disclaimers.
   - Public header navigates to sections and routes.
   - Registration form enforces password strength and rejects unchecked legal checkboxes.
   - Public pricing page renders 4 tiers and routes CTAs to `/register`.
2. **Bundle & Build Verification:**
   - `npm run build` (`tsc && vite build`) executes cleanly with zero TypeScript errors.
   - Verify code splitting produces separate chunks for marketing and dashboard pages.
3. **Backend Regression Testing:**
   - Rerun all 88 Python unit, integration, and security tests to confirm zero backend regressions.
4. **Manual Responsive Check:**
   - Test navigation, tables, and forms across mobile (375px), tablet (768px), and desktop (1440px) viewports.

---

## 28. Final Classification

```
======================================================================
CLASSIFICATION: B — IMPLEMENTATION READY WITH EXTERNAL DEPENDENCIES
======================================================================
Technical Architecture:      100% READY FOR IMPLEMENTATION
Backend API & Onboarding:    100% READY (Validated & tested)
Safety Invariants:           PRESERVED ($0 Capital, Paper Only)
External Dependencies:       Domain name, support email, external legal counsel
======================================================================
```
