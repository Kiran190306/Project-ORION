# Project ORION — Account Ownership Transfer & Infrastructure Handover

**Document Version:** 1.0.0
**Target Milestone:** EPIC-027 Phase 7B Acquisition Due Diligence
**Repository Working Copy:** `project-orion/`
**Classification:** Confidential — Due Diligence Technical Data Room (Tier 3 / Closing)
**Safety Mandate:** STRICT PAPER TRADING ONLY ($0.00 Capital at Risk — Zero Live Broker Endpoints)

---

## 1. Executive Summary & Transfer Principles

This document provides a technically rigorous, step-by-step handover runbook for all external platforms, cloud accounts, SaaS integrations, and database stores associated with **Project ORION**.

### Core Account Transfer Principles
1. **Repository vs Account Boundary:** The Project ORION codebase, blueprints (`render.yaml`), and database schemas transfer as software intellectual property. External cloud and vendor accounts (e.g. Render, Stripe, TwelveData) are separate third-party contracts subject to vendor Terms of Service.
2. **Account Transferability Not Assumed:** Mere existence of configuration or credentials does **not** establish that an account is legally or technically transferable. Where third-party KYC/AML regulations or vendor policies prohibit direct account assignment, the standard handover path is **independent buyer-side provisioning**.
3. **Zero In-Repo Credentials:** No active passwords, private keys, API secrets, or database credentials exist within the repository. Handover procedures focus on secret injection into buyer-controlled environments.
4. **Clean Re-Deployment Priority:** To ensure pristine operational ownership, the recommended handover mechanism for cloud hosting is deploying the repository blueprint into a fresh, buyer-owned cloud tenant rather than inheriting legacy administrative history.

---

## 2. Master Platform & SaaS Account Matrix

| Service / Platform | Role in Platform | Current Repo Status | Transferability Status | Primary Handover Path |
|---|---|---|---|---|
| **GitHub** | Source code repository & Git history | Remote: `Kiran190306/Project-ORION` | Transferable via GitHub Org/Settings | Direct repo transfer OR mirror push to buyer Git org |
| **Render PaaS** | Web hosting, managed DB & cache | Defined in `render.yaml` | Transferability Not Established | Deploy `render.yaml` Blueprint in buyer-owned Render account |
| **PostgreSQL** | Relational data store (`orion-postgres`)| Render Managed DB (v15) | Cross-account transfer not supported by PaaS | Logical backup (`database-backup.sh`) -> restore into buyer DB |
| **Redis** | Cache, rate limiter, task lock | Render Managed Redis (v7) | Ephemeral in-memory store | Fresh instance provisioned via `render.yaml` Blueprint |
| **Stripe** | Commercial billing & subscription state | **TEST MODE ONLY** (`price_test_*`) | **Non-Transferable (KYC/AML Bound)** | Buyer provisions new Stripe account; injects test/live keys |
| **OANDA** | Broker sandbox practice execution | Practice REST API (`api-fxpractice`) | Practice account; Non-Transferable | Buyer registers free OANDA demo account; connects via UI |
| **TwelveData** | Real-time & historical OHLCV feeds | Ingest adapter in `libraries/` | Vendor account transfer not established | Buyer provisions TwelveData API key; sets `ORION_MARKET_DATA_API_KEY` |
| **SMTP Provider** | Transactional verification emails | SMTP adapter in `libraries/` | Vendor account transfer not established | Buyer provisions transactional SMTP relay (SendGrid, SES, Mailgun) |
| **Offsite Backup** | Disaster recovery object storage | Documented in runbooks | Vendor account transfer not established | Buyer provisions AWS S3 / Cloudflare R2 bucket & IAM keys |

---

## 3. Detailed Service Transfer Protocols

### 3.1 GitHub Repository (`Kiran190306/Project-ORION`)

- **Current Repository Configuration:**
  - Remote Origin: `https://github.com/Kiran190306/Project-ORION.git`
  - Active Branch: `main` (commit `29494cf`)
  - No `.github/` workflows or repository secrets are committed in git.
- **Account Identification & Ownership Distinction:**
  - Repository files reference namespace `Kiran190306`. Repository evidence indicates a personal GitHub account.
  - Legal ownership cannot be inferred from a username alone.
