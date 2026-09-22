import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X, ArrowRight, ShieldAlert } from 'lucide-react';
import { PaperTradingBadge } from '../common/Badge';

export const PublicHeader: React.FC = () => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();

  const navLinks = [
    { label: 'Overview', href: '/' },
    { label: 'Research Lab', href: '/#research' },
    { label: 'Risk Controls', href: '/#risk-controls' },
    { label: 'Pricing', href: '/pricing' },
    { label: 'Security & Trust', href: '/security' },
  ];

  const isActive = (href: string) => {
    if (href === '/' && location.pathname === '/') return true;
    if (href === '/pricing' && location.pathname === '/pricing') return true;
    if (href === '/security' && location.pathname === '/security') return true;
    return false;
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-900 bg-slate-950/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo & Name */}
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="flex items-center gap-2.5 text-slate-100 hover:text-sky-400 transition-colors focus:outline-none focus:ring-2 focus:ring-sky-500 rounded-lg p-1"
            >
              <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400 font-mono font-bold text-lg shadow-sm shadow-sky-950">
                Ω
              </div>
              <div className="flex flex-col">
                <span className="font-mono font-bold tracking-wider text-sm text-slate-100">
                  PROJECT ORION
                </span>
                <span className="text-[10px] font-mono text-slate-400 tracking-tight hidden sm:inline">
                  QUANTITATIVE RESEARCH &bull; PAPER TRADING
                </span>
              </div>
            </Link>

            <div className="hidden lg:flex items-center ml-2">
              <PaperTradingBadge size="sm" />
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1 font-mono text-xs" aria-label="Main Navigation">
            {navLinks.map((link) => (
              <Link
                key={link.label}
                to={link.href}
                className={`px-3 py-1.5 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-sky-500 ${
                  isActive(link.href)
                    ? 'text-sky-400 bg-sky-950/40 border border-sky-800/40'
                    : 'text-slate-300 hover:text-slate-100 hover:bg-slate-900'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          {/* Desktop CTAs */}
          <div className="hidden md:flex items-center gap-3 font-mono text-xs">
            <Link
              to="/login"
              className="px-3.5 py-2 text-slate-300 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-sky-500 rounded-lg"
            >
              Sign In
            </Link>
            <Link
              to="/register"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-medium shadow-sm shadow-sky-950 border border-sky-500/50 transition-all focus:outline-none focus:ring-2 focus:ring-sky-400 cursor-pointer"
            >
              <span>Start Paper Trading</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <div className="flex md:hidden items-center gap-2">
            <PaperTradingBadge size="sm" />
            <button
              type="button"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-500"
              aria-label={isMobileMenuOpen ? 'Close Navigation Menu' : 'Open Navigation Menu'}
              aria-expanded={isMobileMenuOpen}
            >
              {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer */}
      {isMobileMenuOpen && (
        <div className="md:hidden border-t border-slate-900 bg-slate-950 px-4 pt-3 pb-5 space-y-3 font-mono text-xs animate-fadeIn">
          <nav className="space-y-1" aria-label="Mobile Navigation">
            {navLinks.map((link) => (
              <Link
                key={link.label}
                to={link.href}
                onClick={() => setIsMobileMenuOpen(false)}
                className={`block px-3 py-2 rounded-lg transition-colors ${
                  isActive(link.href)
                    ? 'text-sky-400 bg-sky-950/40 border border-sky-800/40'
                    : 'text-slate-300 hover:text-slate-100 hover:bg-slate-900'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          <div className="pt-3 border-t border-slate-900 grid grid-cols-2 gap-2">
            <Link
              to="/login"
              onClick={() => setIsMobileMenuOpen(false)}
              className="text-center py-2 px-3 rounded-lg border border-slate-800 bg-slate-900 text-slate-200 hover:text-white transition-colors"
            >
              Sign In
            </Link>
            <Link
              to="/register"
              onClick={() => setIsMobileMenuOpen(false)}
              className="text-center py-2 px-3 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-medium shadow-sm transition-all"
            >
              Start Paper Trading
            </Link>
          </div>

          <div className="pt-2 text-center text-[10px] text-amber-400/80 flex items-center justify-center gap-1.5">
            <ShieldAlert className="w-3 h-3 text-amber-400" />
            <span>Strictly Simulated Paper Mode &bull; $0.00 Capital at Risk</span>
          </div>
        </div>
      )}
    </header>
  );
};
