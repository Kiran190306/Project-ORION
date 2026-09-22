import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, ShieldAlert, FileText, CheckCircle2 } from 'lucide-react';
import { PublicFooter } from '../layout/PublicFooter';

interface LegalSection {
  id: string;
  title: string;
}

interface LegalPageLayoutProps {
  title: string;
  version: string;
  effectiveDate: string;
  badgeLabel?: string;
  badgeVariant?: 'default' | 'warning' | 'info';
  sections: LegalSection[];
  children: React.ReactNode;
}

export const LegalPageLayout: React.FC<LegalPageLayoutProps> = ({
  title,
  version,
  effectiveDate,
  badgeLabel = 'Draft for Legal Review',
  badgeVariant = 'default',
  sections,
  children,
}) => {
  const [activeSection, setActiveSection] = useState(sections[0]?.id || '');
  const badgeClasses =
    badgeVariant === 'info'
      ? 'border-sky-800/60 bg-sky-950/40 text-sky-300'
      : badgeVariant === 'warning'
      ? 'border-amber-800/60 bg-amber-950/40 text-amber-300'
      : 'border-amber-800/60 bg-amber-950/40 text-amber-300';

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col text-slate-100 font-sans selection:bg-sky-500/30 selection:text-sky-200">
      {/* Top Header */}
      <header className="sticky top-0 z-30 border-b border-slate-900 bg-slate-950/90 backdrop-blur-md px-4 sm:px-8 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3 sm:gap-4">
          <Link
            to="/login"
            className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-400 hover:text-sky-400 transition-colors py-1 px-2.5 rounded-lg border border-slate-800 hover:border-slate-700 bg-slate-900/60"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Return to Terminal</span>
            <span className="sm:hidden">Back</span>
          </Link>
          <div className="h-4 w-px bg-slate-800" />
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold text-sky-400 text-sm">Ω</span>
            <span className="font-mono text-xs font-semibold text-slate-200 tracking-wider">
              PROJECT ORION
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <span className="px-2 py-0.5 rounded text-[11px] font-mono border border-slate-800 bg-slate-900 text-slate-400">
            v{version}
          </span>
          <span className={`hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono border ${badgeClasses}`}>
            <ShieldAlert className="w-3 h-3 text-amber-400" />
            {badgeLabel}
          </span>
        </div>
      </header>

      {/* Hero Banner */}
      <div className="border-b border-slate-900 bg-gradient-to-b from-slate-900/40 to-slate-950/60 px-4 sm:px-8 py-8 sm:py-10">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-slate-400 mb-2">
            <span>PUBLIC BETA LEGAL DISCLOSURE</span>
            <span>&bull;</span>
            <span>EFFECTIVE: {effectiveDate}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-100 font-sans">
            {title}
          </h1>
          <p className="mt-2 text-xs sm:text-sm text-slate-400 font-mono">
            Project ORION &bull; Institutional Quantitative Paper Trading Software Architecture
          </p>
        </div>
      </div>

      {/* Main Content with Sidebar Table of Contents */}
      <div className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-8 py-8 flex flex-col lg:flex-row gap-8">
        {/* Sidebar Table of Contents */}
        <aside className="w-full lg:w-64 flex-shrink-0">
          <div className="lg:sticky lg:top-20 p-4 rounded-xl border border-slate-900 bg-slate-900/40 space-y-3">
            <div className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-sky-400" />
              <span>Table of Contents</span>
            </div>
            <nav className="space-y-1">
              {sections.map((section) => (
                <a
                  key={section.id}
                  href={`#${section.id}`}
                  onClick={() => setActiveSection(section.id)}
                  className={`block text-xs py-1.5 px-2 rounded-lg transition-colors font-mono ${
                    activeSection === section.id
                      ? 'bg-sky-500/10 text-sky-400 font-medium'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                  }`}
                >
                  {section.title}
                </a>
              ))}
            </nav>

            <div className="pt-3 border-t border-slate-800/80">
              <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 text-[11px] font-mono text-slate-400 space-y-1">
                <div className="text-slate-200 font-semibold flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-sky-400" />
                  <span>Verified Architecture</span>
                </div>
                <div>Paper Trading Only</div>
                <div className="text-amber-400 font-semibold">$0.00 Capital at Risk</div>
              </div>
            </div>
          </div>
        </aside>

        {/* Content Body */}
        <main className="flex-1 min-w-0 space-y-6 text-sm text-slate-300 leading-relaxed">
          {children}
        </main>
      </div>

      <PublicFooter />
    </div>
  );
};
