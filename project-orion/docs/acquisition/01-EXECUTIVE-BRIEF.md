# Project ORION — Executive Brief & Acquisition Summary

**Document Version:** 1.0.0<br>
**Target Milestone:** EPIC-027 Phase 7B Acquisition Due Diligence<br>
**Repository Working Copy:** `project-orion/`<br>
**Classification:** Confidential — Due Diligence Technical Data Room (Tier 2 / NDA)<br>
**Safety Mandate:** STRICT PAPER TRADING ONLY ($0.00 Capital at Risk — Zero Live Broker Endpoints)

---

## 1. Executive Summary

This executive brief presents an objective, evidence-based technical summary of **Project ORION**, prepared for founder, executive, and technical due-diligence teams evaluating an outright software asset acquisition.

Project ORION is an institutional-architecture quantitative Forex research, combinatorial optimization, Walk-Forward Analysis (WFA), and adverse-slippage paper trading simulation SaaS platform. Developed natively in **Python 3.11** and **TypeScript / React 18**, the system decouples mathematical strategy modeling from execution infrastructure through **Hexagonal (Ports and Adapters)** architecture and **Domain-Driven Design (DDD)**.

The platform is offered as a pure software asset sale. The codebase, configuration, container definitions, migration chains, test suites, and documentation are self-contained within the `project-orion` monorepo.

---

## 2. Product Category & Target Buyer Profile

### Product Category
- **Primary Category:** Quantitative Algorithmic Forex Trading & Research Simulation SaaS.
- **Secondary Category:** Multi-Tenant Strategy Backtesting, Combinatorial Optimization & Walk-Forward Validation Engine.

### Explicit Negative Declarations
To maintain strict compliance and clarity during due diligence, Project ORION is explicitly NOT:
- A live trading brokerage or broker-dealer.
- An investment advisor, asset manager, or hedge fund.
- A custodian of customer capital or funds.
- A real-money trading execution system.
- A regulated financial institution.

All order routing, position matching, margin tracking, and portfolio valuations operate strictly in simulated virtual currency environments ($0.00 capital at risk).

---

## 3. Core Product Capabilities

Project ORION delivers a complete lifecycle for algorithmic Forex strategy design, empirical testing, and paper execution:

1. **Quantitative Strategy Lab:** Modular strategy authoring framework supporting classical, breakout, trend-following, and statistical mean-reversion archetypes with typed parameter schemas.
2. **Deterministic Historical Backtesting:** Bar-by-bar historical simulation calculating comprehensive performance metrics (Sharpe, Sortino, Calmar, maximum drawdown, win rate, profit factor, equity curves).
3. **Combinatorial Parameter Optimization:** Multi-parameter grid search and quasi-random parameter sweeps evaluating bounding spaces.
4. **Walk-Forward Analysis (WFA):** Rolling In-Sample (IS) training and Out-of-Sample (OOS) validation windows designed to detect curve-fitting and assess out-of-sample efficiency.
5. **Strategy Deployment Incubator:** Multi-stage governance pipeline tracking strategy promotion through rigorous validation stages before paper trading deployment.
6. **Realistic Paper Trading Microstructure:** Simulated execution modeling bid/ask spreads, order volume decay, resting limit/stop triggers, and adverse slippage.
7. **Pre-Trade Risk Management:** Enforces leverage ceilings, margin utilization thresholds, maximum drawdown limits, and daily loss caps.
8. **Multi-Tenant SaaS Governance:** Multi-tenant organization partitioning, user invitations, and fine-grained authorization enforcing **41 granular permissions defined by the current RBAC permission model** across 7 roles.
9. **Guided User Onboarding:** Sequential 5-step onboarding workflow (`WELCOME`, `EMAIL_VERIFICATION`, `STRATEGY`, `RISK`, `PAPER_TRADING_READY`) tracking progression in relational storage.
10. **Commercial Billing Integration:** Stripe subscription billing integration operating in Test Mode with automated webhook signature validation.

