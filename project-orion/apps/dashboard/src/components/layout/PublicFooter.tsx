import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldAlert, FileText, Lock, RefreshCw, ShieldCheck, Home, Tag, UserPlus, LogIn } from 'lucide-react';

export const PublicFooter: React.FC = () => {
  return (
    <footer className="w-full mt-auto py-10 px-4 sm:px-6 lg:px-8 border-t border-slate-900 bg-slate-950/90 backdrop-blur-sm text-xs font-mono">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Navigation & Legal Links */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-6 pb-6 border-b border-slate-900/80">
          {/* Main Navigation Links */}
          <div className="flex flex-wrap items-center justify-center md:justify-start gap-x-5 gap-y-2 text-slate-300">
            <Link to="/" className="hover:text-sky-400 transition-colors inline-flex items-center gap-1.5">
              <Home className="w-3.5 h-3.5 text-slate-400" />
              <span>Overview</span>
            </Link>
            <Link to="/pricing" className="hover:text-sky-400 transition-colors inline-flex items-center gap-1.5">
              <Tag className="w-3.5 h-3.5 text-slate-400" />
              <span>Pricing</span>
            </Link>
            <Link to="/security" className="hover:text-emerald-400 transition-colors inline-flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
              <span>Security &amp; Trust</span>
            </Link>
            <Link to="/login" className="hover:text-sky-400 transition-colors inline-flex items-center gap-1.5">
              <LogIn className="w-3.5 h-3.5 text-slate-400" />
              <span>Sign In</span>
            </Link>
            <Link to="/register" className="hover:text-sky-400 transition-colors inline-flex items-center gap-1.5">
              <UserPlus className="w-3.5 h-3.5 text-slate-400" />
              <span>Register</span>
            </Link>
          </div>

          {/* Legal Disclosures Links */}
          <div className="flex flex-wrap items-center justify-center md:justify-end gap-x-5 gap-y-2 text-slate-400">
            <Link
              to="/terms"
              className="hover:text-sky-400 transition-colors inline-flex items-center gap-1.5"
            >
              <FileText className="w-3.5 h-3.5 text-slate-400" />
              <span>Terms of Service</span>
            </Link>
            <Link
              to="/privacy"
              className="hover:text-sky-400 transition-colors inline-flex items-center gap-1.5"
            >
              <Lock className="w-3.5 h-3.5 text-slate-400" />
              <span>Privacy Policy</span>
            </Link>
            <Link
              to="/risk-disclosure"
              className="hover:text-amber-400 transition-colors inline-flex items-center gap-1.5"
            >
              <ShieldAlert className="w-3.5 h-3.5 text-amber-500" />
              <span>Risk Disclosure</span>
            </Link>
            <Link
              to="/refund-policy"
              className="hover:text-sky-400 transition-colors inline-flex items-center gap-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5 text-slate-400" />
              <span>Refund Policy</span>
            </Link>
          </div>
        </div>

        {/* Bottom Disclaimers & Copyright */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] text-slate-400">
          <div className="space-y-1 text-center sm:text-left">
            <div>&copy; 2026 Project ORION. Quantitative Paper Trading Platform &bull; All rights reserved.</div>
            <div className="text-slate-400 max-w-2xl leading-relaxed">
              Project ORION is software technology for quantitative financial research, algorithmic strategy evaluation, and paper execution.
              It is not an investment adviser, broker-dealer, or commodity trading advisor.
            </div>
          </div>

          <div className="text-center sm:text-right flex-shrink-0">
            <div className="text-slate-300 font-semibold">Institutional Paper Architecture</div>
            <div className="text-amber-400 font-semibold mt-0.5 inline-flex items-center gap-1">
              <ShieldAlert className="w-3 h-3 text-amber-400" />
              <span>Strictly Simulated Paper Mode &bull; $0.00 Capital at Risk</span>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};
