# Project ORION — REST API Specification & Service Catalog

**Document Version:** 1.1.0
**Target Milestone:** EPIC-027 Phase 7B Acquisition Due Diligence
**Repository Working Copy:** `project-orion/`
**Classification:** Confidential — Due Diligence Technical Data Room (Tier 2 / NDA)
**Safety Mandate:** STRICT PAPER TRADING ONLY ($0.00 Capital at Risk — Zero Live Broker Endpoints)

---

## 1. Executive API Architecture

The Project ORION Trading Engine exposes an asynchronous RESTful API built on **FastAPI** and **Starlette**, executing on the **Uvicorn ASGI** runtime.

### Authoritative Route Inventory
- **Application Endpoints:** Exactly **122** application endpoints actively registered across 19 operational domain routers.
- **Specification & Documentation Routes:** Exactly **4** OpenAPI/Swagger infrastructure routes (`/openapi.json`, `/docs`, `/docs/oauth2-redirect`, `/redoc`), totaling **126** total ASGI routes.

### Core Architecture & Design Patterns
- **Dynamic OpenAPI 3.1 Specification:** Complete OpenAPI schemas are auto-generated dynamically at runtime and accessible at `/openapi.json`. Interactive API explorers are hosted at `/docs` (Swagger UI) and `/redoc` (ReDoc).
- **Multi-Tenant Scoping (`TenantContext`):** Every protected request extracts user and organization identity from cryptographically verified JWT access tokens. Database queries automatically bind `organization_id` to enforce strict tenant boundary isolation.
- **Role-Based Access Control (RBAC):** Exactly 41 granular permissions across 15 operational domains (canonically enumerated in `libraries/domain/organization/permissions.py`) are enforced at route decorators via `@require_permission(Permission.<NAME>)`.
- **Anti-Enumeration Hardening:** Public authentication routes (`/forgot-password`, `/resend-verification`) return identical HTTP 200 responses regardless of whether an account exists or outbound email transport succeeds.
- **Fail-Safe Paper Invariant:** Order execution endpoints route exclusively to `PaperExecutionAdapter` and `MockBrokerAdapter`. Live broker connections are structurally prohibited ($0.00 Capital at Risk).

---

## 2. API Domain Catalog (122 Endpoints Across 19 Router Domains)

### 2.1 Authentication & Account Lifecycle (`/api/v1/auth`)

| Method | Endpoint | Required Permission | Tenant Context | Description / Request & Response | Rate Limit |
|---|---|---|:---:|---|:---:|
| `POST` | `/api/v1/auth/login` | Public | None | Authenticate with username and password. Issues JWT access token. Body: `LoginRequest`. Returns `LoginResponse` (HTTP 200). | Auth (5/min) |
| `POST` | `/api/v1/auth/logout` | Authenticated | User | Invalidate current session token. Returns generic confirmation (HTTP 200). | Standard |
| `GET` | `/api/v1/auth/me` | Authenticated | User | Retrieve current authenticated user profile, active organization, and global roles. Returns `UserResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/auth/forgot-password` | Public | None | Initiate single-use password reset. Anti-enumeration guarded: returns HTTP 200. Body: `ForgotPasswordRequest`. Returns `GenericMessageResponse` (HTTP 200). | Auth (5/min) |
| `POST` | `/api/v1/auth/reset-password` | Public | None | Complete password reset with single-use token. Body: `ResetPasswordRequest`. Returns `GenericMessageResponse` (HTTP 200). | Auth (5/min) |
| `POST` | `/api/v1/auth/verify-email` | Public | None | Complete email address verification with token. Body: `VerifyEmailRequest`. Returns `GenericMessageResponse` (HTTP 200). | Auth (5/min) |
| `POST` | `/api/v1/auth/resend-verification` | Public | None | Request new verification email. Anti-enumeration guarded. Body: `ResendVerificationRequest`. Returns `GenericMessageResponse` (HTTP 200). | Auth (5/min) |
| `POST` | `/api/v1/auth/deactivate` | Authenticated | User | Self-deactivate account. Sole-owner guard blocks deactivation if sole owner of an active org. Body: `DeactivateAccountRequest`. Returns `GenericMessageResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/auth/users/{target_user_id}/reactivate` | Superuser | System | Administrative reactivation of deactivated user accounts. Returns `GenericMessageResponse` (HTTP 200). | Admin |

---

### 2.2 Tenant Registration & Onboarding Lifecycle (`/api/v1/onboarding`)

