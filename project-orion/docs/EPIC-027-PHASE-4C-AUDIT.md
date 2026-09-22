# EPIC-027 Phase 4C: Public Marketing Website & Pricing â€” Architectural Audit

**Document Version:** 1.0
**Phase:** EPIC-027 Phase 4C (Audit-Only / No-Code Gate)
**Audit Date:** 2026-09-23
**Auditor Roles:** Principal Software Architect, Product UX Architect, Application Security Engineer, SEO Engineer, QA Lead, Release Gatekeeper
**Baseline Commit:** `c9da2a7 feat(onboarding): implement EPIC-027 phase 4B registration funnel`
**Classification:** **`B â€” READY WITH EXTERNAL DEPENDENCIES`**

---

## 1. Executive Summary

This audit assesses the readiness of Project ORION for **EPIC-027 Phase 4C: Public Marketing Website & Pricing**.

Project ORION currently operates as an institutional-grade quantitative research, walk-forward strategy optimization, and simulated paper-trading platform. With the completion of Phase 1 (Authentication & Account Lifecycle), Phase 2 (Public API Rate Limiting), Phase 3 (Legal, Trust & Risk Disclosures), and Phase 4B (Self-Service Registration Funnel), the backend provisioning, legal assent registry, and client-side onboarding flow are verified and operational.

However, **an unauthenticated visitor navigating to the platform root (`/`) is currently intercepted by `<ProtectedRoute>` and redirected to the login page (`/login`)**. There is no public marketing homepage, no visual product presentation, no public navigation header, and no public pricing page (`/pricing`). Commercial subscription tiers are accessible only to authenticated users via `/billing`.

Phase 4C will transform the public experience into a high-credibility, production-grade presentation of Project ORIONâ€™s quantitative research and simulated trading capabilities without compromising its strict safety invariants: **$0.00 capital at risk, paper-trading simulation only, autonomous worker disabled, live broker connections disabled, and Stripe in Test Mode**.

---

## 2. Baseline Commit & Repository Safety

- **Current HEAD:** `c9da2a75e937442f9a78715c408a4b013c5ddf72` (`c9da2a7`)
- **Commit Message:** `feat(onboarding): implement EPIC-027 phase 4B registration funnel`
- **Branch:** `main` (synchronized with `origin/main` at `c9da2a75e937442f9a78715c408a4b013c5ddf72`)
- **Previous Commits:**
  - `0ded05f feat(legal): implement EPIC-027 phase 3 legal trust and risk disclosure`
  - `405ce08 feat(security): implement EPIC-027 public API rate limiting`
  - `a8dcb21 feat(broker): implement EPIC-026 institutional broker sandbox & demo broker integration`
- **Working Tree State:** In `project-orion`, the working tree is 100% clean. Zero uncommitted changes, zero untracked files, zero modified files.
- **Parent Repository Artifacts:** Legacy parent-level artifacts from prior monorepo sprints (`../.coverage`, `../FINAL_QUALITY_GATE_REPORT.md`, `../TODO.md`, `../.continue/`, scratch scripts) remain untouched and strictly excluded.
- **Audit Rule:** No source code, tests, package dependencies, or configurations were modified during this audit.

---

## 3. Git Status Evidence

```text
$ git status --short
 M ../.coverage
 M ../FINAL_QUALITY_GATE_REPORT.md
 M ../TODO.md
 (project-orion working tree: completely clean)

$ git branch --show-current
main

$ git log -3 --oneline
c9da2a7 feat(onboarding): implement EPIC-027 phase 4B registration funnel
0ded05f feat(legal): implement EPIC-027 phase 3 legal trust and risk disclosure
405ce08 feat(security): implement EPIC-027 public API rate limiting

$ git rev-parse HEAD
c9da2a75e937442f9a78715c408a4b013c5ddf72

$ git rev-parse origin/main
c9da2a75e937442f9a78715c408a4b013c5ddf72
```

---

## 4. Existing Public Route Audit

Audited authoritative routing in [`apps/dashboard/src/App.tsx`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/dashboard/src/App.tsx):

