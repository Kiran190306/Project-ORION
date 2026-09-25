#!/usr/bin/env python3
"""
build_pptx.py — Project ORION Buyer Presentation Deck Generator
EPIC-029 Phase 0.6: Buyer Visual Presentation Package

Generates:
docs/acquisition/presentation/visual/pptx/Project-ORION-Buyer-Presentation.pptx

Specifications:
- 15 slides strictly matching docs/acquisition/presentation/01-BUYER-PRESENTATION.md
- 16:9 widescreen layout (13.333" x 7.5")
- Dark theme palette matching apps/dashboard/src/index.css:
  Background: #090D16, Cards: #141E33, Borders: #1E293B, Accents: #0284C7 / #38BDF8
- Full verbatim speaker notes embedded on every slide
- Strict commercial and simulation invariants enforced:
  - Free $0 / Pro $99 / Business $299 / Enterprise Custom
  - Capital at risk: $0.00
  - AutonomousWorkerCoordinator: disabled by default (WORKER_ENABLED=false)
  - Historical benchmarks: 4,260 tests, 99.4% coverage, ~7.2s restore across 29 tables
  - Structural facts: 4 concrete classes, 9 API profiles, 7 RBAC roles, 41 permissions,
    24 routers, 21 domain packages, 18 dossiers, 15 migrations, 29 tables
"""

from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# Paths
OUTPUT_FILE = Path(__file__).parent.parent / "pptx" / "Project-ORION-Buyer-Presentation.pptx"
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# Color Palette Tokens
BG_DARK = RGBColor(9, 13, 22)        # #090D16
BG_CARD = RGBColor(20, 30, 51)       # #141E33
BG_SUBTLE = RGBColor(15, 23, 42)     # #0F172A
BORDER_COLOR = RGBColor(30, 41, 59)  # #1E293B
BORDER_MUTED = RGBColor(51, 65, 85)  # #334155

TEXT_LIGHT = RGBColor(248, 250, 252) # #F8FAFC
TEXT_MUTED = RGBColor(148, 163, 184) # #94A3B8
TEXT_SUBTLE = RGBColor(100, 116, 139)# #64748B

ACCENT_BLUE = RGBColor(2, 132, 199)  # #0284C7
ACCENT_CYAN = RGBColor(56, 189, 248) # #38BDF8
STATUS_GREEN = RGBColor(16, 185, 129)# #10B981
STATUS_AMBER = RGBColor(245, 158, 11)# #F59E0B
STATUS_ROSE = RGBColor(244, 63, 94)  # #F43F5E
BADGE_PAPER = RGBColor(251, 191, 36) # #FBBF24

FONT_HEADING = "Segoe UI"
FONT_BODY = "Segoe UI"
FONT_MONO = "Consolas"


