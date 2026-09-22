import React from 'react';
import { LegalPageLayout } from '../components/legal/LegalPageLayout';
import { AlertCircle, RefreshCw, CreditCard, Clock, ShieldX } from 'lucide-react';

const SECTIONS = [
  { id: 'notice', title: '1. Implementation Notice' },
  { id: 'test-mode', title: '2. Beta Test Mode' },
  { id: 'subscriptions', title: '3. Recurring Billing' },
  { id: 'cancellation', title: '4. Self-Service Cancellation' },
  { id: 'failed-payments', title: '5. Failed Payments' },
  { id: 'refunds', title: '6. Refund Discretion' },
];

export const RefundPolicyPage: React.FC = () => {
  return (
    <LegalPageLayout
      title="Refund & Subscription Cancellation Policy"
      version="1.0"
      effectiveDate="2026-09-22"
      sections={SECTIONS}
    >
      <section id="notice" className="p-4 rounded-xl bg-amber-950/30 border border-amber-800/50 text-amber-300 text-xs font-mono flex items-start gap-3">
        <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-400" />
        <div>
          <span className="font-semibold text-amber-200">Internal Implementation Notice:</span>{' '}
          This document details the operational mechanics of commercial billing and subscription cancellation in Project ORION. Commercial refund policies and statutory withdrawal rights (such as EU consumer cooling-off periods) require formal owner approval and qualified legal counsel review before commercial launch.
        </div>
      </section>

      <section id="test-mode" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2 flex items-center gap-2">
          <CreditCard className="w-4 h-4 text-sky-400" />
          <span>1. Beta Testing Environment (Stripe Test Mode)</span>
        </h2>
        <div className="p-3.5 rounded-lg bg-sky-950/40 border border-sky-800/60 text-xs text-sky-200 font-mono">
          During the Public Beta phase, all billing checkout sessions and plan upgrades operate strictly through <strong>Stripe Test Mode</strong>. No real payment cards are charged, and real currency refunds are not applicable during test mode operations.
        </div>
      </section>

      <section id="subscriptions" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2 flex items-center gap-2">
          <Clock className="w-4 h-4 text-sky-400" />
          <span>2. Subscription Billing &amp; Auto-Renewal</span>
        </h2>
        <p>
          Following commercial launch, subscriptions to paid tiers (such as PRO, BUSINESS, or ENTERPRISE) renew automatically on a recurring monthly billing cycle unless cancelled prior to the renewal date.
        </p>
      </section>

      <section id="cancellation" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2 flex items-center gap-2">
          <RefreshCw className="w-4 h-4 text-sky-400" />
          <span>3. Self-Service Subscription Cancellation</span>
        </h2>
        <ul className="list-disc pl-5 space-y-2 text-slate-300 text-xs sm:text-sm">
          <li><strong>How to Cancel:</strong> Organization Owners and Admins with <code className="text-sky-400 font-mono">SUBSCRIPTION_MANAGE</code> authority may cancel subscriptions anytime directly through the <strong>Commercial Billing &amp; Plans</strong> dashboard.</li>
          <li><strong>Period-End Cancellation:</strong> By default, your plan quotas remain active through the end of the prepaid billing cycle.</li>
          <li><strong>Degradation to Free Sandbox:</strong> At the conclusion of the billing period, your organization automatically degrades to Free Sandbox tier quotas. Your historical data, trading logs, and settings are preserved.</li>
        </ul>
      </section>

      <section id="failed-payments" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2 flex items-center gap-2">
          <ShieldX className="w-4 h-4 text-rose-400" />
          <span>4. Failed Recurring Payments</span>
        </h2>
        <p>
          If a recurring subscription payment fails, automated retries are conducted by the payment processor. If payment cannot be settled, the subscription transitions to unpaid/past_due and entitlements fail closed to the Free Sandbox tier.
        </p>
      </section>

      <section id="refunds" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2">
          5. Refund Discretion &amp; Statutory Consumer Rights
        </h2>
        <p>
          Digital SaaS subscription access fees are earned upon account provisioning. Refunds for partial-month usage are not automatically processed by the software system.
        </p>
        <p className="text-xs text-slate-400 italic">
          (Final commercial refund eligibility, exceptional circumstance reviews, and cooling-off periods are subject to formal owner approval and statutory consumer protection laws in your jurisdiction. Requires jurisdiction-specific legal review.)
        </p>
      </section>
    </LegalPageLayout>
  );
};
