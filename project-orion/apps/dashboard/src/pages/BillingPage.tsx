import React, { useState, useCallback, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  CheckCircle,
  AlertCircle,
  ExternalLink,
  ShieldCheck,
  RefreshCw,
  Clock,
} from 'lucide-react';
import { billingApi } from '../api/endpoints';
import type { BillingOverviewResponse } from '../api/types';
import { Card } from '../components/common/Card';
import { Badge, PaperTradingBadge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { formatCurrency, formatDateTime } from '../utils/formatters';
import { getErrorMessage } from '../utils/errors';

export const BillingPage: React.FC = () => {
  const [overview, setOverview] = useState<BillingOverviewResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const fetchOverview = useCallback(async () => {
    try {
      const data = await billingApi.getOverview();
      setOverview(data);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  const handleUpgrade = async (planCode: string) => {
    setIsProcessing(true);
    setError(null);
    setMessage(null);
    try {
      const res = await billingApi.createCheckout(planCode);
      if (res.url) {
        window.location.href = res.url;
      } else {
        setMessage(`Checkout session generated: ${res.session_id}`);
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCancel = async () => {
    if (!window.confirm('Are you sure you want to cancel your subscription at the end of the current billing period?')) {
      return;
    }
    setIsProcessing(true);
    setError(null);
    try {
      await billingApi.cancelSubscription(true);
      setMessage('Subscription scheduled for cancellation at the end of the billing period.');
      await fetchOverview();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsProcessing(false);
    }
  };

  const currentPlan = overview?.subscription?.plan_code?.toUpperCase() || 'FREE';
  const subStatus = overview?.subscription?.status || 'active';
  const cancelAtPeriodEnd = overview?.subscription?.cancel_at_period_end || false;

  const plans = [
    {
      code: 'FREE',
      name: 'Free Sandbox',
      price: '$0',
      period: '/month',
      description: 'Ideal for getting started with algorithmic paper trading.',
      features: [
        '1 Paper Trading Account',
        '100 Daily Orders Quota',
        '0 Autonomous Workers',
        '4 Major FX Pairs (EUR/USD, GBP/USD, USD/JPY, USD/CHF)',
        '30-Day Data Retention',
      ],
      isPopular: false,
    },
    {
      code: 'PRO',
      name: 'Pro Trader',
      price: '$99',
      period: '/month',
      description: 'Expanded capacity with 1 autonomous trading worker.',
      features: [
        '3 Paper Trading Accounts',
        '2,500 Daily Orders Quota',
        '1 Autonomous Worker Entitled',
        '12 Liquid Forex Pairs',
        '365-Day Historical Data Retention',
        'Email Incident Notifications',
      ],
      isPopular: true,
    },
    {
      code: 'BUSINESS',
      name: 'Business Prop Desk',
      price: '$299',
      period: '/month',
      description: 'Multi-account prop trading with 5 parallel autonomous workers.',
      features: [
        '10 Paper Trading Accounts',
        '50,000 Daily Orders Quota',
        '5 Autonomous Workers Entitled',
        'All Currency Pairs Supported (*)',
        '1,825-Day (5-Year) Retention',
        'Priority SRE Support SLA',
      ],
      isPopular: false,
    },
    {
      code: 'ENTERPRISE',
      name: 'Enterprise Institutional',
      price: 'Custom',
      period: '',
      description: 'Unlimited institutional capacity with bespoke integrations.',
      features: [
        'Unlimited Accounts & Orders',
        'Unlimited Autonomous Workers',
        'All Asset Classes (*)',
        'Long-term system audit log retention (subject to data agreement)',
        'Dedicated SRE Account Manager',
      ],
      isPopular: false,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold tracking-wide text-slate-100 font-mono">
              COMMERCIAL BILLING & PLANS
            </h1>
            <PaperTradingBadge />
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Manage your institutional tier, quota limits, and Stripe test-mode invoices.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchOverview}
            disabled={isLoading}
          >
            <RefreshCw className={`w-3.5 h-3.5 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Safety Notice */}
      <div className="rounded-lg bg-sky-500/10 border border-sky-500/30 p-4 flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-sky-400 mt-0.5 flex-shrink-0" />
        <div className="text-xs text-slate-300 space-y-1">
          <p className="font-semibold text-sky-300">
            Stripe Test Mode Only — Strict Paper-Trading Invariant
          </p>
          <p className="text-slate-400">
            Project ORION operates strictly in Paper Trading mode ($0.00 customer capital at risk).
            All checkouts and payments operate in <strong>Stripe Test Mode</strong>. No real funds are ever charged or processed.
          </p>
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-rose-500/10 border border-rose-500/30 p-4 flex items-center gap-3 text-rose-400 text-xs">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {message && (
        <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/30 p-4 flex items-center gap-3 text-emerald-400 text-xs">
          <CheckCircle className="w-4 h-4 flex-shrink-0" />
          <span>{message}</span>
        </div>
      )}

      {/* Current Subscription Card */}
      <Card title="Current Subscription Status">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 p-4">
          <div>
            <span className="text-xs text-slate-400 font-mono">ACTIVE TIER</span>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-lg font-bold text-slate-100 font-mono">
                {currentPlan}
              </span>
              <Badge variant={subStatus === 'active' ? 'success' : 'warning'}>
                {subStatus.toUpperCase()}
              </Badge>
            </div>
            {cancelAtPeriodEnd && (
              <p className="text-xs text-amber-400 mt-1 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                Cancels at period end
              </p>
            )}
          </div>

          <div>
            <span className="text-xs text-slate-400 font-mono">BILLING CYCLE</span>
            <p className="text-sm text-slate-200 mt-1 font-mono">
              {overview?.subscription?.current_period_end
                ? `Renews / Expires: ${formatDateTime(overview.subscription.current_period_end)}`
                : 'Free Lifetime Sandbox'}
            </p>
          </div>

          <div className="flex items-center justify-start md:justify-end">
            {currentPlan !== 'FREE' && !cancelAtPeriodEnd && (
              <Button
                variant="danger"
                size="sm"
                onClick={handleCancel}
                disabled={isProcessing}
              >
                Cancel Subscription
              </Button>
            )}
          </div>
        </div>
      </Card>

      {/* Plan Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {plans.map((plan) => {
          const isCurrent = currentPlan === plan.code;
          return (
            <div
              key={plan.code}
              className={`rounded-xl border p-6 flex flex-col justify-between transition-all ${
                plan.isPopular
                  ? 'bg-slate-900/90 border-sky-500/50 shadow-lg shadow-sky-500/10'
                  : 'bg-slate-900/50 border-slate-800'
              }`}
            >
              <div>
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-100 font-mono">
                    {plan.name}
                  </h3>
                  {plan.isPopular && (
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-sky-500/20 text-sky-400 border border-sky-500/30">
                      Popular
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-400 mt-2 min-h-[36px]">
                  {plan.description}
                </p>
                <div className="mt-4 flex items-baseline gap-1">
                  <span className="text-2xl font-bold font-mono text-slate-100">
                    {plan.price}
                  </span>
                  <span className="text-xs text-slate-400">{plan.period}</span>
                </div>

                <div className="mt-6 border-t border-slate-800 pt-4 space-y-2">
                  {plan.features.map((feature, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-xs text-slate-300">
                      <CheckCircle className="w-3.5 h-3.5 text-sky-400 mt-0.5 flex-shrink-0" />
                      <span>{feature}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-8">
                {isCurrent ? (
                  <Button variant="outline" className="w-full" disabled>
                    Current Plan
                  </Button>
                ) : plan.code === 'ENTERPRISE' ? (
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => handleUpgrade('ENTERPRISE')}
                    disabled={isProcessing}
                  >
                    Contact Enterprise
                  </Button>
                ) : (
                  <Button
                    variant="primary"
                    className="w-full"
                    onClick={() => handleUpgrade(plan.code)}
                    disabled={isProcessing}
                  >
                    Upgrade to {plan.name}
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Legal & Billing Policy Disclosures Card */}
      <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-400 space-y-2 font-mono">
        <div className="flex items-center gap-2 text-slate-300 font-semibold">
          <ShieldCheck className="w-4 h-4 text-sky-400" />
          <span>COMMERCIAL TERMS &amp; BILLING NOTICE</span>
        </div>
        <p>
          Project ORION operates in Paper Trading / Simulated Mode ($0.00 capital at risk). Subscription tiers entitle organizations to platform compute quotas and system access. Payment processing is currently conducted via Stripe Test Mode.
        </p>
        <p>
          Subscriptions renew automatically each billing cycle unless cancelled prior to renewal. For detailed terms regarding prorations, cancellations, and disputes, please review our{' '}
          <Link to="/refund-policy" className="text-sky-400 hover:text-sky-300 underline underline-offset-2">
            Refund &amp; Cancellation Policy
          </Link>
          ,{' '}
          <Link to="/terms" className="text-sky-400 hover:text-sky-300 underline underline-offset-2">
            Terms of Service
          </Link>
          , and{' '}
          <Link to="/risk-disclosure" className="text-sky-400 hover:text-sky-300 underline underline-offset-2">
            Paper Trading Risk Disclosure
          </Link>
          .
        </p>
      </div>

      {/* Invoices History Table */}
      <Card title="Billing History & Invoices">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/40 text-slate-400 border-b border-slate-800 font-mono">
              <tr>
                <th className="p-3">INVOICE ID</th>
                <th className="p-3">DATE</th>
                <th className="p-3">AMOUNT</th>
                <th className="p-3">STATUS</th>
                <th className="p-3 text-right">RECEIPT</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {overview?.recent_invoices && overview.recent_invoices.length > 0 ? (
                overview.recent_invoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="p-3 font-mono text-slate-200">{inv.provider_invoice_id}</td>
                    <td className="p-3 text-slate-400">{formatDateTime(inv.created_at)}</td>
                    <td className="p-3 font-mono font-semibold text-slate-100">
                      {formatCurrency(inv.amount_paid, inv.currency.toUpperCase())}
                    </td>
                    <td className="p-3">
                      <Badge variant={inv.status === 'paid' ? 'success' : 'danger'}>
                        {inv.status.toUpperCase()}
                      </Badge>
                    </td>
                    <td className="p-3 text-right">
                      {inv.hosted_invoice_url ? (
                        <a
                          href={inv.hosted_invoice_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-sky-400 hover:text-sky-300 font-medium"
                        >
                          View <ExternalLink className="w-3 h-3" />
                        </a>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="p-6 text-center text-slate-500 font-mono">
                    No billing invoices recorded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