| Method | Endpoint | Required Permission | Tenant Context | Description / Request & Response | Rate Limit |
|---|---|---|:---:|---|:---:|
| `POST` | `/api/v1/onboarding/register` | Public | None | Atomic tenant onboarding: creates user, tenant organization (OWNER), provisions default Free tier, initializes $100,000 virtual paper account. Body: `OnboardingRegisterRequest`. Returns `OnboardingResponse` (HTTP 201). | Onboarding (5/min) |
| `GET` | `/api/v1/onboarding/status` | Authenticated | User / Org | Fetch current onboarding step, completion history, and readiness checklist. Returns `OnboardingStatusResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/onboarding/steps/{step}/complete` | Authenticated | User / Org | Advance onboarding state machine with prerequisite validation. Body: `CompleteOnboardingStepRequest` (optional). Returns `OnboardingStatusResponse` (HTTP 200). | Standard |

---

### 2.3 Multi-Tenant Organizations & Team Governance (`/api/v1/organizations` & `/api/v1/invitations`)

| Method | Endpoint | Required Permission | Tenant Context | Description / Request & Response | Rate Limit |
|---|---|---|:---:|---|:---:|
| `GET` | `/api/v1/organizations` | Authenticated | User | List all organizations where the calling user has active membership. Returns `list[OrganizationResponse]` (HTTP 200). | Standard |
| `GET` | `/api/v1/organizations/{id}` | `ORGANIZATION_READ` | Enforced | Retrieve detailed organization settings and metadata. Returns `OrganizationResponse` (HTTP 200). | Standard |
| `PATCH` | `/api/v1/organizations/{id}` | `ORGANIZATION_UPDATE` | Enforced | Update organization display name and preferences. Body: `UpdateOrganizationRequest`. Returns `OrganizationResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/organizations/{id}/members` | `MEMBER_READ` | Enforced | List organization members, email addresses, and assigned roles. Returns `list[OrganizationMemberResponse]` (HTTP 200). | Standard |
| `POST` | `/api/v1/organizations/{id}/members/invite` | `MEMBER_INVITE` | Enforced | Issue email invitation to join organization with assigned role. Body: `CreateInvitationRequest`. Returns `InvitationResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/invitations/{token}/accept` | Public | None | Accept invitation to join organization using single-use invitation token. Returns `AcceptInvitationResponse` (HTTP 200). | Standard |
| `PATCH` | `/api/v1/organizations/{id}/members/{user_id}/role` | `MEMBER_UPDATE` | Enforced | Update member RBAC role. Body: `UpdateMemberRoleRequest`. Returns `OrganizationMemberResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/organizations/{id}/members/{user_id}/suspend` | `MEMBER_UPDATE` | Enforced | Temporarily suspend organization member. Returns `OrganizationMemberResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/organizations/{id}/members/{user_id}/reactivate` | `MEMBER_UPDATE` | Enforced | Reactivate suspended member. Returns `OrganizationMemberResponse` (HTTP 200). | Standard |
| `DELETE` | `/api/v1/organizations/{id}/members/{user_id}` | `MEMBER_REMOVE` | Enforced | Remove member from organization. Sole-owner guard blocks removal of last owner. Returns generic confirmation (HTTP 200). | Standard |
| `GET` | `/api/v1/organizations/{id}/invitations` | `MEMBER_READ` | Enforced | List pending invitations for the organization. Returns `list[InvitationResponse]` (HTTP 200). | Standard |
| `DELETE` | `/api/v1/organizations/{id}/invitations/{invitation_id}` | `MEMBER_INVITE` | Enforced | Revoke pending invitation. Returns generic confirmation (HTTP 200). | Standard |
| `GET` | `/api/v1/organizations/{id}/audit-logs` | `AUDIT_READ` | Enforced | Query compliance audit log trail for tenant actions. Returns `list[AuditLogResponse]` (HTTP 200). | Standard |

---

### 2.4 Account Accounting & Balance (`/api/v1/account`)

| Method | Endpoint | Required Permission | Tenant Context | Description / Request & Response | Rate Limit |
|---|---|---|:---:|---|:---:|
| `GET` | `/api/v1/account/` | `ACCOUNT_READ` | Enforced | Retrieve primary active paper trading account state. Returns `AccountResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/account/summary` | `ACCOUNT_READ` | Enforced | Get account equity, balance, used margin, free margin, and leverage. Returns `AccountSummary` (HTTP 200). | Standard |

---