---

## 4. Technology Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                              CLIENT TIER                                │
│       React 18 / TypeScript 5 / Vite SPA (Multi-Stage Nginx Container) │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS / RESTful JSON
┌───────────────────────────────────▼────────────────────────────────────┐
│                        API & ORCHESTRATION TIER                         │
│     FastAPI / Uvicorn ASGI Server (Python 3.11, Non-Root User orion)    │
│            24 Router Modules | Starlette Defense Middleware             │
└──────────────────┬────────────────────────────────┬────────────────────┘
                   │                                │
┌──────────────────▼──────────────┐   ┌─────────────▼────────────────────┐
│         DOMAIN LAYER            │   │      INFRASTRUCTURE ADAPTERS     │
│   21 Pure Python Bounded        │   │  SQLAlchemy 2.0 / asyncpg Pool   │
│   Contexts (Zero Framework Dims)│   │  Redis 7 Client / Token Bucket   │
└─────────────────────────────────┘   │  SMTPEmailAdapter (Worker Thread)│
                                      │  Stripe Test Billing Adapter     │
                                      │  OANDA Practice Sandbox Adapter  │
                                      └──────────────────────────────────┘
```

- **Clean Domain Separation:** The domain core (`libraries/domain/`) contains pure business logic and financial calculations with zero external framework dependencies.
- **Asynchronous Persistence:** High-concurrency database access orchestrated via SQLAlchemy 2.0 and `asyncpg` connection pooling.
- **Relational Integrity:** 15 linear forward migrations managed by Alembic, ensuring structured database schema versioning up to canonical head `0015_onboarding_progress`.
- **In-Memory Acceleration:** Redis 7 utilized for sliding-window rate limiting, quote caching, and distributed locking.

---

## 5. Quantitative Research & Simulation Capabilities

Project ORION is engineered around scientific quantitative validation rather than unverified commercial promises:
- **Arbitrary Precision Arithmetic:** All financial balances, lot allocations, pip measurements, and P&L calculations strictly use Python `Decimal` to eliminate binary floating-point drift.
- **Adverse Slippage Simulation:** Virtual order matching dynamically penalizes fills based on simulated trade size and market spread volatility, counteracting overly optimistic backtest assumptions.
- **Overfitting Diagnostics:** Integrated Walk-Forward Analysis partitions historical data across rolling training and forward testing slices, quantifying out-of-sample degradation.

---

## 6. Multi-Tenancy, RBAC & Governance

- **Logical Tenant Partitioning:** Row-level multi-tenancy enforced across all persistent entities via indexed `organization_id` foreign keys, validated against cryptographically signed JWT `TenantContext`.
- **Granular RBAC:** Exactly **41 granular permissions defined by the current RBAC permission model** governing organization administration, strategy execution, risk limits, paper trading, and audit inspection.
- **7 Organization Roles:** `OWNER`, `ADMINISTRATOR`, `PORTFOLIO_MANAGER`, `RISK_OFFICER`, `TRADER`, `AUDITOR`, and `VIEWER`.
- **Immutable Audit Logging:** Sensitive administrative actions, membership alterations, and trading decisions append append-only records to `audit_logs`.

---

## 7. Infrastructure & Deployment Blueprint

The primary production deployment model is declaratively defined as an Infrastructure-as-Code (IaC) Blueprint for the **Render Platform-as-a-Service (PaaS)** (`render.yaml`):

| Resource Name | Service Type | Runtime Environment | Render Plan | Network Isolation |
|---|---|---|---|---|
| `orion-api` | Web Service | Docker (`trading-engine/Dockerfile`) | `starter`* | Public HTTPS |
| `orion-dashboard` | Web Service | Docker (`dashboard/Dockerfile`) | `free` | Public HTTPS |
| `orion-postgres` | Managed Relational DB | PostgreSQL 15 | `basic-1gb`* | Private Mesh (`ipAllowList: []`) |
| `orion-redis` | Managed Key-Value Store| Redis 7 | `free` | Private Mesh (`ipAllowList: []`) |

*\*Note on Paid Plan Dependencies: The `starter` web plan is required to enable Render's `preDeployCommand` lifecycle hook. The `basic-1gb` PostgreSQL plan provides persistent SSD storage and automated daily snapshots. Deploying these tiers requires an active payment method on the buyer's Render account.*

### Decoupled Pre-Deployment Migration
Render executes `python scripts/deploy/migrate.py` in an ephemeral container prior to routing traffic to new container builds. If a migration encounters an error, the deployment immediately aborts, providing migration failure isolation before application deployment.

---

## 8. Security & Safety Boundaries

1. **Fail-Closed Execution Invariant:** Live broker endpoints fail closed. Configuration attempting to bind to live broker URLs raises fatal exceptions. External connectivity is structurally restricted to practice environments (e.g. OANDA v20 practice).
2. **Autonomous Loop Safety Lock:** The background strategy execution loop is disabled by default (`ORION_WORKER_ENABLED: "false"`). Enabling autonomous execution requires an explicit operational configuration change.
3. **Fail-Closed Billing Invariant:** The billing configuration rejects live Stripe credentials. If keys with live production prefixes are provided, `LiveCredentialsForbiddenError` is raised immediately.
4. **Credential & Session Hygiene:** Passwords are protected using salted Bcrypt cryptographic hashing. Access tokens are stateless HMAC-SHA256 JWTs with 30-minute expiration. User password modifications update `password_changed_at`, immediately invalidating all active sessions.
5. **Anti-Enumeration Protections:** Public authentication routes (`/forgot-password`, `/resend-verification`) return identical timing and generic response messages regardless of account existence. Outbound email network errors are masked from callers.
6. **Container Security:** Application containers execute strictly as unprivileged non-root users (`orion`, `uid=999`).

---

## 9. Verification Evidence

- **Regression Test Coverage:** Repository verification reports extensive automated backend and frontend regression coverage; exact CI aggregate should be verified by the buyer.
- **Physical Disaster Recovery Demonstration:** In an isolated target environment demonstration (EPIC-027 Phase 6C), database restoration completed in **7 seconds**, within the <60-minute operational RTO target. The documented operational RPO target is <24 hours. The restore verified a schema of 29 tables derived from SQLAlchemy declarative models and `alembic_version`.
- **Pre-Commit Quality Standards:** Zero whitespace warnings, strict type annotations (`mypy`), and complete secret pattern scanning across acquisition documentation.

---

## 10. Acquisition & Handover Scope

The outright software asset acquisition includes:
1. **Full Monorepo Source Code:** Complete backend trading engine, domain libraries, frontend React dashboard, and deployment configurations.
2. **Database Schema & Migrations:** 15 linear forward Alembic revisions and entity relationship definitions.
3. **Disaster Recovery Suite:** Shell scripts for logical dump creation, checksum sidecar generation, and isolated restoration verification.
4. **Technical Documentation Suite:** 14 buyer-facing due-diligence documents in `docs/acquisition/` and historical engineering reports.

---

## 11. Known Commercial & Ownership Unknowns

To ensure fair and transparent due diligence, the buyer should note the following commercial realities:
- **Asset-Sale Basis:** The project is being prepared for an outright software and intellectual-property asset sale; no historical customer revenue, MRR/ARR, or subscriber contracts are established in the repository.
- **No Historical Live Trading Record:** The platform contains no audited real-money trading performance history, track record, or verified investment returns.
- **Absence of Formal Compliance Certifications:** The software has not undergone external SOC 2, ISO 27001, or PCI-DSS compliance audits.
- **Third-Party Account Provisioning:** The buyer must independently provision corporate accounts for Render cloud hosting, Stripe payment processing, TwelveData market feeds, and SMTP transactional email delivery.
- **Chain of Title Verification:** Legal assignment of intellectual property and definitive asset purchase terms require standard bilateral legal agreements between buyer and seller entities.
