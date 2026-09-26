import React, { useState, useEffect } from 'react';
import { Menu, LogOut, ShieldCheck, Building2, ChevronDown, Search, Bell, Globe } from 'lucide-react';
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
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);

  const FX_SEARCH_SYMBOLS = [
    { symbol: 'EUR/USD', name: 'Euro / US Dollar', spread: '0.2 pips' },
    { symbol: 'GBP/USD', name: 'British Pound / US Dollar', spread: '0.4 pips' },
    { symbol: 'USD/JPY', name: 'US Dollar / Japanese Yen', spread: '0.3 pips' },
    { symbol: 'AUD/USD', name: 'Australian Dollar / US Dollar', spread: '0.5 pips' },
    { symbol: 'USD/CAD', name: 'US Dollar / Canadian Dollar', spread: '0.6 pips' },
    { symbol: 'USD/CHF', name: 'US Dollar / Swiss Franc', spread: '0.5 pips' },
  ];

  const filteredSymbols = FX_SEARCH_SYMBOLS.filter(
    (s) =>
      s.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

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
      className="h-16 border-b border-[#1E293B] bg-[#0F172A] backdrop-blur-md px-4 lg:px-6 flex items-center justify-between gap-4 sticky top-0 z-20"
      style={{ backgroundColor: '#0F172A', borderColor: '#1E293B' }}
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
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[#1E293B] bg-[#141E33] hover:bg-[#1A2742] text-xs font-mono text-slate-200 transition-colors cursor-pointer"
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

        <div className="hidden xl:flex items-center gap-2 text-xs font-mono text-slate-400 border-l border-[#1E293B] pl-3">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span>FASTAPI ENGINE READY</span>
        </div>
      </div>

      {/* Center: Global Symbol Search */}
      <div className="relative hidden md:block w-72 lg:w-96">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setShowSearchDropdown(true);
            }}
            onFocus={() => setShowSearchDropdown(true)}
            placeholder="Search FX Symbol (e.g. EUR/USD)..."
            className="w-full bg-[#141E33] border border-[#1E293B] rounded-lg pl-9 pr-14 py-1.5 text-xs font-mono text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-sky-500/60 focus:ring-1 focus:ring-sky-500/40"
          />
          <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] font-mono text-slate-500 bg-[#090D16] px-1.5 py-0.5 rounded border border-[#1E293B]">
            /
          </kbd>
        </div>

        {/* Live Search Dropdown */}
        {showSearchDropdown && searchQuery.trim().length > 0 && (
          <div
            className="absolute left-0 right-0 top-full mt-1.5 bg-[#141E33] border border-[#1E293B] rounded-lg shadow-xl z-50 overflow-hidden font-mono text-xs divide-y divide-[#1E293B]"
            onMouseLeave={() => setShowSearchDropdown(false)}
          >
            {filteredSymbols.length > 0 ? (
              filteredSymbols.map((item) => (
                <div
                  key={item.symbol}
                  onClick={() => {
                    setSearchQuery(item.symbol);
                    setShowSearchDropdown(false);
                  }}
                  className="px-3.5 py-2 hover:bg-[#1A2742] cursor-pointer flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-100">{item.symbol}</span>
                    <span className="text-[10px] text-slate-400">{item.name}</span>
                  </div>
                  <span className="text-[10px] text-sky-400">{item.spread}</span>
                </div>
              ))
            ) : (
              <div className="px-3 py-2 text-slate-500 text-[11px]">No matching symbol</div>
            )}
          </div>
        )}
      </div>

      {/* Right: Market Status, Clock, User and Logout */}
      <div className="flex items-center gap-3 sm:gap-4">
        {/* Market Status Pill */}
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/20 text-[10px] font-mono text-emerald-400 font-semibold">
          <Globe className="w-3 h-3 animate-spin text-emerald-400" />
          <span>MARKET ACTIVE</span>
        </div>

        {/* Notifications Icon */}
        <button
          type="button"
          className="relative p-1.5 text-slate-400 hover:text-slate-200 hover:bg-[#141E33] rounded-lg transition-colors cursor-pointer"
          title="Terminal Notifications"
          aria-label="Notifications"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-sky-400 rounded-full" />
        </button>

        <div className="hidden lg:block text-xs font-mono text-slate-400 tabular-nums">
          {timeUtc}
        </div>

        {user && (
          <div className="flex items-center gap-2.5 border-l border-[#1E293B] pl-3 sm:pl-4">
            <div className="w-8 h-8 rounded-full bg-[#141E33] border border-[#1E293B] flex items-center justify-center text-slate-300 font-bold font-mono text-xs">
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
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#1E293B] bg-[#141E33] text-xs font-medium text-slate-300 hover:text-rose-400 hover:border-rose-800/60 hover:bg-rose-950/20 transition-all cursor-pointer"
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
