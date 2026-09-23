# Project ORION — Technical Handover & Developer Architecture Guide

**Document Version:** 1.0.0<br>
**Target Milestone:** EPIC-027 Phase 7B Acquisition Due Diligence<br>
**Repository Working Copy:** `project-orion/`<br>
**Classification:** Confidential — Due Diligence Technical Data Room (Tier 2 / NDA)<br>
**Safety Mandate:** STRICT PAPER TRADING ONLY ($0.00 Capital at Risk — Zero Live Broker Endpoints)

---

## 1. Handover Purpose & Engineering Overview

This technical handover guide is prepared for the buyer's engineering team assuming operational, maintenance, and development ownership of **Project ORION**.

Project ORION is structured as a modular Python and TypeScript monorepo adhering strictly to **Clean Architecture** and **Domain-Driven Design (DDD)**. The system separates pure financial domain logic from database engines, web frameworks, and third-party SaaS providers.

> [!NOTE]
> **Legacy Documentation Clarification:**
> Early repository artifacts (such as the initial root `README.md` and legacy operations drafts) referenced planned Kubernetes manifests, Go microservices, and mobile clients. The actual, verified, and operational production architecture is an ASGI Python 3.11 backend (`apps/trading-engine/`) and a React 18 TypeScript SPA frontend (`apps/dashboard/`) orchestrated for Render PaaS and Docker Compose.

---

## 2. Monorepo Directory Architecture

The `project-orion` repository is structured into clear architectural tiers:

```
project-orion/
├── apps/
│   ├── dashboard/               # Frontend React 18 / Vite / TypeScript SPA
│   │   ├── src/                 # UI components, pages, hooks, API client
│   │   ├── Dockerfile           # Multi-stage build (Node 20 builder -> Nginx runtime)
│   │   └── package.json         # Dashboard dependencies and scripts
│   └── trading-engine/          # Backend FastAPI / Uvicorn ASGI Application
│       ├── src/
│       │   ├── main.py          # ASGI application entrypoint & middleware assembly
│       │   ├── config.py        # Environment settings with fail-closed validation
│       │   ├── dependencies.py  # FastAPI dependency injection definitions
│       │   ├── routes/          # 24 modular REST API router modules
│       │   ├── services/        # Application orchestration services
│       │   └── middleware/      # Rate limit, tenant context, security headers
│       └── tests/               # Application-level integration tests
├── libraries/
│   ├── domain/                  # Pure domain logic (21 bounded context modules)
│   │   ├── backtesting/         # Historical simulation and tear-sheet metrics
│   │   ├── execution/           # Order entities, fills, positions, paper logic
│   │   ├── indicators/          # Pure Python Decimal technical indicators
│   │   ├── market_data/         # Candle, quote, and tick domain models
│   │   ├── optimization/        # Grid search, random sweep, Walk-Forward Analysis
│   │   ├── organization/        # Multi-tenancy, memberships, and 41 RBAC permissions
│   │   ├── risk/                # Margin policies, leverage rules, drawdown limits
│   │   ├── strategy/            # Strategy base contracts and parameter schemas
│   │   └── legal/               # Versioned legal terms and risk disclosure receipts
│   └── infrastructure/          # Concrete adapters implementing domain ports
│       ├── billing/             # Stripe Test Mode adapter and webhook verification
│       ├── caching/             # Redis client wrapper and sliding-window rate limit
│       ├── communication/       # SMTPEmailAdapter with async worker thread offload
│       ├── execution/           # PaperExecutionAdapter & OANDA practice adapter
│       ├── market_data/         # TwelveData REST client & mock Brownian generator
│       └── persistence/         # SQLAlchemy 2.0 models, base declarative class, asyncpg
├── database/
│   └── migrations/              # Alembic schema migrations (15 linear revisions)
├── docker/                      # Container Dockerfiles and configuration files
├── backup/                      # Disaster recovery scripts (backup, restore, retention)
├── scripts/
│   └── deploy/                  # Production pre-deploy migration runner and restore verifier
├── tests/                       # Automated test suite (unit and integration)
├── pyproject.toml               # Poetry dependencies, build configuration, tool settings
├── render.yaml                  # Declarative 4-tier Render PaaS blueprint
└── docker-compose.yml           # Local development backing services (PostgreSQL & Redis)
```

---

## 3. Workstation Prerequisites

The engineering team requires the following standard developer toolchains:

| Toolchain | Minimum Version | Purpose |
|---|---|---|
| **Python** | `3.11.x` | Runtime environment for backend engine and domain libraries. |
| **Poetry** | `>= 1.7.0` | Python dependency management and virtual environment orchestration. |
| **Node.js** | `20.x LTS` (Iron) | Compilation runtime for the dashboard React Vite application. |
| **npm** | `>= 10.x` | Frontend package manager. |
| **Docker Engine** | `>= 24.0.0` | Container image builds and containerized development stacks. |
| **Docker Compose**| `>= 2.20.0` | Local orchestration of backing PostgreSQL and Redis instances. |
| **PostgreSQL Client**| `15.x` | Administrative CLI utilities (`psql`, `pg_dump`, `pg_restore`). |

---

## 4. Local Development Spin-Up Runbook

Follow these exact steps to initialize and run the platform locally:

