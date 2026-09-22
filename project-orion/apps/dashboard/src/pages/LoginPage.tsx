import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { Lock, User, AlertCircle, ArrowRight, ShieldCheck } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { Button } from '../components/common/Button';
import { PaperTradingBadge } from '../components/common/Badge';
import { PublicFooter } from '../components/layout/PublicFooter';
import { getErrorMessage } from '../utils/errors';

export const LoginPage: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as { from?: { pathname?: string } })?.from?.pathname || '/dashboard';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Client-side validation
    if (username.trim().length < 3) {
      setError('Username must be at least 3 characters.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    setIsSubmitting(true);
    try {
      await login({ username: username.trim(), password });
      navigate(from, { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-between text-slate-100 selection:bg-sky-500/30">
      <div className="flex-1 flex flex-col items-center justify-center p-4 sm:p-6">
        <div className="w-full max-w-md">
          {/* Header Branding */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-sky-500/10 border border-sky-500/30 text-sky-400 font-bold font-mono text-2xl mb-4 shadow-lg shadow-sky-950/40">
              Ω
            </div>
            <h1 className="text-xl font-bold font-mono tracking-wider text-slate-100">
              PROJECT ORION
            </h1>
            <p className="text-xs font-mono text-slate-400 tracking-wider mt-1">
              QUANTITATIVE PAPER TRADING PLATFORM
            </p>
            <p className="text-[11px] font-mono text-amber-400/90 tracking-wide mt-0.5">
              Simulated Execution &bull; $0.00 Capital at Risk
            </p>
            <div className="mt-3 flex justify-center">
              <PaperTradingBadge size="sm" />
            </div>
          </div>

        {/* Login Box */}
        <div
          className="rounded-2xl border border-slate-800 bg-slate-900/90 shadow-2xl p-6 sm:p-8 backdrop-blur-md"
          style={{ backgroundColor: '#0f172a', borderColor: '#1e293b' }}
        >
          <h2 className="text-base font-semibold text-slate-200 mb-1">Trading Terminal Sign In</h2>
          <p className="text-xs text-slate-400 mb-6">
            Enter your credentials to access your paper trading account.
          </p>

          {error && (
            <div
              className="mb-5 p-3.5 rounded-lg bg-rose-950/60 border border-rose-800/60 text-rose-300 text-xs flex items-start gap-2.5 animate-fadeIn"
              role="alert"
            >
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-rose-400" />
              <div className="flex-1 font-medium">{error}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div>
              <label
                htmlFor="username"
                className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-1.5"
              >
                Username
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <User className="w-4 h-4" />
                </div>
                <input
                  id="username"
                  type="text"
                  required
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Trader username"
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-sm text-slate-100 placeholder-slate-600 focus:border-sky-500 focus:outline-none transition-colors"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label
                  htmlFor="password"
                  className="block text-xs font-mono uppercase tracking-wider text-slate-400"
                >
                  Password
                </label>
                <Link
                  to="/forgot-password"
                  className="text-xs text-sky-400 hover:text-sky-300 transition-colors font-mono"
                >
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  id="password"
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Account password"
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-sm text-slate-100 placeholder-slate-600 focus:border-sky-500 focus:outline-none transition-colors"
                />
              </div>
            </div>

            <div className="pt-2">
              <Button
                type="submit"
                variant="primary"
                size="md"
                className="w-full"
                isLoading={isSubmitting}
                rightIcon={<ArrowRight className="w-4 h-4" />}
              >
                Authenticate Session
              </Button>
            </div>

            <div className="pt-2 text-center">
              <Link
                to="/verify-email"
                className="text-xs text-slate-400 hover:text-slate-300 transition-colors font-mono"
              >
                Need to verify your email?
              </Link>
            </div>
          </form>

          <div className="mt-6 pt-5 border-t border-slate-800/80 text-[11px] text-slate-500 flex items-center justify-center gap-1.5 font-mono">
            <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
            <span>JWT Bearer Protection &bull; IDOR Isolated</span>
          </div>
        </div>
      </div>
      </div>
      <PublicFooter />
    </div>
  );
};
