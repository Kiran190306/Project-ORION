import React from 'react';
import { LegalPageLayout } from '../components/legal/LegalPageLayout';
import { ShieldCheck, Lock, Users, Key, AlertCircle, Layers } from 'lucide-react';

const SECTIONS = [
  { id: 'non-certification', title: '1. Compliance Disclosure' },
  { id: 'auth-security', title: '2. Auth & Sessions' },
  { id: 'rate-limiting', title: '3. Abuse Defense' },
  { id: 'tenant-isolation', title: '4. Tenant Isolation & RBAC' },
  { id: 'encryption', title: '5. Encryption at Rest' },
  { id: 'infrastructure', title: '6. Infrastructure & Headers' },
  { id: 'vulnerability', title: '7. Vulnerability Disclosure' },
];

export const SecurityTrustPage: React.FC = () => {
  return (
    <LegalPageLayout
      title="Security & Trust Architecture"
      version="1.0"
      effectiveDate="2026-09-22"
      badgeLabel="Security Architecture"
      sections={SECTIONS}
    >
      <section id="non-certification" className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 text-xs font-mono space-y-2">
        <div className="flex items-center gap-2 font-bold text-sky-400">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>NON-CERTIFICATION DISCLOSURE</span>
        </div>
        <p>
          Project ORION is in active Public Beta. The platform has not undergone external third-party SOC 2, ISO 27001, or PCI DSS compliance audits. This document outlines the technical security controls <strong>currently implemented</strong> within the software architecture. It does not constitute a formal security certification or compliance warranty.
        </p>
      </section>

      <section id="auth-security" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2 flex items-center gap-2">
          <Lock className="w-4 h-4 text-sky-400" />
          <span>1. Authentication &amp; Session Hardening</span>
        </h2>
        <ul className="list-disc pl-5 space-y-2 text-slate-300 text-xs sm:text-sm">
          <li><strong>Stateless HMAC-SHA256 JWT:</strong> Cryptographic token signing strictly fails closed against default developmental secrets in production.</li>
          <li><strong>Bcrypt Password Hashing:</strong> Passwords are cryptographically salted and hashed using <code className="text-sky-400 font-mono">bcrypt</code>. Plaintext passwords are never stored.</li>
          <li><strong>Single-Use Hashed Tokens:</strong> Password resets and email verifications utilize high-entropy random bytes (<code className="text-sky-400 font-mono">secrets.token_urlsafe(32)</code>), hashed with SHA-256 before persistence, and destroyed upon first use.</li>
          <li><strong>Immediate Token Revocation:</strong> Password updates immediately invalidate all previously issued access tokens via <code className="text-slate-300 font-mono">password_changed_at</code> timestamp validation.</li>
        </ul>
      </section>

      <section id="rate-limiting" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>2. Abuse Defense &amp; Sliding-Window Rate Limiting</span>
        </h2>
        <ul className="list-disc pl-5 space-y-2 text-slate-300 text-xs sm:text-sm">
          <li><strong>Atomic Sliding-Window Limiters:</strong> Redis sorted-set counters executed via atomic Lua scripts prevent concurrency race conditions.</li>
          <li><strong>Fail-Closed Sensitive Endpoints:</strong> Authentication routes (<code className="text-slate-300 font-mono">/login, /forgot-password, /resend-verification</code>) fail closed if Redis is unreachable to safeguard credentials.</li>
          <li><strong>Bounded In-Memory Fallback:</strong> General API routes feature an in-memory sliding-window fallback bounded to 10,000 keys with LRU eviction to prevent memory exhaustion.</li>
          <li><strong>Proxy-Aware IP Resolution:</strong> Traverses <code className="text-slate-300 font-mono">X-Forwarded-For</code> headers right-to-left, discarding untrusted proxy addresses with IPv4/IPv6 normalization.</li>
        </ul>
      </section>

      <section id="tenant-isolation" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2 flex items-center gap-2">
          <Users className="w-4 h-4 text-sky-400" />
          <span>3. Multi-Tenant Isolation &amp; RBAC</span>
        </h2>
        <ul className="list-disc pl-5 space-y-2 text-slate-300 text-xs sm:text-sm">
          <li><strong>Mandatory Tenant Context:</strong> Operations require and enforce the <code className="text-sky-400 font-mono">X-Organization-ID</code> header.</li>
          <li><strong>SQL-Level Isolation:</strong> Database queries enforce strict organizational foreign keys (<code className="text-slate-300 font-mono">WHERE organization_id = :org_id</code>).</li>
          <li><strong>Role-Based Access Control:</strong> Fine-grained permissions govern <code className="text-slate-300 font-mono">OWNER, ADMIN, TRADER, VIEWER</code> roles.</li>
          <li><strong>Sole Active Owner Protection:</strong> Organizations are protected against accidental demotion or deletion of their last active owner.</li>
        </ul>
      </section>

      <section id="encryption" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2 flex items-center gap-2">
          <Key className="w-4 h-4 text-amber-400" />
          <span>4. Credential Encryption at Rest</span>
        </h2>
        <p>
          User-supplied API keys for broker sandbox connections are encrypted at rest using <strong>AES-256 in Galois/Counter Mode (GCM)</strong> with random 12-byte initialization vectors and 16-byte authentication tags. Keys are never logged and are decrypted solely in memory when dispatching sandbox requests.
        </p>
      </section>

      <section id="infrastructure" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2 flex items-center gap-2">
          <Layers className="w-4 h-4 text-sky-400" />
          <span>5. Infrastructure &amp; HTTP Security Headers</span>
        </h2>
        <p>The web reverse proxy enforces institutional-grade HTTP security headers:</p>
        <ul className="list-disc pl-5 space-y-1.5 text-slate-300 text-xs sm:text-sm">
          <li><code className="text-sky-400 font-mono">Content-Security-Policy: default-src 'self' ...</code></li>
          <li><code className="text-sky-400 font-mono">X-Frame-Options: DENY</code> (anti-clickjacking)</li>
          <li><code className="text-sky-400 font-mono">X-Content-Type-Options: nosniff</code> (MIME protection)</li>
          <li><code className="text-sky-400 font-mono">Referrer-Policy: strict-origin-when-cross-origin</code></li>
          <li><code className="text-sky-400 font-mono">Strict-Transport-Security: max-age=31536000</code></li>
        </ul>
      </section>

      <section id="vulnerability" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>6. Coordinated Vulnerability Disclosure</span>
        </h2>
        <p>
          Security researchers and users discovering potential platform vulnerabilities are encouraged to report findings directly through coordinated disclosure channels. We commit to prompt triage, non-retaliation for responsible testing within sandbox bounds, and transparent remediation.
        </p>
      </section>
    </LegalPageLayout>
  );
};
