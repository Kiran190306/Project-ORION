import React from 'react';
import { LegalPageLayout } from '../components/legal/LegalPageLayout';
import { AlertCircle, Lock, ShieldCheck, Database, Cookie, Globe } from 'lucide-react';

const SECTIONS = [
  { id: 'notice', title: '1. Implementation Notice' },
  { id: 'overview', title: '2. Overview & Scope' },
  { id: 'data-collected', title: '3. Data We Collect' },
  { id: 'storage', title: '4. Browser Storage & Cookies' },
  { id: 'processors', title: '5. Third-Party Processors' },
  { id: 'retention', title: '6. Retention & Deletion' },
  { id: 'international', title: '7. Jurisdictional Notice' },
];

export const PrivacyPage: React.FC = () => {
  return (
    <LegalPageLayout
      title="Privacy Policy & Data Disclosure"
      version="1.0"
      effectiveDate="2026-09-22"
      sections={SECTIONS}
    >
      <section id="notice" className="p-4 rounded-xl bg-amber-950/30 border border-amber-800/50 text-amber-300 text-xs font-mono flex items-start gap-3">
        <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-400" />
        <div>
          <span className="font-semibold text-amber-200">Internal Implementation Notice:</span>{' '}
          This disclosure outlines the actual technical data handling and storage behaviors of Project ORION during Public Beta. It does not fabricate statutory certifications (such as certified GDPR or CCPA compliance). Comprehensive data protection officer appointments and cross-border transfer mechanisms are subject to external legal counsel review.
        </div>
      </section>

      <section id="overview" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2 flex items-center gap-2">
          <Lock className="w-4 h-4 text-sky-400" />
          <span>1. Overview &amp; Scope</span>
        </h2>
        <p>
          Project ORION (&ldquo;the Platform&rdquo;) is committed to transparent information practices. This Privacy Policy details the categories of personal data collected, technical operational logs stored, browser storage mechanisms utilized, and the third-party infrastructure providers involved in delivering the Platform.
        </p>
      </section>

      <section id="data-collected" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2 flex items-center gap-2">
          <Database className="w-4 h-4 text-sky-400" />
          <span>2. Information We Collect</span>
        </h2>
        <p>We collect only information necessary to authenticate users, enforce multi-tenant isolation, mitigate automated system abuse, and maintain operational stability:</p>
        <ul className="list-disc pl-5 space-y-2 text-slate-300 text-xs sm:text-sm">
          <li><strong>Account Identity:</strong> Username, email address, and a salted hash of your password (<code className="text-sky-400 font-mono">bcrypt</code>). Plaintext passwords are never stored or logged.</li>
          <li><strong>Tenant Organization Data:</strong> Firm/organization name, custom URL slug, member invitations, and assigned roles (<code className="text-slate-200 font-mono">OWNER, ADMIN, TRADER, VIEWER</code>).</li>
          <li><strong>Security Tokens:</strong> Ephemeral single-use cryptographic token hashes (<code className="text-sky-400 font-mono">SHA-256</code>) for password recovery and email verification.</li>
          <li><strong>Abuse Defense Telemetry:</strong> Client IP addresses are processed in-memory via Redis sliding-window counters to mitigate brute-force attacks. Raw IP addresses are not stored in legal consent tables.</li>
          <li><strong>Simulated Trading Data:</strong> Paper accounts, simulated orders, fills, positions, strategy parameters, backtests, and tearsheets.</li>
          <li><strong>Audit Trail:</strong> Immutable system audit logs recording tenant-level administrative events.</li>
        </ul>
      </section>

      <section id="storage" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2 flex items-center gap-2">
          <Cookie className="w-4 h-4 text-sky-400" />
          <span>3. Browser Storage &amp; Cookie Disclosure</span>
        </h2>
        <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800 space-y-2 text-xs">
          <div className="font-semibold text-slate-200 flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Zero Tracking Cookies &bull; Zero Marketing Beacons</span>
          </div>
          <p className="text-slate-300">
            Project ORION does <strong>not</strong> use advertising cookies, marketing pixels, tracking scripts, or analytics beacons.
          </p>
        </div>
        <p>The Platform utilizes HTML5 <code className="text-sky-400 font-mono">sessionStorage</code> strictly to maintain your authenticated session:</p>
        <ul className="list-disc pl-5 space-y-1.5 text-slate-300 text-xs sm:text-sm">
          <li><code className="text-sky-400 font-mono">orion_access_token</code>: JWT bearer token granting API access for your current browser tab.</li>
          <li><code className="text-sky-400 font-mono">orion_active_org_id</code>: UUID of your currently selected tenant organization.</li>
        </ul>
        <p className="text-xs text-slate-400">
          Both session items are destroyed when you log out or close the browser tab. The application does not store profile data in <code className="text-slate-300 font-mono">localStorage</code> or <code className="text-slate-300 font-mono">IndexedDB</code>.
        </p>
      </section>

      <section id="processors" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2 flex items-center gap-2">
          <Globe className="w-4 h-4 text-sky-400" />
          <span>4. Third-Party Infrastructure Processors</span>
        </h2>
        <p>The Platform interfaces with the following infrastructure providers:</p>
        <ul className="list-disc pl-5 space-y-1.5 text-slate-300 text-xs sm:text-sm">
          <li><strong>Render:</strong> Cloud container hosting, managed PostgreSQL, and Redis cache.</li>
          <li><strong>Stripe:</strong> Subscription billing operating strictly in <strong>Test Mode</strong> (<code className="text-slate-300 font-mono">sk_test_...</code>). No live credit cards are debited.</li>
          <li><strong>TwelveData:</strong> External financial market data provider for pricing feeds.</li>
          <li><strong>OANDA:</strong> Broker sandbox integration restricted to practice environments (<code className="text-slate-300 font-mono">api-fxpractice.oanda.com</code>).</li>
        </ul>
      </section>

      <section id="retention" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2">
          5. Data Retention &amp; Deletion
        </h2>
        <p>
          Account records, organization entities, and simulated trading data persist in the database during active account lifecycles. Deactivated accounts fail closed to prevent session creation.
        </p>
        <p className="text-xs text-slate-400 italic">
          (Automated data retention and purging policies across subscription tiers require formal product/legal decision.)
        </p>
      </section>

      <section id="international" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2">
          6. Jurisdictional Legal Notice
        </h2>
        <p className="text-xs text-slate-400 italic">
          (Jurisdictional legal review required before public commercial launch to establish formal Standard Contractual Clauses, Data Protection Officer designation, and regional statutory privacy notices.)
        </p>
      </section>
    </LegalPageLayout>
  );
};