### 2.5 Paper Trading Simulation Controls & Direct Orders (`/api/v1/trading` & `/api/v1/orders`)

| Method | Endpoint | Required Permission | Tenant Context | Description / Request & Response | Rate Limit |
|---|---|---|:---:|---|:---:|
| `POST` | `/api/v1/paper-trade` | `ORDER_CREATE` | Enforced | Execute direct paper trade with simulated broker execution. Body: `PaperTradeRequest`. Returns `PaperTradeResponse` (HTTP 200). | Orders (60/min) |
| `POST` | `/api/v1/trading/paper/reset` | `ORDER_CREATE` | Enforced | Reset virtual paper trading account balance to initial capital ($100,000.00), close open positions, cancel active orders. Body: `PaperResetRequest`. Returns `PaperResetResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/trading/paper/config` | `ACCOUNT_READ` | Enforced | Query paper trading simulation parameters (initial balance, base currency, leverage). Returns `PaperConfigResponse` (HTTP 200). | Standard |
| `PATCH` | `/api/v1/trading/paper/config` | `ACCOUNT_UPDATE` | Enforced | Update paper simulation parameters. Body: `UpdatePaperConfigRequest`. Returns `PaperConfigResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/orders/` | `ORDER_CREATE` | Enforced | Submit simulated paper order (MARKET, LIMIT, STOP). Traverses risk limits, slippage modeling, and margin checks. Body: `CreateOrderRequest`. Returns `OrderResponse` (HTTP 201). | Orders (60/min) |
| `GET` | `/api/v1/orders/` | `ORDER_READ` | Enforced | List historical and resting orders with status and symbol filters. Returns `PaginatedResponse[OrderResponse]` (HTTP 200). | Standard |
| `GET` | `/api/v1/orders/{order_id}` | `ORDER_READ` | Enforced | Retrieve single order details and execution fills. Returns `OrderResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/orders/{order_id}/cancel` | `ORDER_CANCEL` | Enforced | Cancel resting limit or stop order before execution. Returns `CancelOrderResponse` (HTTP 200). | Orders (60/min) |

---

### 2.6 Positions & Execution Trades (`/api/v1/positions` & `/api/v1/trades`)

| Method | Endpoint | Required Permission | Tenant Context | Description / Request & Response | Rate Limit |
|---|---|---|:---:|---|:---:|
| `GET` | `/api/v1/positions/` | `POSITION_READ` | Enforced | List open positions with real-time unrealized P&L and mark-to-market valuations. Returns `PaginatedResponse[PositionResponse]` (HTTP 200). | Standard |
| `GET` | `/api/v1/positions/{position_id}` | `POSITION_READ` | Enforced | Get single position details, netting history, and trade IDs. Returns `PositionResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/positions/{position_id}/close` | `POSITION_CLOSE` | Enforced | Close position at current market simulated bid/ask price; crystallizes realized P&L. Returns `ClosePositionResponse` (HTTP 200). | Orders (60/min) |
| `GET` | `/api/v1/trades/` | `TRADE_READ` | Enforced | List historical trade fills, transaction prices, slippage, and fees. Returns `PaginatedResponse[TradeResponse]` (HTTP 200). | Standard |
| `GET` | `/api/v1/trades/{trade_id}` | `TRADE_READ` | Enforced | Retrieve single fill/trade by ID. Returns `TradeResponse` (HTTP 200). | Standard |

---

### 2.7 Portfolio Analytics & Exposure (`/api/v1/portfolio`)

| Method | Endpoint | Required Permission | Tenant Context | Description / Request & Response | Rate Limit |
|---|---|---|:---:|---|:---:|
| `GET` | `/api/v1/portfolio/` | `ACCOUNT_READ` | Enforced | Aggregated portfolio overview including total equity, margin usage, and risk utilization. Returns `PortfolioOverviewResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/portfolio/equity` | `ACCOUNT_READ` | Enforced | Historical equity curve time series for the account. Returns `EquityCurveResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/portfolio/pnl` | `ACCOUNT_READ` | Enforced | Realized and unrealized P&L breakdown by timeframe and symbol. Returns `PnLBreakdownResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/portfolio/exposure` | `ACCOUNT_READ` | Enforced | Currency and asset class exposure distribution. Returns `ExposureResponse` (HTTP 200). | Standard |

---

### 2.8 Autonomous Strategy Execution Worker (`/api/v1/worker`)

