#!/usr/bin/env python3
"""
generate_diagrams.py — Project ORION Buyer Visual Diagrams Generator
EPIC-029 Phase 0.6: Buyer Visual Presentation Package

Generates 5 standalone, presentation-ready vector SVG diagrams:
1. architecture-hexagonal-map.svg
2. workflow-5-stage-pipeline.svg
3. order-execution-sequence.svg
4. deployment-state-machine.svg
5. data-room-4tier-pyramid.svg

Color tokens adhere strictly to apps/dashboard/src/index.css:
- Background: #090D16 / #0F172A
- Card: #141E33
- Border: #1E293B / #334155
- Accent: #0284C7 / #38BDF8
- Status: #10B981 (Success), #F59E0B (Warning), #F43F5E (Loss/Destructive)
- Badge: #FBBF24 (Paper Mode)
"""

from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "svg"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------
# 1. architecture-hexagonal-map.svg
# ----------------------------------------------------------------------
def generate_architecture_map() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 860" width="1200" height="860">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#090D16" />
      <stop offset="100%" stop-color="#0F172A" />
    </linearGradient>
    <linearGradient id="cardGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#141E33" />
      <stop offset="100%" stop-color="#0E1626" />
    </linearGradient>
    <filter id="cardShadow" x="-5%" y="-5%" width="110%" height="110%">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000000" flood-opacity="0.4" />
    </filter>
  </defs>

  <!-- Background -->
  <rect width="1200" height="860" fill="url(#bgGrad)" />

  <!-- Header -->
  <text x="60" y="50" font-family="Inter, -apple-system, sans-serif" font-size="24" font-weight="700" fill="#F8FAFC">Project ORION — Hexagonal Architecture &amp; Component Map</text>
  <text x="60" y="78" font-family="Inter, -apple-system, sans-serif" font-size="13" font-weight="400" fill="#94A3B8">Strict Layer Separation: Presentation, API Delivery, Application Services, 21 Domain Packages, Infrastructure Adapters</text>

  <!-- LAYER 1: PRESENTATION LAYER -->
  <g transform="translate(60, 110)">
    <rect width="1080" height="90" rx="8" fill="url(#cardGrad)" stroke="#1E293B" stroke-width="1.5" filter="url(#cardShadow)" />
    <rect x="2" y="2" width="1076" height="4" rx="2" fill="#0284C7" />
    <text x="24" y="32" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="700" fill="#38BDF8" letter-spacing="1">1. PRESENTATION LAYER — REACT SINGLE-PAGE APPLICATION</text>
    <rect x="980" y="18" width="76" height="20" rx="4" fill="#0284C7" fill-opacity="0.2" stroke="#0284C7" stroke-width="1" />
    <text x="1018" y="32" font-family="Inter, -apple-system, sans-serif" font-size="10" font-weight="600" fill="#38BDF8" text-anchor="middle">INTERNAL</text>
    
    <text x="24" y="58" font-family="Inter, -apple-system, sans-serif" font-size="14" font-weight="600" fill="#F8FAFC">React 18 + Vite SPA (TypeScript, Tailwind CSS, TanStack Query, Lucide Icons)</text>
    <text x="24" y="76" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="400" fill="#94A3B8">20 Routes: Marketing, Auth, Trading Terminal, Research Lab, Optimization Studio, Strategy Deployments, Org Admin</text>
  </g>

  <!-- Arrow 1 -> 2 -->
  <path d="M 600 200 L 600 225" stroke="#38BDF8" stroke-width="2" stroke-dasharray="4,4" />
  <polygon points="596,225 604,225 600,233" fill="#38BDF8" />
  <text x="615" y="220" font-family="JetBrains Mono, Consolas, monospace" font-size="11" fill="#64748B">HTTPS / JSON REST</text>

  <!-- LAYER 2: API & DELIVERY LAYER -->
  <g transform="translate(60, 235)">
    <rect width="1080" height="95" rx="8" fill="url(#cardGrad)" stroke="#1E293B" stroke-width="1.5" filter="url(#cardShadow)" />
    <rect x="2" y="2" width="1076" height="4" rx="2" fill="#0284C7" />
    <text x="24" y="30" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="700" fill="#38BDF8" letter-spacing="1">2. API &amp; DELIVERY LAYER — FASTAPI ASGI APPLICATION FACTORY</text>
    <rect x="980" y="16" width="76" height="20" rx="4" fill="#0284C7" fill-opacity="0.2" stroke="#0284C7" stroke-width="1" />
    <text x="1018" y="30" font-family="Inter, -apple-system, sans-serif" font-size="10" font-weight="600" fill="#38BDF8" text-anchor="middle">INTERNAL</text>
    
    <text x="24" y="56" font-family="Inter, -apple-system, sans-serif" font-size="14" font-weight="600" fill="#F8FAFC">24 Modular Routers (FastAPI, Python 3.11+, Pydantic v2 Schemas)</text>
    <text x="24" y="76" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="400" fill="#94A3B8">Security Headers (HSTS, CSP, X-Frame DENY) │ Request Correlation Tracing │ Dependency Injection (TenantContext, QuotaGuards)</text>
  </g>

  <!-- Arrow 2 -> 3 -->
  <path d="M 600 330 L 600 355" stroke="#38BDF8" stroke-width="2" stroke-dasharray="4,4" />
  <polygon points="596,355 604,355 600,363" fill="#38BDF8" />
  <text x="615" y="350" font-family="JetBrains Mono, Consolas, monospace" font-size="11" fill="#64748B">Application Dispatch</text>

  <!-- LAYER 3: APPLICATION SERVICES LAYER -->
  <g transform="translate(60, 365)">
    <rect width="1080" height="95" rx="8" fill="url(#cardGrad)" stroke="#1E293B" stroke-width="1.5" filter="url(#cardShadow)" />
    <rect x="2" y="2" width="1076" height="4" rx="2" fill="#0284C7" />
    <text x="24" y="30" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="700" fill="#38BDF8" letter-spacing="1">3. APPLICATION SERVICES LAYER — ORCHESTRATION &amp; WORKFLOWS</text>
    <rect x="980" y="16" width="76" height="20" rx="4" fill="#0284C7" fill-opacity="0.2" stroke="#0284C7" stroke-width="1" />
    <text x="1018" y="30" font-family="Inter, -apple-system, sans-serif" font-size="10" font-weight="600" fill="#38BDF8" text-anchor="middle">INTERNAL</text>
    
    <text x="24" y="56" font-family="Inter, -apple-system, sans-serif" font-size="14" font-weight="600" fill="#F8FAFC">OrderService │ ResearchService │ OptimizationService │ DeploymentPipelineService</text>
    <text x="24" y="76" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="400" fill="#94A3B8">EntitlementService (4-Tier Quotas) │ SubscriptionService (Stripe Test Mode) │ AuditService (Immutable Logs)</text>
  </g>

  <!-- Arrow 3 -> 4 -->
  <path d="M 600 460 L 600 485" stroke="#38BDF8" stroke-width="2" stroke-dasharray="4,4" />
  <polygon points="596,485 604,485 600,493" fill="#38BDF8" />
  <text x="615" y="480" font-family="JetBrains Mono, Consolas, monospace" font-size="11" fill="#64748B">Pure Domain Logic (Zero DB/Web Imports)</text>

  <!-- LAYER 4: DOMAIN LOGIC LAYER -->
  <g transform="translate(60, 495)">
    <rect width="1080" height="115" rx="8" fill="url(#cardGrad)" stroke="#1E293B" stroke-width="1.5" filter="url(#cardShadow)" />
    <rect x="2" y="2" width="1076" height="4" rx="2" fill="#10B981" />
    <text x="24" y="28" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="700" fill="#10B981" letter-spacing="1">4. DOMAIN LOGIC LAYER — 21 PURE INTERNAL PACKAGES (libraries/domain/)</text>
    <rect x="980" y="14" width="76" height="20" rx="4" fill="#10B981" fill-opacity="0.2" stroke="#10B981" stroke-width="1" />
    <text x="1018" y="28" font-family="Inter, -apple-system, sans-serif" font-size="10" font-weight="600" fill="#10B981" text-anchor="middle">INTERNAL</text>
    
    <g transform="translate(24, 45)">
      <text x="0" y="14" font-family="Inter, -apple-system, sans-serif" font-size="13" font-weight="600" fill="#F8FAFC">strategy: <tspan font-weight="400" fill="#94A3B8">StrategyRegistry (4 concrete classes, 9 API profiles)</tspan></text>
      <text x="540" y="14" font-family="Inter, -apple-system, sans-serif" font-size="13" font-weight="600" fill="#F8FAFC">research: <tspan font-weight="400" fill="#94A3B8">DeterministicBacktestEngine, LeakageGuard</tspan></text>
      
      <text x="0" y="36" font-family="Inter, -apple-system, sans-serif" font-size="13" font-weight="600" fill="#F8FAFC">optimization: <tspan font-weight="400" fill="#94A3B8">OptimizationEngine, WalkForwardEngine (WFE)</tspan></text>
      <text x="540" y="36" font-family="Inter, -apple-system, sans-serif" font-size="13" font-weight="600" fill="#F8FAFC">deployment: <tspan font-weight="400" fill="#94A3B8">DeploymentLifecycle, QualityGates (WFE ≥ 0.50, DD ≤ 15%)</tspan></text>
      
      <text x="0" y="58" font-family="Inter, -apple-system, sans-serif" font-size="13" font-weight="600" fill="#F8FAFC">risk &amp; org: <tspan font-weight="400" fill="#94A3B8">RiskEngine (pre-trade leverage/margin), 7 RBAC Roles, 41 Permissions, Decimal Math</tspan></text>
    </g>
  </g>

  <!-- Arrow 4 -> 5 -->
  <path d="M 600 610 L 600 635" stroke="#38BDF8" stroke-width="2" stroke-dasharray="4,4" />
  <polygon points="596,635 604,635 600,643" fill="#38BDF8" />
  <text x="615" y="630" font-family="JetBrains Mono, Consolas, monospace" font-size="11" fill="#64748B">Ports &amp; Adapters</text>

  <!-- LAYER 5: INFRASTRUCTURE & ADAPTER LAYER -->
  <g transform="translate(60, 645)">
    <rect width="1080" height="175" rx="8" fill="url(#cardGrad)" stroke="#1E293B" stroke-width="1.5" filter="url(#cardShadow)" />
    <rect x="2" y="2" width="1076" height="4" rx="2" fill="#F59E0B" />
    <text x="24" y="26" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="700" fill="#F59E0B" letter-spacing="1">5. INFRASTRUCTURE &amp; ADAPTER LAYER — HARDWARE, PERSISTENCE &amp; ADAPTERS</text>

    <!-- Adapter Cards Grid -->
    <!-- Col 1: DB & Redis -->
    <g transform="translate(24, 40)">
      <rect width="320" height="52" rx="6" fill="#090D16" stroke="#1E293B" stroke-width="1" />
      <text x="14" y="22" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">PostgreSQL 16 (SQLAlchemy Async)</text>
      <text x="14" y="40" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8">29 tables, 15 migrations, TenantContext</text>
      <rect x="238" y="10" width="70" height="18" rx="3" fill="#0284C7" fill-opacity="0.2" stroke="#0284C7" stroke-width="1" />
      <text x="273" y="23" font-family="Inter, -apple-system, sans-serif" font-size="9" font-weight="600" fill="#38BDF8" text-anchor="middle">INTERNAL</text>
    </g>

    <g transform="translate(24, 102)">
      <rect width="320" height="52" rx="6" fill="#090D16" stroke="#1E293B" stroke-width="1" />
      <text x="14" y="22" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">Redis 7 (Session &amp; Rate Limit)</text>
      <text x="14" y="40" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8">In-memory degraded fallback active</text>
      <rect x="238" y="10" width="70" height="18" rx="3" fill="#64748B" fill-opacity="0.2" stroke="#64748B" stroke-width="1" />
      <text x="273" y="23" font-family="Inter, -apple-system, sans-serif" font-size="9" font-weight="600" fill="#94A3B8" text-anchor="middle">OPTIONAL</text>
    </g>

    <!-- Col 2: Execution & Mock Data -->
    <g transform="translate(370, 40)">
      <rect width="330" height="52" rx="6" fill="#090D16" stroke="#FBBF24" stroke-width="1" stroke-opacity="0.4" />
      <text x="14" y="22" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">PaperExecutionAdapter</text>
      <text x="14" y="40" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#FBBF24">Spread, slippage, netting ($0.00 capital)</text>
      <rect x="240" y="10" width="76" height="18" rx="3" fill="#FBBF24" fill-opacity="0.2" stroke="#FBBF24" stroke-width="1" />
      <text x="278" y="23" font-family="Inter, -apple-system, sans-serif" font-size="9" font-weight="600" fill="#FBBF24" text-anchor="middle">SIMULATED</text>
    </g>

    <g transform="translate(370, 102)">
      <rect width="330" height="52" rx="6" fill="#090D16" stroke="#FBBF24" stroke-width="1" stroke-opacity="0.4" />
      <text x="14" y="22" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">MockMarketDataProvider</text>
      <text x="14" y="40" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8">Deterministic synthetic candle generator</text>
      <rect x="240" y="10" width="76" height="18" rx="3" fill="#FBBF24" fill-opacity="0.2" stroke="#FBBF24" stroke-width="1" />
      <text x="278" y="23" font-family="Inter, -apple-system, sans-serif" font-size="9" font-weight="600" fill="#FBBF24" text-anchor="middle">SIMULATED</text>
    </g>

    <!-- Col 3: External & Worker -->
    <g transform="translate(726, 40)">
      <rect width="330" height="52" rx="6" fill="#090D16" stroke="#1E293B" stroke-width="1" />
      <text x="14" y="22" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">TwelveData &amp; OANDA Practice</text>
      <text x="14" y="40" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8">Live quotes / practice sandbox adapters</text>
      <rect x="240" y="10" width="76" height="18" rx="3" fill="#64748B" fill-opacity="0.2" stroke="#64748B" stroke-width="1" />
      <text x="278" y="23" font-family="Inter, -apple-system, sans-serif" font-size="9" font-weight="600" fill="#38BDF8" text-anchor="middle">EXTERNAL</text>
    </g>

    <g transform="translate(726, 102)">
      <rect width="330" height="52" rx="6" fill="#090D16" stroke="#F43F5E" stroke-width="1" stroke-opacity="0.4" />
      <text x="14" y="22" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">AutonomousWorkerCoordinator</text>
      <text x="14" y="40" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#F43F5E">Loop disabled by design (WORKER_ENABLED=false)</text>
      <rect x="240" y="10" width="76" height="18" rx="3" fill="#F43F5E" fill-opacity="0.2" stroke="#F43F5E" stroke-width="1" />
      <text x="278" y="23" font-family="Inter, -apple-system, sans-serif" font-size="9" font-weight="600" fill="#F43F5E" text-anchor="middle">DISABLED</text>
    </g>
  </g>
