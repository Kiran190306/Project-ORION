import React from 'react';
import { LegalPageLayout } from '../components/legal/LegalPageLayout';
import { AlertCircle } from 'lucide-react';

const SECTIONS = [
  { id: 'internal-notice', title: '1. Implementation Notice' },
  { id: 'scope', title: '2. Scope of Platform' },
  { id: 'paper-trading', title: '3. Paper Trading Invariant' },
  { id: 'accounts', title: '4. Accounts & Security' },
  { id: 'acceptable-use', title: '5. Acceptable Use' },
  { id: 'intellectual-property', title: '6. Intellectual Property' },
  { id: 'warranties', title: '7. Disclaimer of Warranties' },
  { id: 'liability', title: '8. Limitation of Liability' },
  { id: 'governing-law', title: '9. Governing Law' },
];

export const TermsPage: React.FC = () => {
  return (
    <LegalPageLayout
      title="Terms of Service"
      version="1.0"
      effectiveDate="2026-09-22"
      sections={SECTIONS}
    >
      <section id="internal-notice" className="p-4 rounded-xl bg-amber-950/30 border border-amber-800/50 text-amber-300 text-xs font-mono flex items-start gap-3">
        <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-400" />
        <div>
          <span className="font-semibold text-amber-200">Internal Implementation Notice:</span>{' '}
          This document is an operational draft defining platform software usage terms for Project ORION during Public Beta. It does not constitute formal legal advice. Corporate entity, governing jurisdiction, statutory dispute venues, and final liability formulations are subject to external legal counsel review.
        </div>
      </section>

      <section id="scope" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2">
          1. Scope of the Platform
        </h2>
        <p>
          Project ORION (&ldquo;the Platform&rdquo;, &ldquo;the Software&rdquo;) is a web-based software suite designed for quantitative financial research, algorithmic strategy backtesting, walk-forward optimization, and simulated paper execution in foreign exchange markets. The Software is provided strictly for research, educational, and simulated evaluation purposes.
        </p>
      </section>

      <section id="paper-trading" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2">
          2. Paper Trading Invariant ($0.00 Capital at Risk)
        </h2>
        <p>
          All trading order submission, execution matching, fill pricing, position monitoring, and profit/loss calculations provided through the Platform operate strictly within a simulated matching environment. The Platform does not execute live market orders, does not connect to live broker execution facilities, and does not hold, custody, or risk real client capital (<strong className="text-amber-400">$0.00 capital at risk</strong>).
        </p>
      </section>

      <section id="accounts" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2">
          3. User Accounts &amp; Security
        </h2>
        <ul className="list-disc pl-5 space-y-1.5 text-slate-300">
          <li><strong>Account Registration:</strong> Users must register with a valid email address and a secure password meeting platform minimum complexity requirements.</li>
          <li><strong>Credential Protection:</strong> You are solely responsible for maintaining the confidentiality of your credentials, session tokens, and passwords.</li>
          <li><strong>Sole Active Owner Protection:</strong> Each tenant organization must maintain at least one active user with OWNER role authority.</li>
          <li><strong>Account Termination:</strong> You may discontinue use of the Platform at any time. Platform administrators reserve the right to suspend or deactivate accounts found in violation of these Terms.</li>
        </ul>
      </section>

      <section id="acceptable-use" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2">
          4. Acceptable Use Policy
        </h2>
        <p>You agree that you will not:</p>
        <ul className="list-disc pl-5 space-y-1.5 text-slate-300">
          <li>Use the Platform to reverse-engineer, decompile, or extract proprietary algorithms or code.</li>
          <li>Probe, scan, or test the vulnerability of the Platform, or breach security or authentication measures.</li>
          <li>Subject the Platform APIs to denial-of-service attacks, automated credential stuffing, or request rates exceeding published rate limits.</li>
          <li>Attempt to connect unauthorized live broker production execution endpoints.</li>
        </ul>
      </section>

      <section id="intellectual-property" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2">
          5. Intellectual Property
        </h2>
        <p>
          All algorithms, software interfaces, documentation, visual designs, and systems comprising Project ORION are proprietary and protected by applicable copyright and intellectual property laws. You retain ownership of custom trading strategy parameters, research configurations, and tearsheets generated through your lawful use of the Platform.
        </p>
      </section>

      <section id="warranties" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2">
          6. Disclaimer of Warranties
        </h2>
        <p className="font-mono text-xs text-slate-400 uppercase leading-normal">
          THE PLATFORM IS PROVIDED ON AN &ldquo;AS IS&rdquo; AND &ldquo;AS AVAILABLE&rdquo; BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, NON-INFRINGEMENT, OR UNINTERRUPTED AVAILABILITY. SIMULATED FILLS, HISTORICAL DATA, AND RESEARCH SCORES MAY CONTAIN LATENCY OR APPROXIMATIONS.
        </p>
      </section>

      <section id="liability" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2">
          7. Limitation of Liability
        </h2>
        <p className="font-mono text-xs text-slate-400 uppercase leading-normal">
          TO THE MAXIMUM EXTENT PERMITTED UNDER APPLICABLE LAW, IN NO EVENT SHALL THE OPERATORS, DEVELOPERS, OR CONTRIBUTORS OF PROJECT ORION BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR FOR LOSS OF PROFITS, DATA, USE, GOODWILL, OR OTHER INTANGIBLE LOSSES, ARISING OUT OF OR IN CONNECTION WITH YOUR ACCESS TO OR USE OF THE SOFTWARE.
        </p>
      </section>

      <section id="governing-law" className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-100 font-sans border-b border-slate-900 pb-2">
          8. Governing Law &amp; Jurisdiction
        </h2>
        <p className="text-xs text-slate-400 italic">
          (Requires jurisdiction-specific legal review. Corporate legal entity, governing state/nation, and formal dispute resolution procedures to be designated upon final commercial entity incorporation.)
        </p>
      </section>
    </LegalPageLayout>
  );
};
