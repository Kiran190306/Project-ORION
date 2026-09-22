import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldAlert, FileText, Lock, RefreshCw, ShieldCheck } from 'lucide-react';

export const PublicFooter: React.FC = () => {
  return (
    <footer className="w-full mt-auto py-8 px-4 sm:px-6 border-t border-slate-900 bg-slate-950/80 backdrop-blur-sm text-xs font-mono">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-slate-400">
        <div className="flex flex-wrap items-center justify-center sm:justify-start gap-x-5 gap-y-2">
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
          <Link
            to="/security"
            className="hover:text-emerald-400 transition-colors inline-flex items-center gap-1.5"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
            <span>Security & Trust</span>
          </Link>
        </div>

        <div className="text-center sm:text-right text-[11px] text-slate-400">
          <div>Project ORION &bull; Quantitative Paper Trading Platform</div>
          <div className="text-amber-400 font-semibold mt-0.5">
            Strictly Simulated Paper Mode &bull; $0.00 Capital at Risk
          </div>
        </div>
      </div>
    </footer>
  );
};