</svg>"""

# ----------------------------------------------------------------------
# 2. workflow-5-stage-pipeline.svg
# ----------------------------------------------------------------------
def generate_workflow_pipeline() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 520" width="1200" height="520">
  <defs>
    <linearGradient id="bgGrad2" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#090D16" />
      <stop offset="100%" stop-color="#0F172A" />
    </linearGradient>
    <linearGradient id="chevronGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#141E33" />
      <stop offset="100%" stop-color="#1A2744" />
    </linearGradient>
  </defs>

  <!-- Background -->
  <rect width="1200" height="520" fill="url(#bgGrad2)" />

  <!-- Title -->
  <text x="60" y="50" font-family="Inter, -apple-system, sans-serif" font-size="24" font-weight="700" fill="#F8FAFC">Project ORION — 5-Stage Quantitative Research &amp; Incubation Pipeline</text>
  <text x="60" y="78" font-family="Inter, -apple-system, sans-serif" font-size="13" font-weight="400" fill="#94A3B8">Mathematical Strategy Formulation to Simulated Paper Incubation ($0.00 Live Financial Capital at Risk)</text>

  <!-- CHEVRON 1: SPECIFICATION -->
  <g transform="translate(60, 120)">
    <rect width="200" height="240" rx="8" fill="url(#chevronGrad)" stroke="#1E293B" stroke-width="1.5" />
    <circle cx="36" cy="36" r="16" fill="#0284C7" />
    <text x="36" y="42" font-family="Inter, -apple-system, sans-serif" font-size="14" font-weight="700" fill="#F8FAFC" text-anchor="middle">1</text>
    <text x="62" y="42" font-family="Inter, -apple-system, sans-serif" font-size="14" font-weight="700" fill="#38BDF8">SPECIFICATION</text>
    
    <text x="20" y="80" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">Strategy Formulation</text>
    <text x="20" y="104" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8">• 4 concrete classes in StrategyRegistry</text>
    <text x="20" y="128" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8">• 9 API catalogue archetype schemas</text>
    <text x="20" y="152" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8">• Typed parameter bounds</text>
    <text x="20" y="176" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8">• Arbitrary-precision Decimal arithmetic</text>
    
    <rect x="20" y="198" width="160" height="26" rx="4" fill="#090D16" stroke="#334155" stroke-width="1" />
    <text x="100" y="215" font-family="JetBrains Mono, Consolas, monospace" font-size="10" fill="#38BDF8" text-anchor="middle">POST /experiments</text>
  </g>

  <!-- Arrow 1 -> 2 -->
  <path d="M 265 240 L 285 240" stroke="#38BDF8" stroke-width="2" />
  <polygon points="285,236 293,240 285,244" fill="#38BDF8" />

  <!-- CHEVRON 2: DETERMINISTIC BACKTESTING -->
  <g transform="translate(295, 120)">
    <rect width="200" height="240" rx="8" fill="url(#chevronGrad)" stroke="#1E293B" stroke-width="1.5" />
    <circle cx="36" cy="36" r="16" fill="#0284C7" />
    <text x="36" y="42" font-family="Inter, -apple-system, sans-serif" font-size="14" font-weight="700" fill="#F8FAFC" text-anchor="middle">2</text>
    <text x="62" y="42" font-family="Inter, -apple-system, sans-serif" font-size="14" font-weight="700" fill="#38BDF8">BACKTESTING</text>
    
    <text x="20" y="80" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">Chronological Replay</text>
    <text x="20" y="104" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8">• DeterministicBacktestEngine bar traversal</text>
    <text x="20" y="128" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#10B981">• LeakageGuard look-ahead prevention</text>
    <text x="20" y="152" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8">• Sharpe, Sortino, Max DD &amp; Profit Factor</text>
    <text x="20" y="176" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8">• Identical cent-level reproducibility</text>
    
    <rect x="20" y="198" width="160" height="26" rx="4" fill="#090D16" stroke="#334155" stroke-width="1" />
    <text x="100" y="215" font-family="JetBrains Mono, Consolas, monospace" font-size="10" fill="#10B981" text-anchor="middle">LeakageGuard Monotonic</text>
  </g>

  <!-- Arrow 2 -> 3 -->
  <path d="M 500 240 L 520 240" stroke="#38BDF8" stroke-width="2" />
  <polygon points="520,236 528,240 520,244" fill="#38BDF8" />

  <!-- CHEVRON 3: OPTIMIZATION & WFA -->
  <g transform="translate(530, 120)">
    <rect width="200" height="240" rx="8" fill="url(#chevronGrad)" stroke="#1E293B" stroke-width="1.5" />
    <circle cx="36" cy="36" r="16" fill="#0284C7" />
    <text x="36" y="42" font-family="Inter, -apple-system, sans-serif" font-size="14" font-weight="700" fill="#F8FAFC" text-anchor="middle">3</text>
    <text x="62" y="42" font-family="Inter, -apple-system, sans-serif" font-size="14" font-weight="700" fill="#38BDF8">OPTIMIZATION</text>
    
    <text x="20" y="80" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">Walk-Forward Analysis</text>
    <text x="20" y="104" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8">• Parameter space grid exploration</text>
    <text x="20" y="128" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8">• Rolling In-Sample &amp; Out-Of-Sample</text>
    <text x="20" y="152" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8">• Walk-Forward Efficiency (WFE)</text>
    <text x="20" y="176" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8">• Curve-fitting detection</text>
    
    <rect x="20" y="198" width="160" height="26" rx="4" fill="#090D16" stroke="#334155" stroke-width="1" />
    <text x="100" y="215" font-family="JetBrains Mono, Consolas, monospace" font-size="10" fill="#38BDF8" text-anchor="middle">POST /walk-forward</text>
  </g>

  <!-- Arrow 3 -> 4 -->
  <path d="M 735 240 L 755 240" stroke="#38BDF8" stroke-width="2" />
  <polygon points="755,236 763,240 755,244" fill="#38BDF8" />

  <!-- CHEVRON 4: QUALITY GATES -->
  <g transform="translate(765, 120)">
    <rect width="200" height="240" rx="8" fill="url(#chevronGrad)" stroke="#10B981" stroke-width="1.5" />
    <circle cx="36" cy="36" r="16" fill="#10B981" />
    <text x="36" y="42" font-family="Inter, -apple-system, sans-serif" font-size="14" font-weight="700" fill="#F8FAFC" text-anchor="middle">4</text>
    <text x="62" y="42" font-family="Inter, -apple-system, sans-serif" font-size="14" font-weight="700" fill="#10B981">QUALITY GATES</text>
    
    <text x="20" y="80" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">Automated Hurdles</text>
    <text x="20" y="104" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#10B981">✓ WFE Threshold ≥ 0.50</text>
    <text x="20" y="128" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#10B981">✓ Max Permissible DD ≤ 15%</text>
    <text x="20" y="152" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#10B981">✓ Parameter Surface Stability</text>
    <text x="20" y="176" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8">• Fail-closed rejection</text>
    
    <rect x="20" y="198" width="160" height="26" rx="4" fill="#090D16" stroke="#10B981" stroke-width="1" />
    <text x="100" y="215" font-family="JetBrains Mono, Consolas, monospace" font-size="10" fill="#10B981" text-anchor="middle">GATES_PASSED</text>
  </g>

  <!-- Arrow 4 -> 5 -->
  <path d="M 970 240 L 990 240" stroke="#10B981" stroke-width="2" />
  <polygon points="990,236 998,240 990,244" fill="#10B981" />

  <!-- CHEVRON 5: PAPER INCUBATION -->
  <g transform="translate(1000, 120)">
    <rect width="140" height="240" rx="8" fill="url(#chevronGrad)" stroke="#FBBF24" stroke-width="1.5" />
    <circle cx="36" cy="36" r="16" fill="#FBBF24" />
    <text x="36" y="42" font-family="Inter, -apple-system, sans-serif" font-size="14" font-weight="700" fill="#090D16" text-anchor="middle">5</text>
    <text x="60" y="42" font-family="Inter, -apple-system, sans-serif" font-size="13" font-weight="700" fill="#FBBF24">INCUBATION</text>
    
    <text x="16" y="80" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">Simulated Only</text>
    <text x="16" y="104" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8">• Paper adapter</text>
    <text x="16" y="128" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8">• Spread/slippage</text>
    <text x="16" y="152" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8">• Netting &amp; MTM</text>
    <text x="16" y="176" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#FBBF24">• $0.00 Live Risk</text>
    
    <rect x="16" y="198" width="108" height="26" rx="4" fill="#090D16" stroke="#FBBF24" stroke-width="1" />
    <text x="70" y="215" font-family="JetBrains Mono, Consolas, monospace" font-size="9" fill="#FBBF24" text-anchor="middle">TERMINAL</text>
  </g>

  <!-- Bottom Banner: Paper Safety Invariant -->
  <g transform="translate(60, 400)">
    <rect width="1080" height="70" rx="8" fill="#141E33" stroke="#FBBF24" stroke-width="1.5" />
    <rect x="24" y="20" width="180" height="30" rx="4" fill="#FBBF24" fill-opacity="0.15" stroke="#FBBF24" stroke-width="1" />
    <text x="114" y="40" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="700" fill="#FBBF24" text-anchor="middle">STRICT SAFETY INVARIANT</text>
    
    <text x="225" y="32" font-family="Inter, -apple-system, sans-serif" font-size="13" font-weight="600" fill="#F8FAFC">Pipeline strictly terminates at Paper Validated or Promotion Candidate status.</text>
    <text x="225" y="52" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="400" fill="#94A3B8">Live real-money brokerage execution is absent from the software. Exactly $0.00 live financial capital is exposed at any stage.</text>
  </g>
</svg>"""