### Step 1: Start Backing Services
```bash
cd project-orion
docker compose up -d postgres redis
```
Verify that PostgreSQL is accessible on port `5432` (or mapped port `5433`) and Redis is accessible on port `6379`.

### Step 2: Initialize Python Virtual Environment
```bash
poetry install
```

### Step 3: Apply Database Migrations
Run forward migrations up to the canonical head (`0015_onboarding_progress`):
```bash
poetry run alembic upgrade head
```

### Step 4: Launch Backend ASGI Server
```bash
poetry run uvicorn apps.trading_engine.src.main:app --host 0.0.0.0 --port 8000 --reload
```
Test health probes:
```bash
curl -s http://localhost:8000/health/live
# Expected: {"status":"live"}

curl -s http://localhost:8000/health/ready
# Expected: {"status":"ready","database":"connected","redis":"connected"}
```

### Step 5: Launch Frontend Dashboard
In a separate terminal window:
```bash
cd apps/dashboard
npm install
npm run dev
```
Open `http://localhost:5173` in a web browser. API requests are automatically reverse-proxied to port 8000.

---

## 5. Test Execution & Code Quality Standards

### Running Automated Backend Tests
```bash
# Run all unit tests
poetry run pytest tests/unit/

# Run integration tests
poetry run pytest tests/integration/

# Run tests with coverage reporting
poetry run pytest --cov=apps --cov=libraries tests/
```

### Running Frontend Tests
```bash
cd apps/dashboard
npm run test
```

### Code Formatting & Static Analysis
```bash
# Code formatting check
poetry run black --check .
poetry run isort --check-only .

# Strict type checking
poetry run mypy apps libraries
```

---

## 6. Database Schema Evolution Workflow

Project ORION strictly enforces a **Forward-Fix Only Policy** in production environments. Never execute `alembic downgrade` against a production database.

### Authoring a New Migration
1. Modify or create declarative models in `libraries/infrastructure/persistence/models/`.
2. Generate an Alembic revision script:
   ```bash
   poetry run alembic revision -m "describe_change"
   ```
3. Edit the generated file in `database/migrations/versions/`. Ensure both `upgrade()` and `downgrade()` functions are written cleanly and backward-compatibly (e.g. adding nullable columns first).
4. Verify migration locally:
   ```bash
   poetry run alembic upgrade head
   ```
5. Commit the migration script alongside the model changes.

---

## 7. Extending the Platform

### 7.1 Adding a New Technical Indicator
1. Create a new module or function in `libraries/domain/indicators/`.
2. Accept a sequence of quotes or prices and return calculated indicator values.
3. Use Python `Decimal` for all floating arithmetic.
4. Add comprehensive unit tests in `tests/unit/domain/test_indicators.py` verifying precision against reference data.

### 7.2 Adding a New Quantitative Strategy Archetype
1. Inherit from `BaseStrategy` in `libraries/domain/strategy/base.py`.
2. Define the strategy parameter dataclass with typed fields and default bounding ranges.
3. Implement `generate_signals(self, candle: Candle) -> list[Signal]`.
4. Register the strategy archetype in `libraries/domain/strategies/registry.py`.
5. Expose parameter schema validation in `apps/trading-engine/src/routes/strategies.py`.

### 7.3 Adding a New Infrastructure Adapter
1. Define the abstract port interface as a `typing.Protocol` inside `libraries/domain/` (e.g. `libraries/domain/communication/ports.py`).
2. Implement the concrete adapter class inside `libraries/infrastructure/` (e.g. `libraries/infrastructure/communication/custom_adapter.py`).
3. Inject the adapter in `apps/trading-engine/src/dependencies.py` via FastAPI `Depends()`.

---

## 8. Non-Negotiable Engineering Invariants

1. **Strict Paper Trading Mandate:** All order placement, balance debiting, and fill simulation must route through simulated virtual books. Live broker endpoints are structurally forbidden ($0.00 capital at risk).
2. **Decimal Precision Invariant:** Never use native Python `float` for prices, pip values, currency amounts, margin balances, or P&L. Always use `Decimal`.
3. **No Domain Framework Leaks:** Files inside `libraries/domain/` must never import `fastapi`, `starlette`, `sqlalchemy`, or external cloud vendor SDKs.
4. **Non-Root Container Runtime:** All container definitions must run as unprivileged non-root users (`USER orion` or `USER nginx`).
5. **Zero Hardcoded Secrets:** Configuration must be externalized into environment variables. Fallback secrets are prohibited in production.

---

## 9. Buyer Cloud Provisioning Checklist

Prior to launching in a buyer-owned cloud environment:
1. **Render PaaS Account:** Create account and register payment method (required for `starter` API and `basic-1gb` PostgreSQL plans).
2. **Stripe Account:** Register Stripe account, enable Test Mode, and retrieve test secret key and webhook signing secret.
3. **TwelveData Subscription:** Register for an API key at TwelveData for live market candle data feeds.
4. **SMTP Relay:** Configure transactional email relay (SendGrid, Postmark, AWS SES) and verify domain SPF/DKIM DNS records.
5. **OANDA Practice Sandbox:** Register for an OANDA fxTrade practice account to obtain demo REST credentials.