| Route Path | Type | Component | Current Behavior |
|---|---|---|---|
| `/` | Protected Layout | `<ProtectedRoute><AppShell /></ProtectedRoute>` | Unauthenticated visitors are intercepted and redirected to `/login` |
| `/login` | Public | `LoginPage` | Authentication credentials form |
| `/register` | Public | `RegisterPage` | Self-service registration & onboarding funnel (Phase 4B) |
| `/forgot-password` | Public | `ForgotPasswordPage` | Account recovery request form (Phase 1) |
| `/reset-password` | Public | `ResetPasswordPage` | Cryptographic password reset form (Phase 1) |
| `/verify-email` | Public | `VerifyEmailPage` | Email token verification handler (Phase 1) |
| `/terms` | Public | `TermsPage` | Terms of Service disclosure (Phase 3) |
| `/privacy` | Public | `PrivacyPage` | Privacy policy & data handling disclosure (Phase 3) |
| `/risk-disclosure` | Public | `RiskDisclosurePage` | Paper trading & financial risk disclosure (Phase 3) |
| `/refund-policy` | Public | `RefundPolicyPage` | Beta billing refund & cancellation policy (Phase 3) |
| `/security` | Public | `SecurityTrustPage` | Technical security architecture disclosure (Phase 3) |
| `/dashboard` ... `/audit` | Protected | Dashboard pages (15 routes) | Authenticated trading terminal views |
| `*` (Wildcard) | Redirect | `<Navigate to="/dashboard" replace />` | Unauthenticated visitors redirect to `/login` via `<ProtectedRoute>` |

### What Happens When a Visitor Opens `/`
In `App.tsx` (lines 49â€“57):
```tsx
<Route
  path="/"
  element={
    <ProtectedRoute>
      <AppShell />
    </ProtectedRoute>
  }
>
  <Route index element={<Navigate to="/dashboard" replace />} />
```
In `ProtectedRoute.tsx` (lines 20â€“26):
```tsx
if (!isAuthenticated) {
  if (location.pathname === '/login') {
    return <>{children}</>;
  }
  return <Navigate to="/login" state={{ from: location }} replace />;
}
```
**Conclusion:** Opening `/` issues an immediate client-side redirect to `/login`. A public visitor never sees an explanatory landing page.

---

## 5. Authentication Boundary

Audited [`apps/dashboard/src/auth/ProtectedRoute.tsx`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/dashboard/src/auth/ProtectedRoute.tsx) and [`apps/dashboard/src/auth/AuthContext.tsx`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/dashboard/src/auth/AuthContext.tsx):

- **Unauthenticated Handling:** `isAuthenticated` is evaluated from `!!token && !!user`. If false, `ProtectedRoute` redirects to `/login`.
- **Public Routes:** Declared at the top level of `<Routes>` outside `<ProtectedRoute>`. They render cleanly without triggering auth verification or redirect loops.
- **Architectural Requirement for Phase 4C:**
  - Route `/` must be reclaimed as a public route rendering `MarketingHomePage`.
  - Protected dashboard routes must be nested under a pathless layout route (`<Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>`) or under an explicit prefix (e.g., `/app/*`).
  - Using a pathless layout route in React Router v6 preserves existing authenticated URLs (`/dashboard`, `/orders`, `/portfolio`, etc.) while freeing `/` for the public homepage.

---

## 6. Current Public UI Inventory

### Reusable Assets Available
1. **[`apps/dashboard/src/components/layout/PublicFooter.tsx`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/dashboard/src/components/layout/PublicFooter.tsx):**
   - High-quality dark slate footer with legal links (`/terms`, `/privacy`, `/risk-disclosure`, `/refund-policy`, `/security`).
   - Persistent paper-trading badge: "Strictly Simulated Paper Mode â€¢ $0.00 Capital at Risk".
2. **[`apps/dashboard/src/components/legal/LegalPageLayout.tsx`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/dashboard/src/components/legal/LegalPageLayout.tsx):**
   - Sticky legal header with "Return to Terminal" link, version pill, status badge, and table of contents sidebar.
3. **Common UI Components (`apps/dashboard/src/components/common/`):**
   - `Button`: Primary, secondary, outline, ghost variants with loading states.
   - `Badge` & `PaperTradingBadge`: Status indicators.
   - `Card`, `MetricCard`, `Modal`, `ConfirmationDialog`.
