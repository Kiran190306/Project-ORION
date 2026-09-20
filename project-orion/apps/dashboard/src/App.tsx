import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { ToastProvider } from './components/common/Toast';
import { AppShell } from './components/layout/AppShell';

import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { PortfolioPage } from './pages/PortfolioPage';
import { OrdersPage } from './pages/OrdersPage';
import { PositionsPage } from './pages/PositionsPage';
import { TradesPage } from './pages/TradesPage';
import { StrategiesPage } from './pages/StrategiesPage';
import { RiskPage } from './pages/RiskPage';
import { WorkerPage } from './pages/WorkerPage';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

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
        <Route path="strategies" element={<StrategiesPage />} />
        <Route path="risk" element={<RiskPage />} />
        <Route path="worker" element={<WorkerPage />} />
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
          <AppRoutes />
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  );
};

export default App;
