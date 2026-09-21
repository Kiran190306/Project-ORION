import React, { useState, useEffect } from 'react';
import { Menu, LogOut, ShieldCheck, Building2, ChevronDown } from 'lucide-react';
import { useAuth } from '../../auth/AuthContext';
import { useOrganization } from '../../auth/OrganizationContext';
import { PaperTradingBadge } from '../common/Badge';
import { Dropdown, DropdownItem } from '../common/Dropdown';

interface TopbarProps {
  onToggleSidebar: () => void;
}

export const Topbar: React.FC<TopbarProps> = ({ onToggleSidebar }) => {
  const { user, logout } = useAuth();
  const { currentOrg, organizations, currentRole, switchOrganization } = useOrganization();
  const [timeUtc, setTimeUtc] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeUtc(now.toISOString().replace('T', ' ').substring(11, 19) + ' UTC');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const orgDropdownItems: DropdownItem[] = organizations.map((org) => ({
    id: org.id,
    label: (
      <div className="flex flex-col text-left">
        <span className="font-semibold text-slate-200">{org.name}</span>
        <span className="text-[10px] text-slate-400">{org.slug}</span>
      </div>
    ),
    badge: org.id === currentOrg?.id ? (
      <span className="text-[10px] font-mono text-sky-400 font-bold uppercase">ACTIVE</span>
    ) : undefined,
    onClick: () => switchOrganization(org.id),
  }));

  const roleColor: Record<string, string> = {
    OWNER: 'text-amber-400',
    ADMINISTRATOR: 'text-purple-400',
    PORTFOLIO_MANAGER: 'text-sky-400',
    RISK_OFFICER: 'text-rose-400',
    TRADER: 'text-emerald-400',
    AUDITOR: 'text-indigo-400',
    VIEWER: 'text-slate-400',
  };

  const displayRole = currentRole || (user?.is_superuser ? 'OWNER' : 'TRADER');

  return (
    <header
      className="h-16 border-b border-slate-800 bg-slate-900/90 backdrop-blur-md px-4 lg:px-6 flex items-center justify-between gap-4 sticky top-0 z-20"
      style={{ backgroundColor: '#0f172a', borderColor: '#1e293b' }}
    >
      {/* Left: Mobile hamburger & Organization Selector & Paper Mode Badge */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="p-2 text-slate-400 hover:text-white rounded-lg lg:hidden focus:outline-none focus:ring-2 focus:ring-sky-500 cursor-pointer"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Organization Switcher */}
        {organizations.length > 0 && (
          <div className="hidden sm:block">
            <Dropdown
              trigger={
                <button
                  type="button"
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900/80 hover:bg-slate-800/80 text-xs font-mono text-slate-200 transition-colors cursor-pointer"
                  title="Switch active organization tenant"
                >
                  <Building2 className="w-3.5 h-3.5 text-sky-400" />
                  <span className="max-w-[140px] truncate font-semibold">
                    {currentOrg?.name || 'Select Organization'}
                  </span>
                  <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                </button>
              }
              items={orgDropdownItems}
            />
          </div>
        )}

        <PaperTradingBadge size="sm" />

        <div className="hidden md:flex items-center gap-2 text-xs font-mono text-slate-400 border-l border-slate-800 pl-3">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span>FASTAPI ENGINE READY</span>
        </div>
      </div>

      {/* Right: Clock, User and Logout */}
      <div className="flex items-center gap-3 sm:gap-4">
        <div className="hidden lg:block text-xs font-mono text-slate-400">
          {timeUtc}
        </div>

        {user && (
          <div className="flex items-center gap-2.5 border-l border-slate-800 pl-3 sm:pl-4">
            <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 font-bold font-mono text-xs">
              {user.username.substring(0, 2).toUpperCase()}
            </div>
            <div className="hidden sm:flex flex-col">
              <span className="text-xs font-semibold text-slate-200">{user.username}</span>
              <div className="flex items-center gap-1">
                {user.is_superuser && (
                  <span className="text-[10px] text-sky-400 font-mono flex items-center gap-0.5 mr-1">
                    <ShieldCheck className="w-3 h-3" /> SUPERUSER
                  </span>
                )}
                <span className={`text-[10px] font-mono font-semibold ${roleColor[displayRole] || 'text-slate-400'}`}>
                  {displayRole}
                </span>
              </div>
            </div>
          </div>
        )}

        <button
          onClick={() => logout()}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900/80 text-xs font-medium text-slate-300 hover:text-rose-400 hover:border-rose-800/60 hover:bg-rose-950/20 transition-all cursor-pointer"
          title="Sign out of trading session"
          aria-label="Sign out"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Logout</span>
        </button>
      </div>
    </header>
  );
};
