import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
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

        <footer className="py-3 px-6 border-t border-slate-900 text-center text-xs text-slate-600 font-mono">
          Project ORION v0.1.0 &bull; Institutional Forex Trading Architecture &bull; Paper Simulation Mode Active
        </footer>
      </div>
    </div>
  );
};
