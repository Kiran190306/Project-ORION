import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Lock,
  User,
  Mail,
  Building,
  AlertCircle,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  ExternalLink,
} from 'lucide-react';
import { onboardingApi } from '../api/endpoints';
import type { OnboardingResponse } from '../api/types';
import { Button } from '../components/common/Button';
import { PaperTradingBadge } from '../components/common/Badge';
import { PublicFooter } from '../components/layout/PublicFooter';
import { getErrorMessage } from '../utils/errors';

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();

  // Form input state
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [organizationName, setOrganizationName] = useState('');
  const [organizationSlug, setOrganizationSlug] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Mandatory legal consents state
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [privacyAcknowledged, setPrivacyAcknowledged] = useState(false);
  const [riskDisclosureAcknowledged, setRiskDisclosureAcknowledged] = useState(false);

  // Status & error state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successResult, setSuccessResult] = useState<OnboardingResponse | null>(null);

  // Password criteria calculations
  const passwordLengthOk = password.length >= 8 && new TextEncoder().encode(password).length <= 72;
  const passwordHasLetter = /[a-zA-Z]/.test(password);
  const passwordHasDigitOrSpecial = /[0-9]/.test(password) || /[^a-zA-Z0-9]/.test(password);
  const passwordsMatch = password.length > 0 && password === confirmPassword;
  const isPasswordValid = passwordLengthOk && passwordHasLetter && passwordHasDigitOrSpecial;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Client-side validations
    const cleanUsername = username.trim();
    const cleanEmail = email.trim().toLowerCase();
    const cleanOrgName = organizationName.trim();

    if (cleanUsername.length < 3) {
      setError('Username must be at least 3 characters.');
      return;
    }
    if (!cleanEmail || !cleanEmail.includes('@')) {
      setError('A valid corporate email address is required.');
      return;
    }
    if (cleanOrgName.length < 2) {
      setError('Organization name must be at least 2 characters.');
      return;
    }
    if (!isPasswordValid) {
      setError('Password does not satisfy the security policy requirements.');
      return;
    }
    if (!passwordsMatch) {
      setError('Passwords do not match.');
      return;
    }
    if (!termsAccepted) {
      setError('You must accept the Terms of Service to create an account.');
      return;
    }
    if (!privacyAcknowledged) {
      setError('You must acknowledge the Privacy Policy to create an account.');
      return;
    }
    if (!riskDisclosureAcknowledged) {
      setError('You must acknowledge the Paper Trading Risk Disclosure to create an account.');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await onboardingApi.register({
        username: cleanUsername,
        email: cleanEmail,
        organization_name: cleanOrgName,
        organization_slug: organizationSlug.trim() ? organizationSlug.trim().toLowerCase() : undefined,
        full_name: fullName.trim() ? fullName.trim() : undefined,
        password,
        terms_accepted: termsAccepted,
        privacy_acknowledged: privacyAcknowledged,
        risk_disclosure_acknowledged: riskDisclosureAcknowledged,
      });

      // Clear password fields immediately from memory
      setPassword('');
      setConfirmPassword('');
      setSuccessResult(response);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-between text-slate-100 selection:bg-sky-500/30">
      <div className="flex-1 flex flex-col items-center justify-center p-4 sm:p-6 my-6">
        <div className="w-full max-w-lg">
          {/* Header Branding */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-sky-500/10 border border-sky-500/30 text-sky-400 font-bold font-mono text-2xl mb-4 shadow-lg shadow-sky-950/40">
              Ω
            </div>
            <h1 className="text-xl font-bold font-mono tracking-wider text-slate-100">
              PROJECT ORION
            </h1>
            <p className="text-xs font-mono text-slate-400 tracking-wider mt-1">
              SELF-SERVICE REGISTRATION & ONBOARDING
            </p>
            <p className="text-[11px] font-mono text-amber-400/90 tracking-wide mt-0.5">
              Simulated Execution &bull; $0.00 Capital at Risk
            </p>
            <div className="mt-3 flex justify-center">
              <PaperTradingBadge size="sm" />
            </div>
          </div>

          {/* Registration Card */}
          <div
            className="rounded-2xl border border-slate-800 bg-slate-900/90 shadow-2xl p-6 sm:p-8 backdrop-blur-md"
            style={{ backgroundColor: '#0f172a', borderColor: '#1e293b' }}
          >
            {successResult ? (
              /* Success / Email Verification Notice View */
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-bold text-slate-100 mb-1">
                    Organization &amp; Account Provisioned
                  </h2>
                  <p className="text-xs text-slate-400">
                    Welcome to Project ORION, <span className="font-semibold text-sky-400">{successResult.username}</span>. Your simulated trading account has been created.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-800/60 text-xs space-y-2">
                  <div className="flex items-center gap-2 text-emerald-400 font-semibold font-mono">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Paper Trading Account Initialized</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-emerald-900/40 font-mono text-[11px] text-slate-300">
                    <div>
                      <span className="text-slate-500 block">Account Number</span>
                      <span>{successResult.account_number}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Initial Paper Balance</span>
                      <span className="text-emerald-400 font-semibold">${Number(successResult.initial_balance).toLocaleString()} USD</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Organization</span>
                      <span>{successResult.organization_name}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Subscription Tier</span>
                      <span className="uppercase text-sky-400 font-semibold">{successResult.subscription_tier}</span>
                    </div>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-sky-950/40 border border-sky-800/60 text-xs space-y-2">
                  <div className="flex items-center gap-2 text-sky-400 font-semibold font-mono">
                    <Mail className="w-4 h-4" />
                    <span>Verification Email Dispatched</span>
                  </div>
                  <p className="text-slate-300 text-xs leading-relaxed">
                    A confirmation link has been sent to <span className="text-sky-300 font-mono font-medium">{successResult.email}</span>.
                    Please check your inbox to verify your corporate email address for continuous platform access.
                  </p>
                </div>

                <div className="pt-2 space-y-3">
                  <Button
                    type="button"
                    variant="primary"
                    size="md"
                    className="w-full"
                    onClick={() => navigate('/login')}
                    rightIcon={<ArrowRight className="w-4 h-4" />}
                  >
                    Proceed to Sign In
                  </Button>
                  <div className="text-center">
                    <Link
                      to="/verify-email"
                      className="text-xs text-slate-400 hover:text-slate-300 transition-colors font-mono"
                    >
                      Need to enter a verification token?
                    </Link>
                  </div>
                </div>
              </div>
            ) : (
              /* Registration Form */
              <div>
                <h2 className="text-base font-semibold text-slate-200 mb-1">
                  Create Institutional Paper Trading Account
                </h2>
                <p className="text-xs text-slate-400 mb-6">
                  Self-service enrollment with instantaneous paper trading allocation and zero capital risk.
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
                  {/* Username & Full Name */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label
                        htmlFor="username"
                        className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-1.5"
                      >
                        Username <span className="text-sky-400">*</span>
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
                          placeholder="trader_john"
                          className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-sm text-slate-100 placeholder-slate-600 focus:border-sky-500 focus:outline-none transition-colors"
                        />
                      </div>
                    </div>

                    <div>
                      <label
                        htmlFor="fullName"
                        className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-1.5"
                      >
                        Full Name (Optional)
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                          <User className="w-4 h-4" />
                        </div>
                        <input
                          id="fullName"
                          type="text"
                          autoComplete="name"
                          value={fullName}
                          onChange={(e) => setFullName(e.target.value)}
                          placeholder="John Doe"
                          className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-sm text-slate-100 placeholder-slate-600 focus:border-sky-500 focus:outline-none transition-colors"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Corporate Email */}
                  <div>
                    <label
                      htmlFor="email"
                      className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-1.5"
                    >
                      Corporate Email <span className="text-sky-400">*</span>
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

                  {/* Organization Name & Slug */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label
                        htmlFor="organizationName"
                        className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-1.5"
                      >
                        Organization Name <span className="text-sky-400">*</span>
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                          <Building className="w-4 h-4" />
                        </div>
                        <input
                          id="organizationName"
                          type="text"
                          required
                          value={organizationName}
                          onChange={(e) => setOrganizationName(e.target.value)}
                          placeholder="Alpha Quant LLC"
                          className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-sm text-slate-100 placeholder-slate-600 focus:border-sky-500 focus:outline-none transition-colors"
                        />
                      </div>
                    </div>

                    <div>
                      <label
                        htmlFor="organizationSlug"
                        className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-1.5"
                      >
                        Org Slug (Optional)
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                          <Building className="w-4 h-4" />
                        </div>
                        <input
                          id="organizationSlug"
                          type="text"
                          value={organizationSlug}
                          onChange={(e) => setOrganizationSlug(e.target.value)}
                          placeholder="alpha-quant"
                          className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-sm text-slate-100 placeholder-slate-600 focus:border-sky-500 focus:outline-none transition-colors"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Password & Confirm Password */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label
                        htmlFor="password"
                        className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-1.5"
                      >
                        Password <span className="text-sky-400">*</span>
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                          <Lock className="w-4 h-4" />
                        </div>
                        <input
                          id="password"
                          type="password"
                          required
                          autoComplete="new-password"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
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
                        Confirm Password <span className="text-sky-400">*</span>
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
                  </div>

                  {/* Live Password Policy Checklist */}
                  {password.length > 0 && (
                    <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-1.5 font-mono text-[11px]">
                      <div className="text-slate-400 font-medium mb-1">Password Policy Requirements:</div>
                      <div className="flex items-center gap-1.5">
                        {passwordLengthOk ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                        ) : (
                          <XCircle className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
                        )}
                        <span className={passwordLengthOk ? 'text-emerald-300' : 'text-slate-400'}>
                          Between 8 and 72 bytes
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        {passwordHasLetter ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                        ) : (
                          <XCircle className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
                        )}
                        <span className={passwordHasLetter ? 'text-emerald-300' : 'text-slate-400'}>
                          At least one letter (a-z, A-Z)
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        {passwordHasDigitOrSpecial ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                        ) : (
                          <XCircle className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
                        )}
                        <span className={passwordHasDigitOrSpecial ? 'text-emerald-300' : 'text-slate-400'}>
                          At least one number or symbol
                        </span>
                      </div>
                      {confirmPassword.length > 0 && (
                        <div className="flex items-center gap-1.5">
                          {passwordsMatch ? (
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                          ) : (
                            <XCircle className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
                          )}
                          <span className={passwordsMatch ? 'text-emerald-300' : 'text-rose-400'}>
                            Passwords match
                          </span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Mandatory Legal Consents */}
                  <div className="pt-2 space-y-3 border-t border-slate-800/80">
                    <div className="text-xs font-mono uppercase tracking-wider text-slate-400 mb-2">
                      Mandatory Legal Acknowledgements
                    </div>

                    {/* Terms of Service Checkbox */}
                    <label className="flex items-start gap-2.5 cursor-pointer text-xs group">
                      <input
                        type="checkbox"
                        id="terms_accepted"
                        checked={termsAccepted}
                        onChange={(e) => setTermsAccepted(e.target.checked)}
                        className="mt-0.5 rounded border-slate-700 bg-slate-950 text-sky-500 focus:ring-sky-500 focus:ring-offset-slate-900 cursor-pointer"
                      />
                      <span className="text-slate-300 leading-snug">
                        I have read and explicitly agree to the{' '}
                        <Link
                          to="/terms"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sky-400 hover:text-sky-300 underline underline-offset-2 inline-flex items-center gap-0.5"
                        >
                          Terms of Service <ExternalLink className="w-2.5 h-2.5 inline" />
                        </Link>{' '}
                        (Draft for Legal Review).
                      </span>
                    </label>

                    {/* Privacy Policy Checkbox */}
                    <label className="flex items-start gap-2.5 cursor-pointer text-xs group">
                      <input
                        type="checkbox"
                        id="privacy_acknowledged"
                        checked={privacyAcknowledged}
                        onChange={(e) => setPrivacyAcknowledged(e.target.checked)}
                        className="mt-0.5 rounded border-slate-700 bg-slate-950 text-sky-500 focus:ring-sky-500 focus:ring-offset-slate-900 cursor-pointer"
                      />
                      <span className="text-slate-300 leading-snug">
                        I acknowledge the{' '}
                        <Link
                          to="/privacy"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sky-400 hover:text-sky-300 underline underline-offset-2 inline-flex items-center gap-0.5"
                        >
                          Privacy Policy <ExternalLink className="w-2.5 h-2.5 inline" />
                        </Link>{' '}
                        and consent to processing of account telemetry for paper trading simulation.
                      </span>
                    </label>

                    {/* Paper Trading Risk Disclosure Checkbox */}
                    <label className="flex items-start gap-2.5 cursor-pointer text-xs group">
                      <input
                        type="checkbox"
                        id="risk_disclosure_acknowledged"
                        checked={riskDisclosureAcknowledged}
                        onChange={(e) => setRiskDisclosureAcknowledged(e.target.checked)}
                        className="mt-0.5 rounded border-slate-700 bg-slate-950 text-amber-500 focus:ring-amber-500 focus:ring-offset-slate-900 cursor-pointer"
                      />
                      <span className="text-slate-300 leading-snug">
                        I acknowledge that Project ORION operates{' '}
                        <span className="text-amber-400 font-semibold">strictly as a simulated paper trading environment</span>{' '}
                        with <span className="text-amber-400 font-semibold">$0.00 capital at risk</span>, as set forth in the{' '}
                        <Link
                          to="/risk-disclosure"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-amber-400 hover:text-amber-300 underline underline-offset-2 inline-flex items-center gap-0.5"
                        >
                          Risk Disclosure <ExternalLink className="w-2.5 h-2.5 inline" />
                        </Link>.
                      </span>
                    </label>
                  </div>

                  {/* Submission Button */}
                  <div className="pt-3">
                    <Button
                      type="submit"
                      variant="primary"
                      size="md"
                      className="w-full"
                      isLoading={isSubmitting}
                      rightIcon={<ArrowRight className="w-4 h-4" />}
                    >
                      Create Paper Trading Account
                    </Button>
                  </div>

                  {/* Secondary Links */}
                  <div className="pt-2 text-center">
                    <Link
                      to="/login"
                      className="text-xs text-sky-400 hover:text-sky-300 transition-colors font-mono"
                    >
                      Already have an account? Sign in
                    </Link>
                  </div>
                </form>

                <div className="mt-6 pt-5 border-t border-slate-800/80 text-[11px] text-slate-500 flex items-center justify-center gap-1.5 font-mono">
                  <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
                  <span>Argon2id/Bcrypt Credentials &bull; Tenant IDOR Isolated</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
      <PublicFooter />
    </div>
  );
};