# ----------------------------------------------------------------------
# 3. order-execution-sequence.svg
# ----------------------------------------------------------------------
def generate_order_sequence() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 680" width="1200" height="680">
  <defs>
    <linearGradient id="bgGrad3" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#090D16" />
      <stop offset="100%" stop-color="#0F172A" />
    </linearGradient>
  </defs>

  <rect width="1200" height="680" fill="url(#bgGrad3)" />

  <!-- Title -->
  <text x="60" y="45" font-family="Inter, -apple-system, sans-serif" font-size="22" font-weight="700" fill="#F8FAFC">Project ORION — Paper Order Execution Sequence &amp; Safety Checks</text>
  <text x="60" y="70" font-family="Inter, -apple-system, sans-serif" font-size="13" font-weight="400" fill="#94A3B8">Synchronous Pre-Trade Risk Evaluation, Simulated Execution &amp; Immutable Audit Trail ($0.00 Live Risk)</text>

  <!-- Lifeline Columns -->
  <!-- 1. Trader / Client (x=120) -->
  <!-- 2. FastAPI Router (x=280) -->
  <!-- 3. OrderService (x=450) -->
  <!-- 4. EntitlementService (x=620) -->
  <!-- 5. RiskService (x=790) -->
  <!-- 6. PaperExecutionAdapter (x=950) -->
  <!-- 7. Database & Audit (x=1100) -->

  <!-- Lifeline Headers -->
  <g id="lifelines">
    <!-- Col 1 -->
    <rect x="50" y="95" width="130" height="40" rx="6" fill="#141E33" stroke="#1E293B" stroke-width="1.5" />
    <text x="115" y="120" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#38BDF8" text-anchor="middle">Trader / Client</text>
    <line x1="115" y1="135" x2="115" y2="580" stroke="#1E293B" stroke-width="1.5" stroke-dasharray="4,4" />

    <!-- Col 2 -->
    <rect x="220" y="95" width="130" height="40" rx="6" fill="#141E33" stroke="#1E293B" stroke-width="1.5" />
    <text x="285" y="120" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#38BDF8" text-anchor="middle">FastAPI Router</text>
    <line x1="285" y1="135" x2="285" y2="580" stroke="#1E293B" stroke-width="1.5" stroke-dasharray="4,4" />

    <!-- Col 3 -->
    <rect x="385" y="95" width="130" height="40" rx="6" fill="#141E33" stroke="#1E293B" stroke-width="1.5" />
    <text x="450" y="120" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#38BDF8" text-anchor="middle">OrderService</text>
    <line x1="450" y1="135" x2="450" y2="580" stroke="#1E293B" stroke-width="1.5" stroke-dasharray="4,4" />

    <!-- Col 4 -->
    <rect x="555" y="95" width="130" height="40" rx="6" fill="#141E33" stroke="#1E293B" stroke-width="1.5" />
    <text x="620" y="120" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#38BDF8" text-anchor="middle">EntitlementService</text>
    <line x1="620" y1="135" x2="620" y2="580" stroke="#1E293B" stroke-width="1.5" stroke-dasharray="4,4" />

    <!-- Col 5 -->
    <rect x="725" y="95" width="130" height="40" rx="6" fill="#141E33" stroke="#1E293B" stroke-width="1.5" />
    <text x="790" y="120" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#10B981" text-anchor="middle">RiskService</text>
    <line x1="790" y1="135" x2="790" y2="580" stroke="#1E293B" stroke-width="1.5" stroke-dasharray="4,4" />

    <!-- Col 6 -->
    <rect x="885" y="95" width="130" height="40" rx="6" fill="#141E33" stroke="#FBBF24" stroke-width="1.5" />
    <text x="950" y="120" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="600" fill="#FBBF24" text-anchor="middle">PaperAdapter</text>
    <line x1="950" y1="135" x2="950" y2="580" stroke="#1E293B" stroke-width="1.5" stroke-dasharray="4,4" />

    <!-- Col 7 -->
    <rect x="1035" y="95" width="130" height="40" rx="6" fill="#141E33" stroke="#1E293B" stroke-width="1.5" />
    <text x="1100" y="120" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#38BDF8" text-anchor="middle">PostgreSQL / Audit</text>
    <line x1="1100" y1="135" x2="1100" y2="580" stroke="#1E293B" stroke-width="1.5" stroke-dasharray="4,4" />
  </g>

  <!-- Step 1: POST /api/v1/orders/ -->
  <g transform="translate(0, 160)">
    <line x1="115" y1="0" x2="280" y2="0" stroke="#38BDF8" stroke-width="1.5" />
    <polygon points="280,-4 285,0 280,4" fill="#38BDF8" />
    <text x="200" y="-8" font-family="Inter, -apple-system, sans-serif" font-size="11" fill="#F8FAFC" text-anchor="middle">1. POST /api/v1/orders/ (CreateOrderRequest + JWT)</text>
  </g>

  <!-- Step 2: Validate JWT & TenantContext -->
  <g transform="translate(0, 210)">
    <line x1="285" y1="0" x2="445" y2="0" stroke="#38BDF8" stroke-width="1.5" />
    <polygon points="445,-4 450,0 445,4" fill="#38BDF8" />
    <text x="365" y="-8" font-family="Inter, -apple-system, sans-serif" font-size="11" fill="#F8FAFC" text-anchor="middle">2. Resolve TenantContext &amp; verify TRADER role</text>
  </g>

  <!-- Step 3: Quota Guard Check -->
  <g transform="translate(0, 260)">
    <line x1="450" y1="0" x2="615" y2="0" stroke="#38BDF8" stroke-width="1.5" />
    <polygon points="615,-4 620,0 615,4" fill="#38BDF8" />
    <text x="535" y="-8" font-family="Inter, -apple-system, sans-serif" font-size="11" fill="#F8FAFC" text-anchor="middle">3. Check daily order quota for subscription tier</text>
  </g>

  <!-- Step 4: Pre-Trade Risk Evaluation -->
  <g transform="translate(0, 310)">
    <line x1="450" y1="0" x2="785" y2="0" stroke="#10B981" stroke-width="1.5" />
    <polygon points="785,-4 790,0 785,4" fill="#10B981" />
    <text x="615" y="-8" font-family="Inter, -apple-system, sans-serif" font-size="11" fill="#10B981" text-anchor="middle">4. Evaluate leverage cap (1:100), required margin &amp; daily drawdown</text>
  </g>

  <!-- Step 5: Risk Approved Callback -->
  <g transform="translate(0, 355)">
    <line x1="790" y1="0" x2="455" y2="0" stroke="#10B981" stroke-width="1.5" stroke-dasharray="3,3" />
    <polygon points="455,-4 450,0 455,4" fill="#10B981" />
    <text x="615" y="-8" font-family="Inter, -apple-system, sans-serif" font-size="11" fill="#94A3B8" text-anchor="middle">Risk Checks Passed (Fail-closed evaluation)</text>
  </g>

  <!-- Step 6: Submit Order to PaperExecutionAdapter -->
  <g transform="translate(0, 405)">
    <line x1="450" y1="0" x2="945" y2="0" stroke="#FBBF24" stroke-width="1.5" />
    <polygon points="945,-4 950,0 945,4" fill="#FBBF24" />
    <text x="700" y="-8" font-family="Inter, -apple-system, sans-serif" font-size="11" fill="#FBBF24" text-anchor="middle">5. submit_order() with spread, slippage &amp; position netting (is_paper=True)</text>
  </g>

  <!-- Step 7: Persist Models & Write Audit Log -->
  <g transform="translate(0, 460)">
    <line x1="450" y1="0" x2="1095" y2="0" stroke="#38BDF8" stroke-width="1.5" />
    <polygon points="1095,-4 1100,0 1095,4" fill="#38BDF8" />
    <text x="770" y="-8" font-family="Inter, -apple-system, sans-serif" font-size="11" fill="#F8FAFC" text-anchor="middle">6. Persist OrderModel, FillModel, PositionModel &amp; write ORDER_CREATE audit log</text>
  </g>

  <!-- Step 8: Return HTTP 201 Response -->
  <g transform="translate(0, 520)">
    <line x1="450" y1="0" x2="120" y2="0" stroke="#10B981" stroke-width="1.5" />
    <polygon points="120,-4 115,0 120,4" fill="#10B981" />
    <text x="280" y="-8" font-family="Inter, -apple-system, sans-serif" font-size="11" fill="#10B981" text-anchor="middle">7. HTTP 201 Created (OrderResponse with is_paper=True, $0.00 capital risk)</text>
  </g>

  <!-- Bottom Invariant Footer -->
  <g transform="translate(60, 605)">
    <rect width="1080" height="50" rx="6" fill="#141E33" stroke="#1E293B" stroke-width="1" />
    <text x="24" y="30" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#FBBF24">EXECUTION INVARIANT:</text>
    <text x="180" y="30" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="400" fill="#F8FAFC">Orders are permanently stamped is_paper=True. All calculations use Decimal math. Zero live money accounts exist.</text>
  </g>