4. **Icons & Styling:**
   - Lucide React icon suite.
   - Tailwind CSS dark slate theme (`bg-slate-950`, `bg-slate-900`, `border-slate-800`, `text-slate-100`).

### Missing Public Assets Required for Phase 4C
- **Public Header / Navigation Bar (`PublicHeader.tsx`):** No global public navigation bar exists. Visitors currently have no navbar with links to Features, Pricing, Research, Security, Login, or Register.
- **Marketing Page Shell / Layout (`MarketingLayout.tsx`):** No public page container combining header, content, and footer.
- **Marketing Homepage (`MarketingHomePage.tsx`):** Does not exist.
- **Public Pricing Page (`PricingPage.tsx`):** Does not exist.
- **Shared Pricing Configuration (`src/config/pricing.ts`):** Plan pricing is currently hardcoded only inside the authenticated `BillingPage.tsx`.

---

## 7. Marketing Homepage Gap Analysis

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ CURRENT STATE                                                               â”‚
â”‚ Visitor opens "/" â”€â”€â”€> ProtectedRoute â”€â”€â”€> 302 Redirect â”€â”€â”€> "/login"       â”‚
â”‚ Visitor sees only: "Trading Terminal Sign In"                               â”‚
â”‚ Deficiencies:                                                               â”‚
â”‚ â€¢ No explanation of quantitative research or walk-forward optimization       â”‚
â”‚ â€¢ No visual architecture or feature presentation                            â”‚
â”‚ â€¢ No pricing transparency                                                   â”‚
â”‚ â€¢ First impression is an intimidating credentials barrier                   â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                      â”‚
                                      â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ TARGET STATE (PHASE 4C)                                                     â”‚
â”‚ Visitor opens "/" â”€â”€â”€> Public Marketing Homepage                            â”‚
â”‚ Features:                                                                   â”‚
â”‚ â€¢ Public Header (Logo, Features, Pricing, Security, Sign In, Register)      â”‚
â”‚ â€¢ Hero Section: Institutional Quantitative Research & Paper Trading         â”‚
â”‚ â€¢ Terminal / Simulated Execution Preview                                     â”‚
â”‚ â€¢ Feature Grid: Multi-Timeframe FX, Walk-Forward Analysis, Risk Guardrails  â”‚
â”‚ â€¢ Trust & Invariants: $0.00 Capital at Risk, Bcrypt, Tenant IDOR Isolation   â”‚
â”‚ â€¢ Public Pricing link & comparison                                          â”‚
â”‚ â€¢ Clear CTAs: "Start Paper Trading" (/register) & "Terminal Login" (/login) â”‚
â”‚ â€¢ Comprehensive Public Footer                                               â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## 8. Product Positioning & Marketing Claims Safety

Audited existing repository text from `TermsPage.tsx`, `RiskDisclosurePage.tsx`, `SecurityTrustPage.tsx`, and `BillingPage.tsx`.

### Category A: Factually Supported Claims (Permitted in Phase 4C)
- "Quantitative financial research and algorithmic strategy backtesting."
- "Walk-forward optimization and parameter sensitivity evaluation."
- "Simulated paper trading in foreign exchange markets with $0.00 capital at risk."
- "Multi-timeframe historical candlestick data and spread analysis."
- "Pre-trade and post-trade automated risk management guardrails (drawdown limits, leverage ceilings, daily loss thresholds)."
- "Multi-tenant institutional architecture with strict tenant isolation and Role-Based Access Control (Owner, Admin, Trader, Viewer)."
- "Cryptographic session token management, Bcrypt password hashing, and anti-enumeration protections."

### Category B: Prohibited Claims (Strictly Forbidden in Phase 4C)
- **Zero-Loss / Risk-Free Trading:** Any claim implying trading can be "risk-free" or "guaranteed profitable." (Paper trading has zero capital risk, but trading strategies themselves carry inherent drawdown risk).
- **Guaranteed Returns / Alpha / Sharpe Ratios:** Any promise of specific financial performance.
- **AI Clairvoyance / Market Predictions:** Phrases like "AI knows where the market will go" or "Predicts market tops and bottoms."
- **Regulated Brokerage / Advisory Status:** Claims that Project ORION is a "registered broker-dealer," "licensed investment adviser," or "commodity trading advisor (CTA)."
- **Client Money Custody:** Any implication that ORION holds, custodies, or transmits real fiat or cryptocurrency.

