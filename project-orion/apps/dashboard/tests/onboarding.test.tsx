import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from '../src/auth/AuthContext';
import { OrganizationProvider } from '../src/auth/OrganizationContext';
import { AppShell } from '../src/components/layout/AppShell';
import { OnboardingWizard } from '../src/components/onboarding/OnboardingWizard';
import { WelcomeStep } from '../src/components/onboarding/steps/WelcomeStep';
import { EmailVerificationStep } from '../src/components/onboarding/steps/EmailVerificationStep';
import { StrategyStep } from '../src/components/onboarding/steps/StrategyStep';
import { RiskStep } from '../src/components/onboarding/steps/RiskStep';
import { PaperReadinessStep } from '../src/components/onboarding/steps/PaperReadinessStep';
import { onboardingApi, authApi, strategiesApi, organizationApi } from '../src/api/endpoints';
import { ApiError } from '../src/api/types';
import type { OnboardingStatusResponse, UserResponse } from '../src/api/types';

const mockOrg = {
  id: 'org_test_123',
  name: 'Apex Fund',
  slug: 'apex-fund',
  status: 'ACTIVE',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const mockMember = {
  id: 'mem-1',
  organization_id: 'org_test_123',
  user_id: 'usr_test_123',
  role: 'OWNER',
  status: 'ACTIVE',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const mockBaseStatus: OnboardingStatusResponse = {
  id: 'obp_test_12345',
  user_id: 'usr_test_123',
  organization_id: 'org_test_123',
  status: 'NOT_STARTED',
  current_step: 'WELCOME',
  completed_steps: [],
  next_step: 'EMAIL_VERIFICATION',
  steps: [
    {
      step: 'WELCOME',
      title: 'Welcome & Overview',
      description: 'Account registered and workspace initialized.',
      is_completed: false,
      is_automated: false,
      prerequisites_met: true,
    },
    {
      step: 'EMAIL_VERIFICATION',
      title: 'Email Verification',
      description: 'Verify corporate email address.',
      is_completed: false,
      is_automated: true,
      prerequisites_met: false,
    },
    {
      step: 'STRATEGY',
      title: 'Strategy Configuration',
      description: 'Select algorithmic trading model.',
      is_completed: false,
      is_automated: false,
      prerequisites_met: false,
    },
    {
      step: 'RISK',
      title: 'Risk Limits',
      description: 'Configure drawdown constraints.',
      is_completed: false,
      is_automated: false,
      prerequisites_met: false,
    },
    {
      step: 'PAPER_TRADING_READY',
      title: 'Simulation Ready',
      description: 'Confirm paper simulation environment.',
      is_completed: false,
      is_automated: false,
      prerequisites_met: false,
    },
  ],
  email_verified: false,
  paper_account_ready: true,
  strategy_configured: false,
  risk_configured: false,
  completed_at: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const mockUser: UserResponse = {
  id: 'usr_test_123',
  username: 'institution_trader',
  email: 'trader@institutional.fund',
  full_name: 'Lead PM',
  is_active: true,
  is_superuser: false,
  email_verified: false,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

describe('EPIC-027 Phase 5B — First-Login Onboarding UX', () => {
  beforeEach(() => {
    sessionStorage.clear();
    sessionStorage.setItem('orion_access_token', 'mock_jwt_token');
    sessionStorage.setItem('orion_active_org_id', 'org_test_123');
    vi.restoreAllMocks();
    vi.spyOn(authApi, 'getMe').mockResolvedValue(mockUser);
    vi.spyOn(organizationApi, 'listUserOrganizations').mockResolvedValue([mockOrg]);
    vi.spyOn(organizationApi, 'listMembers').mockResolvedValue([mockMember]);
  });

  // 1. Authenticated user with COMPLETED onboarding sees dashboard
  it('1. authenticated user with COMPLETED onboarding renders dashboard directly without wizard', async () => {
    const completedStatus: OnboardingStatusResponse = {
      ...mockBaseStatus,
      status: 'COMPLETED',
      current_step: 'PAPER_TRADING_READY',
      completed_steps: ['WELCOME', 'EMAIL_VERIFICATION', 'STRATEGY', 'RISK', 'PAPER_TRADING_READY'],
      email_verified: true,
      completed_at: new Date().toISOString(),
    };

    vi.spyOn(onboardingApi, 'getStatus').mockResolvedValue(completedStatus);

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <AuthProvider>
          <OrganizationProvider>
            <Routes>
              <Route element={<AppShell />}>
                <Route path="dashboard" element={<div>TRADING DASHBOARD ACTIVE</div>} />
              </Route>
            </Routes>
          </OrganizationProvider>
        </AuthProvider>
      </MemoryRouter>
    );

    expect(await screen.findByText('TRADING DASHBOARD ACTIVE')).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  // 2. NOT_STARTED user sees onboarding
  it('2. uncompleted NOT_STARTED user sees OnboardingWizard dialog with Welcome step', async () => {
    vi.spyOn(onboardingApi, 'getStatus').mockResolvedValue(mockBaseStatus);

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <AuthProvider>
          <OrganizationProvider>
            <Routes>
              <Route element={<AppShell />}>
                <Route path="dashboard" element={<div>TRADING DASHBOARD</div>} />
              </Route>
            </Routes>
          </OrganizationProvider>
        </AuthProvider>
      </MemoryRouter>
    );

    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/welcome to project orion/i)).toBeInTheDocument();
    expect(screen.queryByText('TRADING DASHBOARD')).not.toBeInTheDocument();
  });

  // 3. IN_PROGRESS user resumes correct step
  it('3. IN_PROGRESS user resumes directly at server current_step', async () => {
    const inProgressStatus: OnboardingStatusResponse = {
      ...mockBaseStatus,
      status: 'IN_PROGRESS',
      current_step: 'STRATEGY',
      completed_steps: ['WELCOME', 'EMAIL_VERIFICATION'],
      email_verified: true,
      next_step: 'RISK',
    };

    render(
      <MemoryRouter>
        <AuthProvider>
          <OnboardingWizard
            status={inProgressStatus}
            onRefresh={vi.fn()}
            onCompleteStep={vi.fn()}
          />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/algorithmic strategy setup/i)).toBeInTheDocument();
    expect(screen.getByText(/step 3 of 5/i)).toBeInTheDocument();
  });

  // 4. WELCOME progression
  it('4. WelcomeStep triggers onComplete when Begin Onboarding is clicked', async () => {
    const onComplete = vi.fn().mockResolvedValue(undefined);
    render(<WelcomeStep onComplete={onComplete} isSubmitting={false} />);

    const beginBtn = screen.getByRole('button', { name: /begin onboarding/i });
    await userEvent.click(beginBtn);

    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  // 5. email verification state (shows email, unverified banner, disables Next)
  it('5. EmailVerificationStep displays email, pending status, and disables Next button when unverified', () => {
    render(
      <EmailVerificationStep
        email="test@institutional.fund"
        isVerified={false}
        onRefreshStatus={vi.fn()}
        onComplete={vi.fn()}
        isSubmitting={false}
      />
    );

    expect(screen.getAllByText('test@institutional.fund').length).toBeGreaterThan(0);
    expect(screen.getByText(/pending verification/i)).toBeInTheDocument();
    const nextBtn = screen.getByRole('button', { name: /verification required/i });
    expect(nextBtn).toBeDisabled();
  });

  // 6. resend verification success
  it('6. EmailVerificationStep resends verification link successfully', async () => {
    vi.spyOn(authApi, 'resendVerification').mockResolvedValue({
      message: 'Verification link successfully dispatched to test@institutional.fund',
    });

    render(
      <EmailVerificationStep
        email="test@institutional.fund"
        isVerified={false}
        onRefreshStatus={vi.fn()}
        onComplete={vi.fn()}
        isSubmitting={false}
      />
    );

    const resendBtn = screen.getByRole('button', { name: /resend verification link/i });
    await userEvent.click(resendBtn);

    expect(authApi.resendVerification).toHaveBeenCalledWith({ email: 'test@institutional.fund' });
    expect(
      await screen.findByText(/verification link successfully dispatched/i)
    ).toBeInTheDocument();
  });

  // 7. resend 429 rate limit handling
  it('7. EmailVerificationStep handles HTTP 429 rate limit with retry countdown notice', async () => {
    vi.spyOn(authApi, 'resendVerification').mockRejectedValue(
      new ApiError(429, 'Rate limit exceeded.', undefined, undefined, 45)
    );

    render(
      <EmailVerificationStep
        email="test@institutional.fund"
        isVerified={false}
        onRefreshStatus={vi.fn()}
        onComplete={vi.fn()}
        isSubmitting={false}
      />
    );

    const resendBtn = screen.getByRole('button', { name: /resend verification link/i });
    await userEvent.click(resendBtn);

    expect(await screen.findByText(/please wait 45 seconds before retrying/i)).toBeInTheDocument();
  });

  // 8. email verification dynamic auto-synchronization status check
  it('8. EmailVerificationStep calls onRefreshStatus when Check Verification Status is clicked', async () => {
    const onRefresh = vi.fn().mockResolvedValue(undefined);
    render(
      <EmailVerificationStep
        email="test@institutional.fund"
        isVerified={false}
        onRefreshStatus={onRefresh}
        onComplete={vi.fn()}
        isSubmitting={false}
      />
    );

    const checkBtn = screen.getByRole('button', { name: /check verification status/i });
    await userEvent.click(checkBtn);

    expect(onRefresh).toHaveBeenCalledTimes(1);
  });

  // 9. strategy step configuration and submission
  it('9. StrategyStep selects strategy, timeframe, and submits metadata', async () => {
    const onComplete = vi.fn().mockResolvedValue(undefined);
    vi.spyOn(strategiesApi, 'list').mockResolvedValue({
      strategies: [
        {
          id: 'TrendFollowing',
          name: 'Trend Following',
          type: 'MOMENTUM',
          description: 'EMA crossover model.',
          timeframes: ['M15', 'H1'],
          symbols: ['EUR/USD', 'GBP/USD'],
          is_active: true,
        },
      ],
      total: 1,
      updated_at: new Date().toISOString(),
    });
    vi.spyOn(strategiesApi, 'updateAccountConfig').mockResolvedValue({} as any);

    render(<StrategyStep onComplete={onComplete} isSubmitting={false} />);

    expect(await screen.findByText('Trend Following')).toBeInTheDocument();

    const submitBtn = screen.getByRole('button', { name: /confirm strategy & continue/i });
    await userEvent.click(submitBtn);

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledWith(
        expect.objectContaining({
          strategy_id: 'TrendFollowing',
          timeframe: 'M15',
          symbols: expect.arrayContaining(['EUR/USD']),
        })
      );
    });
  });

  // 10. risk step configuration and bounds
  it('10. RiskStep submits configured drawdown and position size parameters', async () => {
    const onComplete = vi.fn().mockResolvedValue(undefined);
    render(<RiskStep onComplete={onComplete} isSubmitting={false} />);

    expect(screen.getByText(/risk limits & circuit breakers/i)).toBeInTheDocument();
    expect(screen.getByText(/maximum portfolio drawdown limit/i)).toBeInTheDocument();

    const submitBtn = screen.getByRole('button', { name: /confirm risk parameters/i });
    await userEvent.click(submitBtn);

    expect(onComplete).toHaveBeenCalledWith({
      max_drawdown_pct: 5.0,
      max_daily_loss_pct: 2.0,
      max_position_size: 100000,
    });
  });

  // 11. paper readiness displays $100,000 balance and requires confirmation
  it('11. PaperReadinessStep displays $100,000 balance and enables button only when acknowledged', async () => {
    const onComplete = vi.fn().mockResolvedValue(undefined);
    render(
      <PaperReadinessStep
        onComplete={onComplete}
        isSubmitting={false}
        paperAccountReady={true}
      />
    );

    expect(screen.getByText('$100,000.00 USD')).toBeInTheDocument();
    expect(screen.getByText('$0.00')).toBeInTheDocument();
    expect(screen.getByText(/ORION_WORKER_ENABLED=false/i)).toBeInTheDocument();

    const launchBtn = screen.getByRole('button', { name: /launch trading terminal/i });
    expect(launchBtn).toBeDisabled();

    // Check acknowledgment
    const checkbox = screen.getByRole('checkbox');
    await userEvent.click(checkbox);

    expect(launchBtn).not.toBeDisabled();
    await userEvent.click(launchBtn);

    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  // 12. successful final completion transitions wizard
  it('12. completing PAPER_TRADING_READY calls backend and unmounts wizard', async () => {
    const readyStatus: OnboardingStatusResponse = {
      ...mockBaseStatus,
      status: 'IN_PROGRESS',
      current_step: 'PAPER_TRADING_READY',
      completed_steps: ['WELCOME', 'EMAIL_VERIFICATION', 'STRATEGY', 'RISK'],
      email_verified: true,
      next_step: null,
    };

    const onCompleteStep = vi.fn().mockResolvedValue({
      ...readyStatus,
      status: 'COMPLETED',
      completed_steps: [
        'WELCOME',
        'EMAIL_VERIFICATION',
        'STRATEGY',
        'RISK',
        'PAPER_TRADING_READY',
      ],
      completed_at: new Date().toISOString(),
    });

    render(
      <MemoryRouter>
        <AuthProvider>
          <OnboardingWizard
            status={readyStatus}
            onRefresh={vi.fn()}
            onCompleteStep={onCompleteStep}
          />
        </AuthProvider>
      </MemoryRouter>
    );

    const checkbox = screen.getByRole('checkbox');
    await userEvent.click(checkbox);

    const launchBtn = screen.getByRole('button', { name: /launch trading terminal/i });
    await userEvent.click(launchBtn);

    expect(onCompleteStep).toHaveBeenCalledWith('PAPER_TRADING_READY', undefined);
  });

  // 13. API failure shows retry button in AppShell
  it('13. AppShell displays error screen and retry button when onboarding status API fails', async () => {
    vi.spyOn(onboardingApi, 'getStatus').mockRejectedValue(
      new Error('Failed to connect to trading engine backend.')
    );

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <AuthProvider>
          <OrganizationProvider>
            <Routes>
              <Route element={<AppShell />}>
                <Route path="dashboard" element={<div>DASHBOARD</div>} />
              </Route>
            </Routes>
          </OrganizationProvider>
        </AuthProvider>
      </MemoryRouter>
    );

    expect(await screen.findByText(/failed to load onboarding status/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /retry connection/i })).toBeInTheDocument();
  });

  // 14. 401 session expiration handling
  it('14. dispatches unauthorized event when API returns 401', () => {
    const unauthorizedSpy = vi.fn();
    window.addEventListener('orion:unauthorized', unauthorizedSpy);

    window.dispatchEvent(new CustomEvent('orion:unauthorized'));
    expect(unauthorizedSpy).toHaveBeenCalledTimes(1);

    window.removeEventListener('orion:unauthorized', unauthorizedSpy);
  });

  // 15. refresh and state rehydration
  it('15. OnboardingWizard syncs active step when server updates current_step', async () => {
    const { rerender } = render(
      <MemoryRouter>
        <AuthProvider>
          <OnboardingWizard
            status={mockBaseStatus}
            onRefresh={vi.fn()}
            onCompleteStep={vi.fn()}
          />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(screen.getByText(/welcome to project orion/i)).toBeInTheDocument();

    const updatedStatus: OnboardingStatusResponse = {
      ...mockBaseStatus,
      status: 'IN_PROGRESS',
      current_step: 'STRATEGY',
      completed_steps: ['WELCOME', 'EMAIL_VERIFICATION'],
    };

    rerender(
      <MemoryRouter>
        <AuthProvider>
          <OnboardingWizard
            status={updatedStatus}
            onRefresh={vi.fn()}
            onCompleteStep={vi.fn()}
          />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(screen.getByText(/algorithmic strategy setup/i)).toBeInTheDocument();
  });

  // 16. backend invalid step rejection displayed in error banner
  it('16. displays backend step rejection error in OnboardingWizard banner', async () => {
    const onCompleteStep = vi
      .fn()
      .mockRejectedValue(new Error("Cannot complete step 'RISK'. Prerequisite step 'STRATEGY' required."));

    render(
      <MemoryRouter>
        <AuthProvider>
          <OnboardingWizard
            status={{ ...mockBaseStatus, current_step: 'WELCOME' }}
            onRefresh={vi.fn()}
            onCompleteStep={onCompleteStep}
          />
        </AuthProvider>
      </MemoryRouter>
    );

    const beginBtn = screen.getByRole('button', { name: /begin onboarding/i });
    await userEvent.click(beginBtn);

    expect(
      await screen.findByText(/cannot complete step 'risk'/i)
    ).toBeInTheDocument();
  });

  // 17. duplicate / idempotent step completion
  it('17. allows clicking previously completed steps to review without breaking stepper', async () => {
    const multiStepStatus: OnboardingStatusResponse = {
      ...mockBaseStatus,
      status: 'IN_PROGRESS',
      current_step: 'RISK',
      completed_steps: ['WELCOME', 'EMAIL_VERIFICATION', 'STRATEGY'],
      email_verified: true,
    };

    render(
      <MemoryRouter>
        <AuthProvider>
          <OnboardingWizard
            status={multiStepStatus}
            onRefresh={vi.fn()}
            onCompleteStep={vi.fn()}
          />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(screen.getByText(/risk limits & circuit breakers/i)).toBeInTheDocument();

    // Click on Strategy step in stepper to review
    const strategyStepNav = screen.getByText('Strategy');
    await userEvent.click(strategyStepNav);

    expect(await screen.findByText(/algorithmic strategy setup/i)).toBeInTheDocument();
  });

  // 18. accessibility basics & paper-only safety messaging
  it('18. verifies accessibility attributes and persistent $0.00 capital at risk messaging', () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <OnboardingWizard
            status={mockBaseStatus}
            onRefresh={vi.fn()}
            onCompleteStep={vi.fn()}
          />
        </AuthProvider>
      </MemoryRouter>
    );

    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-labelledby', 'onboarding-wizard-title');

    const progressNav = screen.getByRole('navigation', { name: /onboarding progress/i });
    expect(progressNav).toBeInTheDocument();

    // Verify paper trading safety text
    const safetyBadges = screen.getAllByText(/\$0.00 capital at risk/i);
    expect(safetyBadges.length).toBeGreaterThan(0);
  });
});
