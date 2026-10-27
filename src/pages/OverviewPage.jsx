import React, { useState, useEffect } from 'react';
import { fetchDashboardData } from '../services/api';

export default function OverviewPage({ selectedProduct = 'prod_001', onNavigateIssue, roleLens }) {
  const [backendData, setBackendData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const product = { id: selectedProduct, name: selectedProduct.replace('_', ' ') };

  useEffect(() => {
    let isMounted = true;
    async function loadBackendDashboard() {
      setIsLoading(true);
      try {
        const data = await fetchDashboardData(selectedProduct);
        if (isMounted && data) {
          setBackendData(data);
        }
      } catch (err) {
        console.warn('Backend load error:', err);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    loadBackendDashboard();
    return () => {
      isMounted = false;
    };
  }, [selectedProduct]);

  // Departmental lens mapping
  const LENS_CONFIGS = {
    designer: {
      badge: 'Product Designer (UX / Hardware)',
      color: 'text-violet-300 bg-violet-500/10 border-violet-500/20',
      headline: 'Ergonomics & Hardware Focus',
      focusTag: 'Design & CMF',
      filterIssues: ['packaging', 'build_quality', 'battery_life'],
    },
    qa: {
      badge: 'QA & Engineering Lens',
      color: 'text-zinc-200 bg-zinc-800 border-zinc-700',
      headline: 'Defect Triage & Cluster Analysis',
      focusTag: 'Engineering Triage',
      filterIssues: null,
    },
    operations: {
      badge: 'Operations & Logistics Lens',
      color: 'text-sky-300 bg-sky-500/10 border-sky-500/20',
      headline: 'Supply Chain & Transit Telemetry',
      focusTag: 'Logistics SLA',
      filterIssues: ['packaging', 'delivery_speed', 'build_quality'],
    },
    support: {
      badge: 'Customer Support & CX Lens',
      color: 'text-teal-300 bg-teal-500/10 border-teal-500/20',
      headline: 'Customer Friction & Resolution',
      focusTag: 'Customer Outreach',
      filterIssues: ['customer_support', 'battery_life', 'packaging', 'value_for_money'],
    },
    marketing: {
      badge: 'Marketing & Brand Lens',
      color: 'text-purple-300 bg-purple-500/10 border-purple-500/20',
      headline: 'Brand Perception & Sentiment Trends',
      focusTag: 'Social Proof',
      filterIssues: ['value_for_money', 'performance', 'battery_life'],
    },
    leadership: {
      badge: 'Executive & Leadership Lens',
      color: 'text-amber-300 bg-amber-500/10 border-amber-500/20',
      headline: 'Portfolio Health & Anomaly Triage',
      focusTag: 'Enterprise View',
      filterIssues: null,
    },
  };

  const currentLens = LENS_CONFIGS[roleLens] || LENS_CONFIGS.designer;

  // Real backend metrics
  const healthScore = backendData?.health_score ?? 50;
  const reviewCount = backendData?.review_count ?? 0;
  const flaggedCount = backendData?.flagged_count ?? 0;
  const summaryText = backendData?.product_summary || `Overall Health Score ${healthScore}/100 across ${reviewCount} reviews.`;
  const featureSentiment = backendData?.feature_sentiment || {};
  const platformComparison = backendData?.platform_comparison || {};
  const whatChanged = backendData?.what_changed_this_week || {};

  // Filter issues from backend
  const allIssues = backendData?.issues || [];
  const displayedIssues = currentLens.filterIssues
    ? allIssues.filter((i) => currentLens.filterIssues.includes(i.feature))
    : allIssues;

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Portfolio Health &amp; Diagnostics
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Displaying live telemetry for <strong className="text-white font-mono">{selectedProduct}</strong> · Authenticated Lens: <strong className="text-zinc-200">{currentLens.badge}</strong>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-semibold ${currentLens.color}`}>
            <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
            <span>Active Lens:</span>
            <span className="uppercase tracking-wider">{currentLens.badge.split('(')[0].trim()}</span>
          </div>
          {isLoading && (
            <span className="text-xs text-zinc-300 font-mono animate-pulse">Syncing backend...</span>
          )}
        </div>
      </div>

      {/* Backend Diagnostic Synthesis Banner */}
      <div className="p-5 rounded-xl bg-[#1c1d24] border border-zinc-700/60 flex items-start gap-4">
        <div className="w-9 h-9 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center shrink-0">
          <svg className="w-4 h-4 text-zinc-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
        </div>
        <div className="flex-1 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-zinc-200 uppercase tracking-wider font-mono">
              Diagnostic Synthesis
            </span>
            <span className="text-[10px] font-mono text-zinc-400 px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800">
              {currentLens.focusTag}
            </span>
          </div>
          <p className="text-sm font-medium text-zinc-200 leading-relaxed">
            {summaryText}
          </p>
          <div className="text-[11px] text-zinc-400 pt-1 flex items-center gap-4">
            <span>Total Reviews: <strong className="text-white">{reviewCount}</strong></span>
            <span>Quarantined: <strong className="text-amber-300">{flaggedCount}</strong></span>
            <span>Active Clusters: <strong className="text-white">{allIssues.length}</strong></span>
          </div>
        </div>
      </div>

      {/* Top Telemetry Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Health Score */}
        <div className="p-5 rounded-xl bg-[#1c1d24] border border-zinc-700/60 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span>Product Health Score</span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-teal-500/10 text-teal-300 border border-teal-500/20">
              Calibrated
            </span>
          </div>
          <div className="my-3 flex items-baseline gap-2">
            <span className={`text-4xl font-extrabold tracking-tight ${healthScore >= 70 ? 'text-teal-400' : healthScore >= 50 ? 'text-amber-300' : 'text-rose-400'}`}>
              {healthScore}
            </span>
            <span className="text-xs text-zinc-500">/ 100</span>
          </div>
          <div className="text-[11px] text-zinc-500 border-t border-zinc-800/60 pt-2">
            Feature sentiment weighted
          </div>
        </div>

        {/* Card 2: Total Ingested Reviews */}
        <div className="p-5 rounded-xl bg-[#1c1d24] border border-zinc-700/60 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span>Total Ingested Reviews</span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-200 border border-zinc-700">
              Verified
            </span>
          </div>
          <div className="my-3 flex items-baseline gap-2">
            <span className="text-4xl font-extrabold tracking-tight text-white">{reviewCount}</span>
            <span className="text-xs text-zinc-500">reviews</span>
          </div>
          <div className="text-[11px] text-zinc-500 border-t border-zinc-800/60 pt-2">
            Across 5 storefront channels
          </div>
        </div>

        {/* Card 3: Flagged & Quarantined */}
        <div className="p-5 rounded-xl bg-[#1c1d24] border border-zinc-700/60 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span>Flagged / Quarantined</span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
              Trust Filter
            </span>
          </div>
          <div className="my-3 flex items-baseline gap-2">
            <span className="text-4xl font-extrabold tracking-tight text-amber-300">{flaggedCount}</span>
            <span className="text-xs text-zinc-500">
              ({reviewCount > 0 ? Math.round((flaggedCount / reviewCount) * 100) : 0}%)
            </span>
          </div>
          <div className="text-[11px] text-zinc-500 border-t border-zinc-800/60 pt-2">
            Spam / low-trust anomaly reviews
          </div>
        </div>

        {/* Card 4: Detected Issues */}
        <div className="p-5 rounded-xl bg-[#1c1d24] border border-zinc-700/60 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span>Detected Issue Clusters</span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20">
              Insights
            </span>
          </div>
          <div className="my-3 flex items-baseline gap-2">
            <span className="text-4xl font-extrabold tracking-tight text-purple-300">{allIssues.length}</span>
            <span className="text-xs text-zinc-500">clusters</span>
          </div>
          <div className="text-[11px] text-zinc-500 border-t border-zinc-800/60 pt-2">
            Systemic &amp; batch defect clusters
          </div>
        </div>
      </div>

      {/* Feature Sentiment Matrix */}
      <div className="p-5 rounded-xl bg-[#1c1d24] border border-zinc-700/60 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white">Feature Sentiment Breakdown</h2>
            <p className="text-xs text-zinc-400">
              Zero-shot anchor similarity scoring over all processed customer mentions
            </p>
          </div>
          <span className="text-[11px] text-zinc-400 font-mono">
            {Object.keys(featureSentiment).length} Features Extracted
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {Object.entries(featureSentiment).map(([feat, stats]) => {
            const trend = whatChanged[feat] || 'stable';
            const posPct = Math.round((stats.positive || 0) * 100);
            const negPct = Math.round((stats.negative || 0) * 100);

            return (
              <div key={feat} className="p-3.5 rounded-lg bg-[#14151a] border border-zinc-700/50 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white capitalize">{feat.replace(/_/g, ' ')}</span>
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                      trend === 'up'
                        ? 'bg-teal-500/10 text-teal-300 border-teal-500/20'
                        : trend === 'down'
                        ? 'bg-rose-500/10 text-rose-300 border-rose-500/20'
                        : 'bg-zinc-900 text-zinc-400 border-zinc-800'
                    }`}
                  >
                    {trend === 'up' ? 'Improving' : trend === 'down' ? 'Declining' : 'Stable'}
                  </span>
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-teal-400">Positive: {posPct}%</span>
                    <span className="text-rose-400">Negative: {negPct}%</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-zinc-800 flex overflow-hidden">
                    <div style={{ width: `${posPct}%` }} className="bg-teal-400/90 transition-all duration-300" />
                    <div style={{ width: `${negPct}%` }} className="bg-rose-400/90 transition-all duration-300" />
                  </div>
                </div>

                <div className="flex justify-between text-[10px] text-zinc-500 pt-1 border-t border-zinc-800/60">
                  <span>Mentions: {stats.count}</span>
                  <span className="font-mono">Weight: {feat === 'performance' ? '20%' : feat === 'battery_life' ? '18%' : '15%'}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Real Issues Table */}
      <div className="p-5 rounded-xl bg-[#1c1d24] border border-zinc-700/60 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white">
              {currentLens.badge.split('(')[0].trim()} Priority Clusters ({displayedIssues.length})
            </h2>
            <p className="text-xs text-zinc-400">
              Ranked by confidence &amp; severity directly from the backend clustering engine
            </p>
          </div>
          <button
            onClick={() => onNavigateIssue && onNavigateIssue(displayedIssues[0]?.id)}
            className="text-xs text-zinc-200 hover:text-white transition-colors font-medium cursor-pointer"
          >
            Inspect in Detail &rarr;
          </button>
        </div>

        {displayedIssues.length === 0 ? (
          <div className="p-8 text-center text-zinc-500 text-xs">
            No defect issues detected for this role filter on {selectedProduct}.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-400 text-[11px]">
                  <th className="pb-3 font-semibold">Feature</th>
                  <th className="pb-3 font-semibold">Type</th>
                  <th className="pb-3 font-semibold">Severity</th>
                  <th className="pb-3 font-semibold">Confidence</th>
                  <th className="pb-3 font-semibold">Affected Scope</th>
                  <th className="pb-3 font-semibold">Backend Recommendation</th>
                  <th className="pb-3 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/50">
                {displayedIssues.slice(0, 10).map((issue) => (
                  <tr key={issue.id} className="hover:bg-white/5 transition-colors group">
                    <td className="py-3 pr-4">
                      <div className="font-semibold text-white capitalize">{issue.feature.replace(/_/g, ' ')}</div>
                      <div className="text-[10px] text-zinc-500 font-mono truncate max-w-[120px]">{issue.id}</div>
                    </td>
                    <td className="py-3 pr-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-zinc-800 text-zinc-200 border border-zinc-700 font-mono">
                        {issue.issue_type}
                      </span>
                    </td>
                    <td className="py-3 pr-4">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
                          issue.severity === 'high'
                            ? 'bg-rose-500/10 text-rose-300 border-rose-500/25'
                            : issue.severity === 'medium'
                            ? 'bg-amber-500/10 text-amber-300 border-amber-500/25'
                            : 'bg-zinc-800 text-zinc-300 border-zinc-700'
                        }`}
                      >
                        {issue.severity}
                      </span>
                    </td>
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-1.5 font-mono">
                        <span className="font-bold text-teal-400">
                          {Math.round((issue.confidence || 0) * 100)}%
                        </span>
                        <span className="text-[10px] text-zinc-500">({issue.confidence_level})</span>
                      </div>
                    </td>
                    <td className="py-3 pr-4 text-zinc-300">
                      {issue.affected_pct != null
                        ? `${Math.round(issue.affected_pct * 100)}% of mentions`
                        : 'Systemic'}
                    </td>
                    <td className="py-3 pr-4 max-w-sm text-zinc-300 truncate" title={issue.recommendation}>
                      {issue.recommendation || 'No automated action generated.'}
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => onNavigateIssue && onNavigateIssue(issue.id)}
                        className="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 hover:text-white border border-zinc-700 text-[11px] font-medium transition-colors cursor-pointer"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Storefront Platform Breakdown */}
      <div className="p-5 rounded-xl bg-[#1c1d24] border border-zinc-700/60 space-y-4">
        <div className="flex items-center justify-between text-xs">
          <h2 className="text-base font-bold text-white">Storefront Channel Breakdown</h2>
          <span className="text-zinc-400 font-mono">Aggregated per platform</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {Object.entries(platformComparison).map(([platformKey, data]) => {
            const pHealth = data.health_score ?? '—';
            return (
              <div key={platformKey} className="p-4 rounded-xl bg-[#14151a] border border-zinc-700/50 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white capitalize text-sm">{platformKey}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${
                    pHealth >= 70
                      ? 'bg-teal-500/10 text-teal-300 border-teal-500/25'
                      : pHealth >= 50
                      ? 'bg-amber-500/10 text-amber-300 border-amber-500/25'
                      : 'bg-rose-500/10 text-rose-300 border-rose-500/25'
                  }`}>
                    Health: {pHealth}
                  </span>
                </div>
                <div className="space-y-1.5 text-[11px] text-zinc-400">
                  <div className="flex justify-between">
                    <span>Performance Score:</span>
                    <span className="font-mono text-white">
                      {Math.round(((data.feature_sentiment?.performance?.positive) || 0) * 100)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Battery Feedback:</span>
                    <span className="font-mono text-white">
                      {Math.round(((data.feature_sentiment?.battery_life?.positive) || 0) * 100)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Packaging Health:</span>
                    <span className="font-mono text-white">
                      {Math.round(((data.feature_sentiment?.packaging?.positive) || 0) * 100)}%
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
