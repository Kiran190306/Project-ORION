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
  InvitationResponse,
  LoginRequest,
  LoginResponse,
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