| Method | Endpoint | Required Permission | Tenant Context | Description / Request & Response | Rate Limit |
|---|---|---|:---:|---|:---:|
| `GET` | `/api/v1/worker/status` | `WORKER_READ` | Enforced | Runtime status of autonomous worker execution loop (running state, uptime, iteration counters). Returns `WorkerStatusResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/worker/metrics` | `WORKER_READ` | Enforced | Operational execution metrics: cycle duration, decision latency, throughput. Returns `WorkerMetricsResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/worker/start` | `WORKER_START` | Enforced | Start autonomous worker execution cycle. Returns status confirmation (HTTP 200). | Standard |
| `POST` | `/api/v1/worker/stop` | `WORKER_STOP` | Enforced | Gracefully halt autonomous worker execution cycle. Returns status confirmation (HTTP 200). | Standard |

---

### 2.9 Strategy Management & Archetypes (`/api/v1/strategies`)

| Method | Endpoint | Required Permission | Tenant Context | Description / Request & Response | Rate Limit |
|---|---|---|:---:|---|:---:|
| `GET` | `/api/v1/strategies/` | `STRATEGY_READ` | Enforced | List registered algorithmic strategy archetypes. Returns `StrategyListResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/strategies/{strategy_id}` | `STRATEGY_READ` | Enforced | Fetch archetype metadata, author, and parameter boundaries. Returns `StrategyDetailResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/strategies/{strategy_id}/config-schema` | `STRATEGY_READ` | Enforced | JSON schema defining valid strategy configuration parameters. Returns `StrategyConfigSchemaResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/strategies/account/config` | `STRATEGY_READ` | Enforced | Active strategy configuration applied to caller account. Returns `AccountStrategyConfigResponse` (HTTP 200). | Standard |
| `PUT` | `/api/v1/strategies/account/config` | `STRATEGY_CONFIGURE` | Enforced | Update active strategy configuration for caller account. Body: `UpdateAccountStrategyRequest`. Returns `AccountStrategyConfigResponse` (HTTP 200). | Standard |

---

### 2.10 Risk Governance & Circuit Breakers (`/api/v1/risk`)

| Method | Endpoint | Required Permission | Tenant Context | Description / Request & Response | Rate Limit |
|---|---|---|:---:|---|:---:|
| `GET` | `/api/v1/risk/status` | `RISK_READ` | Enforced | Real-time risk status: drawdown limits, margin thresholds, circuit-breaker trip states. Returns `RiskStatusResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/risk/limits` | `RISK_READ` | Enforced | Query configured institutional risk limit thresholds. Returns `RiskLimitsResponse` (HTTP 200). | Standard |
| `PUT` | `/api/v1/risk/limits` | `RISK_CONFIGURE` | Enforced | Configure institutional risk limit boundaries. Returns `RiskLimitsResponse` (HTTP 200). | Standard |

---

### 2.11 Commercial Billing & Stripe Test Mode (`/api/v1/billing`)

| Method | Endpoint | Required Permission | Tenant Context | Description / Request & Response | Rate Limit |
|---|---|---|:---:|---|:---:|
| `POST` | `/api/v1/billing/webhooks/stripe` | Public (HMAC Verified) | None | Ingest raw asynchronous Stripe webhooks. Enforces HMAC-SHA256 signature verification and event deduplication. Returns processing status (HTTP 200). | Webhooks |
| `GET` | `/api/v1/billing` | `SUBSCRIPTION_READ` | Enforced | Fetch billing overview: customer ID, active plan tier, status (`ACTIVE`, `TRIALING`, `PAST_DUE`), and period end dates. Returns `BillingOverviewResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/billing/invoices` | `SUBSCRIPTION_READ` | Enforced | List historical invoices, payment status, and PDF receipt links. Returns `list[BillingInvoiceResponse]` (HTTP 200). | Standard |
| `POST` | `/api/v1/billing/checkout` | `SUBSCRIPTION_MANAGE` | Enforced | Generate Stripe Checkout session redirect URL for tier upgrades. Body: `CreateCheckoutRequest`. Returns `CheckoutResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/billing/subscription/cancel` | `SUBSCRIPTION_MANAGE` | Enforced | Cancel subscription at period end; retains tier access until cycle conclusion. Body: `CancelSubscriptionRequest`. Returns `BillingSubscriptionResponse` (HTTP 200). | Standard |

---

### 2.12 Subscription Tiers & Entitlements (`/api/v1/plans` & `/api/v1/subscription`)

