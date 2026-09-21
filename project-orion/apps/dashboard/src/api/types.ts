/**
 * Strict TypeScript DTOs and interfaces mirroring the Project ORION backend API.
 * All models align exactly with apps/trading-engine/src/schemas.py.
 */

// ─── Enums ───────────────────────────────────────────────────────────────────

export type OrderSide = 'BUY' | 'SELL';
export type OrderType = 'MARKET' | 'LIMIT' | 'STOP';
export type OrderStatus =
  | 'PENDING'
  | 'SUBMITTED'
  | 'FILLED'
  | 'PARTIALLY_FILLED'
  | 'CANCELLED'
  | 'REJECTED'
  | 'EXPIRED';

// ─── Auth Models ─────────────────────────────────────────────────────────────

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  username: string;
  is_superuser: boolean;
}

export interface UserResponse {
  id: string;
  username: string;
  email: string;
  full_name?: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

// ─── Account & Summary ───────────────────────────────────────────────────────

export interface AccountSummary {
  balance: string;
  equity: string;
  available_cash: string;
  used_margin: string;
  free_margin: string;
  unrealized_pnl: string;
  realized_pnl: string;
  currency: string;
  is_paper: boolean;
  updated_at: string;
}

export interface AccountResponse {
  account_id: string;
  broker_name: string;
  account_number: string;
  balance: string;
  equity: string;
  currency: string;
  leverage: number;
  is_live: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ─── Pagination ──────────────────────────────────────────────────────────────

export interface PaginationParams {
  limit?: number;
  offset?: number;
  sort_by?: string;
  order?: 'asc' | 'desc';
  date_from?: string;
  date_to?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

// ─── Orders ──────────────────────────────────────────────────────────────────

export interface CreateOrderRequest {
  symbol: string;
  side: OrderSide;
  order_type: OrderType;
  quantity: string | number;
  price?: string | number | null;
  stop_price?: string | number | null;
  stop_loss?: string | number | null;
  take_profit?: string | number | null;
  strategy_id?: string | null;
}

export interface OrderResponse {
  id: string;
  broker_order_id?: string | null;
  account_id: string;
  symbol: string;
  side: OrderSide | string;
  order_type: OrderType | string;
  quantity: string | number;
  price?: string | number | null;
  stop_price?: string | number | null;
  stop_loss?: string | number | null;
  take_profit?: string | number | null;
  status: OrderStatus | string;
  filled_quantity: string | number;
  average_fill_price?: string | number | null;
  strategy_id?: string | null;
  is_paper: boolean;
  created_at: string;
  updated_at: string;
  meta_data?: Record<string, unknown>;
}

export interface CancelOrderResponse {
  order_id: string;
  status: string;
  message: string;
}

// ─── Positions ───────────────────────────────────────────────────────────────

export interface PositionResponse {
  id: string;
  account_id: string;
  symbol: string;
  side: OrderSide | string;
  quantity: string | number;
  open_price: string | number;
  current_price: string | number;
  stop_loss?: string | number | null;
  take_profit?: string | number | null;
  realized_pnl: string | number;
  unrealized_pnl: string | number;
  commission: string | number;
  swap: string | number;
  is_open: boolean;
  opened_at: string;
  closed_at?: string | null;
}

export interface ClosePositionResponse {
  position_id: string;
  symbol: string;
  closed_quantity: string | number;
  close_price: string | number;
  realized_pnl: string | number;
  closed_at: string;
  message: string;
}

// ─── Trades (Fills) ──────────────────────────────────────────────────────────

export interface TradeResponse {
  trade_id: string;
  order_id: string;
  broker_fill_id?: string | null;
  symbol: string;
  side: OrderSide | string;
  quantity: string | number;
  price: string | number;
  commission: string | number;
  timestamp: string;
  is_paper: boolean;
}

// ─── Portfolio & Exposure ────────────────────────────────────────────────────

export interface CurrencyExposure {
  currency: string;
  long_exposure: string | number;
  short_exposure: string | number;
  net_exposure: string | number;
  position_count: number;
}

export interface PortfolioOverviewResponse {
  balance: string | number;
  equity: string | number;
  used_margin: string | number;
  free_margin: string | number;
  margin_level: number;
  unrealized_pnl: string | number;
  realized_pnl: string | number;
  net_exposure: string | number;
  gross_exposure: string | number;
  open_positions_count: number;
  currency: string;
  is_paper: boolean;
  updated_at: string;
}

export interface EquityCurveResponse {
  balance: string | number;
  equity: string | number;
  peak_equity: string | number;
  current_drawdown: number;
  max_drawdown: number;
  currency: string;
  updated_at: string;
}

export interface PnLBreakdownResponse {
  realized_pnl: string | number;
  unrealized_pnl: string | number;
  gross_profit: string | number;
  gross_loss: string | number;
  commission: string | number;
  swap: string | number;
  fees: string | number;
  net_pnl: string | number;
  currency: string;
  updated_at: string;
}

export interface ExposureResponse {
  net_exposure: string | number;
  gross_exposure: string | number;
  long_exposure: string | number;
  short_exposure: string | number;
  currency_exposures: CurrencyExposure[];
  updated_at: string;
}

// ─── Strategies ──────────────────────────────────────────────────────────────

export interface StrategyInfo {
  id: string;
  name: string;
  type: string;
  description: string;
  timeframes: string[];
  symbols: string[];
  is_active: boolean;
}

export interface StrategyListResponse {
  strategies: StrategyInfo[];
  total: number;
  updated_at: string;
}

export interface StrategyDetailResponse {
  id: string;
  name: string;
  type: string;
  description: string;
  timeframes: string[];
  symbols: string[];
  parameters: Record<string, unknown>;
  is_active: boolean;
}

export interface StrategyConfigSchemaResponse {
  strategy_id: string;
  name: string;
  schema_definition: Record<string, unknown>;
}

export interface AccountStrategyConfigResponse {
  account_id: string;
  strategy_id: string;
  timeframe: string;
  symbols: string[];
  parameters: Record<string, unknown>;
  is_active: boolean;
  updated_at: string;
}

export interface UpdateAccountStrategyRequest {
  strategy_id: string;
  timeframe: string;
  symbols: string[];
  parameters: Record<string, unknown>;
  is_active: boolean;
}

// ─── Risk ────────────────────────────────────────────────────────────────────

export interface RiskStatusResponse {
  status: string;
  position_count: number;
  total_exposure: string | number;
  used_margin: string | number;
  free_margin: string | number;
  margin_level: number;
  drawdown: number;
  daily_pnl: string | number;
  daily_loss_rate: number;
  consecutive_losses: number;
  emergency_stop_active: boolean;
  recovery_mode_active: boolean;
  updated_at: string;
}

export interface RiskLimitItem {
  name: string;
  category: string;
  description: string;
  is_enabled: boolean;
  severity: string;
  value?: unknown;
}

export interface RiskLimitsResponse {
  limits: RiskLimitItem[];
  total: number;
  updated_at: string;
}

// ─── Worker ──────────────────────────────────────────────────────────────────

export interface WorkerStatusResponse {
  enabled: boolean;
  state: string;
  is_running: boolean;
  last_cycle_at?: string | null;
  next_cycle_at?: string | null;
  last_error?: string | null;
  uptime_seconds: number;
  updated_at: string;
}

export interface WorkerMetricsResponse {
  cycles_started: number;
  cycles_completed: number;
  cycles_failed: number;
  market_poll_failures: number;
  orders_submitted: number;
  risk_rejections: number;
  execution_failures: number;
  uptime_seconds: number;
  updated_at: string;
}

// ─── Consolidated Dashboard ──────────────────────────────────────────────────

export interface DashboardAccount {
  balance: string | number;
  equity: string | number;
  available_cash: string | number;
  used_margin: string | number;
  free_margin: string | number;
  currency: string;
  is_paper: boolean;
}

export interface DashboardPerformance {
  realized_pnl: string | number;
  unrealized_pnl: string | number;
  daily_pnl: string | number;
  drawdown_pct: number;
}

export interface DashboardTrading {
  open_positions: PositionResponse[];
  recent_trades: TradeResponse[];
  pending_orders: OrderResponse[];
}

export interface DashboardStrategy {
  active_strategy: string;
  timeframe: string;
  symbols: string[];
}

export interface DashboardRisk {
  status: string;
  total_exposure: string | number;
  margin_level: number;
  emergency_stop_active: boolean;
  recovery_mode_active: boolean;
}

export interface DashboardWorker {
  enabled: boolean;
  state: string;
  is_running: boolean;
  last_cycle_at?: string | null;
  uptime_seconds: number;
  last_error?: string | null;
}

export interface DashboardSystem {
  status: string;
  market_data_status: string;
  timestamp: string;
}

export interface DashboardResponse {
  account: DashboardAccount;
  performance: DashboardPerformance;
  trading: DashboardTrading;
  strategy: DashboardStrategy;
  risk: DashboardRisk;
  worker: DashboardWorker;
  system: DashboardSystem;
}

// ─── Error Envelope ──────────────────────────────────────────────────────────

export interface ApiErrorResponse {
  error?: string;
  detail?: string | Array<{ loc?: string[]; msg?: string; type?: string }>;
  message?: string;
  correlation_id?: string;
  timestamp?: string;
}

export class ApiError extends Error {
  public statusCode: number;
  public correlationId?: string;
  public rawDetail?: unknown;

