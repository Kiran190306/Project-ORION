/**
 * Shared, immutable pricing configuration for Project ORION.
 *
 * Single source of truth consumed by:
 * - Public Pricing Page (`/pricing`)
 * - Authenticated Commercial Billing Page (`/billing`)
 *
 * All tier quotas, asset entitlements, and retention periods strictly mirror
 * `CANONICAL_PLANS` from `apps/trading-engine/src/services/subscription_service.py`.
 *
 * NOTE: Enterprise pricing is strictly "Custom" / "Contact Enterprise". No numerical
 * price is invented, and all subscriptions operate in Stripe Test Mode with $0.00 capital at risk.
 */

export type PricingTierCode = 'FREE' | 'PRO' | 'BUSINESS' | 'ENTERPRISE';

export interface PricingPlan {
  readonly code: PricingTierCode;
  readonly name: string;
  readonly price: string;
  readonly period: string;
  readonly description: string;
  readonly features: readonly string[];
  readonly isPopular: boolean;
  readonly quotas: {
    readonly accounts: number | 'Unlimited';
    readonly dailyOrders: number | 'Unlimited';
    readonly workers: number | 'Unlimited';
    readonly retentionDays: number | '7 Years';
    readonly assetCoverage: string;
  };
  readonly ctaText: string;
  readonly ctaRoute?: string;
}

export const PRICING_PLANS: readonly PricingPlan[] = [
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
    quotas: {
      accounts: 1,
      dailyOrders: 100,
      workers: 0,
      retentionDays: 30,
      assetCoverage: '4 Major FX Pairs',
    },
    ctaText: 'Start Free Sandbox',
    ctaRoute: '/register',
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
    quotas: {
      accounts: 3,
      dailyOrders: 2500,
      workers: 1,
      retentionDays: 365,
      assetCoverage: '12 Liquid FX Pairs',
    },
    ctaText: 'Start with Pro',
    ctaRoute: '/register',
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
    quotas: {
      accounts: 10,
      dailyOrders: 50000,
      workers: 5,
      retentionDays: 1825,
      assetCoverage: 'All Currency Pairs (*)',
    },
    ctaText: 'Start with Business',
    ctaRoute: '/register',
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
      'All Currency Pairs (*)',
      'Long-term system audit log retention (subject to data agreement)',
      'Dedicated SRE Account Manager',
    ],
    isPopular: false,
    quotas: {
      accounts: 'Unlimited',
      dailyOrders: 'Unlimited',
      workers: 'Unlimited',
      retentionDays: '7 Years',
      assetCoverage: 'All Currency Pairs (*)',
    },
    ctaText: 'Contact Enterprise',
  },
] as const;

export const PRICING_DISCLAIMERS = {
  paperTradingInvariant:
    'Project ORION operates strictly in Paper Trading / Simulated Mode ($0.00 customer capital at risk).',
  billingContext:
    'Subscription tiers entitle organizations to software compute quotas and paper-trading accounts. Payment processing is conducted via Stripe Test Mode.',
  enterpriseContactNotice:
    'Contact details coming soon. For institutional bespoke deployment inquiries, reach out through your assigned account representative.',
} as const;