| Method | Endpoint | Required Permission | Tenant Context | Description / Request & Response | Rate Limit |
|---|---|---|:---:|---|:---:|
| `GET` | `/api/v1/plans` | Public | None | Retrieve commercial tier catalog (FREE, PRO, BUSINESS, ENTERPRISE) and entitlement limits. Returns `list[PlanResponse]` (HTTP 200). | Standard |
| `GET` | `/api/v1/subscription` | `SUBSCRIPTION_READ` | Enforced | Query current active subscription tier, billing period, and status. Returns `SubscriptionResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/entitlements` | `SUBSCRIPTION_READ` | Enforced | Check active resource limits and quota utilization (accounts, daily orders, workers). Returns entitlements dictionary (HTTP 200). | Standard |
| `POST` | `/api/v1/subscription/change-plan` | `SUBSCRIPTION_MANAGE` | Enforced | Change subscription plan tier directly. Body: `ChangePlanRequest`. Returns `SubscriptionResponse` (HTTP 200). | Standard |

---

### 2.13 Strategy Lab & Backtesting Research (`/api/v1/research`)

| Method | Endpoint | Required Permission | Tenant Context | Description / Request & Response | Rate Limit |
|---|---|---|:---:|---|:---:|
| `GET` | `/api/v1/research/strategies` | `RESEARCH_READ` | Enforced | List registered strategy archetypes available for research and backtesting. Returns `list[StrategyCatalogueItemResponse]` (HTTP 200). | Standard |
| `GET` | `/api/v1/research/strategies/{strategy_id}` | `RESEARCH_READ` | Enforced | Fetch archetype research metadata and parameter definitions. Returns `StrategyCatalogueItemResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/research/experiments` | `RESEARCH_EXECUTE` | Enforced | Launch historical backtest on OHLCV data. Body: `CreateExperimentRequest`. Returns `ExperimentSummaryResponse` (HTTP 201). | Heavy (10/min) |
| `GET` | `/api/v1/research/experiments` | `RESEARCH_READ` | Enforced | List backtest experiments and summary metrics (Sharpe, Max Drawdown, Win Rate). Returns `list[ExperimentSummaryResponse]` (HTTP 200). | Standard |
| `GET` | `/api/v1/research/experiments/{experiment_id}` | `RESEARCH_READ` | Enforced | Fetch full backtest report, parameters, and summary performance. Returns `ExperimentDetailResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/research/experiments/{experiment_id}/cancel` | `RESEARCH_CANCEL` | Enforced | Cancel running backtest experiment. Returns `ExperimentSummaryResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/research/experiments/{experiment_id}/results` | `RESEARCH_READ` | Enforced | Query raw performance metrics and trade statistics dictionary. Returns metrics payload (HTTP 200). | Standard |
| `GET` | `/api/v1/research/experiments/{experiment_id}/equity-curve` | `RESEARCH_READ` | Enforced | Fetch backtest equity curve time series data. Returns `ExperimentEquityResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/research/experiments/{experiment_id}/trades` | `RESEARCH_READ` | Enforced | Fetch simulated trade log for completed backtest. Returns `ExperimentTradesResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/research/experiments/compare` | `RESEARCH_READ` | Enforced | Compare performance metrics side-by-side across multiple experiments. Body: `CompareExperimentsRequest`. Returns `ExperimentComparisonResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/research/experiments/{experiment_id}/export` | `RESEARCH_EXPORT` | Enforced | Export experiment results in JSON or CSV format. Returns downloadable payload (HTTP 200). | Standard |

---

### 2.14 Strategy Optimization & Walk-Forward Analysis (`/api/v1/optimization`)

