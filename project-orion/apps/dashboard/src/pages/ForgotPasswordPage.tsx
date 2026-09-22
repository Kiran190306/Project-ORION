import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, AlertCircle, CheckCircle2, ArrowRight, ArrowLeft } from 'lucide-react';
import { authApi } from '../api/endpoints';
import { Button } from '../components/common/Button';
import { PaperTradingBadge } from '../components/common/Badge';
import { getErrorMessage } from '../utils/errors';

export const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail || !cleanEmail.includes('@')) {
      setError('Please enter a valid email address.');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await authApi.forgotPassword({ email: cleanEmail });
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
            ACCOUNT RECOVERY
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
          <h2 className="text-base font-semibold text-slate-200 mb-1">Reset Your Password</h2>
          <p className="text-xs text-slate-400 mb-6">
            Enter your registered email address and we will dispatch secure recovery instructions.
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
                  <p className="font-semibold text-emerald-200 mb-1">Instructions Dispatched</p>
                  <p>{successMessage}</p>
                </div>
              </div>

              <div className="pt-2">
                <Link to="/login" className="w-full block">
                  <Button variant="outline" size="md" className="w-full" leftIcon={<ArrowLeft className="w-4 h-4" />}>
                    Return to Sign In
                  </Button>
                </Link>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              <div>
                <label
                  htmlFor="email"
                  className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-1.5"
                >
                  Registered Email
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Mail className="w-4 h-4" />
                  </div>
                  <input
                    id="email"
                    type="email"
                    required
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="trader@institution.com"
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
                  Send Recovery Link
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
