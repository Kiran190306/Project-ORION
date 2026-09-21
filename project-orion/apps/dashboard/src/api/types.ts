/**
 * Strict TypeScript DTOs and interfaces mirroring the Project ORION backend API.
 * All models align exactly with apps/trading-engine/src/schemas.py.
 */

// ─── Enums ───────────────────────────────────────────────────────────────────

export type OrderSide = 'BUY' | 'SELL';
export type OrderType = 'MARKET' | 'LIMIT' | 'STOP' | 'TRAILING_STOP';
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
  trailing_distance?: string | number | null;
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
  trailing_distance?: string | number | null;
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

// ─── Market Data (EPIC-021) ──────────────────────────────────────────────────

export interface MarketInstrument {
  symbol: string;
  base_currency: string;
  quote_currency: string;
  pip_size: string | number;
  tick_size: string | number;
  display_name: string;
  is_active: boolean;
}

export interface MarketQuote {
  symbol: string;
  bid: string | number;
  ask: string | number;
  mid: string | number;
  spread: string | number;
  spread_pips: string | number;
  timestamp: string;
  provider: string;
  is_stale: boolean;
  quality: string;
}

export interface MarketCandle {
  timestamp: string;
  open: string | number;
  high: string | number;
  low: string | number;
  close: string | number;
  volume: string | number;
}

export interface MarketCandlesResponse {
  symbol: string;
  timeframe: string;
  provider: string;
  candles: MarketCandle[];
}

export interface MarketHealth {
  provider: string;
  status: string;
  data_quality: string;
  last_update_utc: string | null;
  symbols_active: number;
  latency_ms: number;
  stale_count: number;
  is_paper_feed: boolean;
}

// ─── Paper Trading (EPIC-022) ────────────────────────────────────────────────

export interface PaperResetRequest {
  initial_balance?: string | number;
}

export interface PaperResetResponse {
  account_id: string;
  new_balance: string | number;
  cancelled_orders_count: number;
  closed_positions_count: number;
  message: string;
  timestamp: string;
}

export interface PaperConfigResponse {
  default_spread_pips: string | number;
  slippage_bps: string | number;
  latency_ms: number;
  partial_fill_probability: number;
  deterministic: boolean;
  fill_probability: number;
}

export interface UpdatePaperConfigRequest {
  default_spread_pips?: string | number;
  slippage_bps?: string | number;
  latency_ms?: number;
  partial_fill_probability?: number;
  deterministic?: boolean;
  fill_probability?: number;
}

// ─── Research & Strategy Lab (EPIC-023) ──────────────────────────────────────

export interface ParameterSchema {
  name: string;
  type: string;
  default: any;
  min?: number;
  max?: number;
  options?: string[];
  description?: string;
}

export interface StrategyCatalogueItem {
  strategy_id: string;
  name: string;
  description: string;
  category: string;
  version: string;
  is_deterministic: boolean;
  supported_instruments: string[];
  supported_timeframes: string[];
  parameters: ParameterSchema[];
}

export interface CreateExperimentRequest {
  strategy_id: string;
  symbol: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  initial_capital?: number;
  parameters?: Record<string, any>;
  spread_pips?: number;
  adverse_slippage_pips?: number;
  commission_per_lot?: number;
}

export interface ResearchWarning {
  code: string;
  title: string;
  description: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
}

export interface ResearchMetrics {
  initial_capital: number;
  final_balance: number;
  net_profit: number;
  total_return_pct: number;
  gross_profit: number;
  gross_loss: number;
  profit_factor: number;
  win_rate_pct: number;
  loss_rate_pct: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  avg_trade_pnl: number;
  largest_win: number;
  largest_loss: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown_pct: number;
  recovery_factor: number;
  expectancy: number;
}

export interface ExperimentSummary {
  id: string;
  organization_id: string;
  strategy_id: string;
  strategy_version: string;
  symbol: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  execution_time_seconds: number;
  created_at: string;
  completed_at?: string | null;
  metrics?: ResearchMetrics | null;
  warnings?: ResearchWarning[] | null;
  error_message?: string | null;
}

export interface ExperimentDetail extends ExperimentSummary {
  parameters: Record<string, any>;
  simulation_config: Record<string, any>;
}

export interface EquityPoint {
  timestamp: string;
  balance: number;
  equity: number;
  drawdown_pct: number;
}

export interface ExperimentEquityResponse {
  experiment_id: string;
  initial_capital: number;
  points: EquityPoint[];
}

export interface ResearchTradeRecord {
  trade_id: string;
  symbol: string;
  side: string;
  entry_time: string;
  exit_time: string;
  entry_price: number;
  exit_price: number;
  quantity: number;
  gross_pnl: number;
  fees: number;
  net_pnl: number;
  duration_seconds: number;
  exit_reason: string;
}

