import React, { useState, useEffect } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { Lock, AlertCircle, CheckCircle2, ArrowRight, ArrowLeft, Key } from 'lucide-react';
import { authApi } from '../api/endpoints';
import { Button } from '../components/common/Button';
import { PaperTradingBadge } from '../components/common/Badge';
import { getErrorMessage } from '../utils/errors';

export const ResetPasswordPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [token, setToken] = useState(searchParams.get('token') || '');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const urlToken = searchParams.get('token');
    if (urlToken) {
      setToken(urlToken);
    }
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!token.trim()) {
      setError('A valid password reset token is required.');
      return;
    }
    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters long.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match. Please verify both inputs.');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await authApi.resetPassword({
        token: token.trim(),
        new_password: newPassword,
      });
      setSuccessMessage(res.message);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 sm:p-6 text-slate-100 selection:bg-sky-500/30">
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
            SECURITY CREDENTIAL RESET
          </p>
          <div className="mt-3 flex justify-center">
            <PaperTradingBadge size="sm" />
          </div>
        </div>

        {/* Card Container */}
        <div
          className="rounded-2xl border border-slate-800 bg-slate-900/90 shadow-2xl p-6 sm:p-8 backdrop-blur-md"
          style={{ backgroundColor: '#0f172a', borderColor: '#1e293b' }}
        >
          <h2 className="text-base font-semibold text-slate-200 mb-1">Set New Password</h2>
          <p className="text-xs text-slate-400 mb-6">
            Enter your reset token and choose a new secure password for your account.
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

          {successMessage ? (
            <div className="space-y-6">
              <div
                className="p-4 rounded-lg bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 text-xs flex items-start gap-3"
                role="status"
              >
                <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-400" />
                <div className="flex-1 leading-relaxed">
                  <p className="font-semibold text-emerald-200 mb-1">Password Successfully Updated</p>
                  <p>{successMessage}</p>
                </div>
              </div>

              <div className="pt-2">
                <Button
                  variant="primary"
                  size="md"
                  className="w-full"
                  onClick={() => navigate('/login')}
                  rightIcon={<ArrowRight className="w-4 h-4" />}
                >
                  Proceed to Sign In
                </Button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              <div>
                <label
                  htmlFor="token"
                  className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-1.5"
                >
                  Reset Token
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Key className="w-4 h-4" />
                  </div>
                  <input
                    id="token"
                    type="text"
                    required
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    placeholder="Cryptographic reset token"
                    className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-sm font-mono text-slate-100 placeholder-slate-600 focus:border-sky-500 focus:outline-none transition-colors"
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor="newPassword"
                  className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-1.5"
                >
                  New Password (min 8 chars)
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    id="newPassword"
                    type="password"
                    required
                    autoComplete="new-password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-sm text-slate-100 placeholder-slate-600 focus:border-sky-500 focus:outline-none transition-colors"
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor="confirmPassword"
                  className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-1.5"
                >
                  Confirm New Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    id="confirmPassword"
                    type="password"
                    required
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••••••"
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
                  Save New Password
                </Button>
              </div>

              <div className="pt-3 text-center">
                <Link
                  to="/login"
                  className="text-xs text-sky-400 hover:text-sky-300 transition-colors inline-flex items-center gap-1.5 font-mono"
                >
                  <ArrowLeft className="w-3.5 h-3.5" /> Back to Sign In
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