### Required Positioning Language:
> "Project ORION is software technology for quantitative financial research, algorithmic backtesting, walk-forward optimization, and simulated paper execution. It does not provide investment advice or brokerage services. All trading operates strictly in paper mode with $0.00 capital at risk."

---

## 9. Paper-Only Safety Positioning

Audited configuration and runtime state:
- `ORION_WORKER_ENABLED="false"` in `apps/trading-engine/src/config.py` (Worker disabled).
- `broker_name="paper"`, `is_live=False` in `AccountModel`.
- OANDA integration is restricted to sandboxed Practice accounts.
- Stripe billing is enforced in Test Mode only (`BillingConfig` raises `LiveCredentialsForbiddenError` on `sk_live_`).
- Customer capital at risk is strictly **$0.00**.

### Public Communication Rule:
Every public page (Homepage, Pricing, Registration, Login) must carry clear visual paper-trading indicators:
- Badge: `PAPER TRADING ONLY` / `SIMULATED EXECUTION`
- Callout: `$0.00 Capital at Risk`

---

## 10. Pricing Audit & Tier Analysis

Audited [`apps/dashboard/src/pages/BillingPage.tsx`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/dashboard/src/pages/BillingPage.tsx) (lines 81â€“144) and [`apps/trading-engine/src/services/subscription_service.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/trading-engine/src/services/subscription_service.py) (lines 29â€“99):

| Tier Code | Plan Name | Price | Documented Limits | Features |
|---|---|---|---|---|
| `FREE` | **Free Sandbox** | **$0 / month** | 1 account, 100 daily orders, 0 workers, 30-day retention | 4 major FX pairs (EUR/USD, GBP/USD, USD/JPY, USD/CHF) |
| `PRO` | **Pro Trader** | **$99 / month** | 3 accounts, 2,500 daily orders, 1 worker, 365-day retention | 12 liquid FX pairs, email incident alerts |
| `BUSINESS` | **Business / Prop Desk** | **$299 / month** | 10 accounts, 50,000 daily orders, 5 workers, 5-year retention | All FX pairs, priority SRE SLA |
| `ENTERPRISE` | **Enterprise Institutional** | **Custom ("Contact Enterprise")** | Unlimited accounts, orders, workers, max retention | All asset classes, dedicated account manager |

### CRITICAL RULE â€” Enterprise Pricing:
- **Do NOT invent a numerical price for Enterprise** (no $499, $999, etc.).
- The public pricing page must represent Enterprise as **"Custom"** or **"Contact Enterprise"**, linking to a sales/contact action.
- Feature limits must strictly mirror `CANONICAL_PLANS` from `subscription_service.py`.

---

## 11. Stripe & Billing Safety

Audited [`libraries/infrastructure/billing/config.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/infrastructure/billing/config.py):
- Lines 30â€“39: `BillingConfig` enforces that if `secret_key` starts with `sk_live_` or `publishable_key` starts with `pk_live_`, `LiveCredentialsForbiddenError` is thrown immediately.
- Billing is conducted in Stripe Test Mode (`price_test_pro_monthly`, `price_test_business_monthly`).
- Public pricing disclaimers:
  - Must state that payment processing is in Test Mode.
  - Subscriptions entitle organizations to software compute quotas and paper-trading accounts.
  - Subscriptions do not involve real-money trading balances.

---

## 12. Pricing Data Source Architecture

### Current State (Risk of Drift)
- Plan limits are defined in backend `subscription_service.py` (`CANONICAL_PLANS`).
- Plan pricing and marketing bullet points are defined independently in frontend `BillingPage.tsx` (`const plans = [...]`).
- If Phase 4C hardcodes pricing again in `PricingPage.tsx`, pricing data will be duplicated across multiple frontend files.

### Architectural Recommendation
Create a centralized frontend configuration module:
`apps/dashboard/src/config/pricing.ts`
- Export `export const PRICING_PLANS = [...]` with plan codes, names, monthly prices, quotas, and feature matrices.
- Both `PricingPage.tsx` (public) and `BillingPage.tsx` (authenticated) import from this single source of truth.
- Guarantees 100% data consistency without drift.

