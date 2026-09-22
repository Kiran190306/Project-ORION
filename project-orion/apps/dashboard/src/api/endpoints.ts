/**
 * Strongly typed endpoint callers consuming the verified FastAPI backend.
 */

import { apiClient } from './client';
import type {
  AccountResponse,
  AccountStrategyConfigResponse,
  AccountSummary,
  AuditLogResponse,
  BillingInvoiceResponse,
  BillingOverviewResponse,
  BillingSubscriptionResponse,
  CancelOrderResponse,
  CheckoutResponse,
  ClosePositionResponse,
  CreateInvitationRequest,
  CreateOrderRequest,
  DashboardResponse,
  EquityCurveResponse,
  ExposureResponse,
  ForgotPasswordRequest,
  GenericMessageResponse,
  InvitationResponse,
  LoginRequest,
  LoginResponse,
  ResetPasswordRequest,
  ResendVerificationRequest,
  DeactivateAccountRequest,
  VerifyEmailRequest,
  OnboardingRegisterRequest,
  OnboardingResponse,
  MarketCandlesResponse,
  MarketHealth,
  MarketInstrument,
  MarketQuote,
  OrderResponse,
  OrganizationMemberResponse,
  OrganizationResponse,
  PaginatedResponse,
  PaginationParams,
  PaperConfigResponse,
  PaperResetRequest,
  PaperResetResponse,
  PnLBreakdownResponse,
  PortfolioOverviewResponse,
  PositionResponse,
  RiskLimitsResponse,
  RiskStatusResponse,
  StrategyConfigSchemaResponse,
  StrategyDetailResponse,
  StrategyListResponse,
  TradeResponse,
  UpdateAccountStrategyRequest,
  UpdateOrganizationRequest,
  UpdatePaperConfigRequest,
  UserResponse,
  WorkerMetricsResponse,
  WorkerStatusResponse,
  StrategyCatalogueItem,
  CreateExperimentRequest,
  ExperimentSummary,
  ExperimentDetail,
  ExperimentEquityResponse,
  ExperimentTradesResponse,
  CompareExperimentsRequest,
  ExperimentComparisonResponse,
  StrategyDefaultSpaceResponse,
  OptimizationRunRequest,
  WalkForwardRunRequest,
  OptimizationJobSummary,
  OptimizationJobDetail,
  SensitivityHeatmap,
  DeploymentDetail,
  DeploymentListResponse,
  PromoteFromOptimizationRequest,
  PromoteFromExperimentRequest,
  QualityGateReport,
  BrokerProviderInfo,
  BrokerSandboxAccount,
  BrokerSandboxAccountCreateRequest,
  BrokerSandboxConnectResponse,
  BrokerSandboxOrderRequest,
  BrokerSandboxOrderResponse,
  BrokerSandboxPosition,
  BrokerSandboxReconciliationResponse,
} from './types';

// ─── Authentication ──────────────────────────────────────────────────────────