| Method | Endpoint | Required Permission | Tenant Context | Description / Request & Response | Rate Limit |
|---|---|---|:---:|---|:---:|
| `GET` | `/api/v1/optimization/spaces/{strategy_id}` | `OPTIMIZATION_READ` | Enforced | Query canonical parameter bounds and default search grid for an archetype. Returns `StrategyDefaultSpaceResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/optimization/run` | `OPTIMIZATION_EXECUTE` | Enforced | Launch Grid Search or Random Search parameter optimization sweep across historical windows. Body: `OptimizationRunRequest`. Returns `OptimizationJobDetailResponse` (HTTP 200). | Heavy (5/min) |
| `POST` | `/api/v1/optimization/walk-forward` | `OPTIMIZATION_EXECUTE` | Enforced | Execute Walk-Forward Analysis (WFA) comparing in-sample optimization against out-of-sample forward testing. Body: `WalkForwardRunRequest`. Returns `OptimizationJobDetailResponse` (HTTP 200). | Heavy (5/min) |
| `GET` | `/api/v1/optimization/jobs` | `OPTIMIZATION_READ` | Enforced | List optimization jobs and progress status. Returns `list[OptimizationJobSummaryResponse]` (HTTP 200). | Standard |
| `GET` | `/api/v1/optimization/jobs/{job_id}` | `OPTIMIZATION_READ` | Enforced | Fetch optimization results, parameter rankings, and top candidate parameter sets. Returns `OptimizationJobDetailResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/optimization/jobs/{job_id}/cancel` | `OPTIMIZATION_CANCEL` | Enforced | Cancel executing optimization job. Returns cancellation confirmation (HTTP 200). | Standard |
| `GET` | `/api/v1/optimization/jobs/{job_id}/heatmap` | `OPTIMIZATION_READ` | Enforced | 2D parameter sensitivity surface data for robustness analysis. Returns `SensitivityHeatmapResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/optimization/jobs/{job_id}/walk-forward` | `OPTIMIZATION_READ` | Enforced | Breakdown of in-sample vs out-of-sample performance across rolling windows. Returns `WalkForwardAnalysisResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/optimization/jobs/{job_id}/regimes` | `OPTIMIZATION_READ` | Enforced | Breakdown of strategy fitness across detected market regimes (Trending, Mean-Reverting, High-Volatility). Returns `list[RegimeBreakdownResponse]` (HTTP 200). | Standard |
| `GET` | `/api/v1/optimization/jobs/{job_id}/export` | `OPTIMIZATION_EXPORT` | Enforced | Export optimization sweep candidates and parameter metrics to CSV. Returns downloadable file (HTTP 200). | Standard |

---

### 2.15 Strategy Deployment Pipeline & Paper Incubator (`/api/v1/deployments`)

| Method | Endpoint | Required Permission | Tenant Context | Description / Request & Response | Rate Limit |
|---|---|---|:---:|---|:---:|
| `POST` | `/api/v1/deployments/promote/optimization` | `DEPLOYMENT_EXECUTE` | Enforced | Promote optimized strategy parameters into paper incubation deployment. Body: `PromoteFromOptimizationRequest`. Returns `DeploymentDetailResponse` (HTTP 201). | Standard |
| `POST` | `/api/v1/deployments/promote/experiment` | `DEPLOYMENT_EXECUTE` | Enforced | Promote validated backtest experiment into paper incubation deployment. Body: `PromoteFromExperimentRequest`. Returns `DeploymentDetailResponse` (HTTP 201). | Standard |
| `GET` | `/api/v1/deployments` | `DEPLOYMENT_READ` | Enforced | List active and historical incubator deployments. Returns `DeploymentListResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/deployments/{deployment_id}` | `DEPLOYMENT_READ` | Enforced | Retrieve detailed runtime health, uptime, trade count, and paper P&L for a deployment. Returns `DeploymentDetailResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/deployments/{deployment_id}/pause` | `DEPLOYMENT_CANCEL` | Enforced | Temporarily suspend execution for a deployed strategy. Body: `TransitionDeploymentRequest` (optional). Returns `DeploymentDetailResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/deployments/{deployment_id}/resume` | `DEPLOYMENT_EXECUTE` | Enforced | Resume paper execution for a paused strategy deployment. Body: `TransitionDeploymentRequest` (optional). Returns `DeploymentDetailResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/deployments/{deployment_id}/cancel` | `DEPLOYMENT_CANCEL` | Enforced | Cancel / terminate incubator deployment and release allocated resources. Body: `TransitionDeploymentRequest` (optional). Returns `DeploymentDetailResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/deployments/{deployment_id}/validate` | `DEPLOYMENT_PROMOTE` | Enforced | Run authoritative automated quality gates against deployment paper trading performance. Body: `TransitionDeploymentRequest` (optional). Returns `DeploymentDetailResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/deployments/{deployment_id}/promote-candidate` | `DEPLOYMENT_PROMOTE` | Enforced | Advance validated deployment into candidate release state. Body: `TransitionDeploymentRequest` (optional). Returns `DeploymentDetailResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/deployments/{deployment_id}/gates` | `DEPLOYMENT_READ` | Enforced | Inspect quality gate evaluation report (minimum trades, profit factor, max drawdown checks). Returns `QualityGateReportSchema` (HTTP 200). | Standard |
| `GET` | `/api/v1/deployments/{deployment_id}/metrics` | `DEPLOYMENT_READ` | Enforced | Fetch runtime execution telemetry and paper performance statistics. Returns metrics dictionary (HTTP 200). | Standard |

