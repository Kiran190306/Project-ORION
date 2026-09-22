import React from 'react';
import { LegalPageLayout } from '../components/legal/LegalPageLayout';
import { AlertTriangle, ShieldAlert, DollarSign, Activity, Cpu } from 'lucide-react';

const SECTIONS = [
  { id: 'zero-capital', title: '1. Paper Trading Invariant' },
  { id: 'execution-differences', title: '2. Execution Differences' },
  { id: 'hypothetical-results', title: '3. Hypothetical Warnings' },
  { id: 'no-advice', title: '4. No Investment Advice' },
  { id: 'broker-sandbox', title: '5. Broker Sandbox Limits' },
];

export const RiskDisclosurePage: React.FC = () => {
  return (
    <LegalPageLayout
      title="Paper Trading & Financial Risk Disclosure"
      version="1.0"
      effectiveDate="2026-09-22"
      badgeLabel="Strictly Paper Simulation"
      badgeVariant="warning"
      sections={SECTIONS}
    >
      <section id="zero-capital" className="p-4 rounded-xl bg-amber-950/40 border border-amber-800 text-amber-200 text-xs sm:text-sm font-mono space-y-2">
        <div className="flex items-center gap-2 font-bold text-amber-300">
          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
          <span>MANDATORY FINANCIAL SAFETY DISCLOSURE</span>
        </div>
        <p>
          All trading order submission, strategy execution, and portfolio analysis on Project ORION operates exclusively in <strong>Simulated Paper Trading Mode</strong>.
        </p>
        <p className="text-amber-400 font-bold">
          Capital at risk is strictly $0.00. No real funds, customer deposits, or live broker execution facilities are involved.
        </p>
      </section>

      <section id="execution-differences" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2 flex items-center gap-2">
          <Activity className="w-4 h-4 text-sky-400" />
          <span>1. Execution Differences &amp; Simulation Limitations</span>
        </h2>
        <p>Simulated paper execution differs inherently from live market execution:</p>
        <ul className="list-disc pl-5 space-y-2 text-slate-300 text-xs sm:text-sm">
          <li><strong>Liquidity &amp; Market Impact:</strong> In paper simulation, orders are matched without affecting market depth. In live markets, substantial volume creates adverse market impact.</li>
          <li><strong>Slippage &amp; Spread Dynamics:</strong> Although ORION employs Gaussian mathematical models for adverse slippage and spread widening, actual market volatility during economic news releases may cause substantially greater slippage.</li>
          <li><strong>Order Book Priority:</strong> Paper fills do not reflect queue priority or routing delays inherent in live exchange matching engines.</li>
          <li><strong>Partial Fills &amp; Rejections:</strong> Live broker execution facilities may experience rejected orders or partial fills that differ from deterministic algorithmic models.</li>
        </ul>
      </section>

      <section id="hypothetical-results" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2 flex items-center gap-2">
          <Cpu className="w-4 h-4 text-sky-400" />
          <span>2. Hypothetical &amp; Backtested Performance Warning</span>
        </h2>
        <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 font-mono space-y-1.5">
          <div className="font-semibold text-slate-100 uppercase tracking-wide">
            CFTC Rule 4.41 / Quantitative Standard Disclosure:
          </div>
          <p className="uppercase leading-normal text-[11px] text-slate-400">
            HYPOTHETICAL OR SIMULATED PERFORMANCE RESULTS HAVE CERTAIN INHERENT LIMITATIONS. UNLIKE AN ACTUAL PERFORMANCE RECORD, SIMULATED RESULTS DO NOT REPRESENT ACTUAL TRADING. ALSO, SINCE THE TRADES HAVE NOT ACTUALLY BEEN EXECUTED, THE RESULTS MAY HAVE UNDER- OR OVER-COMPENSATED FOR THE IMPACT, IF ANY, OF CERTAIN MARKET FACTORS, SUCH AS LACK OF LIQUIDITY.
          </p>
        </div>
        <p>
          A Quality Gate PASS in the deployment pipeline or high historical Sharpe/Sortino ratios reflect past simulated performance only. <strong>They must never be interpreted as a guarantee of future live profitability.</strong>
        </p>
      </section>

      <section id="no-advice" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2 flex items-center gap-2">
          <DollarSign className="w-4 h-4 text-sky-400" />
          <span>3. Software Only — No Investment Advice</span>
        </h2>
        <ul className="list-disc pl-5 space-y-1.5 text-slate-300 text-xs sm:text-sm">
          <li>Project ORION is software technology, not an investment adviser, broker-dealer, or commodity trading advisor (CTA).</li>
          <li>The Platform does not provide financial, tax, or investment advice.</li>
          <li>No automated score, tearsheet, or model parameter constitutes a recommendation to buy, sell, or trade any financial instrument.</li>
        </ul>
      </section>

      <section id="broker-sandbox" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2 flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-sky-400" />
          <span>4. Broker Sandbox Integration Disclaimers</span>
        </h2>
        <p>
          Connectivity to broker sandbox environments (e.g. OANDA v20 Practice Sandbox) operates strictly in demo practice mode. Demo practice accounts do not execute real money trades and do not establish live broker trading accounts.
        </p>
      </section>
    </LegalPageLayout>
  );
};