---

## 13. SEO Audit

Audited [`apps/dashboard/index.html`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/dashboard/index.html) and static directory:

| SEO Asset / Tag | Current Status | Finding | Action for Phase 4C |
|---|---|---|---|
| `<title>` | **PRESENT** | "Project ORION â€” Institutional Trading Platform (Paper Mode)" | Refine to include quantitative research |
| `<meta name="viewport">` | **PRESENT** | `width=device-width, initial-scale=1.0` | Retain |
| `<meta charset="UTF-8">` | **PRESENT** | UTF-8 charset declared | Retain |
| Favicon | **PARTIAL** | Inline SVG data URI in `index.html` | Retain or provide standard `.svg`/`.png` |
| `<meta name="description">` | **MISSING** | No meta description exists | Add comprehensive institutional description |
| Canonical URL | **MISSING** | No `<link rel="canonical">` | Add (depends on domain confirmation) |
| Open Graph (`og:*`) | **MISSING** | No OG title, description, image, or url | Add standard OG tags |
| Twitter Card (`twitter:*`) | **MISSING** | No Twitter metadata | Add summary_large_image card tags |
| `robots.txt` | **MISSING** | `apps/dashboard/public/` directory does not exist | Create `public/robots.txt` allowing public routes |
| `sitemap.xml` | **MISSING** | No sitemap exists | Create `public/sitemap.xml` listing public URLs |
| JSON-LD Structured Data | **MISSING** | No schema.org markup | Add `SoftwareApplication` JSON-LD schema |

---

## 14. Domain & Canonical URL Dependency

Audited [`render.yaml`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/render.yaml):
- Line 44: `ORION_CORS_ORIGINS = "https://orion-dashboard.onrender.com"`
- Line 59: `VITE_API_URL = "https://orion-api.onrender.com"`
- No custom production domain (e.g. `https://projectorion.com`) is declared.

**Status:** `EXTERNAL INPUT REQUIRED`.
Until a custom domain is formally designated, canonical URLs and sitemap absolute URLs will default to relative paths or the documented Render deployment URL (`https://orion-dashboard.onrender.com`).

---

## 15. Performance Architecture & Bundle Splitting

Audited `apps/dashboard/src/App.tsx` and Vite build output:
- **Current Bundle Size:** `dist/assets/index-DZBQfq8k.js`: **542.90 kB** (127.39 kB gzipped).
- **Import Strategy:** All 25 pages (both public and authenticated) are statically and eagerly imported in `App.tsx`.
- **Impact on Public Visitors:** A visitor opening `/` or `/pricing` downloads the entire trading engine dashboard UI, trading forms, optimization charts, and order management code.
- **Phase 4C Recommendation:**
  - Introduce `React.lazy()` and `Suspense` for route-level code splitting.
  - Chunk 1: Public Marketing & Legal (`MarketingHomePage`, `PricingPage`, `TermsPage`, etc.) â€” <100 kB.
  - Chunk 2: Authentication & Onboarding (`LoginPage`, `RegisterPage`, etc.).
  - Chunk 3: Authenticated Terminal & Trading Engine (`AppShell`, `DashboardPage`, `OrdersPage`, `ResearchLabPage`, etc.).

---

## 16. Public vs. Authenticated Bundle Separation

While client-side code execution does not grant backend access (all data requests require valid JWT bearer tokens with IDOR tenant isolation), downloading authenticated trading terminal logic to unauthenticated visitors increases unnecessary surface exposure.

Route-level code splitting with `React.lazy()` cleanly isolates authenticated modules from public visitors.

---

## 17. Responsive Design Audit

Audited `apps/dashboard/src/index.css`, `LoginPage.tsx`, and `RegisterPage.tsx`:
- Tailwind CSS 3 responsive utilities (`sm: 640px`, `md: 768px`, `lg: 1024px`, `xl: 1280px`).
- Dark slate background (`#020617` / `bg-slate-950`).
- Card backgrounds: `bg-slate-900/90` with `border-slate-800`.
- Text hierarchy: `text-slate-100` (headings), `text-slate-200` (body), `text-slate-400` (muted labels).
- Mobile readiness: All forms and layouts use single-column collapsing on viewports `<640px` with zero horizontal overflow.
- Reusable styling components: Buttons, badges, and cards are immediately available for marketing page composition.