---

### 2.16 Institutional Broker Sandbox Integration (`/api/v1/broker-sandbox`)

| Method | Endpoint | Required Permission | Tenant Context | Description / Request & Response | Rate Limit |
|---|---|---|:---:|---|:---:|
| `GET` | `/api/v1/broker-sandbox/providers` | `BROKER_READ` | Enforced | List approved broker sandbox providers and capabilities (`MOCK`, `OANDA_PRACTICE`). Returns `list[BrokerProviderInfo]` (HTTP 200). | Standard |
| `GET` | `/api/v1/broker-sandbox/accounts` | `BROKER_READ` | Enforced | List configured practice sandbox broker connectors. Returns `list[BrokerSandboxAccountResponse]` (HTTP 200). | Standard |
| `POST` | `/api/v1/broker-sandbox/accounts` | `BROKER_SANDBOX_CONNECT` | Enforced | Connect practice broker account. Credentials encrypted at rest via AES-GCM. Rejects live endpoints. Body: `BrokerSandboxAccountCreateRequest`. Returns `BrokerSandboxAccountResponse` (HTTP 201). | Standard |
| `GET` | `/api/v1/broker-sandbox/accounts/{account_id}` | `BROKER_READ` | Enforced | Fetch broker sandbox account details and connection status. Returns `BrokerSandboxAccountResponse` (HTTP 200). | Standard |
| `PATCH` | `/api/v1/broker-sandbox/accounts/{account_id}` | `BROKER_SANDBOX_CONNECT` | Enforced | Update sandbox account credentials or settings. Body: `BrokerSandboxAccountUpdateRequest`. Returns `BrokerSandboxAccountResponse` (HTTP 200). | Standard |
| `DELETE` | `/api/v1/broker-sandbox/accounts/{account_id}` | `BROKER_SANDBOX_CONNECT` | Enforced | Delete broker sandbox account connector. Returns deletion confirmation (HTTP 200). | Standard |
| `POST` | `/api/v1/broker-sandbox/accounts/{account_id}/connect` | `BROKER_SANDBOX_CONNECT` | Enforced | Establish active connection to practice broker sandbox. Returns `BrokerSandboxConnectResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/broker-sandbox/accounts/{account_id}/disconnect` | `BROKER_SANDBOX_CONNECT` | Enforced | Terminate active connection to practice broker sandbox. Returns `BrokerSandboxConnectResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/broker-sandbox/accounts/{account_id}/positions` | `BROKER_READ` | Enforced | Retrieve open positions reported by practice broker sandbox. Returns `list[BrokerSandboxPositionResponse]` (HTTP 200). | Standard |
| `POST` | `/api/v1/broker-sandbox/accounts/{account_id}/orders` | `BROKER_SANDBOX_EXECUTE` | Enforced | Submit simulated sandbox order to practice broker API. Body: `BrokerSandboxOrderRequest`. Returns `BrokerSandboxOrderResponse` (HTTP 200). | Orders (60/min) |
| `POST` | `/api/v1/broker-sandbox/accounts/{account_id}/orders/{order_id}/cancel` | `BROKER_SANDBOX_EXECUTE` | Enforced | Cancel resting order in practice broker sandbox. Returns cancellation confirmation (HTTP 200). | Orders (60/min) |
| `POST` | `/api/v1/broker-sandbox/accounts/{account_id}/reconcile` | `BROKER_SANDBOX_RECONCILE` | Enforced | Force execution reconciliation comparing internal platform ledger against broker positions. Returns `BrokerSandboxReconciliationResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/broker-sandbox/accounts/{account_id}/reconciliations` | `BROKER_READ` | Enforced | Query historical reconciliation audit snapshots. Returns `list[BrokerSandboxReconciliationResponse]` (HTTP 200). | Standard |

---

### 2.17 Real Market Data Feeds (`/api/v1/market-data`)