export interface ExperimentTradesResponse {
  experiment_id: string;
  total_trades: number;
  trades: ResearchTradeRecord[];
}

export interface CompareExperimentsRequest {
  experiment_ids: string[];
}

export interface ExperimentComparisonResponse {
  comparison: Record<string, any>[];
  normalized_curves: Record<string, { timestamp: string; return_pct: number }[]>;
}

// ---------------------------------------------------------------------------
// EPIC-024: Quantitative Strategy Optimization & Walk-Forward AI Engine
// ---------------------------------------------------------------------------

export interface ParameterRangeConfig {
  name: string;
  param_type: 'int' | 'float' | 'choice';
  min_value: number | string;
  max_value: number | string;
  step?: number | null;
  choices?: (string | number)[] | null;
}

export interface ParameterSpaceConfig {
  strategy_id: string;
  ranges: ParameterRangeConfig[];
}

export interface StrategyDefaultSpaceResponse {
  strategy_id: string;
  ranges: ParameterRangeConfig[];
  estimated_combinations: number;
}

export interface OptimizationRunRequest {
  strategy_id: string;
  symbol?: string;
  timeframe?: string;
  start_date: string;
  end_date: string;
  initial_capital?: number;
  optimization_type?: 'GRID_SEARCH' | 'RANDOM_SEARCH';
  fitness_objective?: string;
  parameter_space?: ParameterSpaceConfig | null;
  max_combinations?: number;
  n_samples?: number;
  random_seed?: number;
  spread_pips?: number;
  slippage_pips?: number;
  commission?: number;
}

export interface WalkForwardRunRequest {
  strategy_id: string;
  symbol?: string;
  timeframe?: string;
  start_date: string;
  end_date: string;
  initial_capital?: number;
  n_windows?: number;
  in_sample_ratio?: number;
  anchored?: boolean;
  fitness_objective?: string;
  parameter_space?: ParameterSpaceConfig | null;
  max_combinations_per_window?: number;
  spread_pips?: number;
  slippage_pips?: number;
  commission?: number;
}

export interface OptimizationCandidate {
  rank: number;
  parameters: Record<string, any>;
  fitness_score: number;
  total_return: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  calmar_ratio: number;
  max_drawdown: number;
  win_rate: number;
  profit_factor: number;
  total_trades: number;
  net_pnl: number;
}

export interface WalkForwardWindow {
  window_index: number;
  is_start: string;
  is_end: string;
  oos_start: string;
  oos_end: string;
  optimal_parameters: Record<string, any>;
  is_metrics: Record<string, any>;
  oos_metrics: Record<string, any>;
  is_return: number;
  oos_return: number;
  efficiency_ratio?: number | null;
  oos_equity_curve?: { timestamp: string; equity: number; drawdown: number }[];
}

export interface WalkForwardAnalysisResult {
  total_windows: number;
  windows: WalkForwardWindow[];
  mean_wfe?: number | null;
  annualized_oos_return: number;
  annualized_oos_sharpe: number;
  robustness_verdict: string;
  concatenated_oos_equity: { timestamp: string; equity: number; drawdown: number }[];
  warnings: string[];
}

export interface RegimeBreakdown {
  regime_name: string;
  trade_count: number;
  win_rate: number;
  profit_factor: number;
  total_return: number;
  sharpe_ratio: number;
  drawdown: number;
}

export interface ParameterStabilityReport {
  optimal_parameters: Record<string, any>;
  plateau_stability_score: number;
  max_neighbor_drop_pct: number;
  is_cliff: boolean;
  cliff_details: string;
  adjacent_evaluations: Record<string, any>[];
}

export interface SensitivityHeatmapPoint {
  param1_value: number | string;
  param2_value: number | string;
  fitness_score: number;
}

export interface SensitivityHeatmap {
  param1_name: string;
  param2_name: string;
  min_fitness: number;
  max_fitness: number;
  points: SensitivityHeatmapPoint[];
}

export interface OptimizationJobSummary {
  id: string;
  organization_id: string;
  strategy_id: string;
  symbol: string;
  timeframe: string;
  optimization_type: string;
  fitness_objective: string;
  status: string;
  total_combinations: number;
  completed_combinations: number;
  execution_time_seconds: number;
  best_parameters?: Record<string, any> | null;
  best_fitness_score?: number | null;
  best_sharpe?: number | null;
  best_return?: number | null;
  created_at: string;
  completed_at?: string | null;
}