---

## 18. Accessibility Baseline

- **Strengths:**
  - Semantic HTML (`<header>`, `<main>`, `<aside>`, `<nav>`, `<footer>`, `<form>`).
  - Inputs have explicit `id` matched to `<label htmlFor="...">`.
  - Semantic `role="alert"` and `role="status"` on alerts and badges.
  - High visible focus outlines (`focus:ring-2 focus:ring-sky-500`).
- **Phase 4C Recommendations:**
  - Implement a hidden "Skip to main content" link for keyboard accessibility.
  - Maintain WCAG AA compliant text contrast across all marketing cards (`text-slate-300`/`text-slate-400` on dark backgrounds).
  - Ensure mobile navigation menu is fully operable via keyboard (Escape key closes drawer).

---

## 19. Legal Page Integration

All 5 Phase 3 legal routes are verified and active:
- `/terms` (Terms of Service)
- `/privacy` (Privacy Policy)
- `/risk-disclosure` (Paper Trading Risk Disclosure)
- `/refund-policy` (Refund & Cancellation Policy)
- `/security` (Security & Trust Architecture)

Marketing pages will link directly to these disclosures via the header navigation and `PublicFooter`. All disclosures continue to display the badge **"Draft for Legal Review"**.

---

## 20. Public Footer Audit

[`apps/dashboard/src/components/layout/PublicFooter.tsx`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/dashboard/src/components/layout/PublicFooter.tsx):
- **Current Content:** Legal links, simulated trading notice, $0.00 capital invariant.
- **Additions for Phase 4C:**
  - Product links: Features (`/`), Pricing (`/pricing`), Security (`/security`).
  - Account links: Sign In (`/login`), Register (`/register`).
  - Copyright: `Â© 2026 Project ORION. All rights reserved.`
  - Advisory disclaimer: "Project ORION is educational and quantitative research software for paper trading simulation."

---

## 21. Support & Contact Dependency

A repository-wide search revealed:
- Support email: **EXTERNAL INPUT REQUIRED**
- Sales/Enterprise inquiry email: **EXTERNAL INPUT REQUIRED**
- Coordinated vulnerability disclosure email: **EXTERNAL INPUT REQUIRED**
- Legal entity name & registered office: **EXTERNAL INPUT REQUIRED**
- Governing jurisdiction: **EXTERNAL INPUT REQUIRED**

**Audit Rule:** These must NOT be fabricated. Public marketing pages should use generic inquiry forms or placeholder routing (e.g. `mailto:contact@...` pending configuration) without claiming fictitious entity names.

---

## 22. Content & Copy Inventory

| Copy Element | Current Context | Source File | Classification | Recommendation for Phase 4C |
|---|---|---|---|---|
| "Quantitative Paper Trading Platform" | Login & Registration headers | `LoginPage.tsx`, `RegisterPage.tsx` | **SUPPORTED** | Retain as primary subtitle |
| "Simulated Execution â€¢ $0.00 Capital at Risk" | Platform badge | `PublicFooter.tsx`, `AppShell.tsx` | **SUPPORTED** | Retain as core invariant banner |
| "Algorithmic Strategy Backtesting & Walk-Forward Optimization" | Platform description | `TermsPage.tsx` L38 | **SUPPORTED** | Feature in hero & feature grid |
| "Multi-Account Prop Trading with Autonomous Workers" | Business plan description | `BillingPage.tsx` L118 | **SUPPORTED** | Retain in pricing table |
| "Guaranteed Alpha / High Win Rate" | N/A | None in codebase | **PROHIBITED** | Strictly forbid |
| "Licensed Broker-Dealer" | N/A | None in codebase | **PROHIBITED** | Strictly forbid |

---

## 23. Public Security Audit

- **XSS:** No `dangerouslySetInnerHTML`, `eval()`, or `new Function()` in frontend code.
- **Token Security:** `sessionStorage` is used solely for authenticated sessions. Public marketing pages will execute zero auth token reads or writes.
- **API Token Leakage:** Public marketing pages will make zero authenticated backend API requests.
- **Redirects:** All public navigation is hardcoded; no dynamic open redirects exist.