class OrionDeckBuilder:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width = Inches(13.333)
        self.prs.slide_height = Inches(7.5)
        self.blank_layout = self.prs.slide_layouts[6]

    def _add_base_slide(self, slide_num: int, title: str, subtitle: str, speaker_notes: str):
        slide = self.prs.slides.add_slide(self.blank_layout)

        # Full bleed dark background
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = BG_DARK
        bg.line.color.rgb = BG_DARK

        # Top Category & Slide Indicator
        tb_meta = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(0.35))
        tf_meta = tb_meta.text_frame
        tf_meta.word_wrap = True
        tf_meta.margin_left = tf_meta.margin_top = tf_meta.margin_right = tf_meta.margin_bottom = 0
        p_meta = tf_meta.paragraphs[0]
        p_meta.text = f"PROJECT ORION  │  ACQUISITION DUE DILIGENCE  │  SLIDE {slide_num} OF 15"
        p_meta.font.name = FONT_MONO
        p_meta.font.size = Pt(9.5)
        p_meta.font.bold = True
        p_meta.font.color.rgb = ACCENT_CYAN

        # Header Title
        tb_title = slide.shapes.add_textbox(Inches(0.8), Inches(0.72), Inches(11.733), Inches(0.55))
        tf_title = tb_title.text_frame
        tf_title.word_wrap = True
        tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
        p_title = tf_title.paragraphs[0]
        p_title.text = title
        p_title.font.name = FONT_HEADING
        p_title.font.size = Pt(21)
        p_title.font.bold = True
        p_title.font.color.rgb = TEXT_LIGHT

        # Subtitle
        if subtitle:
            tb_sub = slide.shapes.add_textbox(Inches(0.8), Inches(1.3), Inches(11.733), Inches(0.35))
            tf_sub = tb_sub.text_frame
            tf_sub.word_wrap = True
            tf_sub.margin_left = tf_sub.margin_top = tf_sub.margin_right = tf_sub.margin_bottom = 0
            p_sub = tf_sub.paragraphs[0]
            p_sub.text = subtitle
            p_sub.font.name = FONT_BODY
            p_sub.font.size = Pt(11)
            p_sub.font.color.rgb = TEXT_MUTED

        # Bottom Invariant Bar
        footer = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(6.85), Inches(11.733), Inches(0.38))
        footer.fill.solid()
        footer.fill.fore_color.rgb = BG_SUBTLE
        footer.line.color.rgb = BORDER_COLOR
        footer.line.width = Pt(1)

        tb_foot = slide.shapes.add_textbox(Inches(0.95), Inches(6.88), Inches(11.433), Inches(0.32))
        tf_foot = tb_foot.text_frame
        tf_foot.margin_left = tf_foot.margin_top = tf_foot.margin_right = tf_foot.margin_bottom = 0
        p_foot = tf_foot.paragraphs[0]
        p_foot.text = "Baseline: d5908d0a │ STRICT PAPER TRADING ONLY │ $0.00 Live Financial Capital at Risk │ Proposed Transferable Software Scope"
        p_foot.font.name = FONT_MONO
        p_foot.font.size = Pt(9)
        p_foot.font.color.rgb = TEXT_SUBTLE

        # Embed Speaker Notes
        slide.notes_slide.notes_text_frame.text = speaker_notes.strip()

        return slide

    def _add_card(self, slide, left, top, width, height, border_color=BORDER_COLOR, bg_color=BG_CARD):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1.5)
        return card

    def build_deck(self):
        # -------------------------------------------------------------
        # SLIDE 1: Title & Executive Identity
        # -------------------------------------------------------------
        notes_s1 = """Project ORION is an institutional-style quantitative foreign exchange research and paper-trading platform. Today's walkthrough covers the platform's architectural, mathematical, and operational capabilities. We emphasize that this platform operates strictly in paper-trading simulation mode with deterministic market data and zero live financial capital at risk."""
        s1 = self._add_base_slide(
            1,
            "Project ORION — Quantitative FX Research & Paper-Trading SaaS",
            "Multi-Tenant Quantitative Engine, Deterministic Backtesting & Simulated Execution Architecture",
            notes_s1
        )
        
        # Center Hero Card
        self._add_card(s1, 0.8, 1.8, 11.733, 4.75, border_color=ACCENT_BLUE)
        
        # Left Block: Core Software Asset
        tb_hero = s1.shapes.add_textbox(Inches(1.2), Inches(2.1), Inches(6.0), Inches(4.1))
        tf_hero = tb_hero.text_frame
        tf_hero.word_wrap = True
        
        p = tf_hero.paragraphs[0]
        p.text = "PROPRIETARY TECHNOLOGY ASSET"
        p.font.name = FONT_MONO
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = ACCENT_CYAN
        
        p2 = tf_hero.add_paragraph()
        p2.space_before = Pt(8)
        p2.text = "Institutional Quantitative Workflow in Pure Software"
        p2.font.name = FONT_HEADING
        p2.font.size = Pt(17)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_LIGHT

        bullets = [
            ("Core Asset:", "Complete proprietary source code repository in Python 3.11+ & React 18."),
            ("Capital Safety Invariant:", "Strict paper-trading execution model with exactly $0.00 live financial capital at risk."),
            ("Research Integrity:", "Chronological deterministic backtesting with LeakageGuard temporal protection."),
            ("Optimization Robustness:", "Multi-window Walk-Forward Analysis computing Walk-Forward Efficiency (WFE)."),
            ("Transaction Deliverables:", "Full Git commit provenance, automated test harness, and 18 closing due diligence dossiers.")
        ]
        for title, desc in bullets:
            pb = tf_hero.add_paragraph()
            pb.space_before = Pt(6)
            pb.text = f"• {title} "
            pb.font.name = FONT_BODY
            pb.font.size = Pt(11)
            pb.font.bold = True
            pb.font.color.rgb = ACCENT_CYAN
            
            run = pb.add_run()
            run.text = desc
            run.font.bold = False
            run.font.color.rgb = TEXT_LIGHT

        # Right Grid: Key Verified Baseline Metrics
        metrics = [
            ("21", "DOMAIN PACKAGES", "Modular Hexagonal Monorepo", ACCENT_CYAN),
            ("24", "FASTAPI ROUTERS", "Pydantic v2 Typed Schemas", ACCENT_CYAN),
            ("4,260", "TESTS (HISTORICAL)", "99.4% Test Coverage Baseline", STATUS_GREEN),
            ("18", "DUE DILIGENCE DOSSIERS", "Comprehensive Data Room", STATUS_AMBER),
            ("~$14/mo", "HOSTING ESTIMATE", "PaaS Baseline Cloud Config", ACCENT_CYAN),
            ("$0.00", "LIVE CAPITAL RISK", "Permanent Paper Safety Invariant", BADGE_PAPER)
        ]
        
        grid_lefts = [7.5, 9.7]
        grid_tops = [2.1, 3.5, 4.9]
        idx = 0
        for r in range(3):
            for c in range(2):
                val, title, sub, color = metrics[idx]
                gl = grid_lefts[c]
                gt = grid_tops[r]
                self._add_card(s1, gl, gt, 2.0, 1.25, border_color=BORDER_MUTED, bg_color=BG_SUBTLE)
                
                tb_m = s1.shapes.add_textbox(Inches(gl + 0.1), Inches(gt + 0.1), Inches(1.8), Inches(1.05))
                tf_m = tb_m.text_frame
                tf_m.word_wrap = True
                
                p_val = tf_m.paragraphs[0]
                p_val.text = val
                p_val.font.name = FONT_HEADING
                p_val.font.size = Pt(18)
                p_val.font.bold = True
                p_val.font.color.rgb = color
                
                p_lbl = tf_m.add_paragraph()
                p_lbl.text = title
                p_lbl.font.name = FONT_MONO
                p_lbl.font.size = Pt(8.5)
                p_lbl.font.bold = True
                p_lbl.font.color.rgb = TEXT_LIGHT
                
                p_sub2 = tf_m.add_paragraph()
                p_sub2.text = sub
                p_sub2.font.name = FONT_BODY
                p_sub2.font.size = Pt(7.5)
                p_sub2.font.color.rgb = TEXT_MUTED
                
                idx += 1

        # -------------------------------------------------------------
        # SLIDE 2: What the Software Is
        # -------------------------------------------------------------
        notes_s2 = """ORION delivers a complete SaaS architecture. Subscription plans, quotas, and paper-account entitlements are enforced in code through our EntitlementService across four distinct tiers. Commercial subscriptions operate in Stripe Test Mode with zero customer capital exposed."""
        s2 = self._add_base_slide(
            2,
            "What the Software Is — Quantitative Platform & Multi-Tier SaaS",
            "Four Authoritative Subscription Tiers Enforced in Source Code (Stripe Test Mode)",
            notes_s2
        )
        
        # 4 Subscription Tier Cards
        tiers = [
            ("FREE SANDBOX", "$0", "/ month", "Self-service onboarding & evaluation", [
                "1 Paper Account ($100k virtual balance)",
                "100 Daily Orders Cap",
                "0 Autonomous Trading Workers",
                "4 Major FX Pairs Supported",
                "30-Day Data Retention Window",
                "Manual Strategy Parameterization"
            ], BORDER_MUTED, TEXT_MUTED),
            ("PRO TRADER", "$99", "/ month", "Individual quantitative quants & active traders", [
                "3 Paper Accounts with Custom Sizing",
                "2,500 Daily Orders Cap",
                "1 Autonomous Trading Worker",
                "12 Liquid FX Pairs Supported",
                "365-Day Historical Data Retention",
                "Walk-Forward Analysis & Optimization"
            ], ACCENT_BLUE, ACCENT_CYAN),
            ("BUSINESS PROP", "$299", "/ month", "Prop desks, family offices & small quant funds", [
                "10 Paper Accounts across Portfolios",
                "50,000 Daily Orders Cap",
                "5 Autonomous Trading Workers",
                "All FX Pairs & Synthetic Baskets",
                "5-Year Historical Data Retention",
                "Multi-User RBAC & Audit Trails"
            ], STATUS_GREEN, STATUS_GREEN),
            ("ENTERPRISE", "Custom", "contract", "Institutional firms requiring dedicated deployment", [
                "Unlimited Paper Accounts",
                "Unlimited Daily Orders Capacity",
                "Custom Worker Process Pool Allocation",
                "Full Cross-Asset & Custom Ingestion",
                "7-Year Regulatory Retention Archive",
                "Custom RBAC & White-Label Theming"
            ], STATUS_AMBER, STATUS_AMBER)
        ]
        
        col_w = 2.75
        col_gap = 0.24
        start_x = 0.8
        for i, (name, price, period, desc, feats, b_color, p_color) in enumerate(tiers):
            x = start_x + i * (col_w + col_gap)
            self._add_card(s2, x, 1.8, col_w, 4.75, border_color=b_color)
            
            tb = s2.shapes.add_textbox(Inches(x + 0.15), Inches(1.95), Inches(col_w - 0.3), Inches(4.4))
            tf = tb.text_frame
            tf.word_wrap = True
            
            p_n = tf.paragraphs[0]
            p_n.text = name
            p_n.font.name = FONT_MONO
            p_n.font.size = Pt(11)
            p_n.font.bold = True
            p_n.font.color.rgb = p_color
            
            p_p = tf.add_paragraph()
            p_p.space_before = Pt(4)
            p_p.text = price
            p_p.font.name = FONT_HEADING
            p_p.font.size = Pt(24)
            p_p.font.bold = True
            p_p.font.color.rgb = TEXT_LIGHT
            run_pd = p_p.add_run()
            run_pd.text = f" {period}"
            run_pd.font.size = Pt(11)
            run_pd.font.bold = False
            run_pd.font.color.rgb = TEXT_MUTED
            
            p_d = tf.add_paragraph()
            p_d.space_before = Pt(4)
            p_d.text = desc
            p_d.font.name = FONT_BODY
            p_d.font.size = Pt(9.5)
            p_d.font.color.rgb = TEXT_MUTED
            
            p_div = tf.add_paragraph()
            p_div.text = "──────────────────────"
            p_div.font.size = Pt(7)
            p_div.font.color.rgb = BORDER_MUTED
            
            for f in feats:
                pf = tf.add_paragraph()
                pf.space_before = Pt(5)
                pf.text = f"✓ {f}"
                pf.font.name = FONT_BODY
                pf.font.size = Pt(9.5)
                pf.font.color.rgb = TEXT_LIGHT

        # -------------------------------------------------------------
        # SLIDE 3: Product Workflow
        # -------------------------------------------------------------
        notes_s3 = """The ORION workflow enforces strict mathematical hygiene. Strategies cannot enter paper trading without passing quantitative quality gates, filtering out overfitted algorithms before they ever touch simulated execution."""
        s3 = self._add_base_slide(
            3,
            "Product Workflow — 5-Stage Research & Incubation Lifecycle",
            "From Mathematical Formulation to Paper Incubation with Automated Quality Gate Governance",
            notes_s3
        )
        
        stages = [
            ("STAGE 1", "Specification", "Strategy Formulation", [
                "4 concrete classes in StrategyRegistry",
                "9 API catalogue archetype schemas",
                "Indicator & threshold parameter bounds",
                "Python Decimal financial arithmetic"
            ], ACCENT_BLUE, ACCENT_CYAN),
            ("STAGE 2", "Deterministic Backtest", "Chronological Replay", [
                "DeterministicBacktestEngine traversal",
                "LeakageGuard temporal monotonicity",
                "Sharpe, Sortino, Max Drawdown metrics",
                "Identical cent-level reproducibility"
            ], ACCENT_BLUE, ACCENT_CYAN),
            ("STAGE 3", "Optimization & WFA", "Robustness Scoring", [
                "Multi-parameter space grid search",
                "Rolling In-Sample & Out-Of-Sample slices",
                "Walk-Forward Efficiency (WFE) score",
                "Parameter surface stability analysis"
            ], ACCENT_BLUE, ACCENT_CYAN),
            ("STAGE 4", "Quality Gates", "Automated Governance", [
                "WFE Threshold Hurdle (WFE ≥ 0.50)",
                "Max Permissible Drawdown (DD ≤ 15%)",
                "Parameter Surface Variance check",
                "Fail-closed GATES_FAILED transition"
            ], STATUS_GREEN, STATUS_GREEN),
            ("STAGE 5", "Paper Incubation", "Simulated Execution", [
                "PaperExecutionAdapter matching engine",
                "Realistic spread, slippage & latency",
                "Simulated mark-to-market valuations",
                "Strict termination at $0.00 Live Risk"
            ], BADGE_PAPER, BADGE_PAPER)
        ]
        
        c_w = 2.18
        c_gap = 0.2
        s_x = 0.8
        for i, (stg, stitle, ssub, points, b_col, t_col) in enumerate(stages):
            x = s_x + i * (c_w + c_gap)
            self._add_card(s3, x, 1.8, c_w, 3.8, border_color=b_col)
            
            tb = s3.shapes.add_textbox(Inches(x + 0.12), Inches(1.95), Inches(c_w - 0.24), Inches(3.5))
            tf = tb.text_frame
            tf.word_wrap = True
            
            p_s = tf.paragraphs[0]
            p_s.text = stg
            p_s.font.name = FONT_MONO
            p_s.font.size = Pt(9.5)
            p_s.font.bold = True
            p_s.font.color.rgb = t_col
            
            p_t = tf.add_paragraph()
            p_t.space_before = Pt(2)
            p_t.text = stitle
            p_t.font.name = FONT_HEADING
            p_t.font.size = Pt(13)
            p_t.font.bold = True
            p_t.font.color.rgb = TEXT_LIGHT
            
            p_sub = tf.add_paragraph()
            p_sub.text = ssub
            p_sub.font.name = FONT_BODY
            p_sub.font.size = Pt(9)
            p_sub.font.color.rgb = TEXT_MUTED
            
            p_d = tf.add_paragraph()
            p_d.text = "──────────────────"
            p_d.font.size = Pt(7)
            p_d.font.color.rgb = BORDER_MUTED
            
            for pt in points:
                ppt = tf.add_paragraph()
                ppt.space_before = Pt(4)
                ppt.text = f"• {pt}"
                ppt.font.name = FONT_BODY
                ppt.font.size = Pt(8.8)
                ppt.font.color.rgb = TEXT_LIGHT

        # Bottom Safety Banner Card
        self._add_card(s3, 0.8, 5.8, 11.733, 0.85, border_color=BADGE_PAPER, bg_color=BG_SUBTLE)
        tb_ban = s3.shapes.add_textbox(Inches(1.0), Inches(5.9), Inches(11.333), Inches(0.65))
        tf_ban = tb_ban.text_frame
        tf_ban.word_wrap = True
        
        p_b1 = tf_ban.paragraphs[0]
        p_b1.text = "STRICT SAFETY INVARIANT — ZERO LIVE FINANCIAL CAPITAL EXPOSURE"
        p_b1.font.name = FONT_MONO
        p_b1.font.size = Pt(10.5)
        p_b1.font.bold = True
        p_b1.font.color.rgb = BADGE_PAPER
        
        p_b2 = tf_ban.add_paragraph()
        p_b2.space_before = Pt(2)
        p_b2.text = "The deployment pipeline strictly terminates at paper validation or promotion candidate status. Live real-money broker execution code is absent from the software. Exactly $0.00 live financial capital is exposed at any stage."
        p_b2.font.name = FONT_BODY
        p_b2.font.size = Pt(9.5)
        p_b2.font.color.rgb = TEXT_LIGHT

        # -------------------------------------------------------------
        # SLIDE 4: Architecture Overview
        # -------------------------------------------------------------
        notes_s4 = """Under the hood, Project ORION follows hexagonal architecture principles. The twenty-one domain packages are entirely decoupled from web frameworks and databases, ensuring quantitative algorithms remain mathematically isolated and portable."""
        s4 = self._add_base_slide(
            4,
            "Architecture Overview — Hexagonal Modular Decoupling",
            "Ports and Adapters Architecture Isolating 21 Pure Domain Packages from Infrastructure",
            notes_s4
        )
        
        layers = [
            ("1. PRESENTATION LAYER", "React 18 Single-Page Application (apps/dashboard/)", [
                "Built with TypeScript, Vite, Tailwind CSS, TanStack Query, and Lucide Icons",
                "20 client routes: Marketing, Auth, Terminal, Research, Optimization, Deployments, Admin",
                "Status: [INTERNAL] — Complete frontend repository"
            ], ACCENT_BLUE),
            ("2. API & DELIVERY LAYER", "FastAPI ASGI Web Application (apps/trading-engine/)", [
                "24 modular routers assembling endpoints with Pydantic v2 schemas and dependency injection",
                "Security headers middleware (HSTS, CSP, X-Frame DENY) & correlation ID request tracing",
                "Status: [INTERNAL] — High-performance asynchronous API factory"
            ], ACCENT_BLUE),
            ("3. APPLICATION SERVICES", "Orchestration & Workflow Coordination (src/services/)", [
                "OrderService, ResearchService, OptimizationService, DeploymentPipelineService",
                "EntitlementService enforcing 4-tier quotas; SubscriptionService handling Stripe test webhooks",
                "Status: [INTERNAL] — Transactional session and service management"
            ], ACCENT_BLUE),
            ("4. DOMAIN LOGIC LAYER", "21 Pure Internal Domain Packages (libraries/domain/)", [
                "Zero database or web framework dependencies; portable quantitative algorithms",
                "StrategyRegistry (4 concrete classes, 9 API profiles), RiskEngine, DeploymentLifecycle",
                "Status: [INTERNAL] — High-value proprietary intellectual property core"
            ], STATUS_GREEN),
            ("5. INFRASTRUCTURE & ADAPTERS", "Decoupled Persistence, Hardware & Execution Adapters", [
                "Persistence: SQLAlchemy 2.0 Async ORM + PostgreSQL 16 (29 tables) [INTERNAL]",
                "Simulated Matching: PaperExecutionAdapter (spread, slippage, $0 risk) [SIMULATED]",
                "Market Data: MockMarketDataProvider [SIMULATED] │ TwelveData Provider [EXTERNAL]",
                "Broker Sandbox: OandaBrokerAdapter [EXTERNAL] │ WorkerCoordinator [DISABLED BY DEFAULT]"
            ], STATUS_AMBER)
        ]
        
        ly_top = 1.8
        ly_h = 0.92
        ly_gap = 0.08
        for i, (ltitle, lsub, lpts, lcol) in enumerate(layers):
            y = ly_top + i * (ly_h + ly_gap)
            self._add_card(s4, 0.8, y, 11.733, ly_h, border_color=lcol)
            
            tb = s4.shapes.add_textbox(Inches(1.0), Inches(y + 0.08), Inches(11.333), Inches(ly_h - 0.16))
            tf = tb.text_frame
            tf.word_wrap = True
            
            p_lt = tf.paragraphs[0]
            p_lt.text = ltitle
            p_lt.font.name = FONT_MONO
            p_lt.font.size = Pt(10)
            p_lt.font.bold = True
            p_lt.font.color.rgb = lcol
            
            run_sub = p_lt.add_run()
            run_sub.text = f"  │  {lsub}"
            run_sub.font.name = FONT_HEADING
            run_sub.font.size = Pt(10.5)
            run_sub.font.bold = True
            run_sub.font.color.rgb = TEXT_LIGHT
            
            p_lp = tf.add_paragraph()
            p_lp.space_before = Pt(2)
            p_lp.text = " • ".join(lpts)
            p_lp.font.name = FONT_BODY
            p_lp.font.size = Pt(9)
            p_lp.font.color.rgb = TEXT_MUTED

        # -------------------------------------------------------------
        # SLIDE 5: Quantitative Research Engine
        # -------------------------------------------------------------
        notes_s5 = """The research engine implements four concrete algorithmic strategy classes in its core registry, supported by a nine-archetype parameter catalogue in the API. All financial arithmetic uses arbitrary-precision Decimal types, avoiding binary floating-point rounding errors."""
        s5 = self._add_base_slide(
            5,
            "Quantitative Research Engine — Strategies & Precision Math",
            "4 Concrete Backtesting Classes in StrategyRegistry & 9 Archetype API Catalogue Profiles",
            notes_s5
        )
        
        # Left Card: 4 Concrete Registry Classes
        self._add_card(s5, 0.8, 1.8, 5.7, 4.75, border_color=ACCENT_BLUE)
        tb_reg = s5.shapes.add_textbox(Inches(1.0), Inches(1.95), Inches(5.3), Inches(4.4))
        tf_reg = tb_reg.text_frame
        tf_reg.word_wrap = True
        
        p = tf_reg.paragraphs[0]
        p.text = "CORE STRATEGY REGISTRY (4 Concrete Classes)"
        p.font.name = FONT_MONO
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = ACCENT_CYAN
        
        strategies = [
            ("TrendFollowingStrategy", "Dual Exponential Moving Average (EMA) crossover with dynamic Average True Range (ATR) volatility trailing stop loss."),
            ("MeanReversionStrategy", "Bollinger Bands volatility envelopes with Relative Strength Index (RSI) multi-timeframe oscillator reversion triggers."),
            ("BreakoutStrategy", "Donchian Channel multi-bar price breakout with volume-spread expansion filtering and volatility expansion confirmation."),
            ("MomentumStrategy", "Moving Average Convergence Divergence (MACD) signal line crossover paired with Stochastic momentum divergence confirmation.")
        ]
        for name, desc in strategies:
            p_s = tf_reg.add_paragraph()
            p_s.space_before = Pt(8)
            p_s.text = f"• {name}"
            p_s.font.name = FONT_MONO
            p_s.font.size = Pt(11)
            p_s.font.bold = True
            p_s.font.color.rgb = STATUS_GREEN
            
            p_d = tf_reg.add_paragraph()
            p_d.space_before = Pt(2)
            p_d.text = desc
            p_d.font.name = FONT_BODY
            p_d.font.size = Pt(9.5)
            p_d.font.color.rgb = TEXT_LIGHT

        # Right Card: 9 API Catalogue Profiles + Decimal Math Invariant
        self._add_card(s5, 6.833, 1.8, 5.7, 4.75, border_color=STATUS_GREEN)
        tb_cat = s5.shapes.add_textbox(Inches(7.033), Inches(1.95), Inches(5.3), Inches(4.4))
        tf_cat = tb_cat.text_frame
        tf_cat.word_wrap = True
        
        p = tf_cat.paragraphs[0]
        p.text = "API CATALOGUE SPECIFICATION (9 Profiles)"
        p.font.name = FONT_MONO
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = STATUS_GREEN
        
        cat_items = [
            "1. Trend Following (EMA Crossover + ATR)",
            "2. Mean Reversion (Bollinger Bands + RSI)",
            "3. Breakout (Donchian Channel + Volume)",
            "4. Momentum (MACD + Stochastic)",
            "5. Carry Trade (Interest Differential Scoring)",
            "6. Volatility Breakout (Keltner Channels)",
            "7. Statistical Arbitrage (Cointegrated Pairs)",
            "8. News Event Momentum (Economic Calendar)",
            "9. Machine Learning Classifier (Feature Vectors)"
        ]
        for ci in cat_items:
            p_ci = tf_cat.add_paragraph()
            p_ci.space_before = Pt(2)
            p_ci.text = ci
            p_ci.font.name = FONT_BODY
            p_ci.font.size = Pt(9)
            p_ci.font.color.rgb = TEXT_LIGHT

        p_dec = tf_cat.add_paragraph()
        p_dec.space_before = Pt(8)
        p_dec.text = "ARBITRARY-PRECISION DECIMAL ARITHMETIC"
        p_dec.font.name = FONT_MONO
        p_dec.font.size = Pt(10)
        p_dec.font.bold = True
        p_dec.font.color.rgb = BADGE_PAPER
        
        p_dec_d = tf_cat.add_paragraph()
        p_dec_d.space_before = Pt(2)
        p_dec_d.text = "All account balances, lots, pip values, execution fills, and P&L metrics strictly use Python Decimal arithmetic to avoid binary floating-point rounding errors."
        p_dec_d.font.name = FONT_BODY
        p_dec_d.font.size = Pt(9)
        p_dec_d.font.color.rgb = TEXT_MUTED

        # -------------------------------------------------------------
        # SLIDE 6: Backtesting & Temporal Leakage Controls
        # -------------------------------------------------------------
        notes_s6 = """Backtesting integrity relies on LeakageGuard, which enforces temporal monotonicity at each step, preventing look-ahead contamination during sequential bar evaluation."""
        s6 = self._add_base_slide(
            6,
            "Backtesting & Temporal Leakage Controls — Mathematical Rigor",
            "Deterministic Historical Bar Traversal Protected by LeakageGuard Monotonicity Enforcement",
            notes_s6
        )
        
        b_cards = [
            ("CHRONOLOGICAL TRAVERSAL", "Sequential Bar Processing", [
                "DeterministicBacktestEngine steps historical bars in strict chronological sequence (t[0], t[1], ... t[N]).",
                "Zero future lookahead: indicators only compute over historical slices available at bar close.",
                "Simulates realistic bar-by-bar decision making as experienced in live paper execution."
            ], ACCENT_BLUE),
            ("LEAKAGEGUARD DEFENSE", "Temporal Monotonicity Enforcement", [
                "LeakageGuard.validate_slice() inspects every data window before indicator calculation.",
                "Enforces strict timestamp monotonicity: timestamp[i] <= timestamp[i+1].",
                "Architecturally prevents forward look-ahead bias and data leakage from contaminating backtest validity."
            ], STATUS_GREEN),
            ("DETERMINISTIC REPRODUCIBILITY", "Exact Cent-Level Equity Curve", [
                "Re-running backtests with identical inputs generates mathematically identical equity curves.",
                "No stochastic or random fills in core research mode; fully auditable research journal.",
                "Generates trade-by-trade logs, execution slippage tracking, and time-in-trade distributions."
            ], ACCENT_BLUE),
            ("PERFORMANCE ANALYTICS", "Institutional Risk & Return Metrics", [
                "Sharpe Ratio (Annualized excess return relative to standard deviation).",
                "Sortino Ratio (Downside deviation risk measurement).",
                "Maximum Drawdown (Peak-to-trough decline percentage and recovery duration).",
                "Profit Factor (Gross profit divided by gross loss across all trade fills)."
            ], STATUS_AMBER)
        ]
        
        for i, (btitle, bsub, bpts, bcol) in enumerate(b_cards):
            col = i % 2
            row = i // 2
            bx = 0.8 + col * (5.7 + 0.333)
            by = 1.8 + row * (2.3 + 0.15)
            self._add_card(s6, bx, by, 5.7, 2.3, border_color=bcol)
            
            tb = s6.shapes.add_textbox(Inches(bx + 0.15), Inches(by + 0.12), Inches(5.4), Inches(2.05))
            tf = tb.text_frame
            tf.word_wrap = True
            
            p_bt = tf.paragraphs[0]
            p_bt.text = btitle
            p_bt.font.name = FONT_MONO
            p_bt.font.size = Pt(10)
            p_bt.font.bold = True
            p_bt.font.color.rgb = bcol
            
            p_bs = tf.add_paragraph()
            p_bs.text = bsub
            p_bs.font.name = FONT_HEADING
            p_bs.font.size = Pt(12)
            p_bs.font.bold = True
            p_bs.font.color.rgb = TEXT_LIGHT
            
            for pt in bpts:
                p_pt = tf.add_paragraph()
                p_pt.space_before = Pt(3)
                p_pt.text = f"• {pt}"
                p_pt.font.name = FONT_BODY
                p_pt.font.size = Pt(9)
                p_pt.font.color.rgb = TEXT_MUTED

        # -------------------------------------------------------------
        # SLIDE 7: Optimization & Walk-Forward Analysis
        # -------------------------------------------------------------
        notes_s7 = """To combat curve-fitting, ORION provides rolling Walk-Forward Analysis. By comparing optimized parameter performance against out-of-sample data across multiple windows, the system calculates Walk-Forward Efficiency."""
        s7 = self._add_base_slide(
            7,
            "Optimization & Walk-Forward Analysis — Detecting Curve-Fitting",
            "Multi-Parameter Grid Search & Rolling In-Sample / Out-Of-Sample Walk-Forward Efficiency (WFE)",
            notes_s7
        )
        
        # Left Card: Grid Search & Parameter Space
        self._add_card(s7, 0.8, 1.8, 5.7, 4.75, border_color=ACCENT_BLUE)
        tb_opt = s7.shapes.add_textbox(Inches(1.0), Inches(1.95), Inches(5.3), Inches(4.4))
        tf_opt = tb_opt.text_frame
        tf_opt.word_wrap = True
        
        p = tf_opt.paragraphs[0]
        p.text = "PARAMETER SPACE OPTIMIZATION ENGINE"
        p.font.name = FONT_MONO
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = ACCENT_CYAN
        
        opt_points = [
            ("Multi-Dimensional Grid Search:", "Explores user-defined parameter permutations (e.g. fast EMA 8-21, slow EMA 21-55, ATR multiplier 1.5-3.0)."),
            ("Metric Ranking Objective:", "Candidates ranked automatically by user-selected target function (Sharpe ratio, Sortino ratio, Profit Factor, or Total Return)."),
            ("Sensitivity Surface Mapping:", "Evaluates parameter neighbors to ensure optimal regions represent stable plateaus rather than isolated overfitted spikes."),
            ("REST API Trigger:", "POST /api/v1/optimization/run asynchronous job with status polling and cancel support.")
        ]
        for opt_t, opt_d in opt_points:
            p_ot = tf_opt.add_paragraph()
            p_ot.space_before = Pt(8)
            p_ot.text = f"• {opt_t} "
            p_ot.font.name = FONT_BODY
            p_ot.font.size = Pt(10)
            p_ot.font.bold = True
            p_ot.font.color.rgb = STATUS_GREEN
            run = p_ot.add_run()
            run.text = opt_d
            run.font.bold = False
            run.font.color.rgb = TEXT_LIGHT

        # Right Card: Walk-Forward Analysis
        self._add_card(s7, 6.833, 1.8, 5.7, 4.75, border_color=STATUS_GREEN)
        tb_wfa = s7.shapes.add_textbox(Inches(7.033), Inches(1.95), Inches(5.3), Inches(4.4))
        tf_wfa = tb_wfa.text_frame
        tf_wfa.word_wrap = True
        
        p = tf_wfa.paragraphs[0]
        p.text = "ROLLING WALK-FORWARD ANALYSIS (WFA)"
        p.font.name = FONT_MONO
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = STATUS_GREEN
        
        wfa_points = [
            ("Rolling Slices:", "Partitions historical candle series into overlapping In-Sample (IS) training windows and subsequent Out-Of-Sample (OOS) testing windows."),
            ("Walk-Forward Efficiency (WFE):", "Computes WFE = (Annualized OOS Return / Annualized IS Return). Quantifies performance retention on unseen future bars."),
            ("Robustness Classification:", "Verdicts categorized as ROBUST (WFE ≥ 0.60), MODERATE (0.40 ≤ WFE < 0.60), or OVERFITTED (WFE < 0.40)."),
            ("Quality Gate Prerequisite:", "Only parameter candidates achieving verified WFE scores are eligible to pass deployment quality gates.")
        ]
        for wfa_t, wfa_d in wfa_points:
            p_wt = tf_wfa.add_paragraph()
            p_wt.space_before = Pt(8)
            p_wt.text = f"• {wfa_t} "
            p_wt.font.name = FONT_BODY
            p_wt.font.size = Pt(10)
            p_wt.font.bold = True
            p_wt.font.color.rgb = ACCENT_CYAN
            run = p_wt.add_run()
            run.text = wfa_d
            run.font.bold = False
            run.font.color.rgb = TEXT_LIGHT

        # -------------------------------------------------------------
        # SLIDE 8: Strategy Deployment Lifecycle
        # -------------------------------------------------------------
        notes_s8 = """The deployment pipeline enforces institutional governance. Strategies must pass programmatic quality gates before entering incubation, and the pipeline strictly terminates at paper validation with zero live brokerage execution pathways."""
        s8 = self._add_base_slide(
            8,
            "Strategy Deployment Lifecycle — Governance & Quality Gates",
            "Fail-Closed State Machine: Automated Evaluation Hurdles Leading Strictly to Paper Incubation",
            notes_s8
        )
        
        # State Machine Path Diagram Card
        self._add_card(s8, 0.8, 1.8, 11.733, 2.1, border_color=ACCENT_BLUE)
        tb_sm = s8.shapes.add_textbox(Inches(1.0), Inches(1.95), Inches(11.333), Inches(1.8))
        tf_sm = tb_sm.text_frame
        tf_sm.word_wrap = True
        
        p = tf_sm.paragraphs[0]
        p.text = "FAIL-CLOSED STATE MACHINE TRANSITIONS"
        p.font.name = FONT_MONO
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = ACCENT_CYAN
        
        p_path = tf_sm.add_paragraph()
        p_path.space_before = Pt(6)
        p_path.text = "PENDING_GATES  ──[Gates Eval]──>  GATES_PASSED  ──[Incubate]──>  INCUBATING  ──[Validate]──>  PAPER_VALIDATED  ──[Promote]──>  PROMOTION_CANDIDATE"
        p_path.font.name = FONT_MONO
        p_path.font.size = Pt(10.5)
        p_path.font.bold = True
        p_path.font.color.rgb = STATUS_GREEN
        
        p_fail = tf_sm.add_paragraph()
        p_fail.space_before = Pt(8)
        p_fail.text = "Terminal / Failure Transitions:  GATES_FAILED (failed hurdles)  │  INCUBATION_FAILED (drawdown breach)  │  CANCELLED  │  SUSPENDED"
        p_fail.font.name = FONT_MONO
        p_fail.font.size = Pt(9.5)
        p_fail.font.color.rgb = STATUS_ROSE

        # Two Lower Cards: Quality Gates & Separation of Duties
        self._add_card(s8, 0.8, 4.1, 5.7, 2.45, border_color=STATUS_GREEN)
        tb_qg = s8.shapes.add_textbox(Inches(1.0), Inches(4.2), Inches(5.3), Inches(2.2))
        tf_qg = tb_qg.text_frame
        tf_qg.word_wrap = True
        
        p = tf_qg.paragraphs[0]
        p.text = "AUTOMATED QUALITY GATES"
        p.font.name = FONT_MONO
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = STATUS_GREEN
        
        qg_rules = [
            "1. Walk-Forward Efficiency (WFE ≥ 0.50): Rejects algorithms demonstrating significant out-of-sample degradation.",
            "2. Drawdown Ceiling (Max DD ≤ 15%): Restricts risk exposure across all evaluated historical testing windows.",
            "3. Parameter Stability Surface: Enforces parameter resilience against neighboring parameter variations."
        ]
        for qr in qg_rules:
            p_qr = tf_qg.add_paragraph()
            p_qr.space_before = Pt(3)
            p_qr.text = qr
            p_qr.font.name = FONT_BODY
            p_qr.font.size = Pt(9)
            p_qr.font.color.rgb = TEXT_LIGHT

        self._add_card(s8, 6.833, 4.1, 5.7, 2.45, border_color=BADGE_PAPER)
        tb_gov = s8.shapes.add_textbox(Inches(7.033), Inches(4.2), Inches(5.3), Inches(2.2))
        tf_gov = tb_gov.text_frame
        tf_gov.word_wrap = True
        
        p = tf_gov.paragraphs[0]
        p.text = "ORGANIZATIONAL SEPARATION OF DUTIES"
        p.font.name = FONT_MONO
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = BADGE_PAPER
        
        gov_rules = [
            "• Dual-Role Authorization: Traders formulate and submit strategy candidates; Risk Officers or Portfolio Managers review and promote.",
            "• Paper Execution Invariant: The deployment pipeline strictly terminates at paper validation; no live real-money execution transitions exist.",
            "• Immutable Audit Recording: All quality gate evaluations and lifecycle state transitions are logged in AuditLogModel."
        ]
        for gr in gov_rules:
            p_gr = tf_gov.add_paragraph()
            p_gr.space_before = Pt(3)
            p_gr.text = gr
            p_gr.font.name = FONT_BODY
            p_gr.font.size = Pt(9)
            p_gr.font.color.rgb = TEXT_LIGHT

        # -------------------------------------------------------------
        # SLIDE 9: Paper Trading & Risk Management
        # -------------------------------------------------------------
        notes_s9 = """The demonstrated execution path uses simulated paper capital only, with $0.00 live financial capital at risk. Pre-trade risk controls dynamically evaluate margin and leverage before any order is accepted."""
        s9 = self._add_base_slide(
            9,
            "Paper Trading & Risk Management — Simulated Matching Engine",
            "Pre-Trade Risk Checks, Realistic Spread & Slippage Modeling, and Permanent Paper Stamping",
            notes_s9
        )
        
        # Left Card: Matching Engine
        self._add_card(s9, 0.8, 1.8, 5.7, 4.75, border_color=BADGE_PAPER)
        tb_pe = s9.shapes.add_textbox(Inches(1.0), Inches(1.95), Inches(5.3), Inches(4.4))
        tf_pe = tb_pe.text_frame
        tf_pe.word_wrap = True
        
        p = tf_pe.paragraphs[0]
        p.text = "PAPER EXECUTION ADAPTER (PaperExecutionAdapter)"
        p.font.name = FONT_MONO
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = BADGE_PAPER
        
        pe_points = [
            ("Order Types Supported:", "Market, Limit, Stop, and dynamic Trailing Stop orders."),
            ("Realistic Transaction Costs:", "Models realistic bid-ask spread and configurable adverse execution slippage."),
            ("Position Netting & FIFO:", "Simulates position aggregation, netting, and realized P&L accounting upon exit."),
            ("Simulated Mark-to-Market:", "Real-time unrealized P&L calculated on-demand against current simulated market rates."),
            ("Permanent Stamping:", "Every database order, fill, and position is permanently stamped with is_paper=True.")
        ]
        for pet, ped in pe_points:
            p_pt = tf_pe.add_paragraph()
            p_pt.space_before = Pt(7)
            p_pt.text = f"• {pet} "
            p_pt.font.name = FONT_BODY
            p_pt.font.size = Pt(9.5)
            p_pt.font.bold = True
            p_pt.font.color.rgb = ACCENT_CYAN
            run = p_pt.add_run()
            run.text = ped
            run.font.bold = False
            run.font.color.rgb = TEXT_LIGHT

        # Right Card: Pre-Trade Risk Engine
        self._add_card(s9, 6.833, 1.8, 5.7, 4.75, border_color=STATUS_GREEN)
        tb_risk = s9.shapes.add_textbox(Inches(7.033), Inches(1.95), Inches(5.3), Inches(4.4))
        tf_risk = tb_risk.text_frame
        tf_risk.word_wrap = True
        
        p = tf_risk.paragraphs[0]
        p.text = "SYNCHRONOUS PRE-TRADE RISK SERVICE (RiskService)"
        p.font.name = FONT_MONO
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = STATUS_GREEN
        
        risk_points = [
            ("Leverage Ceiling Enforcement:", "Restricts simulated leverage exposure (default 1:100 cap; customizable by tier)."),
            ("Available Margin Verification:", "Calculates required initial margin; rejects orders exceeding simulated available balance."),
            ("Maximum Position Sizing:", "Restricts maximum single-order and aggregate symbol volume lots."),
            ("Daily Account Drawdown Cap:", "Monitors cumulative intraday loss thresholds; halts trading if limit breached."),
            ("Zero Live Financial Risk:", "Orders route strictly to internal simulation. Live financial capital at risk is exactly $0.00.")
        ]
        for rt, rd in risk_points:
            p_rt = tf_risk.add_paragraph()
            p_rt.space_before = Pt(7)
            p_rt.text = f"• {rt} "
            p_rt.font.name = FONT_BODY
            p_rt.font.size = Pt(9.5)
            p_rt.font.bold = True
            p_rt.font.color.rgb = STATUS_GREEN
            run = p_rt.add_run()
            run.text = rd
            run.font.bold = False
            run.font.color.rgb = TEXT_LIGHT

        # -------------------------------------------------------------
        # SLIDE 10: Market Data & Broker Adapter Architecture
        # -------------------------------------------------------------
        notes_s10 = """ORION runs self-contained by default using deterministic synthetic market data. Integration adapters for external providers like TwelveData and OANDA Practice are fully implemented and activate when the operator supplies credentials."""
        s10 = self._add_base_slide(
            10,
            "Market Data & Broker Adapter Architecture — Boundaries",
            "Decoupled Providers: Default Offline Mock, External TwelveData Feed & OANDA Practice Sandbox",
            notes_s10
        )
        
        adapters = [
            ("MockMarketDataProvider", "SIMULATED / INTERNAL", [
                "Default provider enabling self-contained, offline operation without external API keys.",
                "Generates deterministic synthetic currency bars, spreads, and tick fluctuations.",
                "Enables automated CI/CD test harness execution with deterministic reproducible data."
            ], BADGE_PAPER),
            ("TwelveDataMarketDataProvider", "EXTERNAL PROVIDER", [
                "Implemented REST market data client designed to ingest real-time quotes.",
                "Requires operator-provisioned TWELVE_DATA_API_KEY environment variable.",
                "Decoupled through MarketDataProvider protocol interface; pluggable with any provider."
            ], ACCENT_BLUE),
            ("OandaBrokerAdapter", "EXTERNAL PRACTICE SANDBOX", [
                "External sandbox execution adapter connecting to OANDA Practice environment.",
                "Operates with OANDA_ENVIRONMENT=practice for testing API communication protocols.",
                "Strictly restricted to sandbox testing; live production trading is not enabled."
            ], ACCENT_CYAN),
            ("AutonomousWorkerCoordinator", "DISABLED BY DESIGN", [
                "Autonomous strategy execution worker implemented in source code.",
                "Manual execution trigger available via POST /api/v1/worker/run-once endpoint.",
                "Background loop is disabled by default in cloud deployments (WORKER_ENABLED=false)."
            ], STATUS_ROSE)
        ]
        
        for i, (aname, aclass, apts, acol) in enumerate(adapters):
            col = i % 2
            row = i // 2
            ax = 0.8 + col * (5.7 + 0.333)
            ay = 1.8 + row * (2.3 + 0.15)
            self._add_card(s10, ax, ay, 5.7, 2.3, border_color=acol)
            
            tb = s10.shapes.add_textbox(Inches(ax + 0.15), Inches(ay + 0.12), Inches(5.4), Inches(2.05))
            tf = tb.text_frame
            tf.word_wrap = True
            
            p_an = tf.paragraphs[0]
            p_an.text = aname
            p_an.font.name = FONT_MONO
            p_an.font.size = Pt(11)
            p_an.font.bold = True
            p_an.font.color.rgb = TEXT_LIGHT
            
            p_ac = tf.add_paragraph()
            p_ac.text = f"Classification: [{aclass}]"
            p_ac.font.name = FONT_MONO
            p_ac.font.size = Pt(9)
            p_ac.font.bold = True
            p_ac.font.color.rgb = acol
            
            for pt in apts:
                p_pt = tf.add_paragraph()
                p_pt.space_before = Pt(3)
                p_pt.text = f"• {pt}"
                p_pt.font.name = FONT_BODY
                p_pt.font.size = Pt(9)
                p_pt.font.color.rgb = TEXT_MUTED

        # -------------------------------------------------------------
        # SLIDE 11: Multi-Tenancy & Organization-Level RBAC
        # -------------------------------------------------------------
        notes_s11 = """Multi-tenancy is enforced at the database query level. The platform implements seven organization-level RBAC roles governing forty-one granular permissions across all operational endpoints."""
        s11 = self._add_base_slide(
            11,
            "Multi-Tenancy & Organization-Level RBAC — Access Governance",
            "Relational Tenant Isolation via TenantContext & 7 Distinct RBAC Roles Governing 41 Permissions",
            notes_s11
        )
        
        # Left Card: TenantContext & Isolation
        self._add_card(s11, 0.8, 1.8, 4.5, 4.75, border_color=ACCENT_BLUE)
        tb_tn = s11.shapes.add_textbox(Inches(1.0), Inches(1.95), Inches(4.1), Inches(4.4))
        tf_tn = tb_tn.text_frame
        tf_tn.word_wrap = True
        
        p = tf_tn.paragraphs[0]
        p.text = "TENANT ISOLATION ARCHITECTURE"
        p.font.name = FONT_MONO
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = ACCENT_CYAN
        
        tn_points = [
            ("Relational Bounding:", "Every account, order, fill, position, strategy, and deployment record binds to OrganizationModel."),
            ("Dependency-Injected Context:", "TenantContext dependency automatically extracts organization_id from authenticated JWT session."),
            ("Query-Level Filtering:", "Database queries enforce WHERE organization_id = :org_id, mitigating cross-tenant data leakage."),
            ("Self-Service Registration:", "New registrations provision fresh isolated tenants with dedicated paper accounts.")
        ]
        for tt, td in tn_points:
            p_tt = tf_tn.add_paragraph()
            p_tt.space_before = Pt(7)
            p_tt.text = f"• {tt} "
            p_tt.font.name = FONT_BODY
            p_tt.font.size = Pt(9.5)
            p_tt.font.bold = True
            p_tt.font.color.rgb = STATUS_GREEN
            run = p_tt.add_run()
            run.text = td
            run.font.bold = False
            run.font.color.rgb = TEXT_LIGHT

        # Right Card: 7 RBAC Roles & 41 Permissions
        self._add_card(s11, 5.6, 1.8, 6.933, 4.75, border_color=STATUS_GREEN)
        tb_rbac = s11.shapes.add_textbox(Inches(5.8), Inches(1.95), Inches(6.533), Inches(4.4))
        tf_rbac = tb_rbac.text_frame
        tf_rbac.word_wrap = True
        
        p = tf_rbac.paragraphs[0]
        p.text = "7 ORGANIZATIONAL RBAC ROLES & 41 PERMISSIONS"
        p.font.name = FONT_MONO
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = STATUS_GREEN
        
        roles_desc = [
            ("OWNER", "Full tenant administrative control, subscription billing management, and user deletion."),
            ("ADMINISTRATOR", "User invitation, role assignment, and organization configuration management."),
            ("PORTFOLIO_MANAGER", "Multi-account oversight, strategy allocation, and promotion review authorization."),
            ("RISK_OFFICER", "Pre-trade risk limit adjustment, drawdown threshold oversight, and strategy halt controls."),
            ("TRADER", "Order creation, trade execution, strategy parameter formulation, and backtesting."),
            ("AUDITOR", "Read-only access to immutable audit trails, trade logs, and compliance records."),
            ("VIEWER", "Read-only access to dashboard portfolio metrics and performance analytics.")
        ]
        for rname, rdesc in roles_desc:
            p_r = tf_rbac.add_paragraph()
            p_r.space_before = Pt(4)
            p_r.text = f"{rname}: "
            p_r.font.name = FONT_MONO
            p_r.font.size = Pt(9.5)
            p_r.font.bold = True
            p_r.font.color.rgb = ACCENT_CYAN
            run = p_r.add_run()
            run.text = rdesc
            run.font.name = FONT_BODY
            run.font.size = Pt(9)
            run.font.bold = False
            run.font.color.rgb = TEXT_LIGHT

        p_perm = tf_rbac.add_paragraph()
        p_perm.space_before = Pt(8)
        p_perm.text = "41 Granular Permissions across 14 Functional Domains:"
        p_perm.font.name = FONT_BODY
        p_perm.font.size = Pt(9)
        p_perm.font.bold = True
        p_perm.font.color.rgb = BADGE_PAPER
        
        p_pdesc = tf_rbac.add_paragraph()
        p_pdesc.text = "Governs orders:create, positions:close, research:backtest, optimization:run, deployments:promote, audit:read, billing:manage, org:invite, and 33 additional programmatic actions."
        p_pdesc.font.name = FONT_BODY
        p_pdesc.font.size = Pt(8.5)
        p_pdesc.font.color.rgb = TEXT_MUTED

        # -------------------------------------------------------------
        # SLIDE 12: Security, Auditability & Operations
        # -------------------------------------------------------------
        notes_s12 = """Security controls include strict HTTP headers, rate limiting, and an immutable audit trail capturing platform actions with structured contextual JSON details."""
        s12 = self._add_base_slide(
            12,
            "Security, Auditability & Operations — Enterprise Hardening",
            "Perimeter Defense, HTTP Security Headers, Immutable Audit Trail & Health Probes",
            notes_s12
        )
        
        sec_cards = [
            ("AUTHENTICATION & PERIMETER", "Stateless Tokens & Password Hashing", [
                "Stateless JWT HS256 authentication with configurable token expiration.",
                "Bcrypt password hashing (work factor 12) with salted storage in UserModel.",
                "IP-based and tenant-based rate limiting via Redis with in-memory degraded fallback.",
                "Strict CORS middleware with configurable origin allowlists for SPA domain binding."
            ], ACCENT_BLUE),
            ("HTTP SECURITY HEADERS", "Defensive Browser Policies", [
                "Strict-Transport-Security (HSTS): max-age=31536000; includeSubDomains.",
                "Content-Security-Policy (CSP): Restricts external script and style execution.",
                "X-Frame-Options: DENY (architecturally prevents clickjacking attacks).",
                "X-Content-Type-Options: nosniff & X-XSS-Protection: 1; mode=block."
            ], STATUS_GREEN),
            ("IMMUTABLE AUDIT LOGGING", "Structured Event Trail (AuditLogModel)", [
                "Records key operational actions: ORDER_CREATE, USER_REGISTER, STRATEGY_DEPLOY.",
                "Captures acting user ID, organization ID, component tag, and exact UTC timestamp.",
                "Stores contextual metadata in structured JSON details column for compliance review.",
                "Audit trail queryable via dedicated Auditor role interface (/api/v1/audit)."
            ], ACCENT_BLUE),
            ("OPERATIONAL OBSERVABILITY", "Health Probes & Metrics Export", [
                "/health/live: Immediate liveness probe for load balancer orchestration.",
                "/health/ready: Deep readiness probe verifying PostgreSQL and Redis connections.",
                "/metrics: Prometheus metrics endpoint exporting request counts and latencies.",
                "Structured JSON application logging with correlation ID request tracing."
            ], STATUS_AMBER)
        ]
        
        for i, (stitle, ssub, spts, scol) in enumerate(sec_cards):
            col = i % 2
            row = i // 2
            sx = 0.8 + col * (5.7 + 0.333)
            sy = 1.8 + row * (2.3 + 0.15)
            self._add_card(s12, sx, sy, 5.7, 2.3, border_color=scol)
            
            tb = s12.shapes.add_textbox(Inches(sx + 0.15), Inches(sy + 0.12), Inches(5.4), Inches(2.05))
            tf = tb.text_frame
            tf.word_wrap = True
            
            p_st = tf.paragraphs[0]
            p_st.text = stitle
            p_st.font.name = FONT_MONO
            p_st.font.size = Pt(10)
            p_st.font.bold = True
            p_st.font.color.rgb = scol
            
            p_ss = tf.add_paragraph()
            p_ss.text = ssub
            p_ss.font.name = FONT_HEADING
            p_ss.font.size = Pt(12)
            p_ss.font.bold = True
            p_ss.font.color.rgb = TEXT_LIGHT
            
            for pt in spts:
                p_pt = tf.add_paragraph()
                p_pt.space_before = Pt(3)
                p_pt.text = f"• {pt}"
                p_pt.font.name = FONT_BODY
                p_pt.font.size = Pt(9)
                p_pt.font.color.rgb = TEXT_MUTED

        # -------------------------------------------------------------
        # SLIDE 13: Deployment, Backup & Recovery
        # -------------------------------------------------------------
        notes_s13 = """ORION deploys declaratively via Render blueprint for an approximately fourteen dollar monthly configuration estimate. In isolated disaster recovery testing, physical database restoration across twenty-nine tables was benchmarked in roughly seven seconds."""
        s13 = self._add_base_slide(
            13,
            "Deployment, Backup & Recovery — PaaS Blueprint & DR Evidence",
            "Declarative Render PaaS Infrastructure-as-Code & Benchmark Disaster Recovery Verification",
            notes_s13
        )
        
        # Left Card: PaaS Blueprint
        self._add_card(s13, 0.8, 1.8, 5.7, 4.75, border_color=ACCENT_BLUE)
        tb_paas = s13.shapes.add_textbox(Inches(1.0), Inches(1.95), Inches(5.3), Inches(4.4))
        tf_paas = tb_paas.text_frame
        tf_paas.word_wrap = True
        
        p = tf_paas.paragraphs[0]
        p.text = "DECLARATIVE PAAS BLUEPRINT (render.yaml)"
        p.font.name = FONT_MONO
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = ACCENT_CYAN
        
        paas_points = [
            ("Infrastructure Topology:", "4-tier architecture: FastAPI web service ('starter'), React static SPA ('free'), PostgreSQL 16 ('basic-1gb'), and Redis 7 ('free')."),
            ("Base Hosting Cost Estimate:", "Baseline cloud hosting configured on Render for approximately $14/month ($7 DB + $7 API under published 2026 pricing)."),
            ("Decoupled Migrations:", "Executed via preDeployCommand (python scripts/deploy/migrate.py) before application boot, preventing dirty schema starts."),
            ("Zero Secrets in Repository:", "All database credentials, JWT keys, and API tokens injected dynamically via environment variables.")
        ]
        for pt, pd in paas_points:
            p_pt = tf_paas.add_paragraph()
            p_pt.space_before = Pt(7)
            p_pt.text = f"• {pt} "
            p_pt.font.name = FONT_BODY
            p_pt.font.size = Pt(9.5)
            p_pt.font.bold = True
            p_pt.font.color.rgb = STATUS_GREEN
            run = p_pt.add_run()
            run.text = pd
            run.font.bold = False
            run.font.color.rgb = TEXT_LIGHT

        # Right Card: Disaster Recovery & Alembic Evolution
        self._add_card(s13, 6.833, 1.8, 5.7, 4.75, border_color=STATUS_GREEN)
        tb_dr = s13.shapes.add_textbox(Inches(7.033), Inches(1.95), Inches(5.3), Inches(4.4))
        tf_dr = tb_dr.text_frame
        tf_dr.word_wrap = True
        
        p = tf_dr.paragraphs[0]
        p.text = "DISASTER RECOVERY BENCHMARK & MIGRATIONS"
        p.font.name = FONT_MONO
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = STATUS_GREEN
        
        dr_points = [
            ("Historical Restore Benchmark:", "Documented test benchmark demonstrating physical schema and data restoration across 29 tables in ~7.2 seconds in an isolated testing container."),
            ("Tested DR Runbook:", "Complete restoration procedures documented in docs/acquisition/08-BACKUP-RESTORE-RUNBOOK.md."),
            ("Linear Schema Evolution:", "15 linear Alembic migration revisions maintaining deterministic database upgrades and rollbacks."),
            ("Automated Verification Scripts:", "backup/restore-database.sh automated shell script verified against local PostgreSQL instances.")
        ]
        for dt, dd in dr_points:
            p_dt = tf_dr.add_paragraph()
            p_dt.space_before = Pt(7)
            p_dt.text = f"• {dt} "
            p_dt.font.name = FONT_BODY
            p_dt.font.size = Pt(9.5)
            p_dt.font.bold = True
            p_dt.font.color.rgb = ACCENT_CYAN
            run = p_dt.add_run()
            run.text = dd
            run.font.bold = False
            run.font.color.rgb = TEXT_LIGHT

        # -------------------------------------------------------------
        # SLIDE 14: Technical Asset / IP Inventory
        # -------------------------------------------------------------
        notes_s14 = """The technical asset includes clean Git commit history, a documented historical baseline of over four thousand two hundred automated tests, and eighteen comprehensive closing dossiers covering every area of due diligence."""
        s14 = self._add_base_slide(
            14,
            "Technical Asset & IP Inventory — Codebase Deliverables",
            "Documented Historical Baseline of 4,260 Automated Tests, 99.4% Coverage & 18 Due Diligence Dossiers",
            notes_s14
        )
        
        # 6 Category Cards Grid
        ip_cards = [
            ("SOURCE CODE ASSET", "Proposed Transferable Codebase", [
                "Full Git repository with unbroken commit provenance.",
                "Python 3.11+ FastAPI backend (24 modular routers).",
                "React 18 + Vite frontend SPA (20 client routes).",
                "21 internal domain packages under libraries/domain/."
            ], ACCENT_BLUE),
            ("TEST HARNESS BASELINE", "Documented Historical Evidence", [
                "4,260 automated tests across 103 test suites.",
                "99.4% test coverage across core domain modules.",
                "Deterministic backtesting and leakage regression suites.",
                "Continuous execution via standard pytest commands."
            ], STATUS_GREEN),
            ("DATABASE ARCHITECTURE", "PostgreSQL 16 & Alembic", [
                "29 relational tables managing accounts, orders & risks.",
                "15 linear Alembic migration revisions.",
                "SQLAlchemy 2.0 Async declarative ORM models.",
                "Tenant isolation enforced on all entity relations."
            ], ACCENT_CYAN),
            ("DUE DILIGENCE DATA ROOM", "18 Comprehensive Dossiers", [
                "Tier 1: Executive & Architectural Orientation (01-03).",
                "Tier 2: Technical Deep-Dive & Harness Audit (04-10).",
                "Tier 3: Operational & Dependency Audit (11-14).",
                "Tier 4: Transaction, IP & Account Transfer (15-18)."
            ], STATUS_AMBER),
            ("OPEN-SOURCE COMPLIANCE", "Commercially Permissive SBOM", [
                "Permissive open-source licensing: MIT, Apache 2.0, BSD-3-Clause.",
                "Zero copyleft (GPL / AGPL) code contamination.",
                "Complete Software Bill of Materials (12-DEPENDENCY-SBOM.md).",
                "Automated dependency vulnerability scan history."
            ], STATUS_GREEN),
            ("INFRASTRUCTURE BLUEPRINTS", "Ready for Cloud Deployment", [
                "render.yaml declarative 4-tier infrastructure blueprint.",
                "Docker container configurations for API and frontend.",
                "Automated preDeployCommand database migration script.",
                "~$14/month baseline configuration hosting estimate."
            ], ACCENT_BLUE)
        ]
        
        for i, (ititle, isub, ipts, icol) in enumerate(ip_cards):
            col = i % 3
            row = i // 3
            ix = 0.8 + col * (3.75 + 0.24)
            iy = 1.8 + row * (2.3 + 0.15)
            self._add_card(s14, ix, iy, 3.75, 2.3, border_color=icol)
            
            tb = s14.shapes.add_textbox(Inches(ix + 0.12), Inches(iy + 0.1), Inches(3.51), Inches(2.1))
            tf = tb.text_frame
            tf.word_wrap = True
            
            p_it = tf.paragraphs[0]
            p_it.text = ititle
            p_it.font.name = FONT_MONO
            p_it.font.size = Pt(9.5)
            p_it.font.bold = True
            p_it.font.color.rgb = icol
            
            p_is = tf.add_paragraph()
            p_is.text = isub
            p_is.font.name = FONT_HEADING
            p_is.font.size = Pt(11)
            p_is.font.bold = True
            p_is.font.color.rgb = TEXT_LIGHT
            
            for pt in ipts:
                p_pt = tf.add_paragraph()
                p_pt.space_before = Pt(3)
                p_pt.text = f"• {pt}"
                p_pt.font.name = FONT_BODY
                p_pt.font.size = Pt(8.5)
                p_pt.font.color.rgb = TEXT_MUTED

        # -------------------------------------------------------------
        # SLIDE 15: Acquisition Scope, Handover & Known Limitations
        # -------------------------------------------------------------
        notes_s15 = """The proposed acquisition scope includes complete source code and IP deliverables. Third-party vendor services like Render and Stripe are provisioned directly by the buyer under their corporate identity, ensuring clean vendor separation."""
        s15 = self._add_base_slide(
            15,
            "Acquisition Scope, Handover & Known Limitations — Transaction Truth",
            "Clear Delineation of Proprietary Deliverables, Buyer Obligations, and Engineering Boundaries",
            notes_s15
        )
        
        # Left Card: Transferable IP vs Buyer Provisioned
        self._add_card(s15, 0.8, 1.8, 5.7, 4.75, border_color=ACCENT_BLUE)
        tb_tx = s15.shapes.add_textbox(Inches(1.0), Inches(1.95), Inches(5.3), Inches(4.4))
        tf_tx = tb_tx.text_frame
        tf_tx.word_wrap = True
        
        p = tf_tx.paragraphs[0]
        p.text = "PROPOSED TRANSACTION SCOPE & HANDOVER"
        p.font.name = FONT_MONO
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = ACCENT_CYAN
        
        tx_points = [
            ("Proposed Transferable Software Scope:", "Complete Git source repository, test suites, database models, and 18 closing dossiers, subject to executed agreements."),
            ("Independent Account Provisioning Path:", "Third-party vendor account transferability is not established in the repository. To eliminate friction, the buyer independently provisions their own accounts:"),
            ("• Cloud Hosting:", "Buyer creates their own Render account (~$14/mo baseline hosting config estimate)."),
            ("• Payment Gateway:", "Buyer provisions their own Stripe merchant account."),
            ("• Market Data:", "Buyer provisions TwelveData API key for live quotes."),
            ("• Broker Sandbox:", "Buyer registers OANDA Practice credentials."),
            ("• Domain & DNS:", "Buyer purchases proprietary domain & TLS certificates.")
        ]
        for txt, txd in tx_points:
            p_tt = tf_tx.add_paragraph()
            p_tt.space_before = Pt(4)
            p_tt.text = f"{txt} "
            p_tt.font.name = FONT_BODY
            p_tt.font.size = Pt(9)
            p_tt.font.bold = True
            p_tt.font.color.rgb = STATUS_GREEN
            run = p_tt.add_run()
            run.text = txd
            run.font.bold = False
            run.font.color.rgb = TEXT_LIGHT

        # Right Card: Transparent Engineering Boundaries & Commercial Status
        self._add_card(s15, 6.833, 1.8, 5.7, 4.75, border_color=BADGE_PAPER)
        tb_lim = s15.shapes.add_textbox(Inches(7.033), Inches(1.95), Inches(5.3), Inches(4.4))
        tf_lim = tb_lim.text_frame
        tf_lim.word_wrap = True
        
        p = tf_lim.paragraphs[0]
        p.text = "TRANSPARENT ENGINEERING BOUNDARIES & COMMERCIAL STATUS"
        p.font.name = FONT_MONO
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = BADGE_PAPER
        
        lim_points = [
            ("Commercial Revenue Status:", "Pre-revenue technology asset. Paying customers, active subscribers, and recurring revenue are NOT ESTABLISHED IN REPOSITORY."),
            ("Stateless REST Polling:", "Client updates via on-demand HTTP REST polling; continuous WebSocket push endpoints are not implemented."),
            ("Single-Process Worker:", "Autonomous worker designed as single-process event loop; horizontal worker scaling requires future Celery/Redis queue adoption."),
            ("Paper Trading Scope:", "Software strictly terminates at paper validation. Commercial broker deployment requires buyer regulatory licensing."),
            ("Strict Liability & Risk:", "Platform operates with exactly $0.00 live financial capital at risk under all demonstrated execution paths.")
        ]
        for lt, ld in lim_points:
            p_lt = tf_lim.add_paragraph()
            p_lt.space_before = Pt(6)
            p_lt.text = f"• {lt} "
            p_lt.font.name = FONT_BODY
            p_lt.font.size = Pt(9)
            p_lt.font.bold = True
            p_lt.font.color.rgb = BADGE_PAPER
            run = p_lt.add_run()
            run.text = ld
            run.font.bold = False
            run.font.color.rgb = TEXT_LIGHT

        # Save presentation
        self.prs.save(str(OUTPUT_FILE))
        print(f"[OK] Generated 15-slide presentation: {OUTPUT_FILE} ({OUTPUT_FILE.stat().st_size} bytes)")


def main():
    print("Building Project ORION 15-Slide Buyer Presentation Deck...")
    builder = OrionDeckBuilder()
    builder.build_deck()
    print("Build complete.")

if __name__ == "__main__":
    main()