- **Transfer / Re-Provisioning Paths:**
  - **Path A (Direct GitHub Transfer — Preferred if Seller Agrees):**
    1. Buyer provides their target GitHub Organization name (e.g. `github.com/BuyerOrg`).
    2. Seller navigates to `Repository Settings -> Danger Zone -> Transfer ownership`.
    3. Seller enters target organization name and confirms with two-factor authentication (2FA).
    4. Buyer accepts transfer invitation in target organization settings.
    5. GitHub automatically redirects existing Git remote URLs.
  - **Path B (Clean Git Mirror Push — Autonomous Alternative):**
    1. Buyer provisions empty private repository `github.com/BuyerOrg/project-orion`.
    2. Seller or Buyer executes mirror push preserving full history and tags:
       ```bash
       git clone --mirror https://github.com/Kiran190306/Project-ORION.git
       cd Project-ORION.git
       git push --mirror https://github.com/BuyerOrg/project-orion.git
       ```
- **Validation After Transfer:**
  - Verify commit count (46 commits) and HEAD commit SHA (`29494cf`).
  - Verify commit integrity: `git fsck --full`.
- **Rollback / Contingency:**
  - Both parties maintain offline local git mirrors prior to transfer initiation.

---

### 3.2 Render Cloud PaaS (`render.yaml`)

- **Current Repository Configuration:**
  - Services defined in `render.yaml`:
    - `orion-postgres`: Managed PostgreSQL 15 (`basic-1gb` tier).
    - `orion-redis`: Managed Redis 7 (`free` tier).
    - `orion-api`: Python 3.11 FastAPI web service (`starter` tier).
    - `orion-dashboard`: React 18 / Nginx web service (`free` tier).
  - Production deployments currently operate on `*.onrender.com`.
- **Account Transferability Status:**
  - Render does not offer automated cross-account transfer of managed PostgreSQL databases.
  - Transferring a personal Render account to an external corporate buyer is not supported by standard PaaS workflows.
- **Primary Handover Path (Clean Blueprint Deployment in Buyer Account):**
  1. Buyer registers a new corporate Render account (`dashboard.render.com`) and adds a corporate payment method.
  2. Buyer connects their transferred GitHub repository (`BuyerOrg/project-orion`) to Render.
  3. Buyer navigates to **Blueprints -> New Blueprint Instance** and selects the connected repository.
  4. Render parses `render.yaml` and automatically provisions `orion-postgres`, `orion-redis`, `orion-api`, and `orion-dashboard`.
  5. Secret injection: Render auto-generates `ORION_JWT_SECRET_KEY` and links database/redis connection strings.
- **Alternative Path (Team Workspace Invitation):**
  - If the existing deployment is already in a Render Team workspace, the seller can invite the buyer as Team Owner, verify administrative elevation, and remove the seller account.
- **Validation After Transfer:**
  - `GET https://<buyer-api>.onrender.com/health/live` returns `HTTP 200 {"status":"alive"}`.
  - `GET https://<buyer-api>.onrender.com/health/ready` returns `HTTP 200` with healthy database and Redis status.
- **Rollback / Contingency:**
  - Seller leaves existing Render deployment active in staging mode until buyer validates independent production deployment.

---

### 3.3 Relational Database Store (PostgreSQL)

- **Current Repository Configuration:**
  - Database engine: PostgreSQL 15 via `asyncpg` driver.
  - Managed service identifier: `orion-postgres` (`basic-1gb` tier).
  - 15 linear migrations base to head `0015_onboarding_progress`.
- **Credential Handling:**
  - Injected via `ORION_DATABASE_URL` (dynamic binding in `render.yaml`).
  - Zero database passwords or IP hostnames exist in repository code.
- **Transfer & Data Migration Procedure:**
  1. **Logical Export (Pre-Transfer Dump):**
     Execute logical backup script on existing instance:
     ```bash
     bash backup/database-backup.sh
     ```
     Produces compressed logical SQL dump (`orion_backup_<TIMESTAMP>.sql.gz`).
  2. **Schema Provisioning:**
     Buyer's fresh database instance automatically executes Alembic migrations on initial deploy via `scripts/deploy/migrate.py` (`preDeployCommand` in `render.yaml`).
  3. **Data Restoration (If transferring seed/historical data):**
     Execute restore script into buyer's target database:
     ```bash
     bash backup/restore-database.sh orion_backup_<TIMESTAMP>.sql.gz
     ```
  4. **Post-Restore Integrity Check:**
     Verify Alembic current revision:
     ```bash
     poetry run alembic current
     ```
     Expected output: `0015_onboarding_progress (head)`.
- **Validation After Transfer:**
  - Verify table count (29 tables: 28 declarative models + alembic_version, as demonstrated in EPIC-027 Phase 6C) and foreign key constraints.
  - Test user authentication and onboarding status endpoints.

---

### 3.4 In-Memory Cache & Key-Value Store (Redis)