export interface OptimizationJobDetail {
  id: string;
  organization_id: string;
  strategy_id: string;
  symbol: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  optimization_type: string;
  fitness_objective: string;
  parameter_space: Record<string, any>;
  optimization_config: Record<string, any>;
  status: string;
  total_combinations: number;
  completed_combinations: number;
  execution_time_seconds: number;
  best_parameters?: Record<string, any> | null;
  best_metrics?: Record<string, any> | null;
  top_candidates?: OptimizationCandidate[] | null;
  walk_forward_result?: WalkForwardAnalysisResult | null;
  regime_breakdowns?: RegimeBreakdown[] | null;
  stability_analysis?: ParameterStabilityReport | null;
  heatmap?: SensitivityHeatmap | null;
  warnings?: string[] | null;
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
}

// ─── Strategy Deployment Pipeline & Paper Incubator (EPIC-025) ───────────────

export type DeploymentStatusType =
  | 'PENDING_GATES'
  | 'GATES_PASSED'
  | 'GATES_FAILED'
  | 'INCUBATING'
  | 'PAUSED'
  | 'PAPER_VALIDATED'
  | 'INCUBATION_FAILED'
  | 'CANCELLED'
  | 'SUSPENDED'
  | 'PROMOTION_CANDIDATE';

export interface QualityGateResult {
  gate_type: string;
  verdict: 'PASS' | 'FAIL' | 'INCONCLUSIVE' | 'INSUFFICIENT_DATA';
  actual_value?: number | null;
  threshold?: number | null;
  details: string;
  evaluated_at: string;
}

export interface QualityGateReport {
  all_passed: boolean;
  summary_verdict: 'PASS' | 'FAIL' | 'INCONCLUSIVE' | 'INSUFFICIENT_DATA';
  gate_results: QualityGateResult[];
  evaluated_at: string;
}

export interface IncubationConfig {
  min_duration_days: number;
  min_trade_count: number;
  max_drawdown_pct: number;
  daily_loss_limit_pct: number;
  risk_violation_limit: number;
  performance_deviation_threshold_pct: number;
  initial_capital: string;
  require_market_data_quality: boolean;
  evaluation_mode: string;
}

export interface IncubationMetrics {
  net_pnl: string;
  total_return_pct: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown_pct: number;
  win_rate_pct: number;
  total_trades: number;
  profit_factor: number;
  daily_loss_violations: number;
  risk_violations: number;
  trading_days: number;
  data_quality_score: number;
}

export interface BenchmarkComparison {
  backtest_return_pct: number;
  paper_return_pct: number;
  return_ratio: number;
  backtest_sharpe: number;
  paper_sharpe: number;
  sharpe_diff: number;
  backtest_max_dd_pct: number;
  paper_max_dd_pct: number;
  drawdown_diff: number;
  backtest_win_rate_pct: number;
  paper_win_rate_pct: number;
  backtest_trades: number;
  paper_trades: number;
  deviation_acceptable: boolean;
}

export interface DeploymentSummary {
  id: string;
  organization_id: string;
  created_by?: string | null;
  strategy_id: string;
  strategy_version: string;
  symbol: string;
  timeframe: string;
  status: DeploymentStatusType;
  initial_capital: number;
  promotion_verdict: string;
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  source_optimization_id?: string | null;
  source_experiment_id?: string | null;
}

export interface DeploymentDetail {
  id: string;
  organization_id: string;
  created_by?: string | null;
  strategy_id: string;
  strategy_version: string;
  symbol: string;
  timeframe: string;
  status: DeploymentStatusType;
  parameters: Record<string, any>;
  evidence_chain: Record<string, any>;
  initial_capital: number;
  quality_gate_policy?: Record<string, any> | null;
  quality_gate_results?: QualityGateReport | null;
  incubation_config: IncubationConfig;
  incubation_metrics?: IncubationMetrics | null;
  benchmark_comparison?: BenchmarkComparison | null;
  backtest_benchmark?: Record<string, any> | null;
  promotion_verdict: string;
  transition_history: Record<string, any>[];
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
  error_message?: string | null;
  warnings?: string[] | null;
  source_optimization_id?: string | null;
  source_experiment_id?: string | null;
}

export interface DeploymentListResponse {
  items: DeploymentSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface PromoteFromOptimizationRequest {
  optimization_job_id: string;
  candidate_rank?: number;
  symbol?: string;
  timeframe?: string;
  initial_capital?: number;
  incubation_duration_days?: number;
  min_trade_count?: number;
  max_drawdown_pct?: number;
  enforce_separation_of_duties?: boolean;
}

export interface PromoteFromExperimentRequest {
  experiment_id: string;
  initial_capital?: number;
  incubation_duration_days?: number;
  min_trade_count?: number;
  max_drawdown_pct?: number;
  enforce_separation_of_duties?: boolean;
}

