# Project ORION — Claim Control & Lexicon Matrix

**Document Reference:** `docs/acquisition/presentation/08-CLAIM-CONTROL-MATRIX.md`  
**Classification:** Confidential — Acquisition Technical Due Diligence  
**Repository Working Copy:** `project-orion/`  
**Git Baseline Commit:** `d5908d0a0cc2feff99fa02573adb12b8eea33782`  
**Governance Purpose:** Authoritative Lexicon and Statement Guidance for Buyer Presentations

---

## 1. Core Claim Control Matrix

This matrix establishes the mandatory phrasing and strictly prohibited language for all buyer-facing presentations, product briefs, and due diligence conversations:

| Feature / Metric | Source of Truth in Repository | Precision Classification | Mandatory Safe Buyer Wording | Strictly Prohibited Phrasing |
|---|---|---|---|---|
| **4,260 Tests** | [`docs/acquisition/EPIC-028-ACQUISITION-LAUNCH-AUDIT.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/EPIC-028-ACQUISITION-LAUNCH-AUDIT.md) | **Historical Documented Evidence** | *"Documented historical test baseline of 4,260 automated tests across 103 test suites."* | "Guaranteed 100% bug-free", "zero defect codebase", "4,260 tests currently passing" (unless freshly run). |
| **99.4% Coverage** | [`docs/acquisition/EPIC-028-ACQUISITION-LAUNCH-AUDIT.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/EPIC-028-ACQUISITION-LAUNCH-AUDIT.md) | **Historical Documented Evidence** | *"Documented historical test coverage of 99.4% across domain modules."* | "Complete universal test coverage", "flawlessly tested". |
| **~7.2s Restore** | `docs/EPIC-027-PHASE-6C-RESTORE-DEMONSTRATION.md` | **Historical Documented Evidence** | *"Demonstrated physical schema and data restoration benchmark of ~7 seconds across 29 tables in an isolated testing container."* | "Certified disaster recovery", "guaranteed 24-hour RPO", "enterprise recovery SLA". |
| **$100,000 Balance**| [`libraries/infrastructure/persistence/models/account.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/infrastructure/persistence/models/account.py) | **Current Verified Invariant** | *"Initial virtual paper trading balance provisioned at $100,000."* | "Real deposited cash balance", "custodial bank account balance". |
| **4 Concrete Strategies**| [`libraries/domain/strategy/registry.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/domain/strategy/registry.py) | **Current Verified Invariant** | *"4 concrete backtesting algorithmic strategy classes in StrategyRegistry."* | "9 fully implemented algorithmic execution engines". |
| **9 Strategy Profiles**| [`apps/trading-engine/src/routes/strategies.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/trading-engine/src/routes/strategies.py) | **Current Verified Invariant** | *"9 strategy parameter schemas defined in API catalogue specification."* | "9 running automated trading robots". |
| **7 RBAC Roles** | [`libraries/domain/organization/models.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/domain/organization/models.py) | **Current Verified Invariant** | *"7 distinct organization-level RBAC roles."* | "Institutional banking governance certification", "statutory compliance roles". |
| **41 Permissions** | [`libraries/domain/organization/permissions.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/domain/organization/permissions.py) | **Current Verified Invariant** | *"41 granular domain permissions across 14 functional domains."* | "Universal security guarantee". |
| **24 API Routers** | [`apps/trading-engine/src/main.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/trading-engine/src/main.py) | **Current Verified Invariant** | *"24 modular routers assembled in FastAPI application factory."* | "Microservice cluster". |
| **21 Domain Packages**| [`libraries/domain/`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/domain/) directory listing | **Current Verified Invariant** | *"21 internal domain packages in modular hexagonal architecture."* | "21 standalone external PyPI libraries". |
| **18 Dossiers** | [`docs/acquisition/`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/) directory listing | **Current Verified Invariant** | *"18 closing dossiers in technical due diligence data room."* | "Full legal transaction executed". |
| **~$14/mo Hosting** | [`render.yaml`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/render.yaml) | **Configuration Estimate** | *"Base cloud hosting configured on Render for approximately $14/month ($7 DB + $7 API)."* | "Runs reliably in all production workloads for $14", "guaranteed fixed hosting price". |
| **$0 Capital at Risk**| [`libraries/infrastructure/execution/paper_execution.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/infrastructure/execution/paper_execution.py) | **Current Verified Invariant** | *"The demonstrated execution path uses simulated paper capital only, with $0.00 live financial capital at risk."* | "Zero financial liability" (untenable legal warranty), "risk-free live trading". |
| **Mock Market Data**| [`libraries/infrastructure/market_data/mock_provider.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/infrastructure/market_data/mock_provider.py) | **Simulated / Invariant** | *"Deterministic synthetic market data generated offline by default."* | "Live institutional market quote stream", "real-time broker feeds". |
| **OANDA Practice** | [`libraries/infrastructure/execution/oanda_adapter.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/infrastructure/execution/oanda_adapter.py) | **External Sandbox** | *"External broker sandbox adapter supporting OANDA Practice environments."* | "Live real-money broker execution clearing". |
| **TwelveData Feed** | [`libraries/infrastructure/market_data/twelve_data.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/infrastructure/market_data/twelve_data.py) | **External Provider** | *"External market data provider adapter requiring buyer-provisioned API key."* | "Built-in active real-time data subscription". |
| **Trading Worker** | [`apps/trading-engine/src/workers/`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/trading-engine/src/workers/) | **Disabled by Design** | *"Autonomous worker coordinator implemented with manual trigger, disabled by default."* | "100% automated autonomous trading robot currently active in cloud". |
| **Subscription Pricing**| [`apps/dashboard/src/config/pricing.ts`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/dashboard/src/config/pricing.ts) | **Current Verified Invariant** | *"Implemented subscription tiers: Free Sandbox ($0), Pro ($99), Business ($299), Enterprise (Custom)."* | Legacy preliminary tiers ($49 / $149 / $399). |
| **Commercial Revenue**| Database and migration scan | **Not Established** | *"Commercial revenue, paying customers, and active subscribers are NOT ESTABLISHED IN REPOSITORY."* | Any invented ARR, MRR, customer counts, or valuation metrics. |

---

## 2. Universal Statement Rules

1. **Avoid Unqualified Absolutes:**  
   Never use "100% ready", "flawless", "guaranteed", "zero defects", or "certified" unless referencing a specific historical benchmark explicitly qualified in the text.
2. **Preserve Simulation Truth:**  
   Always maintain the distinction between internal simulation (`PaperExecutionAdapter`, `MockMarketDataProvider`) and external integrations (`TwelveDataMarketDataProvider`, `OandaBrokerAdapter`).
3. **No Financial Guarantees:**  
   Past simulated performance from backtesting, optimization, or quality gates must never be represented as an indicator or guarantee of future live market profitability.
4. **Clean Transaction Boundaries:**  
   Always describe the transaction as a proposed software and intellectual property transfer, subject to mutually executed transaction agreements.