- **Current Repository Configuration:**
  - Service identifier: `orion-redis` (`free` tier).
  - In-memory data: Rate-limiting sliding windows, distributed lock tokens, quote cache.
- **Transfer Procedure:**
  - Redis contains strictly ephemeral runtime cache and non-persistent session data.
  - **No data migration is required.** Provisioning a clean Redis instance via `render.yaml` instantly initializes all required application state upon first startup.
- **Validation After Transfer:**
  - Check `/health/ready` response: `"redis": {"status": "healthy"}`.

---

### 3.5 Payment Gateway (Stripe)

- **Current Repository Configuration:**
  - **Platform Status:** Operates strictly in **Stripe Test Mode** (`libraries/infrastructure/billing/config.py`).
  - Safety Switch: Any attempt to supply live keys (`sk_live_...` or `pk_live_...`) raises a fatal `LiveCredentialsForbiddenError`.
  - Configured Price IDs: `price_test_pro_monthly`, `price_test_business_monthly`, `price_test_enterprise_monthly`.
- **Transferability Assessment:**
  - Stripe account transferability is not established in the repository; whether Stripe permits account assignment between distinct corporate entities requires external vendor and legal verification. To eliminate third-party transfer friction and establish KYC/AML compliance under buyer's corporate identity, the buyer should independently provision its own Stripe account in Test Mode.
- **Mandatory Buyer Handover Path:**
  1. Buyer registers their own corporate Stripe account (`dashboard.stripe.com`).
  2. Buyer enables Stripe Test Mode.
  3. Buyer creates Product and Recurring Prices matching Project ORION tiers (Pro, Business, Enterprise) or configures custom pricing.
  4. Buyer obtains new Test API keys (`sk_test_...`, `pk_test_...`) and webhook signing secret.
  5. Buyer injects keys into Render Environment Variables:
     - `ORION_STRIPE_SECRET_KEY`
     - `ORION_STRIPE_PUBLISHABLE_KEY`
     - `ORION_STRIPE_WEBHOOK_SECRET`
     - `ORION_STRIPE_PRICE_PRO`
     - `ORION_STRIPE_PRICE_BUSINESS`
     - `ORION_STRIPE_PRICE_ENTERPRISE`
  6. Buyer configures webhook endpoint in Stripe dashboard pointing to:
     `https://<buyer-api>.onrender.com/api/v1/billing/webhooks/stripe`
     with events: `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_succeeded`, `invoice.payment_failed`.
- **Validation After Transfer:**
  - Execute test checkout flow: `POST /api/v1/billing/checkout`.
  - Verify webhook HMAC signature verification in application logs.

---

### 3.6 Broker Sandbox Integration (OANDA Practice)

- **Current Repository Configuration:**
  - Connector: `libraries/infrastructure/execution/oanda_execution.py`.
  - Endpoint: `https://api-fxpractice.oanda.com` (OANDA v20 fxTrade practice API).
  - Production safety guard: Broker endpoint validator strictly rejects live trading URLs (`api-fxtrade.oanda.com`).
- **Credential Storage:**
  - Practice API keys and account IDs are never placed in repository environment files.
  - Sandbox credentials are created via REST API (`/api/v1/broker-sandbox/accounts`) and stored **AES-GCM encrypted at rest** in the `broker_sandbox_accounts` database table.
- **Transferability Assessment:**
  - OANDA practice accounts are free developer accounts. No financial value or live capital attaches to practice accounts. Account transfer is neither necessary nor supported.
- **Buyer Setup Action:**
  1. Buyer creates a free fxTrade practice account at `hub.oanda.com`.
  2. Buyer generates a personal practice API access token.
  3. Buyer registers the practice connector inside the Project ORION dashboard or via API:
     ```bash
     POST /api/v1/broker-sandbox/accounts
     {
       "provider": "oanda_practice",
       "account_id": "<BUYER_PRACTICE_ACCOUNT_ID>",
       "api_key": "<BUYER_PRACTICE_TOKEN>",
       "environment": "practice"
     }
     ```
- **Validation After Transfer:**
  - Execute connection check: `POST /api/v1/broker-sandbox/accounts/{id}/connect`.
  - Verify reconciliation snapshot: `POST /api/v1/broker-sandbox/accounts/{id}/reconcile`.

---

### 3.7 Market Data Provider (TwelveData)

- **Current Repository Configuration:**
  - Adapter: `libraries/infrastructure/market_data/` (`TwelveDataClient`).
  - Base URL: `https://api.twelvedata.com`.
  - Configuration: `ORION_MARKET_DATA_PROVIDER=twelvedata`, `ORION_MARKET_DATA_API_KEY`.