  constructor(statusCode: number, message: string, correlationId?: string, rawDetail?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.correlationId = correlationId;
    this.rawDetail = rawDetail;
  }
}

// ─── Commercial Billing ─────────────────────────────────────────────────────

export interface BillingCustomerResponse {
  id: string;
  organization_id: string;
  provider_customer_id: string;
  email: string;
  name: string;
}

export interface BillingSubscriptionResponse {
  id: string;
  organization_id: string;
  provider_subscription_id: string;
  plan_code: string;
  status: string;
  current_period_start: string;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

export interface BillingInvoiceResponse {
  id: string;
  provider_invoice_id: string;
  amount_due: number;
  amount_paid: number;
  currency: string;
  status: string;
  hosted_invoice_url: string | null;
  invoice_pdf: string | null;
  created_at: string;
}

export interface BillingOverviewResponse {
  customer: BillingCustomerResponse | null;
  subscription: BillingSubscriptionResponse | null;
  recent_invoices: BillingInvoiceResponse[];
}

export interface CheckoutResponse {
  session_id: string;
  url: string;
  plan_code: string;
  customer_id: string;
}

// ─── Organization & Governance ──────────────────────────────────────────────

export interface OrganizationResponse {
  id: string;
  name: string;
  slug: string;
  status: string;
  created_at: string;
  updated_at: string;
  meta_data?: Record<string, unknown>;
}

export interface UpdateOrganizationRequest {
  name?: string;
  meta_data?: Record<string, unknown>;
}

export interface OrganizationMemberResponse {
  id: string;
  organization_id: string;
  user_id: string;
  role: string;
  status: string;
  created_at: string;
  updated_at: string;
  meta_data?: Record<string, unknown>;
}

export interface UpdateMemberRoleRequest {
  role: string;
}

export interface CreateInvitationRequest {
  email: string;
  role: string;
}

export interface InvitationResponse {
  id: string;
  organization_id: string;
  email: string;
  role: string;
  status: string;
  invited_by_user_id: string;
  expires_at: string;
  created_at: string;
  invitation_token?: string;
  invitation_url?: string;
}

export interface AcceptInvitationResponse {
  membership_id: string;
  organization_id: string;
  user_id: string;
  role: string;
  status: string;
  accepted_at: string;
}

export interface AuditLogResponse {
  id: string;
  organization_id: string;
  event_type: string;
  component: string;
  actor: string;
  details: Record<string, unknown>;
  timestamp: string;
}

