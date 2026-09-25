# Project ORION — Buyer Visual Presentation & Due Diligence Package

**Document Reference:** `docs/acquisition/presentation/visual/README.md`  
**Classification:** Confidential — Acquisition Technical Due Diligence  
**Repository Working Copy:** `project-orion/`  
**Git Baseline Commit:** `d5908d0a0cc2feff99fa02573adb12b8eea33782`  
**Operational Mandate:** STRICT PAPER TRADING ONLY — Exactly $0.00 Live Financial Capital at Risk  

---

## 1. Package Overview

This package contains the visual presentation assets, slide decks, standalone vector diagrams, HTML print templates, and compiled due diligence PDFs for **Project ORION** (Quantitative FX Research & Paper-Trading SaaS). All visual materials enforce the authoritative claims, subscription tiers, and architectural classifications established in EPIC-029 Phase 0.5.

```
docs/acquisition/presentation/visual/
├── README.md
├── scripts/
│   ├── generate_diagrams.py        # Generates the 5 standalone SVG vector diagrams
│   ├── build_pptx.py               # Generates the 15-slide 16:9 widescreen PPTX with notes
│   └── build_pdf.py                # Compiles the 7 HTML templates into publication PDFs
├── templates/                      # Self-contained HTML print templates (dark theme #090D16)
│   ├── executive-one-pager.html    # Executive product brief & SaaS subscription model
│   ├── architecture-sheet.html     # Hexagonal architecture & component status classification
│   ├── acquisition-ip-scope.html   # Proposed Transferable Software/IP Scope vs. buyer obligations
│   ├── buyer-faq.html              # 26 technical & commercial due diligence Q&As
│   ├── demo-runbook.html           # 8-minute demonstration script & failure protocols
│   ├── data-room-guide.html        # 4-tier navigation model across 18 due diligence dossiers
│   └── claim-control-matrix.html   # Master claim matrix & universal statement governance
├── svg/                            # Standalone vector SVG diagrams (1200px width)
│   ├── architecture-hexagonal-map.svg
│   ├── workflow-5-stage-pipeline.svg
│   ├── order-execution-sequence.svg
│   ├── deployment-state-machine.svg
│   └── data-room-4tier-pyramid.svg
├── pptx/
│   └── Project-ORION-Buyer-Presentation.pptx   # 15 widescreen slides with full speaker notes
└── pdf/                            # High-resolution compiled A4 PDF documents
    ├── Project-ORION-Executive-Brief.pdf
    ├── Project-ORION-Technical-Architecture.pdf
    ├── Project-ORION-Acquisition-IP-Scope.pdf
    ├── Project-ORION-Buyer-FAQ.pdf
    ├── Project-ORION-Demo-Operator-Sheet.pdf
    ├── Project-ORION-Data-Room-Guide.pdf
    └── Project-ORION-Claim-Control-Matrix.pdf
```

---

## 2. Reproduction & Build Commands

All generation scripts are deterministic, require zero external network dependencies, and use pre-installed system tools:

```bash
# 1. Regenerate Standalone Vector SVGs
python docs/acquisition/presentation/visual/scripts/generate_diagrams.py

# 2. Build 15-Slide Presentation Deck with Embedded Speaker Notes
python docs/acquisition/presentation/visual/scripts/build_pptx.py

# 3. Compile HTML Templates to High-Resolution A4 PDFs (via Playwright / Edge)
python docs/acquisition/presentation/visual/scripts/build_pdf.py
```

---

## 3. Visual Asset Inventory

### Slide Presentation Deck (`pptx/`)
* **File:** `Project-ORION-Buyer-Presentation.pptx`
* **Format:** 16:9 Widescreen (13.333" x 7.5"), 15 Slides
* **Theme:** Deep Brand Dark (`#090D16`), Card Containers (`#141E33`), Borders (`#1E293B`), Accents (`#0284C7` / `#38BDF8`)
* **Speaker Notes:** Embedded on all 15 slides matching `docs/acquisition/presentation/01-BUYER-PRESENTATION.md` verbatim.
* **Slides Covered:**
  1. Title & Executive Identity
  2. What the Software Is (4-tier SaaS model)
  3. Product Workflow (5-stage quantitative pipeline)
  4. Architecture Overview (Hexagonal modular decoupling)
  5. Quantitative Research Engine (4 concrete registry classes vs 9 API profiles, Decimal math)
  6. Backtesting & Temporal Leakage Controls (`LeakageGuard` monotonicity)
  7. Optimization & Walk-Forward Analysis (`WFE` scoring)
  8. Strategy Deployment Lifecycle (Fail-closed state machine & quality gates)
  9. Paper Trading & Risk Management (`PaperExecutionAdapter`, $0.00 capital risk)
  10. Market Data & Broker Adapter Architecture (`MockMarketDataProvider`, TwelveData, OANDA Practice, Worker disabled)
  11. Multi-Tenancy & Organization-Level RBAC (`TenantContext`, 7 roles, 41 permissions)
  12. Security, Auditability & Operations (JWT, bcrypt, security headers, `AuditLogModel`, health probes)
  13. Deployment, Backup & Recovery (`render.yaml`, ~$14/mo hosting config, ~7.2s DR restore benchmark)
  14. Technical Asset / IP Inventory (4,260 tests, 99.4% coverage, 29 tables, 15 migrations, 18 dossiers)
  15. Acquisition Scope, Handover & Known Limitations (Proposed transferable software/IP scope, buyer accounts, pre-revenue status)

