import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Check,
  ShieldAlert,
  ArrowRight,
  Info,
  HelpCircle,
  Building,
  Sparkles,
} from 'lucide-react';
import { PublicHeader } from '../components/layout/PublicHeader';
import { PublicFooter } from '../components/layout/PublicFooter';
import { PRICING_PLANS, PRICING_DISCLAIMERS } from '../config/pricing';

export const PricingPage: React.FC = () => {
  const [enterpriseNoticeOpen, setEnterpriseNoticeOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col text-slate-100 selection:bg-sky-500/30 selection:text-sky-200">
      <PublicHeader />

      <main id="main-content" className="flex-1 py-12 md:py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Header & Title */}
          <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-mono">
              <ShieldAlert className="w-4 h-4 text-amber-400" />
              <span>Strictly Simulated Paper Mode &bull; $0.00 Capital at Risk</span>
            </div>

            <h1 className="text-3xl sm:text-5xl font-bold tracking-tight text-white font-sans">
              Transparent Institutional Pricing
            </h1>

            <p className="text-sm sm:text-base text-slate-300 font-sans leading-relaxed">
              Predictable platform tiers scaled for individual quantitative researchers, prop trading desks, and institutional funds.
              All tiers operate in simulated paper trading mode with zero capital exposure.
            </p>

            <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400 font-mono flex items-center justify-center gap-2 max-w-2xl mx-auto">
              <Info className="w-4 h-4 text-sky-400 flex-shrink-0" />
              <span>Beta Environment: Commercial subscription checkouts are simulated via Stripe Test Mode.</span>
            </div>
          </div>

          {/* Pricing Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-20">
            {PRICING_PLANS.map((plan) => {
              const isEnterprise = plan.code === 'ENTERPRISE';

              return (
                <div
                  key={plan.code}
                  className={`relative flex flex-col justify-between rounded-2xl border p-6 backdrop-blur-md transition-all ${
                    plan.isPopular
                      ? 'border-sky-500/50 bg-slate-900/90 shadow-xl shadow-sky-950/40 ring-1 ring-sky-500/30'
                      : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                  }`}
                >
                  {plan.isPopular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full bg-sky-500 text-slate-950 font-mono font-bold text-[10px] uppercase tracking-wider shadow-sm flex items-center gap-1">
                      <Sparkles className="w-3 h-3" />
                      <span>Most Popular</span>
                    </div>
                  )}

                  <div className="space-y-4">
                    <div>
                      <h2 className="text-base font-bold text-slate-100 font-mono tracking-wide">{plan.name}</h2>
                      <p className="text-xs text-slate-400 mt-1 min-h-[32px]">{plan.description}</p>
                    </div>

                    <div className="pt-2 border-t border-slate-800/80">
                      <div className="flex items-baseline gap-1 font-mono">
                        <span className="text-3xl font-extrabold text-white tracking-tight">{plan.price}</span>
                        {plan.period && <span className="text-xs text-slate-400">{plan.period}</span>}
                      </div>
                      <span className="text-[10px] font-mono text-slate-400 block mt-0.5">
                        {isEnterprise ? 'Bespoke institutional agreement' : 'Billed monthly in Stripe Test Mode'}
                      </span>
                    </div>

                    {/* Quota Highlights */}
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1.5 font-mono text-[11px] text-slate-300">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Accounts:</span>
                        <span className="font-semibold text-slate-200">{plan.quotas.accounts}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Daily Orders:</span>
                        <span className="font-semibold text-slate-200">{typeof plan.quotas.dailyOrders === 'number' ? plan.quotas.dailyOrders.toLocaleString() : plan.quotas.dailyOrders}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Workers:</span>
                        <span className="font-semibold text-slate-200">{plan.quotas.workers}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Retention:</span>
                        <span className="font-semibold text-slate-200">{typeof plan.quotas.retentionDays === 'number' ? `${plan.quotas.retentionDays} Days` : plan.quotas.retentionDays}</span>
                      </div>
                    </div>

                    {/* Features List */}
                    <div className="space-y-2 pt-2">
                      <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
                        Features Included:
                      </div>
                      <ul className="space-y-2 text-xs text-slate-300">
                        {plan.features.map((feature, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <Check className="w-3.5 h-3.5 text-sky-400 flex-shrink-0 mt-0.5" />
                            <span className="leading-tight">{feature}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* CTA Action */}
                  <div className="pt-6 mt-6 border-t border-slate-800/80 font-mono text-xs">
                    {isEnterprise ? (
                      <div>
                        <button
                          type="button"
                          onClick={() => setEnterpriseNoticeOpen(true)}
                          className="w-full py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium border border-slate-700 transition-colors cursor-pointer text-center"
                        >
                          Contact Enterprise
                        </button>
                      </div>
                    ) : (
                      <Link
                        to={plan.ctaRoute || '/register'}
                        className={`w-full inline-flex items-center justify-center gap-1.5 py-2.5 px-4 rounded-xl font-medium transition-all ${
                          plan.isPopular
                            ? 'bg-sky-600 hover:bg-sky-500 text-white shadow-md shadow-sky-950/60 border border-sky-500/50'
                            : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700'
                        }`}
                      >
                        <span>{plan.ctaText}</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Enterprise Modal Notice */}
          {enterpriseNoticeOpen && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
              <div className="max-w-md w-full rounded-2xl border border-slate-800 bg-slate-900 p-6 space-y-4 shadow-2xl">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
                    <Building className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-slate-100 font-sans">Enterprise Inquiries</h3>
                    <p className="text-xs text-slate-400 font-mono">Bespoke Capacity &amp; SLA</p>
                  </div>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed font-sans">
                  {PRICING_DISCLAIMERS.enterpriseContactNotice}
                </p>

                <p className="text-xs text-slate-400 leading-relaxed font-sans">
                  During Public Beta, enterprise quotas and custom dedicated worker clusters are provisioned through account representatives.
                </p>

                <div className="pt-2 flex justify-end">
                  <button
                    type="button"
                    onClick={() => setEnterpriseNoticeOpen(false)}
                    className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-mono font-medium transition-colors cursor-pointer"
                  >
                    Acknowledge
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Quota Feature Comparison Matrix Table */}
          <div className="max-w-5xl mx-auto rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-xl mb-16">
            <div className="p-6 border-b border-slate-800 bg-slate-950/80">
              <h2 className="text-lg font-bold text-white font-sans">Detailed Tier Quota Matrix</h2>
              <p className="text-xs text-slate-400 font-mono mt-1">
                Authoritative limits derived directly from backend subscription entitlement models.
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left font-mono text-xs">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-900/40 text-slate-400 text-[11px] uppercase tracking-wider">
                    <th className="p-4 font-semibold">Capacity Dimension</th>
                    <th className="p-4 font-semibold">Free Sandbox</th>
                    <th className="p-4 font-semibold text-sky-400">Pro Trader</th>
                    <th className="p-4 font-semibold">Business Desk</th>
                    <th className="p-4 font-semibold">Enterprise</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  <tr>
                    <td className="p-4 font-sans font-medium text-slate-200">Monthly Price</td>
                    <td className="p-4">$0 / mo</td>
                    <td className="p-4 text-sky-400 font-semibold">$99 / mo</td>
                    <td className="p-4">$299 / mo</td>
                    <td className="p-4 text-slate-400">Custom</td>
                  </tr>
                  <tr>
                    <td className="p-4 font-sans font-medium text-slate-200">Paper Trading Accounts</td>
                    <td className="p-4">1 Account</td>
                    <td className="p-4">3 Accounts</td>
                    <td className="p-4">10 Accounts</td>
                    <td className="p-4 text-emerald-400 font-semibold">Unlimited</td>
                  </tr>
                  <tr>
                    <td className="p-4 font-sans font-medium text-slate-200">Daily Orders Limit</td>
                    <td className="p-4">100 / day</td>
                    <td className="p-4">2,500 / day</td>
                    <td className="p-4">50,000 / day</td>
                    <td className="p-4 text-emerald-400 font-semibold">Unlimited</td>
                  </tr>
                  <tr>
                    <td className="p-4 font-sans font-medium text-slate-200">Autonomous Workers</td>
                    <td className="p-4">0 (Manual only)</td>
                    <td className="p-4">1 Entitled</td>
                    <td className="p-4">5 Entitled</td>
                    <td className="p-4 text-emerald-400 font-semibold">Unlimited</td>
                  </tr>
                  <tr>
                    <td className="p-4 font-sans font-medium text-slate-200">FX Asset Coverage</td>
                    <td className="p-4">4 Major Pairs</td>
                    <td className="p-4">12 Liquid Pairs</td>
                    <td className="p-4">All Pairs (*)</td>
                    <td className="p-4 text-emerald-400 font-semibold">All Currency Pairs (*)</td>
                  </tr>
                  <tr>
                    <td className="p-4 font-sans font-medium text-slate-200">Historical Data Retention</td>
                    <td className="p-4">30 Days</td>
                    <td className="p-4">365 Days</td>
                    <td className="p-4">1,825 Days (5 Yr)</td>
                    <td className="p-4 text-emerald-400 font-semibold">7 Years</td>
                  </tr>
                  <tr>
                    <td className="p-4 font-sans font-medium text-slate-200">Support Level</td>
                    <td className="p-4">Community Docs</td>
                    <td className="p-4">Standard Email</td>
                    <td className="p-4">Priority SRE SLA</td>
                    <td className="p-4 text-emerald-400 font-semibold">Dedicated SRE Mgr</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Disclaimers & Regulatory Notices */}
          <div className="max-w-4xl mx-auto p-6 rounded-2xl border border-slate-900 bg-slate-900/30 space-y-3 font-mono text-xs text-slate-400">
            <div className="flex items-center gap-2 text-slate-300 font-semibold">
              <HelpCircle className="w-4 h-4 text-sky-400" />
              <span>Platform Commercial Disclosures &bull; Public Beta</span>
            </div>
            <p className="leading-relaxed">
              {PRICING_DISCLAIMERS.paperTradingInvariant} All strategies, indicators, and optimizations are evaluated against simulated paper execution.
              Fees paid for subscriptions entitle customer organizations to dedicated cloud compute resources, multi-tenant database capacity, and API quota allowances.
            </p>
            <p className="leading-relaxed">
              {PRICING_DISCLAIMERS.billingContext} Subscriptions can be upgraded, downgraded, or canceled at any time from the authenticated billing portal.
              For more details on cancellations, please review our{' '}
              <Link to="/refund-policy" className="text-sky-400 hover:text-sky-300 underline underline-offset-2">
                Refund &amp; Cancellation Policy
              </Link>{' '}
              and{' '}
              <Link to="/terms" className="text-sky-400 hover:text-sky-300 underline underline-offset-2">
                Terms of Service
              </Link>.
            </p>
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
};