- **Transferability Assessment:**
  - TwelveData subscriptions are standard SaaS commercial agreements. Seller's subscription does not transfer with the software code.
- **Buyer Action:**
  1. Buyer registers an account at `twelvedata.com` and selects an appropriate plan tier based on quote frequency requirements.
  2. Buyer injects their new API key into Render environment variable: `ORION_MARKET_DATA_API_KEY`.
- **Validation After Transfer:**
  - `GET /api/v1/market-data/health` returns HTTP 200 with active provider status and latency telemetry.

---

### 3.8 Outbound Transactional Email (SMTP Relay)

- **Current Repository Configuration:**
  - Service: `libraries/infrastructure/communication/email_service.py`.
  - Configurable via `ORION_EMAIL_BACKEND=smtp` and `ORION_SMTP_*` variables.
- **Transferability Assessment:**
  - Transactional email delivery requires verified domain DNS records (SPF, DKIM, DMARC) tied to the sending domain. Buyer must provision their own email infrastructure.
- **Buyer Action:**
  1. Buyer provisions an account with a transactional email vendor (e.g., SendGrid, Mailgun, Amazon SES).
  2. Buyer verifies their corporate sending domain in the vendor console.
  3. Buyer configures Render environment variables:
     - `ORION_EMAIL_BACKEND=smtp`
     - `ORION_SMTP_HOST=<smtp.provider.net>`
     - `ORION_SMTP_PORT=587`
     - `ORION_SMTP_USERNAME=<API_KEY_OR_USER>`
     - `ORION_SMTP_PASSWORD=<API_SECRET>`
     - `ORION_SMTP_USE_TLS=true`
     - `ORION_SMTP_FROM_EMAIL=notifications@<buyer-domain>.com`
     - `ORION_SMTP_FROM_NAME="Project ORION"`
- **Validation After Transfer:**
  - Initiate registration verification email: `POST /api/v1/auth/resend-verification`.
  - Confirm delivery to inbox and anti-enumeration response (`HTTP 200`).

---

### 3.9 Offsite Backup Storage (AWS S3 / Cloudflare R2)

- **Current Repository Configuration:**
  - Storage target for encrypted database snapshots (`backup/database-backup.sh`).
- **Buyer Action:**
  1. Buyer provisions an S3 or Cloudflare R2 bucket (`orion-backups-<buyer>`).
  2. Buyer creates an IAM user / service token with strict bucket put/get permissions.
  3. Buyer configures the backup automation environment to replicate dumps to the private bucket.

---

## 4. Post-Transfer Security Credential Rotation Runbook

Immediately following the transfer of administrative control, the buyer must execute the following cryptographic rotation sequence:

```
[Step 1] Generate New 256-bit JWT Secret:
         openssl rand -hex 32
         Inject as ORION_JWT_SECRET_KEY in Render

[Step 2] Generate New Database Backup Encryption Key:
         openssl rand -hex 32
         Inject as BACKUP_ENCRYPTION_KEY in operational environment

[Step 3] Rotate Database Connection Password:
         Trigger password reset via Render or target PostgreSQL console
         Update ORION_DATABASE_URL

[Step 4] Update Stripe Test Mode Webhook Secret:
         Regenerate secret in Stripe dashboard
         Inject as ORION_STRIPE_WEBHOOK_SECRET

[Step 5] Replace Third-Party API Keys:
         Inject buyer TwelveData API key (ORION_MARKET_DATA_API_KEY)
         Inject buyer SMTP credentials (ORION_SMTP_PASSWORD)

[Step 6] Trigger Service Redeployment:
         Restart web services to clear in-memory caches and establish connections
```

---

## 5. Summary Checklist & Handover Verification Gate

- [ ] **GitHub Repository:** Ownership transferred to buyer organization or clean mirror pushed.
- [ ] **Render PaaS:** Clean blueprint deployment active in buyer account.
- [ ] **PostgreSQL Database:** Migrations executed up to `0015_onboarding_progress`; data restored.
- [ ] **Redis Cache:** Active and connected on private network.
- [ ] **Stripe Gateway:** Buyer test keys configured; webhook signature verified.
- [ ] **Broker Sandbox:** OANDA practice credentials encrypted and verified.
- [ ] **Market Data:** TwelveData API key configured and quote feed verified.
- [ ] **Transactional Email:** SMTP relay active; test verification email delivered.
- [ ] **Secrets Rotated:** All cryptographic keys regenerated independently by buyer.
