import React, { useState, useEffect } from 'react';
import { Mail, CheckCircle2, AlertCircle, RefreshCw, ArrowRight, ShieldCheck, Clock } from 'lucide-react';
import { Button } from '../../common/Button';
import { Badge } from '../../common/Badge';
import { authApi } from '../../../api/endpoints';
import { getErrorMessage } from '../../../utils/errors';
import { ApiError } from '../../../api/types';

interface EmailVerificationStepProps {
  email: string;
  isVerified: boolean;
  onRefreshStatus: () => Promise<any>;
  onComplete: () => Promise<void>;
  isSubmitting: boolean;
}

export const EmailVerificationStep: React.FC<EmailVerificationStepProps> = ({
  email,
  isVerified,
  onRefreshStatus,
  onComplete,
  isSubmitting,
}) => {
  const [resendCooldown, setResendCooldown] = useState<number>(0);
  const [isResending, setIsResending] = useState<boolean>(false);
  const [resendSuccess, setResendSuccess] = useState<string | null>(null);
  const [resendError, setResendError] = useState<string | null>(null);
  const [isChecking, setIsChecking] = useState<boolean>(false);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (resendCooldown > 0) {
      timer = setTimeout(() => setResendCooldown((prev) => prev - 1), 1000);
    }
    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [resendCooldown]);

  const handleResend = async () => {
    if (resendCooldown > 0 || !email) return;

    setIsResending(true);
    setResendError(null);
    setResendSuccess(null);

    try {
      const res = await authApi.resendVerification({ email });
      setResendSuccess(res.message || 'Verification link dispatched successfully.');
      setResendCooldown(60); // 60s UX cooldown
    } catch (err: unknown) {
      if (err instanceof ApiError && err.statusCode === 429) {
        const retrySecs = err.retryAfterSeconds || 60;
        setResendCooldown(retrySecs);
        setResendError(`Rate limit exceeded. Please wait ${retrySecs} seconds before retrying.`);
      } else {
        setResendError(getErrorMessage(err));
      }
    } finally {
      setIsResending(false);
    }
  };

  const handleCheckStatus = async () => {
    setIsChecking(true);
    setResendError(null);
    try {
      await onRefreshStatus();
    } catch (err) {
      setResendError(getErrorMessage(err));
    } finally {
      setIsChecking(false);
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold font-mono tracking-tight text-slate-100">
            CORPORATE EMAIL VERIFICATION
          </h2>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Validate institutional identity and account ownership
          </p>
        </div>
        <div>
          {isVerified ? (
            <Badge variant="success" dot>
              Verified
            </Badge>
          ) : (
            <Badge variant="warning" dot>
              Pending Verification
            </Badge>
          )}
        </div>
      </div>

      {/* Email Display Card */}
      <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400 flex items-center justify-center">
            <Mail className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
              Account Email
            </div>
            <div className="text-sm font-semibold font-mono text-slate-100">{email || 'Unknown'}</div>
          </div>
        </div>
        {isVerified && (
          <div className="flex items-center gap-1.5 text-xs font-mono text-emerald-400 font-semibold">
            <ShieldCheck className="w-4 h-4" />
            Confirmed
          </div>
        )}
      </div>

      {/* Status Notice */}
      {isVerified ? (
        <div
          className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-800/40 text-emerald-300 text-xs flex items-start gap-3"
          role="status"
        >
          <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5 text-emerald-400" />
          <div>
            <div className="font-semibold text-emerald-200">Email Address Verified</div>
            <p className="mt-0.5 text-slate-300 leading-relaxed">
              Your institutional corporate email address has been verified. You can now proceed to configure your
              portfolio trading strategy.
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div
            className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs space-y-2"
            role="region"
            aria-label="Verification Instructions"
          >
            <div className="font-semibold text-slate-200 flex items-center gap-2">
              <Clock className="w-4 h-4 text-amber-400" />
              Action Required: Confirm Your Email
            </div>
            <p className="text-slate-400 leading-relaxed">
              During registration, a single-use verification email was dispatched to{' '}
              <span className="text-slate-200 font-mono">{email}</span>. Click the link in that email to verify your
              identity.
            </p>
            <p className="text-slate-500 text-[11px]">
              If you verified in another tab or window, click &quot;Check Verification Status&quot; below to synchronize.
            </p>
          </div>

          {resendSuccess && (
            <div
              className="p-3.5 rounded-lg bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 text-xs flex items-center gap-2.5"
              role="status"
            >
              <CheckCircle2 className="w-4 h-4 flex-shrink-0 text-emerald-400" />
              <span>{resendSuccess}</span>
            </div>
          )}

          {resendError && (
            <div
              className="p-3.5 rounded-lg bg-rose-950/60 border border-rose-800/60 text-rose-300 text-xs flex items-center gap-2.5"
              role="alert"
            >
              <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400" />
              <span>{resendError}</span>
            </div>
          )}

          {/* Action Row */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={handleResend}
              isLoading={isResending}
              disabled={resendCooldown > 0}
            >
              {resendCooldown > 0 ? `Resend Available in ${resendCooldown}s` : 'Resend Verification Link'}
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={handleCheckStatus}
              isLoading={isChecking}
              leftIcon={<RefreshCw className="w-4 h-4" />}
            >
              Check Verification Status
            </Button>
          </div>
        </div>
      )}

      {/* Action Footer */}
      <div className="pt-4 border-t border-slate-800 flex justify-end">
        <Button
          variant="primary"
          size="md"
          onClick={onComplete}
          isLoading={isSubmitting}
          disabled={!isVerified}
          rightIcon={<ArrowRight className="w-4 h-4" />}
        >
          {isVerified ? 'Continue to Strategy Setup' : 'Verification Required'}
        </Button>
      </div>
    </div>
  );
};
