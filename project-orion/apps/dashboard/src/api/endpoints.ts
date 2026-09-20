/**
 * Strongly typed endpoint callers consuming the verified FastAPI backend.
 */

import { apiClient } from './client';
import type {
  AccountResponse,
  AccountStrategyConfigResponse,
  AccountSummary,
  CancelOrderResponse,
  ClosePositionResponse,
  CreateOrderRequest,
  DashboardResponse,
  EquityCurveResponse,
  ExposureResponse,
  LoginRequest,
  LoginResponse,
  OrderResponse,
  PaginatedResponse,
  PaginationParams,
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
  UserResponse,
  WorkerMetricsResponse,
  WorkerStatusResponse,
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
