import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { OrganizationProvider } from './auth/OrganizationContext';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { ToastProvider } from './components/common/Toast';
import { AppShell } from './components/layout/AppShell';

import { LoginPage } from './pages/LoginPage';
import { ForgotPasswordPage } from './pages/ForgotPasswordPage';
import { ResetPasswordPage } from './pages/ResetPasswordPage';
import { VerifyEmailPage } from './pages/VerifyEmailPage';
import { DashboardPage } from './pages/DashboardPage';
import { PortfolioPage } from './pages/PortfolioPage';
import { OrdersPage } from './pages/OrdersPage';
import { PositionsPage } from './pages/PositionsPage';
import { TradesPage } from './pages/TradesPage';
import { StrategiesPage } from './pages/StrategiesPage';
import { ResearchLabPage } from './pages/ResearchLabPage';
import { OptimizationStudioPage } from './pages/OptimizationStudioPage';
import { DeploymentPipelinePage } from './pages/DeploymentPipelinePage';
import { BrokerSandboxPage } from './pages/BrokerSandboxPage';
import { RiskPage } from './pages/RiskPage';
import { WorkerPage } from './pages/WorkerPage';
import { BillingPage } from './pages/BillingPage';
import { OrganizationPage } from './pages/OrganizationPage';
import { AuditPage } from './pages/AuditPage';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
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

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
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
