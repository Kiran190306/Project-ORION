import React, { useState } from 'react';
import { Outlet, Link } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

export const AppShell: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col lg:flex-row text-slate-100 antialiased selection:bg-sky-500/30 selection:text-sky-200">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex-1 flex flex-col min-w-0">
        <Topbar onToggleSidebar={() => setSidebarOpen((prev) => !prev)} />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto overflow-y-auto">
          <Outlet />
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