</svg>"""

# ----------------------------------------------------------------------
# 4. deployment-state-machine.svg
# ----------------------------------------------------------------------
def generate_state_machine() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 650" width="1200" height="650">
  <defs>
    <linearGradient id="bgGrad4" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#090D16" />
      <stop offset="100%" stop-color="#0F172A" />
    </linearGradient>
  </defs>

  <rect width="1200" height="650" fill="url(#bgGrad4)" />

  <!-- Title -->
  <text x="60" y="45" font-family="Inter, -apple-system, sans-serif" font-size="22" font-weight="700" fill="#F8FAFC">Project ORION — Strategy Deployment Lifecycle State Machine</text>
  <text x="60" y="70" font-family="Inter, -apple-system, sans-serif" font-size="13" font-weight="400" fill="#94A3B8">Fail-Closed Governance: Automated Quality Gates to Paper Incubation (Terminates with $0.00 Live Risk)</text>

  <!-- ACTIVE LIFECYCLE PATH (TOP / MIDDLE) -->

  <!-- Node 1: PENDING_GATES -->
  <g transform="translate(60, 160)">
    <rect width="180" height="90" rx="8" fill="#141E33" stroke="#38BDF8" stroke-width="2" />
    <text x="90" y="34" font-family="Inter, -apple-system, sans-serif" font-size="13" font-weight="700" fill="#38BDF8" text-anchor="middle">PENDING_GATES</text>
    <text x="90" y="58" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8" text-anchor="middle">Candidate Submitted</text>
    <text x="90" y="74" font-family="Inter, -apple-system, sans-serif" font-size="10" font-weight="400" fill="#64748B" text-anchor="middle">Awaiting Evaluation</text>
  </g>

  <!-- Arrow 1 -> 2 (Quality Gates Evaluation) -->
  <g transform="translate(240, 205)">
    <line x1="0" y1="0" x2="90" y2="0" stroke="#10B981" stroke-width="2" />
    <polygon points="90,-5 100,0 90,5" fill="#10B981" />
    <text x="50" y="-12" font-family="Inter, -apple-system, sans-serif" font-size="10" font-weight="600" fill="#10B981" text-anchor="middle">GATES EVAL</text>
    <text x="50" y="16" font-family="JetBrains Mono, Consolas, monospace" font-size="9" fill="#94A3B8" text-anchor="middle">WFE≥0.50, DD≤15%</text>
  </g>

  <!-- Node 2: GATES_PASSED -->
  <g transform="translate(340, 160)">
    <rect width="180" height="90" rx="8" fill="#141E33" stroke="#10B981" stroke-width="2" />
    <text x="90" y="34" font-family="Inter, -apple-system, sans-serif" font-size="13" font-weight="700" fill="#10B981" text-anchor="middle">GATES_PASSED</text>
    <text x="90" y="58" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8" text-anchor="middle">Criteria Verified</text>
    <text x="90" y="74" font-family="Inter, -apple-system, sans-serif" font-size="10" font-weight="400" fill="#64748B" text-anchor="middle">Ready for Incubation</text>
  </g>

  <!-- Arrow 2 -> 3 (Incubate) -->
  <g transform="translate(520, 205)">
    <line x1="0" y1="0" x2="80" y2="0" stroke="#38BDF8" stroke-width="2" />
    <polygon points="80,-5 90,0 80,5" fill="#38BDF8" />
    <text x="45" y="-12" font-family="Inter, -apple-system, sans-serif" font-size="10" font-weight="600" fill="#38BDF8" text-anchor="middle">INCUBATE</text>
    <text x="45" y="16" font-family="JetBrains Mono, Consolas, monospace" font-size="9" fill="#94A3B8" text-anchor="middle">POST /incubate</text>
  </g>

  <!-- Node 3: INCUBATING -->
  <g transform="translate(610, 160)">
    <rect width="180" height="90" rx="8" fill="#141E33" stroke="#38BDF8" stroke-width="2" />
    <text x="90" y="34" font-family="Inter, -apple-system, sans-serif" font-size="13" font-weight="700" fill="#38BDF8" text-anchor="middle">INCUBATING</text>
    <text x="90" y="58" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8" text-anchor="middle">Simulated Paper Execution</text>
    <text x="90" y="74" font-family="Inter, -apple-system, sans-serif" font-size="10" font-weight="400" fill="#FBBF24" text-anchor="middle">$0.00 Capital Risk</text>
  </g>

  <!-- Arrow 3 -> 4 (Validate) -->
  <g transform="translate(790, 205)">
    <line x1="0" y1="0" x2="80" y2="0" stroke="#10B981" stroke-width="2" />
    <polygon points="80,-5 90,0 80,5" fill="#10B981" />
    <text x="45" y="-12" font-family="Inter, -apple-system, sans-serif" font-size="10" font-weight="600" fill="#10B981" text-anchor="middle">VALIDATE</text>
    <text x="45" y="16" font-family="JetBrains Mono, Consolas, monospace" font-size="9" fill="#94A3B8" text-anchor="middle">Incubation Target Met</text>
  </g>

  <!-- Node 4: PAPER_VALIDATED -->
  <g transform="translate(870, 160)">
    <rect width="180" height="90" rx="8" fill="#141E33" stroke="#10B981" stroke-width="2" />
    <text x="90" y="34" font-family="Inter, -apple-system, sans-serif" font-size="13" font-weight="700" fill="#10B981" text-anchor="middle">PAPER_VALIDATED</text>
    <text x="90" y="58" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#94A3B8" text-anchor="middle">Incubation Success</text>
    <text x="90" y="74" font-family="Inter, -apple-system, sans-serif" font-size="10" font-weight="400" fill="#10B981" text-anchor="middle">Target Metrics Verified</text>
  </g>

  <!-- Arrow 4 -> 5 (Promote) -->
  <g transform="translate(960, 250)">
    <line x1="0" y1="0" x2="0" y2="60" stroke="#38BDF8" stroke-width="2" />
    <polygon points="-5,60 0,70 5,60" fill="#38BDF8" />
    <text x="12" y="36" font-family="Inter, -apple-system, sans-serif" font-size="10" font-weight="600" fill="#38BDF8">PROMOTE</text>
  </g>

  <!-- Node 5: PROMOTION_CANDIDATE (TERMINAL SUCCESS) -->
  <g transform="translate(870, 320)">
    <rect width="180" height="90" rx="8" fill="#141E33" stroke="#FBBF24" stroke-width="2" />
    <text x="90" y="32" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="700" fill="#FBBF24" text-anchor="middle">PROMOTION_CANDIDATE</text>
    <text x="90" y="54" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#F8FAFC" text-anchor="middle">Institutional Review</text>
    <text x="90" y="72" font-family="Inter, -apple-system, sans-serif" font-size="10" font-weight="600" fill="#FBBF24" text-anchor="middle">TERMINAL STATUS</text>
  </g>

  <!-- TERMINAL & FAILURE STATES (BOTTOM ROW) -->

  <!-- Node: GATES_FAILED -->
  <g transform="translate(60, 340)">
    <rect width="160" height="70" rx="6" fill="#141E33" stroke="#F43F5E" stroke-width="1.5" />
    <text x="80" y="30" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="700" fill="#F43F5E" text-anchor="middle">GATES_FAILED</text>
    <text x="80" y="50" font-family="Inter, -apple-system, sans-serif" font-size="10" font-weight="400" fill="#94A3B8" text-anchor="middle">Failed WFE / DD Checks</text>
  </g>
  <line x1="150" y1="250" x2="150" y2="340" stroke="#F43F5E" stroke-width="1.5" stroke-dasharray="3,3" />
  <polygon points="146,335 150,340 154,335" fill="#F43F5E" />

  <!-- Node: INCUBATION_FAILED -->
  <g transform="translate(620, 340)">
    <rect width="160" height="70" rx="6" fill="#141E33" stroke="#F43F5E" stroke-width="1.5" />
    <text x="80" y="30" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="700" fill="#F43F5E" text-anchor="middle">INCUBATION_FAILED</text>
    <text x="80" y="50" font-family="Inter, -apple-system, sans-serif" font-size="10" font-weight="400" fill="#94A3B8" text-anchor="middle">Excess Drawdown in Paper</text>
  </g>
  <line x1="700" y1="250" x2="700" y2="340" stroke="#F43F5E" stroke-width="1.5" stroke-dasharray="3,3" />
  <polygon points="696,335 700,340 704,335" fill="#F43F5E" />

  <!-- Node: SUSPENDED / CANCELLED -->
  <g transform="translate(340, 340)">
    <rect width="180" height="70" rx="6" fill="#141E33" stroke="#F59E0B" stroke-width="1.5" />
    <text x="90" y="30" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="700" fill="#F59E0B" text-anchor="middle">SUSPENDED / CANCELLED</text>
    <text x="90" y="50" font-family="Inter, -apple-system, sans-serif" font-size="10" font-weight="400" fill="#94A3B8" text-anchor="middle">Operator Manual Override</text>
  </g>

  <!-- Governance & Invariant Footer Card -->
  <g transform="translate(60, 480)">
    <rect width="1080" height="120" rx="8" fill="#141E33" stroke="#1E293B" stroke-width="1.5" />
    <text x="24" y="32" font-family="Inter, -apple-system, sans-serif" font-size="13" font-weight="700" fill="#38BDF8">FAIL-CLOSED GOVERNANCE &amp; TERMINATION BOUNDARY</text>
    
    <text x="24" y="60" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">Separation of Duties:</text>
    <text x="175" y="60" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="400" fill="#94A3B8">Trader submits candidate; Risk Officer / Portfolio Manager reviews and promotes.</text>

    <text x="24" y="82" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">Automated Quality Gates:</text>
    <text x="175" y="82" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="400" fill="#94A3B8">Candidates failing WFE (≥0.50) or Drawdown (≤15%) transition immediately to GATES_FAILED.</text>

    <text x="24" y="104" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#FBBF24">Safety Boundary:</text>
    <text x="175" y="104" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="400" fill="#F8FAFC">The pipeline strictly terminates at paper validation; zero code pathways exist for real-money execution.</text>
  </g>
</svg>"""

