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
  FlaskConical,
  CreditCard,
  Users,
  FileText,
  X,
  Zap,
  Rocket,
  Server,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '../../auth/AuthContext';
import { useOrganization } from '../../auth/OrganizationContext';
import { hasPermission, Permission } from '../../auth/permissions';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

interface NavGroup {
  title: string;
  items: {
    path: string;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    permission?: Permission;
  }[];
}

const navGroups: NavGroup[] = [
  {
    title: 'TRADING OPERATIONS',
    items: [
      { path: '/dashboard', label: 'Overview', icon: LayoutDashboard },
      { path: '/orders', label: 'Paper Trading', icon: ClipboardList },
      { path: '/positions', label: 'Positions', icon: Layers },
      { path: '/trades', label: 'Trade Journal', icon: History },
      { path: '/portfolio', label: 'Portfolio', icon: PieChart },
      { path: '/broker-sandbox', label: 'Broker Sandbox', icon: Server, permission: Permission.BROKER_READ },
    ],
  },
  {
    title: 'QUANTITATIVE ENGINE',
    items: [
      { path: '/strategies', label: 'Strategies', icon: Sliders },
      { path: '/research', label: 'Research & Backtest', icon: FlaskConical, permission: Permission.RESEARCH_READ },
      { path: '/optimization', label: 'Optimization Studio', icon: Zap, permission: Permission.OPTIMIZATION_READ },
      { path: '/deployments', label: 'Deployment Pipeline', icon: Rocket, permission: Permission.DEPLOYMENT_READ },
      { path: '/risk', label: 'Risk Controls & Alerts', icon: ShieldAlert },
      { path: '/worker', label: 'Worker Status', icon: Cpu },
    ],
  },
  {
    title: 'GOVERNANCE & SAAS',
    items: [
      { path: '/billing', label: 'Billing & Plans', icon: CreditCard },
      { path: '/organization', label: 'Organization', icon: Users },
      { path: '/audit', label: 'Audit Trail', icon: FileText, permission: Permission.AUDIT_READ },
      { path: '/security', label: 'Security & Trust', icon: ShieldCheck },
    ],
  },
];

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const { user } = useAuth();
  const { currentRole } = useOrganization();

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/70 backdrop-blur-xs z-30 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed top-0 bottom-0 left-0 z-40 w-64 bg-[#090D16] border-r border-[#1E293B] transition-transform duration-200 ease-in-out flex flex-col ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } lg:translate-x-0 lg:static`}
        style={{ backgroundColor: '#090D16', borderColor: '#1E293B' }}
      >
        {/* Brand Header */}
        <div className="h-16 px-6 border-b border-[#1E293B] flex items-center justify-between bg-[#0B101D]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-sky-500/15 border border-sky-500/40 flex items-center justify-center text-sky-400 font-bold font-mono shadow-xs shadow-sky-500/20">
              Ω
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-wider text-slate-100 font-mono">
                PROJECT ORION
              </h1>
              <p className="text-[10px] text-sky-400/90 font-mono tracking-wider font-semibold">
                QUANT TRADING TERMINAL
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white lg:hidden p-1 cursor-pointer"
            aria-label="Close menu"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Links Grouped */}
        <nav className="flex-1 px-3 py-4 space-y-5 overflow-y-auto">
          {navGroups.map((group) => {
            const visibleItems = group.items.filter((item) => {
              if (!item.permission) return true;
              return hasPermission(currentRole, item.permission, user?.is_superuser);
            });

            if (visibleItems.length === 0) return null;

            return (
              <div key={group.title} className="space-y-1">
                <div className="px-3.5 py-1 text-[10px] font-mono font-semibold tracking-wider text-slate-500 uppercase">
                  {group.title}
                </div>
                {visibleItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      onClick={onClose}
                      className={({ isActive }) =>
                        `flex items-center gap-3 px-3.5 py-2 rounded-lg text-xs font-medium transition-all ${
                          isActive
                            ? 'bg-sky-500/15 text-sky-300 border border-sky-500/30 font-semibold shadow-xs'
                            : 'text-slate-400 hover:text-slate-200 hover:bg-[#141E33]/70 hover:border hover:border-[#1E293B]'
                        }`
                      }
                    >
                      <Icon className="w-4 h-4 flex-shrink-0" />
                      <span>{item.label}</span>
                    </NavLink>
                  );
                })}
              </div>
            );
          })}
        </nav>

        {/* Mode Footer Badge */}
        <div className="p-3 border-t border-[#1E293B] bg-[#0B101D]">
          <div className="rounded-lg bg-amber-500/10 border border-amber-500/30 p-2.5 text-center">
            <div className="text-[10px] font-bold text-amber-300 font-mono tracking-widest flex items-center justify-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
              PAPER TRADING ONLY
            </div>
            <p className="text-[9px] text-amber-400/90 font-mono mt-0.5 font-semibold">
              $0 REAL CAPITAL AT RISK
            </p>
          </div>
        </div>
      </aside>
    </>
  );
};
