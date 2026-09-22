import React from 'react';
import { Link } from 'react-router-dom';
import {
  ShieldCheck,
  ShieldAlert,
  ArrowRight,
  BarChart3,
  Layers,
  Lock,
  GitBranch,
  Activity,
  CheckCircle2,
  Database,
  Sliders,
  HelpCircle,
} from 'lucide-react';
import { PublicHeader } from '../components/layout/PublicHeader';
import { PublicFooter } from '../components/layout/PublicFooter';

export const MarketingHomePage: React.FC = () => {
  const researchFeatures = [
    {
      icon: <Database className="w-5 h-5 text-sky-400" />,
      title: 'Multi-Timeframe Market Data',
      description:
        'Streamlined ingestion of major and liquid forex pairs across 1-minute to daily intervals with bid/ask spread telemetry and historical candle replay.',
    },
    {
      icon: <Sliders className="w-5 h-5 text-sky-400" />,
      title: 'Walk-Forward Optimization',
      description:
        'Rigorous parameter sensitivity analysis and walk-forward verification designed to combat overfitting and evaluate out-of-sample strategy robustness.',
    },
    {
      icon: <BarChart3 className="w-5 h-5 text-sky-400" />,
      title: 'Quantitative Statistical Tearsheets',
      description:
        'Comprehensive performance metrics including Sharpe ratio, Sortino ratio, max drawdown, win rate, profit factor, and expectancy distribution.',
    },
    {
      icon: <GitBranch className="w-5 h-5 text-sky-400" />,
      title: 'Strategy Incubator & Pipeline',
      description:
        'Promote strategies through formal lifecycle phases: Ideation, Backtest, Optimization, Staging, and Paper Incubation with audit tracking.',
    },
  ];

  const riskControls = [
    {
      title: 'Pre-Trade Order Validation',
      description:
        'Deterministic order verification ensuring trade sizing complies with margin requirements, account balance, and maximum order size limits.',
    },
    {
      title: 'Drawdown Circuit Breakers',
      description:
        'Real-time equity curve monitoring that automatically halts new orders when account drawdown exceeds configurable risk thresholds.',
    },
    {
      title: 'Automated Position Protection',
      description:
        'Native support for stop-loss, take-profit, and trailing stops simulated at the paper matching engine level with millisecond precision.',
    },
    {
      title: 'Account Isolation & Quota Limits',
      description:
        'Strict tenant-level order quotas, worker boundaries, and isolated paper accounts guaranteeing independent risk envelopes.',
    },
  ];

  const workflowSteps = [
    {
      step: '01',
      title: 'Formulate & Research',
      description: 'Define mathematical trading rules and market regime hypotheses using structured indicators and multi-pair feeds.',
    },
    {
      step: '02',
      title: 'Historical Backtest',
      description: 'Simulate historical execution against multi-year high-fidelity price feeds with realistic spread models.',
    },
    {
      step: '03',
      title: 'Walk-Forward Analysis',
      description: 'Optimize parameters across rolling in-sample windows and evaluate performance on strictly unseen out-of-sample data.',
    },
    {
      step: '04',
      title: 'Paper Incubation',
      description: 'Deploy strategy candidates into live forward-simulated execution with $100,000 USD paper allocation and $0.00 capital at risk.',
    },
    {
      step: '05',
      title: 'Audit & Review',
      description: 'Inspect fill logs, slippage metrics, trade distributions, and audit trails to verify behavioral fidelity before scaling.',
    },
  ];

  const trustArchitecture = [
    {
      icon: <Lock className="w-5 h-5 text-emerald-400" />,
      title: 'Cryptographic Credentials',
      description: 'Bcrypt password hashing with 72-byte input validation and single-use cryptographic tokens.',
    },
    {
      icon: <Layers className="w-5 h-5 text-emerald-400" />,
      title: 'Tenant IDOR Isolation',
      description: 'Row-level multi-tenant isolation enforcing Organization boundaries across all accounts, orders, and strategies.',
    },
    {
      icon: <ShieldCheck className="w-5 h-5 text-emerald-400" />,
      title: 'Role-Based Access Control',
      description: 'Granular permissions distinguishing Organization Owners, Administrators, Traders, and Read-Only Viewers.',
    },
    {
      icon: <Activity className="w-5 h-5 text-emerald-400" />,
      title: 'Immutable Audit Logging',
      description: 'Tamper-resistant audit trails capturing administrative actions, membership changes, and strategy promotions.',
    },
  ];

  const faqs = [
    {
      q: 'Is Project ORION a live financial broker?',
      a: 'No. Project ORION is software technology built for quantitative financial research, algorithmic strategy backtesting, and simulated paper execution. ORION is not a registered broker-dealer, investment adviser, or commodity trading advisor (CTA).',
    },
    {
      q: 'How much real capital is at risk?',
      a: 'Strictly $0.00. All accounts, orders, fills, and portfolios operate exclusively in Simulated Paper Trading Mode. You cannot deposit, lose, or risk real money on the platform.',
    },
    {
      q: 'What does a new account receive upon registration?',
      a: 'Self-service registration immediately provisions a default Free Sandbox organization with 1 paper trading account allocated with $100,000.00 USD in simulated balance, 100 daily orders quota, and 4 major FX pairs.',
    },
    {
      q: 'How are commercial subscriptions processed?',
      a: 'All subscription tier upgrades (Pro Trader, Business Prop Desk) are processed in Stripe Test Mode during Beta. Subscriptions entitle organizations to expanded compute quotas and paper-trading capacities.',
    },
  ];

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col text-slate-100 selection:bg-sky-500/30 selection:text-sky-200">
      <PublicHeader />

      <main id="main-content" className="flex-1">
        {/* Hero Section */}
        <section className="relative overflow-hidden pt-12 pb-20 md:pt-20 md:pb-28 border-b border-slate-900 bg-gradient-to-b from-slate-950 via-slate-900/30 to-slate-950">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto space-y-6">
              {/* Paper Trading Safety Badge */}
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-mono">
                <ShieldAlert className="w-4 h-4 text-amber-400" />
                <span>Strictly Simulated Paper Mode &bull; $0.00 Capital at Risk</span>
              </div>

              {/* Main Headline */}
              <h1 className="text-3xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-white font-sans">
                Quantitative Research &amp; <br />
                <span className="bg-gradient-to-r from-sky-400 to-indigo-400 bg-clip-text text-transparent">
                  Algorithmic Paper Trading
                </span>
              </h1>

              {/* Subtitle */}
              <p className="text-sm sm:text-base text-slate-300 font-sans leading-relaxed">
                Project ORION provides institutional-grade strategy backtesting, walk-forward parameter optimization,
                and simulated order matching for foreign exchange markets. Evaluate algorithmic performance with zero real-capital exposure.
              </p>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2 font-mono text-xs">
                <Link
                  to="/register"
                  className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-semibold shadow-lg shadow-sky-950/60 border border-sky-500/50 transition-all cursor-pointer"
                >
                  <span>Start Paper Trading — Free Sandbox</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <Link
                  to="/pricing"
                  className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 font-medium border border-slate-800 hover:border-slate-700 transition-colors"
                >
                  <span>Explore Pricing Tiers</span>
                </Link>
              </div>

              {/* Safety Footnote */}
              <div className="pt-2 text-[11px] font-mono text-slate-400 flex items-center justify-center gap-4">
                <span>&bull; $100,000 Initial Paper Balance</span>
                <span>&bull; No Credit Card Required for Sandbox</span>
                <span>&bull; Instant Provisioning</span>
              </div>
            </div>

            {/* Terminal Preview Mockup */}
            <div className="mt-12 sm:mt-16 max-w-5xl mx-auto rounded-2xl border border-slate-800 bg-slate-900/90 shadow-2xl overflow-hidden backdrop-blur-md">
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800/80 bg-slate-950/80 text-xs font-mono text-slate-400">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-rose-500/70" />
                  <div className="w-3 h-3 rounded-full bg-amber-500/70" />
                  <div className="w-3 h-3 rounded-full bg-emerald-500/70" />
                  <span className="ml-2 text-slate-300 font-semibold">ORION Quantitative Paper Terminal</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span>PAPER EXECUTION ENGINE ONLINE</span>
                </div>
              </div>

              <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
                  <span className="text-slate-400 block text-[11px]">Simulated Account Balance</span>
                  <span className="text-xl font-bold text-emerald-400">$100,000.00 USD</span>
                  <span className="text-[10px] text-amber-400 block">Strictly Paper Mode ($0 Capital)</span>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
                  <span className="text-slate-400 block text-[11px]">Strategy Optimization Regime</span>
                  <span className="text-xl font-bold text-sky-400">Walk-Forward WFA</span>
                  <span className="text-[10px] text-slate-400 block">12 Rolling Out-of-Sample Windows</span>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
                  <span className="text-slate-400 block text-[11px]">Automated Risk Status</span>
                  <span className="text-xl font-bold text-emerald-400">CIRCUITS NOMINAL</span>
                  <span className="text-[10px] text-slate-400 block">Max DD Limit: 5.0% &bull; Current: 0.8%</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Section: Quantitative Research Capabilities */}
        <section id="research" className="py-16 md:py-24 border-b border-slate-900 bg-slate-950">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-2xl mb-12">
              <div className="text-xs font-mono text-sky-400 uppercase tracking-wider mb-2">
                Quantitative Engineering
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold text-white font-sans">
                Built for Mathematical Rigor and Strategy Evaluation
              </h2>
              <p className="mt-2 text-sm text-slate-400 leading-relaxed font-sans">
                Evaluate trading models against real historical tick and candle dynamics without heuristic guessing.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {researchFeatures.map((feat) => (
                <div
                  key={feat.title}
                  className="p-6 rounded-2xl border border-slate-800/80 bg-slate-900/50 hover:border-slate-700 transition-colors space-y-3"
                >
                  <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center">
                    {feat.icon}
                  </div>
                  <h3 className="text-sm font-semibold text-slate-100 font-sans">{feat.title}</h3>
                  <p className="text-xs text-slate-400 leading-relaxed">{feat.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Section: Paper Trading & Simulated Execution */}
        <section className="py-16 md:py-24 border-b border-slate-900 bg-gradient-to-b from-slate-900/30 to-slate-950">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
              <div className="space-y-6">
                <div className="inline-flex items-center gap-1.5 text-xs font-mono text-amber-400">
                  <ShieldAlert className="w-4 h-4" />
                  <span>Simulated Paper Execution Invariant</span>
                </div>
                <h2 className="text-2xl sm:text-3xl font-bold text-white font-sans leading-tight">
                  High-Fidelity Simulated Matching with Zero Real-Capital Risk
                </h2>
                <p className="text-sm text-slate-300 leading-relaxed font-sans">
                  ORION’s paper execution engine mirrors institutional order lifecycles—supporting market orders, limit orders,
                  and stop orders with configurable spread and latency models.
                </p>

                <div className="space-y-3 font-mono text-xs">
                  <div className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                    <span className="text-slate-300">Default $100,000 USD paper trading capital allocated upon registration.</span>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                    <span className="text-slate-300">Simulated fill engine tracks bid/ask pricing with realistic slippage.</span>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                    <span className="text-slate-300">Autonomous trading background workers remain strictly disabled by default.</span>
                  </div>
                </div>

                <div className="pt-2">
                  <Link
                    to="/register"
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-medium text-xs font-mono transition-colors shadow-sm"
                  >
                    <span>Open Practice Account</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>

              <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 space-y-4 font-mono text-xs">
                <div className="text-xs font-semibold text-slate-200 border-b border-slate-800 pb-2 flex items-center justify-between">
                  <span>Paper Execution Telemetry</span>
                  <span className="text-[11px] text-amber-400">$0.00 Capital Risk</span>
                </div>
                <div className="space-y-2 text-slate-300">
                  <div className="flex justify-between py-1 border-b border-slate-800/40">
                    <span className="text-slate-500">Execution Mode</span>
                    <span className="text-emerald-400 font-semibold">Simulated Paper Only</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/40">
                    <span className="text-slate-500">Broker Adapter</span>
                    <span className="text-slate-200">PaperExecutionAdapter (In-Memory)</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/40">
                    <span className="text-slate-500">Sandbox Provider</span>
                    <span className="text-slate-200">OANDA v20 Practice Sandbox</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/40">
                    <span className="text-slate-500">Autonomous Workers</span>
                    <span className="text-amber-400">Disabled (ORION_WORKER_ENABLED=false)</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-slate-500">Live Capital Deployment</span>
                    <span className="text-rose-400 font-bold">STRICTLY $0.00 (FORBIDDEN)</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Section: Automated Risk Controls */}
        <section id="risk-controls" className="py-16 md:py-24 border-b border-slate-900 bg-slate-950">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-2xl mb-12">
              <div className="text-xs font-mono text-sky-400 uppercase tracking-wider mb-2">
                Capital Protection Architecture
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold text-white font-sans">
                Systematic Risk Guardrails Enforced at the Engine Level
              </h2>
              <p className="mt-2 text-sm text-slate-400 leading-relaxed font-sans">
                Quantifiable limits protect your research simulations from catastrophic drawdowns and uncontrolled position sizing.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {riskControls.map((rc) => (
                <div
                  key={rc.title}
                  className="p-6 rounded-2xl border border-slate-800/80 bg-slate-900/40 space-y-2"
                >
                  <h3 className="text-base font-semibold text-slate-100 font-sans">{rc.title}</h3>
                  <p className="text-xs text-slate-400 leading-relaxed">{rc.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Section: Research & Evaluation Workflow */}
        <section className="py-16 md:py-24 border-b border-slate-900 bg-gradient-to-b from-slate-900/20 to-slate-950">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-2xl mx-auto mb-16">
              <div className="text-xs font-mono text-sky-400 uppercase tracking-wider mb-2">
                Methodology
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold text-white font-sans">
                The 5-Stage Strategy Validation Pipeline
              </h2>
              <p className="mt-2 text-sm text-slate-400 leading-relaxed font-sans">
                Progress from theoretical hypothesis to forward paper validation through disciplined scientific stages.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              {workflowSteps.map((ws) => (
                <div
                  key={ws.step}
                  className="p-5 rounded-2xl border border-slate-800/80 bg-slate-900/60 relative space-y-2"
                >
                  <span className="text-xs font-mono font-bold text-sky-400/80 block">{ws.step}</span>
                  <h3 className="text-sm font-semibold text-slate-100 font-sans">{ws.title}</h3>
                  <p className="text-[11px] text-slate-400 leading-relaxed">{ws.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Section: Institutional Trust & Security */}
        <section className="py-16 md:py-24 border-b border-slate-900 bg-slate-950">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-2xl mb-12">
              <div className="text-xs font-mono text-emerald-400 uppercase tracking-wider mb-2">
                Security by Design
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold text-white font-sans">
                Institutional Security &amp; Data Isolation
              </h2>
              <p className="mt-2 text-sm text-slate-400 leading-relaxed font-sans">
                Project ORION is engineered with enterprise multi-tenancy, cryptographic authentication, and zero third-party tracking.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {trustArchitecture.map((ta) => (
                <div
                  key={ta.title}
                  className="p-6 rounded-2xl border border-slate-800/80 bg-slate-900/40 space-y-3"
                >
                  <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                    {ta.icon}
                  </div>
                  <h3 className="text-sm font-semibold text-slate-100 font-sans">{ta.title}</h3>
                  <p className="text-xs text-slate-400 leading-relaxed">{ta.description}</p>
                </div>
              ))}
            </div>

            <div className="mt-8 text-center">
              <Link
                to="/security"
                className="text-xs font-mono text-sky-400 hover:text-sky-300 transition-colors inline-flex items-center gap-1"
              >
                <span>Read our full Security &amp; Trust Architecture Disclosure</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </section>

        {/* Section: Public FAQ */}
        <section className="py-16 md:py-24 border-b border-slate-900 bg-slate-900/20">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <div className="text-xs font-mono text-sky-400 uppercase tracking-wider mb-2">
                Frequently Asked Questions
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold text-white font-sans">
                Common Questions &amp; Invariants
              </h2>
            </div>

            <div className="space-y-4">
              {faqs.map((faq) => (
                <div
                  key={faq.q}
                  className="p-6 rounded-2xl border border-slate-800/80 bg-slate-900/60 space-y-2"
                >
                  <h3 className="text-sm font-semibold text-slate-200 flex items-start gap-2 font-sans">
                    <HelpCircle className="w-4 h-4 text-sky-400 flex-shrink-0 mt-0.5" />
                    <span>{faq.q}</span>
                  </h3>
                  <p className="text-xs text-slate-400 pl-6 leading-relaxed font-sans">{faq.a}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Section: Final CTA Banner */}
        <section className="py-20 bg-gradient-to-t from-slate-950 to-slate-900/60 text-center">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
            <h2 className="text-2xl sm:text-4xl font-bold text-white font-sans">
              Start Your Algorithmic Journey in Simulated Paper Mode
            </h2>
            <p className="text-sm text-slate-300 max-w-xl mx-auto font-sans leading-relaxed">
              Enroll in seconds. No credit card required. Receive an instantaneous $100,000 USD paper trading allocation and begin evaluating quantitative strategies today.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2 font-mono text-xs">
              <Link
                to="/register"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-semibold shadow-lg shadow-sky-950/60 border border-sky-500/50 transition-all cursor-pointer"
              >
                <span>Create Paper Trading Account</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/pricing"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 font-medium border border-slate-800 hover:border-slate-700 transition-colors"
              >
                <span>View All Tiers &amp; Quotas</span>
              </Link>
            </div>
          </div>
        </section>
      </main>

      <PublicFooter />
    </div>
  );
};
