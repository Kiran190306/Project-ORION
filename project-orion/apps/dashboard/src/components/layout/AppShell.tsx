import React, { useState } from 'react';
import { Outlet, Link } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { useOnboarding } from '../../hooks/useOnboarding';
import { OnboardingWizard } from '../onboarding/OnboardingWizard';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '../common/Button';

export const AppShell: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const {
    status,
    isLoading: isOnboardingLoading,
    error: onboardingError,
    refreshStatus,
    completeStep,
  } = useOnboarding();

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col lg:flex-row text-slate-100 antialiased selection:bg-sky-500/30 selection:text-sky-200">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex-1 flex flex-col min-w-0">
        <Topbar onToggleSidebar={() => setSidebarOpen((prev) => !prev)} />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto overflow-y-auto">
          {isOnboardingLoading ? (
            <div
              role="status"
              aria-live="polite"
              className="py-24 flex flex-col items-center justify-center text-slate-300"
            >
              <div className="w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full animate-spin mb-4" />
              <p className="text-xs font-mono tracking-wider text-slate-400">
                Checking institutional onboarding status...
              </p>
            </div>
          ) : onboardingError && !status ? (
            <div className="py-20 text-center space-y-4">
              <div className="inline-flex p-3 rounded-full bg-rose-950/60 border border-rose-800 text-rose-400">
                <AlertCircle className="w-6 h-6" />
              </div>
              <h2 className="text-base font-semibold text-slate-200">
                Failed to Load Onboarding Status
              </h2>
              <p className="text-xs text-slate-400 max-w-md mx-auto">{onboardingError}</p>
              <Button variant="secondary" size="sm" onClick={() => refreshStatus()}>
                <RefreshCw className="w-4 h-4 mr-1.5" />
                Retry Connection
              </Button>
            </div>
          ) : status && status.status !== 'COMPLETED' ? (
            <OnboardingWizard
              status={status}
              onRefresh={refreshStatus}
              onCompleteStep={completeStep}
            />
          ) : (
            <Outlet />
          )}
        </main>

        <footer className="py-3 px-6 border-t border-slate-900 flex flex-col sm:flex-row items-center justify-between gap-2 text-[11px] text-slate-500 font-mono">
          <div>
            Project ORION v0.1.0 &bull; Paper Simulation Mode Active &bull; <span className="text-amber-400 font-semibold">$0.00 Capital at Risk</span>
          </div>
          <div className="flex items-center gap-4">
            <Link to="/terms" className="hover:text-slate-300 transition-colors">Terms</Link>
            <Link to="/privacy" className="hover:text-slate-300 transition-colors">Privacy</Link>
            <Link to="/risk-disclosure" className="hover:text-amber-400 transition-colors">Risk Disclosure</Link>
            <Link to="/security" className="hover:text-emerald-400 transition-colors">Security</Link>
          </div>
        </footer>
      </div>
    </div>
  );
};
