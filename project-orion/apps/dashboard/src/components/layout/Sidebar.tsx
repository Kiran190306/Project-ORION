import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  ClipboardList,
  Layers,
  History,
  PieChart,
  Cpu,
  ShieldAlert,
  Sliders,
  CreditCard,
  X,
} from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/orders', label: 'Orders', icon: ClipboardList },
  { path: '/positions', label: 'Positions', icon: Layers },
  { path: '/trades', label: 'Trade History', icon: History },
  { path: '/portfolio', label: 'Portfolio', icon: PieChart },
  { path: '/strategies', label: 'Strategies', icon: Sliders },
  { path: '/risk', label: 'Risk Controls', icon: ShieldAlert },
  { path: '/worker', label: 'Worker Status', icon: Cpu },
  { path: '/billing', label: 'Billing & Plans', icon: CreditCard },
];

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-xs z-30 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed top-0 bottom-0 left-0 z-40 w-64 bg-slate-900 border-r border-slate-800 transition-transform duration-200 ease-in-out flex flex-col ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } lg:translate-x-0 lg:static`}
        style={{ backgroundColor: '#0c1322', borderColor: '#1e293b' }}
      >
        {/* Brand Header */}
        <div className="h-16 px-6 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400 font-bold font-mono">
              Ω
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-wider text-slate-100 font-mono">
                PROJECT ORION
              </h1>
              <p className="text-[10px] text-slate-500 font-mono tracking-wider">
                INSTITUTIONAL FOREX
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white lg:hidden p-1"
            aria-label="Close menu"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-sky-500/15 text-sky-300 border border-sky-500/30 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`
                }
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Mode Footer Badge */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/30">
          <div className="rounded-lg bg-amber-500/10 border border-amber-500/30 p-3 text-center">
            <div className="text-[11px] font-bold text-amber-300 font-mono tracking-widest flex items-center justify-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
              PAPER TRADING
            </div>
            <p className="text-[10px] text-amber-400/80 mt-1">
              Zero live broker capital risk
            </p>
          </div>
        </div>
      </aside>
    </>
  );
};