# ----------------------------------------------------------------------
# 5. data-room-4tier-pyramid.svg
# ----------------------------------------------------------------------
def generate_data_room_pyramid() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 760" width="1200" height="760">
  <defs>
    <linearGradient id="bgGrad5" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#090D16" />
      <stop offset="100%" stop-color="#0F172A" />
    </linearGradient>
  </defs>

  <rect width="1200" height="760" fill="url(#bgGrad5)" />

  <!-- Title -->
  <text x="60" y="45" font-family="Inter, -apple-system, sans-serif" font-size="22" font-weight="700" fill="#F8FAFC">Project ORION — Due Diligence Data Room Navigation Pyramid</text>
  <text x="60" y="70" font-family="Inter, -apple-system, sans-serif" font-size="13" font-weight="400" fill="#94A3B8">Structured 4-Tier Due Diligence Architecture for Technical, Operational, SRE &amp; Legal Evaluators (18 Dossiers)</text>

  <!-- TIER 1: EXECUTIVE & ARCHITECTURAL ORIENTATION -->
  <g transform="translate(240, 100)">
    <rect width="720" height="110" rx="8" fill="#141E33" stroke="#0284C7" stroke-width="2" />
    <rect x="2" y="2" width="716" height="4" rx="2" fill="#0284C7" />
    <text x="24" y="30" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="700" fill="#38BDF8" letter-spacing="1">TIER 1: EXECUTIVE &amp; ARCHITECTURAL ORIENTATION (Dossiers 01–03)</text>
    <text x="680" y="30" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="600" fill="#94A3B8" text-anchor="end">Sponsors, CEOs &amp; M&amp;A Leads</text>
    
    <g transform="translate(24, 50)">
      <text x="0" y="16" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">01-EXECUTIVE-BRIEF.md <tspan font-weight="400" fill="#94A3B8">— Software positioning, paper-only $0 risk invariant</tspan></text>
      <text x="0" y="36" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">02-PRODUCT-OVERVIEW.md <tspan font-weight="400" fill="#94A3B8">— 5-stage research workflow, strategy catalogue profiles</tspan></text>
      <text x="0" y="56" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">03-ARCHITECTURE-OVERVIEW.md <tspan font-weight="400" fill="#94A3B8">— Hexagonal architecture, 21 domain packages, ports/adapters</tspan></text>
    </g>
  </g>

  <!-- TIER 2: TECHNICAL DEEP-DIVE & HARNESS AUDIT -->
  <g transform="translate(160, 230)">
    <rect width="880" height="155" rx="8" fill="#141E33" stroke="#10B981" stroke-width="2" />
    <rect x="2" y="2" width="876" height="4" rx="2" fill="#10B981" />
    <text x="24" y="28" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="700" fill="#10B981" letter-spacing="1">TIER 2: TECHNICAL DEEP-DIVE &amp; HARNESS AUDIT (Dossiers 04–10)</text>
    <text x="840" y="28" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="600" fill="#94A3B8" text-anchor="end">CTOs, Tech Leads &amp; Engineers</text>
    
    <g transform="translate(24, 46)">
      <text x="0" y="16" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">04-TECHNICAL-HANDOVER-GUIDE.md <tspan font-weight="400" fill="#94A3B8">— Local dev, pytest harness (4,260 tests, 99.4% coverage)</tspan></text>
      <text x="0" y="36" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">05-DEPLOYMENT-HANDOVER.md <tspan font-weight="400" fill="#94A3B8">— Render PaaS deployment, container builds, secret injection</tspan></text>
      <text x="0" y="56" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">06-OPERATIONS-RUNBOOK.md <tspan font-weight="400" fill="#94A3B8">— Day-two procedures, health probes (/health/live, /health/ready)</tspan></text>
      <text x="0" y="76" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">07-SECURITY-OVERVIEW.md <tspan font-weight="400" fill="#94A3B8">— JWT HS256 auth, bcrypt, security headers, 7-role RBAC matrix</tspan></text>
      <text x="0" y="96" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">08-BACKUP-RESTORE-RUNBOOK.md <tspan font-weight="400" fill="#94A3B8">— Database restore runbook, ~7.2s historical benchmark across 29 tables</tspan></text>
      <text x="460" y="16" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">09-API-DOCUMENTATION.md <tspan font-weight="400" fill="#94A3B8">— 24 routers, Pydantic v2 schemas</tspan></text>
      <text x="460" y="36" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">10-DATABASE-MIGRATION-GUIDE.md <tspan font-weight="400" fill="#94A3B8">— 15 Alembic migrations, 29 tables</tspan></text>
    </g>
  </g>

  <!-- TIER 3: OPERATIONAL & DEPENDENCY AUDIT -->
  <g transform="translate(100, 405)">
    <rect width="1000" height="135" rx="8" fill="#141E33" stroke="#F59E0B" stroke-width="2" />
    <rect x="2" y="2" width="996" height="4" rx="2" fill="#F59E0B" />
    <text x="24" y="28" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="700" fill="#F59E0B" letter-spacing="1">TIER 3: OPERATIONAL &amp; DEPENDENCY AUDIT (Dossiers 11–14)</text>
    <text x="960" y="28" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="600" fill="#94A3B8" text-anchor="end">SRE, DevOps &amp; Security Evaluators</text>
    
    <g transform="translate(24, 46)">
      <text x="0" y="16" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">11-ENVIRONMENT-VARIABLE-REFERENCE.md <tspan font-weight="400" fill="#94A3B8">— Pydantic Settings, environment reference, secret handling</tspan></text>
      <text x="0" y="36" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">12-DEPENDENCY-SBOM.md <tspan font-weight="400" fill="#94A3B8">— Software Bill of Materials, MIT/Apache/BSD open-source license audit</tspan></text>
      <text x="0" y="56" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">13-KNOWN-LIMITATIONS.md <tspan font-weight="400" fill="#94A3B8">— Transparent limits: REST polling, single-process worker, paper-only mode</tspan></text>
      <text x="0" y="76" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">14-INFRASTRUCTURE-TOPOLOGY-MAP.md <tspan font-weight="400" fill="#94A3B8">— PaaS architecture, Render resources (~$14/mo config estimate)</tspan></text>
    </g>
  </g>

  <!-- TIER 4: TRANSACTION, IP & ACCOUNT TRANSFER -->
  <g transform="translate(60, 560)">
    <rect width="1080" height="135" rx="8" fill="#141E33" stroke="#38BDF8" stroke-width="2" />
    <rect x="2" y="2" width="1076" height="4" rx="2" fill="#38BDF8" />
    <text x="24" y="28" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="700" fill="#38BDF8" letter-spacing="1">TIER 4: TRANSACTION, IP &amp; ACCOUNT TRANSFER (Dossiers 15–18)</text>
    <text x="1040" y="28" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="600" fill="#94A3B8" text-anchor="end">Legal Counsel &amp; Corporate Development</text>
    
    <g transform="translate(24, 46)">
      <text x="0" y="16" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">15-IP-ASSIGNMENT-CHECKLIST.md <tspan font-weight="400" fill="#94A3B8">— Copyright, patent, trade secret transfer verification</tspan></text>
      <text x="0" y="36" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">16-ACCOUNT-OWNERSHIP-TRANSFER.md <tspan font-weight="400" fill="#94A3B8">— Vendor accounts, Independent Account Provisioning Path</tspan></text>
      <text x="0" y="56" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">17-DOMAIN-TRANSFER-CHECKLIST.md <tspan font-weight="400" fill="#94A3B8">— Domain DNS transition runbook and SSL/TLS certificate steps</tspan></text>
      <text x="0" y="76" font-family="Inter, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#F8FAFC">18-DUE-DILIGENCE-DATA-ROOM-INDEX.md <tspan font-weight="400" fill="#94A3B8">— Master verification matrix and artifact cross-reference index</tspan></text>
    </g>
  </g>

  <!-- Footer note -->
  <text x="600" y="730" font-family="Inter, -apple-system, sans-serif" font-size="11" font-weight="400" fill="#64748B" text-anchor="middle">Project ORION Due Diligence Data Room — All 18 dossiers available under docs/acquisition/</text>
</svg>"""

def main():
    print("Generating standalone SVG vector diagrams...")
    diagrams = {
        "architecture-hexagonal-map.svg": generate_architecture_map(),
        "workflow-5-stage-pipeline.svg": generate_workflow_pipeline(),
        "order-execution-sequence.svg": generate_order_sequence(),
        "deployment-state-machine.svg": generate_state_machine(),
        "data-room-4tier-pyramid.svg": generate_data_room_pyramid(),
    }
    
    for filename, svg_content in diagrams.items():
        file_path = OUTPUT_DIR / filename
        file_path.write_text(svg_content.strip(), encoding="utf-8")
        print(f"  [OK] Generated {filename} ({len(svg_content)} bytes)")

    print(f"All 5 SVG diagrams generated successfully in {OUTPUT_DIR}.")

if __name__ == "__main__":
    main()
