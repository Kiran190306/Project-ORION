import React, { useState, useEffect } from 'react';
import { Check, AlertCircle } from 'lucide-react';
import type { OnboardingStatusResponse, OnboardingStep } from '../../api/types';
import { PaperTradingBadge } from '../common/Badge';
import { WelcomeStep } from './steps/WelcomeStep';
import { EmailVerificationStep } from './steps/EmailVerificationStep';
import { StrategyStep } from './steps/StrategyStep';
import { RiskStep } from './steps/RiskStep';
import { PaperReadinessStep } from './steps/PaperReadinessStep';
import { useAuth } from '../../auth/AuthContext';

interface OnboardingWizardProps {
  status: OnboardingStatusResponse;
  onRefresh: () => Promise<any>;
  onCompleteStep: (
    step: OnboardingStep,
    metadata?: Record<string, any>
  ) => Promise<OnboardingStatusResponse>;
}

export const OnboardingWizard: React.FC<OnboardingWizardProps> = ({
  status,
  onRefresh,
  onCompleteStep,
}) => {
  const { user } = useAuth();
  const [activeStep, setActiveStep] = useState<OnboardingStep>(status.current_step);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [generalError, setGeneralError] = useState<string | null>(null);

  // Sync active step whenever backend current_step changes
  useEffect(() => {
    setActiveStep(status.current_step);
  }, [status.current_step]);

  const stepMeta: Record<
    OnboardingStep,
    { index: number; title: string; shortTitle: string }
  > = {
    WELCOME: { index: 0, title: 'Welcome & Overview', shortTitle: 'Welcome' },
    EMAIL_VERIFICATION: { index: 1, title: 'Email Verification', shortTitle: 'Verification' },
    STRATEGY: { index: 2, title: 'Strategy Configuration', shortTitle: 'Strategy' },
    RISK: { index: 3, title: 'Risk Limits', shortTitle: 'Risk' },
    PAPER_TRADING_READY: { index: 4, title: 'Simulation Ready', shortTitle: 'Ready' },
  };

  const stepsList: OnboardingStep[] = [
    'WELCOME',
    'EMAIL_VERIFICATION',
    'STRATEGY',
    'RISK',
    'PAPER_TRADING_READY',
  ];

  const handleStepComplete = async (
    step: OnboardingStep,
    metadata?: Record<string, any>
  ) => {
    setIsSubmitting(true);
    setGeneralError(null);
    try {
      await onCompleteStep(step, metadata);
    } catch (err: any) {
      setGeneralError(err?.message || 'Failed to advance onboarding step.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const activeIndex = stepMeta[activeStep]?.index ?? 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-950/85 backdrop-blur-md animate-fadeIn"
      role="dialog"
      aria-modal="true"
      aria-labelledby="onboarding-wizard-title"
    >
      <div className="w-full max-w-4xl rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Wizard Header Bar */}
        <div className="px-5 py-4 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-950/50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400 font-bold font-mono text-sm flex items-center justify-center">
              Ω
            </div>
            <div>
              <h1 id="onboarding-wizard-title" className="text-sm font-bold font-mono tracking-wider text-slate-100">
                PROJECT ORION &bull; GUIDED ONBOARDING
              </h1>
              <p className="text-[11px] font-mono text-slate-400">
                Step {activeIndex + 1} of {stepsList.length}: {stepMeta[activeStep]?.title}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 self-start sm:self-auto">
            <PaperTradingBadge size="sm" />
            <span className="text-[11px] font-mono text-amber-300 font-semibold bg-amber-500/10 border border-amber-500/20 px-2.5 py-0.5 rounded-full">
              $0.00 Capital at Risk
            </span>
          </div>
        </div>

        {/* Accessible Progress Stepper Navigation */}
        <nav aria-label="Onboarding Progress" className="px-4 py-3 bg-slate-950/30 border-b border-slate-800/80 overflow-x-auto">
          <ol className="flex items-center justify-between min-w-[500px] text-xs">
            {stepsList.map((step, idx) => {
              const isCompleted = status.completed_steps.includes(step);
              const isCurrent = activeStep === step;
              const isAccessible = isCompleted || step === status.current_step;

              return (
                <li key={step} className="flex-1 flex items-center">
                  <div
                    onClick={() => {
                      if (isAccessible) {
                        setActiveStep(step);
                      }
                    }}
                    className={`flex items-center gap-2 px-2 py-1 rounded-md transition-colors ${
                      isAccessible ? 'cursor-pointer hover:bg-slate-800/60' : 'cursor-not-allowed opacity-50'
                    }`}
                    aria-current={isCurrent ? 'step' : undefined}
                  >
                    <div
                      className={`w-6 h-6 rounded-full flex items-center justify-center font-mono text-xs font-bold transition-all ${
                        isCompleted
                          ? 'bg-emerald-500 text-slate-950'
                          : isCurrent
                          ? 'bg-sky-500 text-slate-950 ring-2 ring-sky-400/40'
                          : 'bg-slate-800 text-slate-400 border border-slate-700'
                      }`}
                    >
                      {isCompleted ? <Check className="w-3.5 h-3.5 stroke-[3]" /> : idx + 1}
                    </div>
                    <span
                      className={`font-mono text-[11px] tracking-wide whitespace-nowrap ${
                        isCurrent
                          ? 'text-sky-300 font-semibold'
                          : isCompleted
                          ? 'text-slate-300'
                          : 'text-slate-500'
                      }`}
                    >
                      {stepMeta[step].shortTitle}
                    </span>
                  </div>
                  {idx < stepsList.length - 1 && (
                    <div
                      className={`flex-1 h-0.5 mx-2 ${
                        status.completed_steps.includes(stepsList[idx + 1]) ||
                        status.completed_steps.includes(step)
                          ? 'bg-emerald-500/50'
                          : 'bg-slate-800'
                      }`}
                    />
                  )}
                </li>
              );
            })}
          </ol>
        </nav>

        {/* Global Error Notice */}
        {generalError && (
          <div
            className="mx-6 mt-4 p-3.5 rounded-lg bg-rose-950/60 border border-rose-800/60 text-rose-300 text-xs flex items-center gap-2.5 animate-fadeIn"
            role="alert"
          >
            <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400" />
            <span className="flex-1">{generalError}</span>
          </div>
        )}

        {/* Step Body Container */}
        <div className="p-5 sm:p-7 overflow-y-auto flex-1 text-slate-300">
          {activeStep === 'WELCOME' && (
            <WelcomeStep
              onComplete={() => handleStepComplete('WELCOME')}
              isSubmitting={isSubmitting}
            />
          )}

          {activeStep === 'EMAIL_VERIFICATION' && (
            <EmailVerificationStep
              email={user?.email || ''}
              isVerified={status.email_verified}
              onRefreshStatus={onRefresh}
              onComplete={() => handleStepComplete('EMAIL_VERIFICATION')}
              isSubmitting={isSubmitting}
            />
          )}

          {activeStep === 'STRATEGY' && (
            <StrategyStep
              onComplete={(meta) => handleStepComplete('STRATEGY', meta)}
              isSubmitting={isSubmitting}
            />
          )}

          {activeStep === 'RISK' && (
            <RiskStep
              onComplete={(meta) => handleStepComplete('RISK', meta)}
              isSubmitting={isSubmitting}
            />
          )}

          {activeStep === 'PAPER_TRADING_READY' && (
            <PaperReadinessStep
              paperAccountReady={status.paper_account_ready}
              onComplete={() => handleStepComplete('PAPER_TRADING_READY')}
              isSubmitting={isSubmitting}
            />
          )}
        </div>

        {/* Wizard Persistent Footer Disclaimer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-950/60 flex flex-col sm:flex-row items-center justify-between gap-2 text-[11px] font-mono text-slate-500">
          <div>
            Project ORION Paper Simulation Engine &bull; Strictly{' '}
            <span className="text-amber-400 font-semibold">$0.00 Capital at Risk</span>
          </div>
          <div className="flex items-center gap-4 text-slate-400">
            <span>Server Authoritative State</span>
          </div>
        </div>
      </div>
    </div>
  );
};
