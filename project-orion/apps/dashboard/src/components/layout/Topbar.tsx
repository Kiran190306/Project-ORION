import React, { useState, useEffect } from 'react';
import { Menu, LogOut, User, ShieldCheck } from 'lucide-react';
import { useAuth } from '../../auth/AuthContext';
import { PaperTradingBadge } from '../common/Badge';

interface TopbarProps {
  onToggleSidebar: () => void;
}

export const Topbar: React.FC<TopbarProps> = ({ onToggleSidebar }) => {
  const { user, logout } = useAuth();
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

  return (
    <header
      className="h-16 border-b border-slate-800 bg-slate-900/90 backdrop-blur-md px-4 lg:px-6 flex items-center justify-between gap-4 sticky top-0 z-20"
      style={{ backgroundColor: '#0f172a', borderColor: '#1e293b' }}
    >
      {/* Left: Mobile hamburger & Environment Status */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="p-2 text-slate-400 hover:text-white rounded-lg lg:hidden focus:outline-none focus:ring-2 focus:ring-sky-500"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <PaperTradingBadge size="sm" />

        <div className="hidden sm:flex items-center gap-2 text-xs font-mono text-slate-400 border-l border-slate-800 pl-3">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          <span>FASTAPI ENGINE READY</span>
        </div>
      </div>

      {/* Right: Clock, User and Logout */}
      <div className="flex items-center gap-3 sm:gap-4">
        <div className="hidden md:block text-xs font-mono text-slate-400">
          {timeUtc}
        </div>

        {user && (
          <div className="flex items-center gap-2.5 border-l border-slate-800 pl-3 sm:pl-4">
            <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300">
              <User className="w-4 h-4" />
            </div>
            <div className="hidden sm:flex flex-col">
              <span className="text-xs font-semibold text-slate-200">{user.username}</span>
              <div className="flex items-center gap-1">
                {user.is_superuser ? (
                  <span className="text-[10px] text-sky-400 font-mono flex items-center gap-0.5">
                    <ShieldCheck className="w-3 h-3" /> SUPERUSER
                  </span>
                ) : (
                  <span className="text-[10px] text-slate-400 font-mono">TRADER</span>
                )}
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
