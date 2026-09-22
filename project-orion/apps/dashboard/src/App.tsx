import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { OrganizationProvider } from './auth/OrganizationContext';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { ToastProvider } from './components/common/Toast';
import { AppShell } from './components/layout/AppShell';

// ─── Public Marketing & Presentation Pages (Code-Split) ─────────────────────
const MarketingHomePage = lazy(() =>
  import('./pages/MarketingHomePage').then((m) => ({ default: m.MarketingHomePage }))
);
const PricingPage = lazy(() =>
  import('./pages/PricingPage').then((m) => ({ default: m.PricingPage }))
);

// ─── Public Authentication & Onboarding Pages (Code-Split) ───────────────────
const LoginPage = lazy(() =>
  import('./pages/LoginPage').then((m) => ({ default: m.LoginPage }))
);
const RegisterPage = lazy(() =>
  import('./pages/RegisterPage').then((m) => ({ default: m.RegisterPage }))
);
const ForgotPasswordPage = lazy(() =>
  import('./pages/ForgotPasswordPage').then((m) => ({ default: m.ForgotPasswordPage }))
);
const ResetPasswordPage = lazy(() =>
  import('./pages/ResetPasswordPage').then((m) => ({ default: m.ResetPasswordPage }))
);
const VerifyEmailPage = lazy(() =>
  import('./pages/VerifyEmailPage').then((m) => ({ default: m.VerifyEmailPage }))
);

// ─── Public Legal & Trust Disclosure Pages (Code-Split) ─────────────────────
const TermsPage = lazy(() =>
  import('./pages/TermsPage').then((m) => ({ default: m.TermsPage }))
);
const PrivacyPage = lazy(() =>
  import('./pages/PrivacyPage').then((m) => ({ default: m.PrivacyPage }))
);
const RiskDisclosurePage = lazy(() =>
  import('./pages/RiskDisclosurePage').then((m) => ({ default: m.RiskDisclosurePage }))
);
const RefundPolicyPage = lazy(() =>
  import('./pages/RefundPolicyPage').then((m) => ({ default: m.RefundPolicyPage }))
);
const SecurityTrustPage = lazy(() =>
  import('./pages/SecurityTrustPage').then((m) => ({ default: m.SecurityTrustPage }))
);

// ─── Authenticated Trading Terminal Pages (Code-Split) ──────────────────────
const DashboardPage = lazy(() =>
  import('./pages/DashboardPage').then((m) => ({ default: m.DashboardPage }))
);
const PortfolioPage = lazy(() =>
  import('./pages/PortfolioPage').then((m) => ({ default: m.PortfolioPage }))
);
const OrdersPage = lazy(() =>
  import('./pages/OrdersPage').then((m) => ({ default: m.OrdersPage }))
);
const PositionsPage = lazy(() =>
  import('./pages/PositionsPage').then((m) => ({ default: m.PositionsPage }))
);
const TradesPage = lazy(() =>
  import('./pages/TradesPage').then((m) => ({ default: m.TradesPage }))
);
const StrategiesPage = lazy(() =>
  import('./pages/StrategiesPage').then((m) => ({ default: m.StrategiesPage }))
);
const ResearchLabPage = lazy(() =>
  import('./pages/ResearchLabPage').then((m) => ({ default: m.ResearchLabPage }))
);
const OptimizationStudioPage = lazy(() =>
  import('./pages/OptimizationStudioPage').then((m) => ({ default: m.OptimizationStudioPage }))
);
const DeploymentPipelinePage = lazy(() =>
  import('./pages/DeploymentPipelinePage').then((m) => ({ default: m.DeploymentPipelinePage }))
);
const BrokerSandboxPage = lazy(() =>
  import('./pages/BrokerSandboxPage').then((m) => ({ default: m.BrokerSandboxPage }))
);
const RiskPage = lazy(() =>
  import('./pages/RiskPage').then((m) => ({ default: m.RiskPage }))
);
const WorkerPage = lazy(() =>
  import('./pages/WorkerPage').then((m) => ({ default: m.WorkerPage }))
);
const BillingPage = lazy(() =>
  import('./pages/BillingPage').then((m) => ({ default: m.BillingPage }))
);
const OrganizationPage = lazy(() =>
  import('./pages/OrganizationPage').then((m) => ({ default: m.OrganizationPage }))
);
const AuditPage = lazy(() =>
  import('./pages/AuditPage').then((m) => ({ default: m.AuditPage }))
);

// ─── Accessible Loading Fallback ─────────────────────────────────────────────
export const PageLoadingFallback: React.FC = () => (
  <div
    role="status"
    aria-live="polite"
    className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-300"
  >
    <div className="w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full animate-spin mb-4" />
    <p className="text-xs font-mono tracking-wider text-slate-400">
      Loading Project ORION module...
    </p>
  </div>
);

export const AppRoutes: React.FC = () => {
  return (
    <Suspense fallback={<PageLoadingFallback />}>
      <Routes>
        {/* Public Marketing & Product Presentation */}
        <Route path="/" element={<MarketingHomePage />} />
        <Route path="/pricing" element={<PricingPage />} />

        {/* Public Authentication & Onboarding */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />

        {/* Public Legal & Trust Disclosures */}
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/risk-disclosure" element={<RiskDisclosurePage />} />
        <Route path="/refund-policy" element={<RefundPolicyPage />} />
        <Route path="/security" element={<SecurityTrustPage />} />

        {/* Authenticated Trading Terminal (Protected Layout Route) */}
        <Route
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
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

        {/* Fallback Catch-All */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <OrganizationProvider>
            <AppRoutes />
          </OrganizationProvider>
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  );
};

export default App;