---

## 24. Analytics & Privacy Boundary

- **Current State:** Zero tracking cookies, zero analytics beacons (Google Analytics, Meta Pixel, Hotjar, Segment, PostHog are completely absent).
- **Privacy Policy Commitment:** [`PrivacyPage.tsx`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/dashboard/src/pages/PrivacyPage.tsx) explicitly states: *"Project ORION does not use advertising cookies, marketing pixels, tracking scripts, or analytics beacons."*
- **Phase 4C Rule:** Strictly maintain this privacy boundary. **Zero analytics or tracking scripts may be introduced during Phase 4C.**

---

## 25. Proposed Route Architecture

```tsx
// Public Marketing & Presentation
<Route path="/" element={<MarketingHomePage />} />
<Route path="/pricing" element={<PricingPage />} />

// Public Authentication & Onboarding
<Route path="/login" element={<LoginPage />} />
<Route path="/register" element={<RegisterPage />} />
<Route path="/forgot-password" element={<ForgotPasswordPage />} />
<Route path="/reset-password" element={<ResetPasswordPage />} />
<Route path="/verify-email" element={<VerifyEmailPage />} />

// Public Legal & Trust Disclosures
<Route path="/terms" element={<TermsPage />} />
<Route path="/privacy" element={<PrivacyPage />} />
<Route path="/risk-disclosure" element={<RiskDisclosurePage />} />
<Route path="/refund-policy" element={<RefundPolicyPage />} />
<Route path="/security" element={<SecurityTrustPage />} />

// Authenticated Terminal (Pathless Protected Layout)
<Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
  <Route path="dashboard" element={<DashboardPage />} />
  <Route path="orders" element={<OrdersPage />} />
  <Route path="positions" element={<PositionsPage />} />
  <Route path="trades" element={<TradesPage />} />
  <Route path="portfolio" element={<PortfolioPage />} />
  <Route path="broker-sandbox" element={<BrokerSandboxPage />} />
  <Route path="strategies" element={<StrategiesPage />} />
  <Route path="research" element={<ResearchLabPage />} />
  <Route path="optimization" element={<OptimizationStudioPage />} />
  <Route path="deployments" element={<DeploymentPipelinePage />} />
  <Route path="risk" element={<RiskPage />} />
  <Route path="worker" element={<WorkerPage />} />
  <Route path="billing" element={<BillingPage />} />
  <Route path="organization" element={<OrganizationPage />} />
  <Route path="audit" element={<AuditPage />} />
</Route>

// Wildcard Redirect
<Route path="*" element={<Navigate to="/" replace />} />
```

---

## 26. Phase 4C Scope Boundary

| Priority | Feature / Deliverable | Status |
|---|---|---|
| **MUST HAVE** | Public Navigation Header (`PublicHeader.tsx`) with desktop & mobile menu | Required |
| **MUST HAVE** | Public Marketing Homepage (`MarketingHomePage.tsx`) with Hero, Features, Architecture, Trust, CTAs | Required |
| **MUST HAVE** | Public Pricing Page (`PricingPage.tsx`) displaying Free, Pro ($99), Business ($299), Enterprise | Required |
| **MUST HAVE** | Shared Pricing Configuration (`src/config/pricing.ts`) to eliminate drift with `BillingPage.tsx` | Required |
| **MUST HAVE** | Primary CTA to `/register` and secondary CTA to `/login` | Required |
| **MUST HAVE** | Reclaim `/` for homepage and preserve authenticated dashboard route protection | Required |
| **MUST HAVE** | Expanded `PublicFooter.tsx` with full navigation links | Required |
| **SHOULD HAVE** | Route-level code splitting (`React.lazy` + `Suspense`) for bundle optimization | Recommended |
| **SHOULD HAVE** | SEO metadata in `index.html` (title, meta description, Open Graph, Twitter cards) | Recommended |
| **SHOULD HAVE** | Static `robots.txt` and `sitemap.xml` | Recommended |
| **SHOULD HAVE** | Public FAQ section on homepage | Recommended |
| **OPTIONAL** | Complex interactive canvas animations / dynamic charts | Excluded |
| **OPTIONAL** | Testimonials or customer logos (cannot fabricate) | Excluded |
| **FORBIDDEN** | Third-party analytics, tracking pixels, or advertising beacons | Strictly Forbidden |
| **FORBIDDEN** | Unsubstantiated claims of profitability or real-money brokerage | Strictly Forbidden |

