import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Mail, CheckCircle2, AlertCircle, ArrowRight, RefreshCw, ArrowLeft } from 'lucide-react';
import { authApi } from '../api/endpoints';
import { Button } from '../components/common/Button';
import { PaperTradingBadge } from '../components/common/Badge';
import { getErrorMessage } from '../utils/errors';

export const VerifyEmailPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';

  const [isVerifying, setIsVerifying] = useState(false);
  const [verificationSuccess, setVerificationSuccess] = useState<string | null>(null);
  const [verificationError, setVerificationError] = useState<string | null>(null);

  // Resend state
  const [resendEmail, setResendEmail] = useState('');
  const [isResending, setIsResending] = useState(false);
  const [resendSuccess, setResendSuccess] = useState<string | null>(null);
  const [resendError, setResendError] = useState<string | null>(null);

  useEffect(() => {
    if (token) {
      handleVerify(token);
    }
  }, [token]);

  const handleVerify = async (tokenToVerify: string) => {
    setIsVerifying(true);
    setVerificationError(null);
    setVerificationSuccess(null);

    try {
      const res = await authApi.verifyEmail({ token: tokenToVerify.trim() });
      setVerificationSuccess(res.message);
    } catch (err) {
      setVerificationError(getErrorMessage(err));
    } finally {
      setIsVerifying(false);
    }
  };

  const handleResend = async (e: React.FormEvent) => {
    e.preventDefault();
    setResendError(null);
    setResendSuccess(null);

    const cleanEmail = resendEmail.trim().toLowerCase();
    if (!cleanEmail || !cleanEmail.includes('@')) {
      setResendError('Please enter a valid email address.');
      return;
    }

    setIsResending(true);
    try {
      const res = await authApi.resendVerification({ email: cleanEmail });
      setResendSuccess(res.message);
    } catch (err) {
      setResendError(getErrorMessage(err));
    } finally {
      setIsResending(false);
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
            EMAIL VERIFICATION
          </p>
          <div className="mt-3 flex justify-center">
            <PaperTradingBadge size="sm" />
          </div>
        </div>

        {/* Main Card */}
        <div
          className="rounded-2xl border border-slate-800 bg-slate-900/90 shadow-2xl p-6 sm:p-8 backdrop-blur-md"
          style={{ backgroundColor: '#0f172a', borderColor: '#1e293b' }}
        >
          {isVerifying ? (
            <div className="py-8 text-center space-y-4">
              <RefreshCw className="w-8 h-8 text-sky-400 animate-spin mx-auto" />
              <h2 className="text-base font-semibold text-slate-200">Verifying Security Token</h2>
              <p className="text-xs text-slate-400 font-mono">
                Validating your cryptographic single-use verification link...
              </p>
            </div>
          ) : verificationSuccess ? (
            <div className="space-y-6">
              <div
                className="p-4 rounded-lg bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 text-xs flex items-start gap-3"
                role="status"
              >
                <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-400" />
                <div className="flex-1 leading-relaxed">
                  <p className="font-semibold text-emerald-200 mb-1">Email Verified</p>
                  <p>{verificationSuccess}</p>
                </div>
              </div>

              <Link to="/login" className="block w-full">
                <Button variant="primary" size="md" className="w-full" rightIcon={<ArrowRight className="w-4 h-4" />}>
                  Proceed to Sign In
                </Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-6">
              <div>
                <h2 className="text-base font-semibold text-slate-200 mb-1">Verify Your Email</h2>
                <p className="text-xs text-slate-400">
                  {verificationError
                    ? 'The verification token was invalid or has expired. You can request a new verification link below.'
                    : 'Confirm your institutional account by entering your email to receive a verification link.'}
                </p>
              </div>

              {verificationError && (
                <div
                  className="p-3.5 rounded-lg bg-rose-950/60 border border-rose-800/60 text-rose-300 text-xs flex items-start gap-2.5 animate-fadeIn"
                  role="alert"
                >
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-rose-400" />
                  <div className="flex-1 font-medium">{verificationError}</div>
                </div>
              )}

              {resendSuccess && (
                <div
                  className="p-3.5 rounded-lg bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 text-xs flex items-start gap-2.5"
                  role="status"
                >
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0 mt-0.5 text-emerald-400" />
                  <div className="flex-1 font-medium">{resendSuccess}</div>
                </div>
              )}

              {resendError && (
                <div
                  className="p-3.5 rounded-lg bg-rose-950/60 border border-rose-800/60 text-rose-300 text-xs flex items-start gap-2.5"
                  role="alert"
                >
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-rose-400" />
                  <div className="flex-1 font-medium">{resendError}</div>
                </div>
              )}

              <form onSubmit={handleResend} className="space-y-4" noValidate>
                <div>
                  <label
                    htmlFor="resendEmail"
                    className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-1.5"
                  >
                    Registered Email
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                      <Mail className="w-4 h-4" />
                    </div>
                    <input
                      id="resendEmail"
                      type="email"
                      required
                      value={resendEmail}
                      onChange={(e) => setResendEmail(e.target.value)}
                      placeholder="trader@institution.com"
                      className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-sm text-slate-100 placeholder-slate-600 focus:border-sky-500 focus:outline-none transition-colors"
                    />
                  </div>
                </div>

                <Button
                  type="submit"
                  variant="primary"
                  size="md"
                  className="w-full"
                  isLoading={isResending}
                  rightIcon={<ArrowRight className="w-4 h-4" />}
                >
                  Resend Verification Link
                </Button>

                <div className="pt-2 text-center">
                  <Link
                    to="/login"
                    className="text-xs text-sky-400 hover:text-sky-300 transition-colors inline-flex items-center gap-1.5 font-mono"
                  >
                    <ArrowLeft className="w-3.5 h-3.5" /> Back to Sign In
                  </Link>
                </div>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
