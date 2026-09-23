# Project ORION — Software Bill of Materials (SBOM) & Dependency Audit

**Document Version:** 1.0.0
**Target Milestone:** EPIC-027 Phase 7B Acquisition Due Diligence
**Repository Working Copy:** `project-orion/`
**Classification:** Confidential — Due Diligence Technical Data Room (Tier 2 / NDA)
**Safety Mandate:** STRICT PAPER TRADING ONLY ($0.00 Capital at Risk — Zero Live Broker Endpoints)

---

## 1. Executive Summary & Inventory Methodology

This Software Bill of Materials (SBOM) provides a complete accounting of third-party open-source libraries, frameworks, runtime runtimes, and developer tooling utilized by Project ORION across both the Python trading engine backend and the React TypeScript frontend dashboard.

### Source of Truth
- **Backend (Python):** `pyproject.toml` and `poetry.lock` (Poetry dependency manager, Python 3.11 target).
- **Frontend (Node/React):** `apps/dashboard/package.json` and `package-lock.json` (Vite, React 18, TypeScript 5 target).
- **Container Infrastructure:** `docker/apps/*.Dockerfile`, `render.yaml`.

---

## 2. Backend Runtime Dependencies (Python 3.11)

These packages are installed in the production container image (`docker/apps/trading-engine/Dockerfile`) and execute in the live application lifespan.

| Package | Declared Version | Purpose | Dependency Type | Known License* |
|---|---|---|---|---|
| `python` | `^3.11` | Core language runtime | Core Runtime | Python Software Foundation License |
| `fastapi` | `^0.115` | High-performance asynchronous web & REST API framework | Direct Runtime | MIT |
| `uvicorn` | `^0.34` (standard) | Asynchronous Server Gateway Interface (ASGI) web server | Direct Runtime | BSD-3-Clause |
| `pydantic` | `^2.0` | Data validation, request parsing, and schema serialization | Direct Runtime | MIT |
| `sqlalchemy` | `^2.0.52` (asyncio) | SQL toolkit and Object-Relational Mapper (ORM) | Direct Runtime | MIT |
| `alembic` | `^1.20.0` | Database schema migrations management | Direct Runtime | MIT |
| `asyncpg` | `^0.31.0` | High-performance asynchronous PostgreSQL database driver | Direct Runtime | Apache-2.0 |
| `aiosqlite` | `^0.22.1` | Asynchronous SQLite driver for local dev & unit tests | Direct Runtime | MIT |
| `redis` | `^8.1.0` | Async client for Redis caching, rate limiting, and state | Direct Runtime | MIT |
| `pyyaml` | `^6.0.1` | YAML configuration file parsing | Direct Runtime | MIT |
| `passlib` | `^1.7.4` (bcrypt) | Password hashing utilities (Bcrypt & Argon2 support) | Direct Runtime | BSD-3-Clause |
| `python-jose` | `^3.5.0` (crypto) | JavaScript Object Signing and Encryption (JWT handling) | Direct Runtime | MIT |
| `starlette` | *Transitive via FastAPI* | ASGI toolkit underlying FastAPI | Transitive Runtime | BSD-3-Clause |
| `bcrypt` | *Transitive via passlib* | Native C-binding Bcrypt password hashing | Transitive Runtime | Apache-2.0 |
| `cryptography` | *Transitive via jose* | Core cryptographic primitives and SSL bindings | Transitive Runtime | Apache-2.0 / BSD-3-Clause |

*\*Note on License Verification: Package licenses are reported based on canonical upstream registry declarations. Where licenses cannot be verified from repository files alone, license verification requires package-registry/license-database confirmation.*

---

## 3. Backend Development, Quality & Test Tooling

These packages are restricted strictly to developer workstations and CI/CD pipelines (`poetry.group.dev.dependencies`) and are excluded from production container builds.

| Package | Declared Version | Purpose | Dependency Scope | Known License* |
|---|---|---|---|---|
| `pytest` | `^8.4` | Automated test runner and assertion framework | Dev / Test | MIT |
| `pytest-cov` | `^4.1.0` | Test coverage reporting and metrics | Dev / Test | MIT |
| `pytest-asyncio` | `^1.4` | Async fixture and event loop execution for pytest | Dev / Test | Apache-2.0 |
| `httpx` | `^0.27` | Async HTTP client for ASGI integration testing | Dev / Test | BSD-3-Clause |
| `anyio` | `^4` (trio) | Async concurrency networking library | Dev / Test | MIT |
| `black` | `^23.7.0` | Deterministic Python code formatter | Dev Tool | MIT |
| `isort` | `^5.12.0` | Import statement sorting and organization | Dev Tool | MIT |
| `mypy` | `^1.5.0` | Static type checker enforcing strict typing | Dev Tool | MIT |
| `pylint` | `^2.17.0` | Python source code analyzer and linter | Dev Tool | GPL-2.0-or-later (Dev Only)** |
| `pip-audit` | `^2.10.1` | Vulnerability scanner for installed dependencies | Dev / Security | Apache-2.0 |
| `types-pyyaml` | `^6.0.12` | Type stubs for PyYAML | Dev / Typing | Apache-2.0 |

*\*\*Note on Dev-Only Licensing: `pylint` is licensed under GPL-2.0-or-later. It is installed purely as an offline CLI linting tool; it is never linked, distributed, or bundled into production application artifacts.*

---

## 4. Frontend Runtime Dependencies (React Dashboard)

Source: `apps/dashboard/package.json`. These packages are bundled into static browser assets during `vite build` and served via Nginx in `docker/apps/dashboard/Dockerfile`.