export const authApi = {
  login: (credentials: LoginRequest): Promise<LoginResponse> =>
    apiClient<LoginResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    }),

  logout: (): Promise<{ message: string }> =>
    apiClient<{ message: string }>('/api/v1/auth/logout', {
      method: 'POST',
    }),

  getMe: (): Promise<UserResponse> =>
    apiClient<UserResponse>('/api/v1/auth/me', {
      method: 'GET',
    }),

  forgotPassword: (data: ForgotPasswordRequest): Promise<GenericMessageResponse> =>
    apiClient<GenericMessageResponse>('/api/v1/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  resetPassword: (data: ResetPasswordRequest): Promise<GenericMessageResponse> =>
    apiClient<GenericMessageResponse>('/api/v1/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  verifyEmail: (data: VerifyEmailRequest): Promise<GenericMessageResponse> =>
    apiClient<GenericMessageResponse>('/api/v1/auth/verify-email', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  resendVerification: (data: ResendVerificationRequest): Promise<GenericMessageResponse> =>
    apiClient<GenericMessageResponse>('/api/v1/auth/resend-verification', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  deactivateAccount: (data: DeactivateAccountRequest): Promise<GenericMessageResponse> =>
    apiClient<GenericMessageResponse>('/api/v1/auth/deactivate', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

// ─── Onboarding ──────────────────────────────────────────────────────────────

export const onboardingApi = {
  register: (data: OnboardingRegisterRequest): Promise<OnboardingResponse> =>
    apiClient<OnboardingResponse>('/api/v1/onboarding/register', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

// ─── Account ─────────────────────────────────────────────────────────────────

export const accountApi = {
  getSummary: (): Promise<AccountSummary> =>
    apiClient<AccountSummary>('/api/v1/account/summary', {
      method: 'GET',
    }),

  getDetails: (): Promise<AccountResponse> =>
    apiClient<AccountResponse>('/api/v1/account/', {
      method: 'GET',
    }),
};

// ─── Orders ──────────────────────────────────────────────────────────────────

export const ordersApi = {
  list: (
    params?: PaginationParams & { symbol?: string; status?: string }
  ): Promise<PaginatedResponse<OrderResponse>> =>
    apiClient<PaginatedResponse<OrderResponse>>('/api/v1/orders/', {
      method: 'GET',
      params: params as Record<string, string | number | boolean | undefined>,
    }),

  getById: (orderId: string): Promise<OrderResponse> =>
    apiClient<OrderResponse>(`/api/v1/orders/${encodeURIComponent(orderId)}`, {
      method: 'GET',
    }),

  create: (request: CreateOrderRequest): Promise<OrderResponse> =>
    apiClient<OrderResponse>('/api/v1/orders/', {
      method: 'POST',
      body: JSON.stringify(request),
    }),

  cancel: (orderId: string): Promise<CancelOrderResponse> =>
    apiClient<CancelOrderResponse>(`/api/v1/orders/${encodeURIComponent(orderId)}/cancel`, {
      method: 'POST',
    }),
};

// ─── Positions ───────────────────────────────────────────────────────────────

export const positionsApi = {
  list: (
    params?: PaginationParams & { symbol?: string; is_open?: boolean }
  ): Promise<PaginatedResponse<PositionResponse>> =>
    apiClient<PaginatedResponse<PositionResponse>>('/api/v1/positions/', {
      method: 'GET',
      params: params as Record<string, string | number | boolean | undefined>,
    }),

  getById: (positionId: string): Promise<PositionResponse> =>
    apiClient<PositionResponse>(`/api/v1/positions/${encodeURIComponent(positionId)}`, {
      method: 'GET',
    }),

  close: (positionId: string): Promise<ClosePositionResponse> =>
    apiClient<ClosePositionResponse>(`/api/v1/positions/${encodeURIComponent(positionId)}/close`, {
      method: 'POST',
    }),
};

// ─── Trades (Fills) ──────────────────────────────────────────────────────────

export const tradesApi = {
  list: (
    params?: PaginationParams & { symbol?: string }
  ): Promise<PaginatedResponse<TradeResponse>> =>
    apiClient<PaginatedResponse<TradeResponse>>('/api/v1/trades/', {
      method: 'GET',
      params: params as Record<string, string | number | boolean | undefined>,
    }),

  getById: (tradeId: string): Promise<TradeResponse> =>
    apiClient<TradeResponse>(`/api/v1/trades/${encodeURIComponent(tradeId)}`, {
      method: 'GET',
    }),
};

// ─── Portfolio ───────────────────────────────────────────────────────────────

export const portfolioApi = {
  getOverview: (): Promise<PortfolioOverviewResponse> =>
    apiClient<PortfolioOverviewResponse>('/api/v1/portfolio/', {
      method: 'GET',
    }),

  getEquityCurve: (): Promise<EquityCurveResponse> =>
    apiClient<EquityCurveResponse>('/api/v1/portfolio/equity', {
      method: 'GET',
    }),

  getPnL: (): Promise<PnLBreakdownResponse> =>
    apiClient<PnLBreakdownResponse>('/api/v1/portfolio/pnl', {
      method: 'GET',
    }),

  getExposure: (): Promise<ExposureResponse> =>
    apiClient<ExposureResponse>('/api/v1/portfolio/exposure', {
      method: 'GET',
    }),
};

// ─── Strategies ──────────────────────────────────────────────────────────────

export const strategiesApi = {
  list: (): Promise<StrategyListResponse> =>
    apiClient<StrategyListResponse>('/api/v1/strategies/', {
      method: 'GET',
    }),

  getById: (strategyId: string): Promise<StrategyDetailResponse> =>
    apiClient<StrategyDetailResponse>(`/api/v1/strategies/${encodeURIComponent(strategyId)}`, {
      method: 'GET',
    }),

  getSchema: (strategyId: string): Promise<StrategyConfigSchemaResponse> =>
    apiClient<StrategyConfigSchemaResponse>(
      `/api/v1/strategies/${encodeURIComponent(strategyId)}/config-schema`,
      {
        method: 'GET',
      }
    ),

  getAccountConfig: (): Promise<AccountStrategyConfigResponse> =>
    apiClient<AccountStrategyConfigResponse>('/api/v1/strategies/account/config', {
      method: 'GET',
    }),

  updateAccountConfig: (
    config: UpdateAccountStrategyRequest
  ): Promise<AccountStrategyConfigResponse> =>
    apiClient<AccountStrategyConfigResponse>('/api/v1/strategies/account/config', {
      method: 'PUT',
      body: JSON.stringify(config),
    }),
};

// ─── Risk ────────────────────────────────────────────────────────────────────

export const riskApi = {
  getStatus: (): Promise<RiskStatusResponse> =>
    apiClient<RiskStatusResponse>('/api/v1/risk/status', {
      method: 'GET',
    }),

  getLimits: (): Promise<RiskLimitsResponse> =>
    apiClient<RiskLimitsResponse>('/api/v1/risk/limits', {
      method: 'GET',
    }),
};

// ─── Worker ──────────────────────────────────────────────────────────────────

export const workerApi = {
  getStatus: (): Promise<WorkerStatusResponse> =>
    apiClient<WorkerStatusResponse>('/api/v1/worker/status', {
      method: 'GET',
    }),

  getMetrics: (): Promise<WorkerMetricsResponse> =>
    apiClient<WorkerMetricsResponse>('/api/v1/worker/metrics', {
      method: 'GET',
    }),
};

// ─── Consolidated Dashboard ──────────────────────────────────────────────────

export const dashboardApi = {
  get: (): Promise<DashboardResponse> =>
    apiClient<DashboardResponse>('/api/v1/dashboard/', {
      method: 'GET',
    }),
};

// ─── Commercial Billing ──────────────────────────────────────────────────────

export const billingApi = {
  getOverview: (): Promise<BillingOverviewResponse> =>
    apiClient<BillingOverviewResponse>('/api/v1/billing', {
      method: 'GET',
    }),

  listInvoices: (): Promise<BillingInvoiceResponse[]> =>
    apiClient<BillingInvoiceResponse[]>('/api/v1/billing/invoices', {
      method: 'GET',
    }),

  createCheckout: (planCode: string): Promise<CheckoutResponse> =>
    apiClient<CheckoutResponse>('/api/v1/billing/checkout', {
      method: 'POST',
      body: JSON.stringify({ plan_code: planCode }),
    }),

  cancelSubscription: (atPeriodEnd: boolean = true): Promise<BillingSubscriptionResponse> =>
    apiClient<BillingSubscriptionResponse>('/api/v1/billing/subscription/cancel', {
      method: 'POST',
      body: JSON.stringify({ at_period_end: atPeriodEnd }),
    }),
};

// ─── Organization & Governance ──────────────────────────────────────────────

export const organizationApi = {
  listUserOrganizations: (): Promise<OrganizationResponse[]> =>
    apiClient<OrganizationResponse[]>('/api/v1/organizations', {
      method: 'GET',
    }),

  getById: (orgId: string): Promise<OrganizationResponse> =>
    apiClient<OrganizationResponse>(`/api/v1/organizations/${encodeURIComponent(orgId)}`, {
      method: 'GET',
    }),

  update: (orgId: string, req: UpdateOrganizationRequest): Promise<OrganizationResponse> =>
    apiClient<OrganizationResponse>(`/api/v1/organizations/${encodeURIComponent(orgId)}`, {
      method: 'PATCH',
      body: JSON.stringify(req),
    }),

  listMembers: (orgId: string): Promise<OrganizationMemberResponse[]> =>
    apiClient<OrganizationMemberResponse[]>(
      `/api/v1/organizations/${encodeURIComponent(orgId)}/members`,
      {
        method: 'GET',
      }
    ),

  updateMemberRole: (
    orgId: string,
    userId: string,
    role: string
  ): Promise<OrganizationMemberResponse> =>
    apiClient<OrganizationMemberResponse>(
      `/api/v1/organizations/${encodeURIComponent(orgId)}/members/${encodeURIComponent(userId)}/role`,
      {
        method: 'PATCH',
        body: JSON.stringify({ role }),
      }
    ),

  removeMember: (orgId: string, userId: string): Promise<void> =>
    apiClient<void>(
      `/api/v1/organizations/${encodeURIComponent(orgId)}/members/${encodeURIComponent(userId)}`,
      {
        method: 'DELETE',
      }
    ),

  inviteMember: (orgId: string, req: CreateInvitationRequest): Promise<InvitationResponse> =>
    apiClient<InvitationResponse>(
      `/api/v1/organizations/${encodeURIComponent(orgId)}/members/invite`,
      {
        method: 'POST',
        body: JSON.stringify(req),
      }
    ),

  listAuditLogs: (
    orgId: string,
    params?: { limit?: number; offset?: number; event_type?: string }
  ): Promise<AuditLogResponse[]> =>
    apiClient<AuditLogResponse[]>(
      `/api/v1/organizations/${encodeURIComponent(orgId)}/audit-logs`,
      {
        method: 'GET',
        params: params as Record<string, string | number | boolean | undefined>,
      }
    ),
};

// ─── Market Data (EPIC-021) ──────────────────────────────────────────────────

export const marketDataApi = {
  getInstruments: (): Promise<MarketInstrument[]> =>
    apiClient<MarketInstrument[]>('/api/v1/market-data/instruments', {
      method: 'GET',
    }),

  getQuote: (symbol: string): Promise<MarketQuote> =>
    apiClient<MarketQuote>(`/api/v1/market-data/quotes/${encodeURIComponent(symbol)}`, {
      method: 'GET',
    }),

  getCandles: (
    symbol: string,
    params?: { timeframe?: string; limit?: number; start?: string; end?: string }
  ): Promise<MarketCandlesResponse> =>
    apiClient<MarketCandlesResponse>('/api/v1/market-data/candles', {
      method: 'GET',
      params: { symbol, ...params } as Record<string, string | number | boolean | undefined>,
    }),

  getHealth: (): Promise<MarketHealth> =>
    apiClient<MarketHealth>('/api/v1/market-data/health', {
      method: 'GET',
    }),
};

// ─── Paper Trading (EPIC-022) ────────────────────────────────────────────────

export const paperApi = {
  reset: (req?: PaperResetRequest): Promise<PaperResetResponse> =>
    apiClient<PaperResetResponse>('/api/v1/trading/paper/reset', {
      method: 'POST',
      body: JSON.stringify(req || { initial_balance: 100000.0 }),
    }),

  getConfig: (): Promise<PaperConfigResponse> =>
    apiClient<PaperConfigResponse>('/api/v1/trading/paper/config', {
      method: 'GET',
    }),

  updateConfig: (req: UpdatePaperConfigRequest): Promise<PaperConfigResponse> =>
    apiClient<PaperConfigResponse>('/api/v1/trading/paper/config', {
      method: 'PATCH',
      body: JSON.stringify(req),
    }),
};

// ─── Research & Strategy Lab (EPIC-023) ──────────────────────────────────────

export const researchApi = {
  listStrategies: (): Promise<StrategyCatalogueItem[]> =>
    apiClient<StrategyCatalogueItem[]>('/api/v1/research/strategies', {
      method: 'GET',
    }),

  getStrategy: (strategyId: string): Promise<StrategyCatalogueItem> =>
    apiClient<StrategyCatalogueItem>(`/api/v1/research/strategies/${encodeURIComponent(strategyId)}`, {
      method: 'GET',
    }),

  createExperiment: (req: CreateExperimentRequest): Promise<ExperimentSummary> =>
    apiClient<ExperimentSummary>('/api/v1/research/experiments', {
      method: 'POST',
      body: JSON.stringify(req),
    }),

  listExperiments: (params?: { status?: string; limit?: number; offset?: number }): Promise<ExperimentSummary[]> =>
    apiClient<ExperimentSummary[]>('/api/v1/research/experiments', {
      method: 'GET',
      params: params as Record<string, string | number | boolean | undefined>,
    }),

  getExperiment: (experimentId: string): Promise<ExperimentDetail> =>
    apiClient<ExperimentDetail>(`/api/v1/research/experiments/${encodeURIComponent(experimentId)}`, {
      method: 'GET',
    }),

  cancelExperiment: (experimentId: string): Promise<ExperimentSummary> =>
    apiClient<ExperimentSummary>(`/api/v1/research/experiments/${encodeURIComponent(experimentId)}/cancel`, {
      method: 'POST',
    }),

  getResults: (experimentId: string): Promise<any> =>
    apiClient<any>(`/api/v1/research/experiments/${encodeURIComponent(experimentId)}/results`, {
      method: 'GET',
    }),

  getEquityCurve: (experimentId: string): Promise<ExperimentEquityResponse> =>
    apiClient<ExperimentEquityResponse>(`/api/v1/research/experiments/${encodeURIComponent(experimentId)}/equity-curve`, {
      method: 'GET',
    }),

  getTrades: (experimentId: string): Promise<ExperimentTradesResponse> =>
    apiClient<ExperimentTradesResponse>(`/api/v1/research/experiments/${encodeURIComponent(experimentId)}/trades`, {
      method: 'GET',
    }),

  compare: (req: CompareExperimentsRequest): Promise<ExperimentComparisonResponse> =>
    apiClient<ExperimentComparisonResponse>('/api/v1/research/experiments/compare', {
      method: 'POST',
      body: JSON.stringify(req),
    }),

  getExportUrl: (experimentId: string, format: 'csv' | 'json' = 'csv'): string =>
    `/api/v1/research/experiments/${encodeURIComponent(experimentId)}/export?format=${format}`,
};

// ─── EPIC-024: Quantitative Strategy Optimization Engine ───────────────────

export const optimizationApi = {
  getDefaultSpace: (strategyId: string): Promise<StrategyDefaultSpaceResponse> =>
    apiClient<StrategyDefaultSpaceResponse>(`/api/v1/optimization/spaces/${encodeURIComponent(strategyId)}`, {
      method: 'GET',
    }),

  runOptimization: (req: OptimizationRunRequest): Promise<OptimizationJobDetail> =>
    apiClient<OptimizationJobDetail>('/api/v1/optimization/run', {
      method: 'POST',
      body: JSON.stringify(req),
    }),

  runWalkForward: (req: WalkForwardRunRequest): Promise<OptimizationJobDetail> =>
    apiClient<OptimizationJobDetail>('/api/v1/optimization/walk-forward', {
      method: 'POST',
      body: JSON.stringify(req),
    }),

  listJobs: (status?: string): Promise<OptimizationJobSummary[]> => {
    const query = status ? `?status=${encodeURIComponent(status)}` : '';
    return apiClient<OptimizationJobSummary[]>(`/api/v1/optimization/jobs${query}`, {
      method: 'GET',
    });
  },

  getJob: (jobId: string): Promise<OptimizationJobDetail> =>
    apiClient<OptimizationJobDetail>(`/api/v1/optimization/jobs/${encodeURIComponent(jobId)}`, {
      method: 'GET',
    }),

  cancelJob: (jobId: string): Promise<{ status: string; job_id: string }> =>
    apiClient<{ status: string; job_id: string }>(`/api/v1/optimization/jobs/${encodeURIComponent(jobId)}/cancel`, {
      method: 'POST',
    }),

  getHeatmap: (jobId: string): Promise<SensitivityHeatmap> =>
    apiClient<SensitivityHeatmap>(`/api/v1/optimization/jobs/${encodeURIComponent(jobId)}/heatmap`, {
      method: 'GET',
    }),

  getExportUrl: (jobId: string, format: 'csv' | 'json' = 'csv'): string =>
    `/api/v1/optimization/jobs/${encodeURIComponent(jobId)}/export?format=${format}`,
};

// ─── EPIC-025: Strategy Deployment Pipeline & Paper Incubator ───────────────

export const deploymentApi = {
  promoteFromOptimization: (req: PromoteFromOptimizationRequest): Promise<DeploymentDetail> =>
    apiClient<DeploymentDetail>('/api/v1/deployments/promote/optimization', {
      method: 'POST',
      body: JSON.stringify(req),
    }),

  promoteFromExperiment: (req: PromoteFromExperimentRequest): Promise<DeploymentDetail> =>
    apiClient<DeploymentDetail>('/api/v1/deployments/promote/experiment', {
      method: 'POST',
      body: JSON.stringify(req),
    }),

  listDeployments: (params?: {
    status?: string;
    strategy_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<DeploymentListResponse> =>
    apiClient<DeploymentListResponse>('/api/v1/deployments', {
      method: 'GET',
      params: params as Record<string, string | number | boolean | undefined>,
    }),

  getDeployment: (deploymentId: string): Promise<DeploymentDetail> =>
    apiClient<DeploymentDetail>(`/api/v1/deployments/${encodeURIComponent(deploymentId)}`, {
      method: 'GET',
    }),

  pauseDeployment: (deploymentId: string, reason = ''): Promise<DeploymentDetail> =>
    apiClient<DeploymentDetail>(`/api/v1/deployments/${encodeURIComponent(deploymentId)}/pause`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  resumeDeployment: (deploymentId: string, reason = ''): Promise<DeploymentDetail> =>
    apiClient<DeploymentDetail>(`/api/v1/deployments/${encodeURIComponent(deploymentId)}/resume`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  cancelDeployment: (deploymentId: string, reason = ''): Promise<DeploymentDetail> =>
    apiClient<DeploymentDetail>(`/api/v1/deployments/${encodeURIComponent(deploymentId)}/cancel`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  validateDeployment: (deploymentId: string, reason = ''): Promise<DeploymentDetail> =>
    apiClient<DeploymentDetail>(`/api/v1/deployments/${encodeURIComponent(deploymentId)}/validate`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  promoteToCandidate: (deploymentId: string, reason = ''): Promise<DeploymentDetail> =>
    apiClient<DeploymentDetail>(`/api/v1/deployments/${encodeURIComponent(deploymentId)}/promote-candidate`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  getQualityGates: (deploymentId: string): Promise<QualityGateReport> =>
    apiClient<QualityGateReport>(`/api/v1/deployments/${encodeURIComponent(deploymentId)}/gates`, {
      method: 'GET',
    }),

  getMetrics: (deploymentId: string): Promise<any> =>
    apiClient<any>(`/api/v1/deployments/${encodeURIComponent(deploymentId)}/metrics`, {
      method: 'GET',
    }),
};

// ─── EPIC-026: Institutional Broker Sandbox API ─────────────────────────────

export const brokerSandboxApi = {
  listProviders: (): Promise<BrokerProviderInfo[]> =>
    apiClient<BrokerProviderInfo[]>('/api/v1/broker-sandbox/providers', {
      method: 'GET',
    }),

  listAccounts: (): Promise<BrokerSandboxAccount[]> =>
    apiClient<BrokerSandboxAccount[]>('/api/v1/broker-sandbox/accounts', {
      method: 'GET',
    }),

  createAccount: (req: BrokerSandboxAccountCreateRequest): Promise<BrokerSandboxAccount> =>
    apiClient<BrokerSandboxAccount>('/api/v1/broker-sandbox/accounts', {
      method: 'POST',
      body: JSON.stringify(req),
    }),

  getAccount: (accountId: string): Promise<BrokerSandboxAccount> =>
    apiClient<BrokerSandboxAccount>(`/api/v1/broker-sandbox/accounts/${encodeURIComponent(accountId)}`, {
      method: 'GET',
    }),

  connectAccount: (accountId: string): Promise<BrokerSandboxConnectResponse> =>
    apiClient<BrokerSandboxConnectResponse>(`/api/v1/broker-sandbox/accounts/${encodeURIComponent(accountId)}/connect`, {
      method: 'POST',
    }),

  disconnectAccount: (accountId: string): Promise<{ account_id: string; status: string; message: string }> =>
    apiClient<{ account_id: string; status: string; message: string }>(
      `/api/v1/broker-sandbox/accounts/${encodeURIComponent(accountId)}/disconnect`,
      { method: 'POST' }
    ),

  submitOrder: (accountId: string, req: BrokerSandboxOrderRequest): Promise<BrokerSandboxOrderResponse> =>
    apiClient<BrokerSandboxOrderResponse>(`/api/v1/broker-sandbox/accounts/${encodeURIComponent(accountId)}/orders`, {
      method: 'POST',
      body: JSON.stringify(req),
    }),

  listPositions: (accountId: string): Promise<BrokerSandboxPosition[]> =>
    apiClient<BrokerSandboxPosition[]>(`/api/v1/broker-sandbox/accounts/${encodeURIComponent(accountId)}/positions`, {
      method: 'GET',
    }),

  reconcileAccount: (accountId: string): Promise<BrokerSandboxReconciliationResponse> =>
    apiClient<BrokerSandboxReconciliationResponse>(
      `/api/v1/broker-sandbox/accounts/${encodeURIComponent(accountId)}/reconcile`,
      { method: 'POST' }
    ),

  listReconciliations: (accountId: string): Promise<BrokerSandboxReconciliationResponse[]> =>
    apiClient<BrokerSandboxReconciliationResponse[]>(
      `/api/v1/broker-sandbox/accounts/${encodeURIComponent(accountId)}/reconciliations`,
      { method: 'GET' }
    ),
};