### Standalone Vector SVGs (`svg/`)
1. **`architecture-hexagonal-map.svg`**: Hexagonal component layout across 5 layers with explicit status badges (`[INTERNAL]`, `[SIMULATED]`, `[EXTERNAL]`, `[OPTIONAL]`, `[DISABLED]`).
2. **`workflow-5-stage-pipeline.svg`**: Horizontal chevron pipeline from Specification through Deterministic Backtest, Optimization/WFA, and Quality Gates to Paper Incubation ($0.00 Live Risk).
3. **`order-execution-sequence.svg`**: 7-step sequence flow showing pre-trade risk checks, paper matching, persistence, and audit logging.
4. **`deployment-state-machine.svg`**: State transitions (`PENDING_GATES` to `PROMOTION_CANDIDATE`) highlighting automated quality gate hurdles and fail-closed rejection.
5. **`data-room-4tier-pyramid.svg`**: 4-tier due diligence hierarchy structuring dossiers 01 through 18.

### Publication PDF Documents (`pdf/`)
1. **`Project-ORION-Executive-Brief.pdf`**: 1-page executive summary covering product identification, capabilities, tech stack, and SaaS tiers.
2. **`Project-ORION-Technical-Architecture.pdf`**: Component status classification table, interface sequence flows, and architectural boundaries.
3. **`Project-ORION-Acquisition-IP-Scope.pdf`**: Proposed transferable software & IP deliverables vs. buyer-provisioned obligations and transition protocol.
4. **`Project-ORION-Buyer-FAQ.pdf`**: 26 structured technical and commercial due diligence questions & answers.
5. **`Project-ORION-Demo-Operator-Sheet.pdf`**: Demo preflight timeline (T-24h to T-5m), 8-minute demonstration script, and real-time failure protocols.
6. **`Project-ORION-Data-Room-Guide.pdf`**: 4-tier due diligence navigation model across all 18 dossiers.
7. **`Project-ORION-Claim-Control-Matrix.pdf`**: Master claim matrix (18 metrics), evidence classifications, and universal statement rules.

---

## 4. Authoritative Claim Invariants Enforced

All visual assets in this package adhere to the following verified repository invariants:

1. **Commercial SaaS Pricing:** Implemented strictly as Free Sandbox ($0/mo), Pro Trader ($99/mo), Business Prop ($299/mo), and Enterprise (Custom Contract). Legacy preliminary $49/$149/$399 figures are prohibited.
2. **Commercial Revenue Status:** Commercial revenue, ARR, MRR, customer counts, and subscribers are **NOT ESTABLISHED IN REPOSITORY** (clean pre-revenue technology asset sale). Stripe operates in Test Mode.
3. **Capital Risk Model:** Capital at risk is exactly **$0.00**. Orders are stamped `is_paper=True`.
4. **Autonomous Worker:** Implemented in source code with manual execution trigger (`/api/v1/worker/run-once`), but background loop is disabled by default in cloud deployments (`WORKER_ENABLED=false`).
5. **Historical Benchmarks:** Documented historical baseline of 4,260 automated tests, 99.4% coverage, and ~7.2s database restore benchmark across 29 tables are explicitly labeled as historical evidence.
6. **Hosting Cost:** Cloud hosting on Render is described as an approximately $14/month configuration estimate ($7 DB + $7 API under published 2026 pricing).
7. **Structural Invariants:** Exactly 4 concrete backtesting classes in `StrategyRegistry`, 9 API catalogue archetype profiles, 7 RBAC roles, 41 permissions, 24 FastAPI routers, 21 domain packages, 15 Alembic migrations, 29 tables, and 18 closing dossiers.