| Method | Endpoint | Required Permission | Tenant Context | Description / Request & Response | Rate Limit |
|---|---|---|:---:|---|:---:|
| `GET` | `/api/v1/market-data/instruments` | `ACCOUNT_READ` | Enforced | Retrieve all supported canonical forex and commodity instruments with precision metadata. Returns `list[MarketInstrumentResponse]` (HTTP 200). | Standard |
| `GET` | `/api/v1/market-data/quotes/{symbol:path}` | `ACCOUNT_READ` | Enforced | Retrieve latest simulated bid/ask quote and spread for instrument. Returns `MarketQuoteResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/market-data/candles` | `ACCOUNT_READ` | Enforced | Query OHLCV candle bars for symbol and timeframe (`M1`, `M5`, `H1`, `D1`). Returns `MarketCandlesListResponse` (HTTP 200). | Standard |
| `GET` | `/api/v1/market-data/health` | `ACCOUNT_READ` | Enforced | Query real-time market data feed latency, provider status, and circuit-breaker state. Returns `MarketHealthResponse` (HTTP 200). | Standard |

---

### 2.18 Legal Disclosures & Consent Auditing (`/api/v1/legal`)

| Method | Endpoint | Required Permission | Tenant Context | Description / Request & Response | Rate Limit |
|---|---|---|:---:|---|:---:|
| `GET` | `/api/v1/legal/documents` | Public | None | List active legal documents, versions, effective dates, and consent requirements. Returns `list[LegalDocumentResponse]` (HTTP 200). | Standard |
| `GET` | `/api/v1/legal/documents/{document_type}` | Public | None | Retrieve complete Markdown content and metadata for a specific document. Returns `LegalDocumentDetailResponse` (HTTP 200). | Standard |
| `POST` | `/api/v1/legal/acceptances` | Authenticated | User | Record user consent or acknowledgement with client IP and user-agent hash. Body: `SubmitLegalAcceptanceRequest`. Returns `LegalAcceptanceResponse` (HTTP 201). | Standard |
| `GET` | `/api/v1/legal/acceptances` | Authenticated | User | Retrieve current user's consent and acknowledgement history. Returns `list[LegalAcceptanceResponse]` (HTTP 200). | Standard |

---

### 2.19 Operational Telemetry, Health & Scrape Probes

| Method | Endpoint | Required Permission | Description |
|---|---|---|---|
| `GET` | `/health/live` | Public | Process liveness probe. Returns HTTP 200 with `LivenessResponse(status="alive")` when ASGI application loop is responsive. |
| `GET` | `/health/ready` | Public | Dependency readiness probe. Checks active PostgreSQL database and Redis connectivity. Returns HTTP 200 with `HealthResponse` when ready; HTTP 503 if downstream dependencies fail. |
| `GET` | `/metrics` | Public (Unprotected) | Prometheus telemetry exposition format. Exposes HTTP latency histograms, order volume counters, risk limit triggers, and worker status. **Note on Authentication:** `GET /metrics` is currently exposed without an application-level authentication dependency. External network-level protection must be configured separately if required. |
| `GET` | `/api/v1/dashboard/` | `ACCOUNT_READ` | Aggregated frontend telemetry endpoint providing portfolio equity, open positions, active deployments, and risk metrics in a single payload. Returns `DashboardResponse` (HTTP 200). |

---

## 3. Standard HTTP Status & Error Protocols

All error payloads conform to a standardized RFC 7807 problem structure enforced by `apps/trading-engine/src/errors.py`:

```json
{
  "error": "UNAUTHORIZED_ACCESS",
  "message": "Invalid credentials or token expired.",
  "detail": "Invalid credentials or token expired.",
  "correlation_id": "c62b4899-73bf-4c6e-a3ef-92e1f43a084d",
  "timestamp": "2026-09-24T00:00:00Z"
}
```

| HTTP Status | Typical Condition |
|---|---|
| `200 OK` | Request succeeded; response payload returned. |
| `201 Created` | Resource successfully created (order submitted, deployment initialized, tenant registered). |
| `202 Accepted` | Asynchronous task queued. |
| `204 No Content` | Operation completed without content. |
| `400 Bad Request` | Malformed JSON, cross-tenant operation mismatch, or invalid query syntax. |
| `401 Unauthorized` | Missing, expired, or invalid JWT bearer token. |
| `403 Forbidden` | Authenticated user lacks required RBAC permission or organization membership suspended. |
| `404 Not Found` | Requested entity does not exist or belongs to another tenant organization (IDOR defense). |
| `409 Conflict` | Unique constraint violation (username or email already registered). |
| `422 Unprocessable` | Pydantic schema validation failure or business invariant violation. |
| `429 Too Many Requests` | Redis token-bucket sliding-window rate limit threshold exceeded. |
| `500 Internal Error` | Unhandled server exception (stack trace suppressed; logged with correlation ID). |
| `503 Service Unavailable` | Readiness probe failure; database or Redis unreachable. |