---

## 27. External Dependencies

1. **Qualified Legal Counsel Review:** Final approval of Terms of Service, Privacy Policy, and Risk Disclosures before commercial beta launch.
2. **Production Domain & DNS:** Designation of production custom domain for canonical URL, sitemap, and Open Graph tags.
3. **Official Corporate Identity:** Legal entity name, registered office address, and governing jurisdiction.
4. **Official Contact Channels:** Provisioning of `support@`, `sales@`, and `security@` mailboxes.
5. **Stripe Production Underwriting:** Stripe merchant approval prior to enabling live billing.

---

## 28. Test & Quality Gate Plan

Phase 4C implementation must satisfy the following gates:

### Frontend Gates:
- `apps/dashboard/tests/marketing_pages.test.tsx`:
  - Verify `MarketingHomePage` renders hero, feature cards, safety badges, and CTAs.
  - Verify `PublicHeader` renders navigation links and toggles mobile menu.
  - Verify `PricingPage` renders all 4 tiers accurately without inventing Enterprise pricing.
  - Verify primary CTA routes to `/register` and secondary CTA routes to `/login`.
  - Verify legal links in header and footer resolve properly.
  - Verify ProtectedRoute continues to intercept unauthenticated attempts to access `/dashboard`.
- Vitest suite: `npm test -- --run` (all test files passing).
- Production build: `npm run build` (`tsc && vite build`) passing with 0 errors.

### Backend Regression Gates:
- No backend code modifications are required for Phase 4C.
- Run pytest regression suite: `test_auth_lifecycle.py`, `test_onboarding_legal.py`, `test_legal_registry.py`, `test_legal_routes.py`, `test_rate_limiting.py`, `test_rate_limit_service.py`.

---

## 29. Implementation Sequence

The recommended step-by-step implementation plan for Phase 4C:

1. **Phase 4C-1: Shared Data & Public Navigation Shell**
   - Create `src/config/pricing.ts` (canonical plans data).
   - Create `src/components/layout/PublicHeader.tsx` (responsive public navigation).
   - Update `src/components/layout/PublicFooter.tsx` (expanded footer links).
2. **Phase 4C-2: Public Marketing Homepage**
   - Create `src/pages/MarketingHomePage.tsx` (Hero, Feature Grid, Architecture Preview, Safety Invariant Banner, FAQ, CTA).
3. **Phase 4C-3: Public Pricing Page**
   - Create `src/pages/PricingPage.tsx` (Tier cards, feature comparison, Stripe test mode disclaimer, CTAs).
4. **Phase 4C-4: Route Architecture & Route-Level Code Splitting**
   - Refactor `src/App.tsx` with `React.lazy` and `Suspense`.
   - Reclaim `/` for `MarketingHomePage` and mount `/pricing`.
   - Nest dashboard routes under pathless `<ProtectedRoute><AppShell /></ProtectedRoute>`.
5. **Phase 4C-5: SEO Metadata & Static Files**
   - Update `index.html` with meta description, OG tags, Twitter cards.
   - Create `public/robots.txt` and `public/sitemap.xml`.
6. **Phase 4C-6: Automated Testing & Verification**
   - Create `apps/dashboard/tests/marketing_pages.test.tsx`.
   - Execute full frontend and backend quality gates.

---

## 30. Final Audit Classification

```
================================================================================
CLASSIFICATION: B â€” READY WITH EXTERNAL DEPENDENCIES
================================================================================
```

### Justification:
1. **Technical Architecture:** The repository has completed all prerequisites (Phases 1â€“3, 4B) and is architecturally ready for Phase 4C public marketing and pricing presentation.
2. **Safety & Security:** Zero compromises to the $0.00 capital risk invariant, paper-only matching engine, disabled worker (`ORION_WORKER_ENABLED=false`), or Stripe Test Mode.
3. **External Dependencies:** Production domain configuration, legal entity details, and external legal counsel review remain pending before commercial launch.

---

EPIC-027 PHASE 4C â€” AUDIT COMPLETE â€” AWAITING REVIEW