| Package | Declared Version | Purpose | Dependency Type | Known License* |
|---|---|---|---|---|
| `react` | `^18.3.1` | Core React UI component library | Direct Runtime | MIT |
| `react-dom` | `^18.3.1` | React DOM renderer for browser environments | Direct Runtime | MIT |
| `react-router-dom` | `^6.26.2` | Client-side routing and navigation | Direct Runtime | MIT |
| `lucide-react` | `^0.441.0` | Institutional UI icons and visual glyphs | Direct Runtime | ISC |

---

## 5. Frontend Development & Build Tooling

Source: `apps/dashboard/package.json` (`devDependencies`). Excluded from runtime Nginx image.

| Package | Declared Version | Purpose | Dependency Scope | Known License* |
|---|---|---|---|---|
| `vite` | `^5.4.2` | Frontend build tool and local dev server | Dev / Build | MIT |
| `typescript` | `^5.5.3` | TypeScript compiler and language server | Dev / Build | Apache-2.0 |
| `@vitejs/plugin-react` | `^4.3.1` | Fast Refresh and JSX transform plugin | Dev / Build | MIT |
| `vitest` | `^2.0.5` | Fast unit test runner powered by Vite | Dev / Test | MIT |
| `jsdom` | `^25.0.0` | Pure-JavaScript DOM implementation for Vitest | Dev / Test | MIT |
| `@testing-library/react` | `^16.0.0` | React component testing utilities | Dev / Test | MIT |
| `@testing-library/jest-dom` | `^6.5.0` | Custom Jest matchers for DOM assertions | Dev / Test | MIT |
| `@testing-library/user-event` | `^14.5.2` | User interaction simulation for tests | Dev / Test | MIT |
| `@types/react` | `^18.3.5` | TypeScript type declarations for React | Dev / Typing | MIT |
| `@types/react-dom` | `^18.3.0` | TypeScript type declarations for React DOM | Dev / Typing | MIT |
| `@types/node` | `^20.14.0` | TypeScript type declarations for Node.js | Dev / Typing | MIT |

---

## 6. Runtime Platforms & Container Base Images

| Component | Base Technology | Version / Tag | Supplier / Distributor |
|---|---|---|---|
| **API Container** | `python:3.11-slim` | 3.11-slim (Debian) | Docker Official Images |
| **Dashboard Container** | `node:20-alpine` (Build) / `nginx:1.27-alpine-slim` (Runtime) | Node 20 / Nginx 1.27 Alpine Slim | Docker Official Images |
| **Relational Database** | PostgreSQL | 15 | Render Managed PostgreSQL / Docker Official |
| **In-Memory Cache** | Redis | 7 | Render Managed Key-Value / Docker Official |

---

## 7. External SaaS & Cloud Service Dependencies

Project ORION incorporates integration adapters designed to connect to external SaaS and cloud platforms. These represent external service dependencies that require buyer-provisioned commercial accounts; no proprietary subscriber accounts or vendor licenses transfer with the software code repository:

| Service / Provider | Purpose | Integration Point | Operational Environment | Buyer Provisioning Requirement |
|---|---|---|---|---|
| **Render Cloud PaaS** | Cloud deployment platform, web hosting, managed PostgreSQL & Redis | `render.yaml` | Production / Staging | Buyer provisions independent Render corporate account & payment method. |
| **TwelveData** | Real-time and historical OHLCV market data feeds | `libraries/infrastructure/market_data/` | All Environments | Buyer provisions TwelveData API key (`ORION_MARKET_DATA_API_KEY`). |
| **OANDA Practice REST API** | Demo broker sandbox and reconciliation testing | `libraries/infrastructure/execution/oanda_execution.py` | Staging / Testing | Buyer provisions OANDA v20 fxTrade demo account and practice API token. |
| **Stripe Test Mode** | Subscription lifecycle, billing invoices, checkout session webhooks | `libraries/infrastructure/billing/` | Staging / Testing | Buyer provisions Stripe account in Test Mode (`ORION_STRIPE_SECRET_KEY`). |
| **External SMTP Relay** | Outbound transactional email delivery (verification, password reset) | `libraries/infrastructure/communication/email_service.py` | Staging / Production | Buyer provisions transactional SMTP credentials (e.g. SendGrid, Mailgun, Amazon SES). |

---

## 8. Known License-Review Limitations & Certification Disclaimers

1. **Independent Verification Mandate:** Package licenses reported throughout this document are derived from canonical upstream registry declarations (PyPI and npm). Where license status has not been independently legally audited, license classification requires buyer/legal verification.
2. **No Repository Legal SBOM Certification:** This document represents an architectural and technical inventory compiled from build manifests (`pyproject.toml`, `package.json`, Dockerfiles). The repository itself does not constitute a formal legal SBOM certification or warranty of intellectual property non-infringement.
3. **Dual / Complex Licenses in Transitive Packages:** Transitive packages pulled by cryptography or web assembly toolchains may contain dual licenses (e.g. OpenSSL license, Apache 2.0). License verification requires package-registry/license-database confirmation.
4. **Offline Tooling Segregation:** Developer tooling that contains copyleft licensing (`pylint` under GPL-2.0) is strictly quarantined within `poetry.group.dev.dependencies`. It is never executed in production containers, ensuring no copyleft reciprocal obligations attach to Project ORION proprietary source code.
5. **No Proprietary Vendor Lock-in:** All backend and frontend dependencies are standard open-source projects hosted on public PyPI and npm registries without proprietary runtime licensing fees.
