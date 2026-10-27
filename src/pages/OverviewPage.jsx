import React, { useState, useEffect } from 'react';
import { fetchDashboardData } from '../services/api';

const PRODUCT_CATALOG = {
  prod_001: { name: 'Voyage Horizon ANC', category: 'Over-Ear Headphones', sku: 'VYG-ANC-01' },
  prod_002: { name: 'Voyage StreamCast Pro', category: 'Studio Condenser Mic', sku: 'VYG-MIC-02' },
  prod_003: { name: 'Voyage Apex Wireless', category: 'Ergonomic Gaming Mouse', sku: 'VYG-MSE-03' },
  prod_004: { name: 'Voyage UltraVision 27"', category: 'QHD 165Hz Gaming Monitor', sku: 'VYG-MON-04' },
  'prod-001': { name: 'Voyage Horizon ANC', category: 'Over-Ear Headphones', sku: 'VYG-ANC-01' },
  steam_games: { name: 'Voyage Steam Gaming Suite', category: 'PC Software Suite', sku: 'VYG-STM-05' },
};

export default function OverviewPage({ selectedProduct = 'prod_001', onNavigateIssue }) {
  const [backendData, setBackendData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const productMeta = PRODUCT_CATALOG[selectedProduct] || {
    name: selectedProduct.replace(/_/g, ' '),
    category: 'Voyage Hardware Series',
    sku: selectedProduct,
  };

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

  // Real backend metrics
  const healthScore = backendData?.health_score ?? 50;
  const reviewCount = backendData?.review_count ?? 0;
  const flaggedCount = backendData?.flagged_count ?? 0;
  const summaryText = backendData?.product_summary || `Overall Health Score ${healthScore}/100 across ${reviewCount} customer reviews.`;
  const featureSentiment = backendData?.feature_sentiment || {};
  const platformComparison = backendData?.platform_comparison || {};
  const allIssues = backendData?.issues || [];

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* Page Header with High-Contrast Hierarchy */}
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-zinc-800/80 pb-6">
        <div>
          <div className="text-[11px] font-mono uppercase tracking-widest text-zinc-400 mb-1">
            {productMeta.category} • {productMeta.sku}
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">
            {productMeta.name}
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Real-time quality intelligence aggregated across Amazon, Flipkart, JioMart, Brand Direct &amp; Steam.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="px-3.5 py-1.5 rounded-lg bg-zinc-900 border border-zinc-700/80 text-xs font-mono text-zinc-200 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
            <span>Target: <strong className="text-white">{selectedProduct}</strong></span>
          </div>
          {isLoading && (
            <span className="text-xs text-zinc-400 font-mono animate-pulse">Syncing...</span>
          )}
        </div>
      </div>

      {/* Executive Summary Card (Clean, Non-Cluttered) */}
      <div className="p-6 rounded-2xl bg-[#111217] border border-zinc-800 shadow-lg">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-bold uppercase tracking-wider text-zinc-300 font-mono">
            Executive Synthesis
          </span>
          <span className="text-[11px] font-mono text-zinc-400">
            5 Storefront Sources
          </span>
        </div>
        <p className="text-base font-semibold text-white leading-relaxed">
          {summaryText}
        </p>
      </div>

      {/* Top 4 Core KPI Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Health Score */}
        <div className="p-5 rounded-xl bg-[#111217] border border-zinc-800 flex flex-col justify-between">
          <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wide">
            Product Health
          </span>
          <div className="my-3 flex items-baseline gap-2">
            <span className="text-4xl font-extrabold tracking-tight text-white font-mono">
              {healthScore}
            </span>
            <span className="text-xs text-zinc-500 font-mono">/ 100</span>
          </div>
          <div className="text-[11px] text-zinc-400 border-t border-zinc-800/80 pt-2 font-medium">
            Weighted consumer sentiment
          </div>
        </div>

        {/* Metric 2: Reviews Analyzed */}
        <div className="p-5 rounded-xl bg-[#111217] border border-zinc-800 flex flex-col justify-between">
          <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wide">
            Ingested Reviews
          </span>
          <div className="my-3 flex items-baseline gap-2">
            <span className="text-4xl font-extrabold tracking-tight text-white font-mono">
              {reviewCount}
            </span>
            <span className="text-xs text-zinc-500 font-mono">total</span>
          </div>
          <div className="text-[11px] text-zinc-400 border-t border-zinc-800/80 pt-2 font-medium">
            Verified across 5 retail channels
          </div>
        </div>

        {/* Metric 3: Quarantined */}
        <div className="p-5 rounded-xl bg-[#111217] border border-zinc-800 flex flex-col justify-between">
          <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wide">
            Trust &amp; Spam Filter
          </span>
          <div className="my-3 flex items-baseline gap-2">
            <span className="text-4xl font-extrabold tracking-tight text-white font-mono">
              {flaggedCount}
            </span>
            <span className="text-xs text-zinc-500 font-mono">
              ({reviewCount > 0 ? Math.round((flaggedCount / reviewCount) * 100) : 0}%)
            </span>
          </div>
          <div className="text-[11px] text-zinc-400 border-t border-zinc-800/80 pt-2 font-medium">
            Incentivized &amp; bot reviews isolated
          </div>
        </div>

        {/* Metric 4: Active Issue Clusters */}
        <div className="p-5 rounded-xl bg-[#111217] border border-zinc-800 flex flex-col justify-between">
          <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wide">
            Defect Clusters
          </span>
          <div className="my-3 flex items-baseline gap-2">
            <span className="text-4xl font-extrabold tracking-tight text-white font-mono">
              {allIssues.length}
            </span>
            <span className="text-xs text-zinc-500 font-mono">clusters</span>
          </div>
          <div className="text-[11px] text-zinc-400 border-t border-zinc-800/80 pt-2 font-medium">
            Prioritized by RAG forensic graph
          </div>
        </div>
      </div>

      {/* Feature Sentiment Matrix (Clean Monochrome Bright Gray & Red) */}
      <div className="p-6 rounded-2xl bg-[#111217] border border-zinc-800 space-y-5">
        <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
          <div>
            <h2 className="text-base font-bold text-white tracking-tight">Feature Sentiment Breakdown</h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              Consumer perception scored across primary hardware and operational attributes
            </p>
          </div>
          <span className="text-[11px] text-zinc-400 font-mono">
            {Object.keys(featureSentiment).length} Features Extracted
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(featureSentiment).map(([feat, stats]) => {
            const posPct = Math.round((stats.positive || 0) * 100);
            const negPct = Math.round((stats.negative || 0) * 100);

            return (
              <div key={feat} className="p-4 rounded-xl bg-[#16171e] border border-zinc-800/80 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white capitalize text-sm">{feat.replace(/_/g, ' ')}</span>
                  <span className="text-[11px] font-mono text-zinc-400">
                    {stats.count} mentions
                  </span>
                </div>

                <div className="space-y-1.5">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className="text-zinc-200">Positive {posPct}%</span>
                    <span className="text-rose-400">Negative {negPct}%</span>
                  </div>
                  {/* Clean Monochrome Bar: White Positive / Crimson Negative / Dark Track */}
                  <div className="w-full h-2 rounded-full bg-zinc-800 flex overflow-hidden">
                    <div style={{ width: `${posPct}%` }} className="bg-white transition-all duration-300" />
                    <div style={{ width: `${negPct}%` }} className="bg-rose-500 transition-all duration-300" />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Priority Defect Clusters Table */}
      <div className="p-6 rounded-2xl bg-[#111217] border border-zinc-800 space-y-4">
        <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
          <div>
            <h2 className="text-base font-bold text-white tracking-tight">
              Priority Defect Clusters ({allIssues.length})
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              Ranked by confidence and failure severity from clustering engine
            </p>
          </div>
          <button
            onClick={() => onNavigateIssue && onNavigateIssue(allIssues[0]?.id)}
            className="text-xs text-zinc-300 hover:text-white transition-colors font-medium cursor-pointer"
          >
            Inspect in Detail &rarr;
          </button>
        </div>

        {allIssues.length === 0 ? (
          <div className="p-8 text-center text-zinc-500 text-xs font-mono">
            No defect issues detected for {productMeta.name}.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-400 text-[11px]">
                  <th className="pb-3 font-semibold uppercase tracking-wider font-mono">Feature</th>
                  <th className="pb-3 font-semibold uppercase tracking-wider font-mono">Type</th>
                  <th className="pb-3 font-semibold uppercase tracking-wider font-mono">Severity</th>
                  <th className="pb-3 font-semibold uppercase tracking-wider font-mono">Confidence</th>
                  <th className="pb-3 font-semibold uppercase tracking-wider font-mono">Scope</th>
                  <th className="pb-3 font-semibold uppercase tracking-wider font-mono">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {allIssues.slice(0, 8).map((issue) => (
                  <tr key={issue.id} className="hover:bg-white/[0.03] transition-colors">
                    <td className="py-3 pr-4">
                      <div className="font-semibold text-white capitalize">{issue.feature.replace(/_/g, ' ')}</div>
                      <div className="text-[10px] text-zinc-500 font-mono">{issue.id}</div>
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
                      <span className="font-bold text-white font-mono">
                        {Math.round((issue.confidence || 0) * 100)}%
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-zinc-300 font-mono text-[11px]">
                      {issue.affected_pct != null
                        ? `${Math.round(issue.affected_pct * 100)}% mentions`
                        : 'Systemic'}
                    </td>
                    <td className="py-3">
                      <button
                        onClick={() => onNavigateIssue && onNavigateIssue(issue.id)}
                        className="px-3 py-1 rounded bg-zinc-800 hover:bg-white hover:text-zinc-950 text-zinc-200 border border-zinc-700 text-[11px] font-semibold transition-all cursor-pointer"
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

      {/* Storefront Channel Comparison (Clean Monochrome) */}
      <div className="p-6 rounded-2xl bg-[#111217] border border-zinc-800 space-y-4">
        <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
          <h2 className="text-base font-bold text-white tracking-tight">Storefront Channel Breakdown</h2>
          <span className="text-zinc-400 text-xs font-mono">5 Retail Streams</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(platformComparison).map(([platformKey, data]) => {
            const pHealth = data.health_score ?? '—';
            return (
              <div key={platformKey} className="p-4 rounded-xl bg-[#16171e] border border-zinc-800/80 space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white capitalize text-sm">{platformKey}</span>
                  <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-zinc-800 text-white border border-zinc-700">
                    Health: {pHealth}
                  </span>
                </div>
                <div className="space-y-1 text-xs text-zinc-400">
                  <div className="flex justify-between">
                    <span>Performance:</span>
                    <span className="font-mono text-white font-medium">
                      {Math.round(((data.feature_sentiment?.performance?.positive) || 0) * 100)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Battery Life:</span>
                    <span className="font-mono text-white font-medium">
                      {Math.round(((data.feature_sentiment?.battery_life?.positive) || 0) * 100)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Packaging:</span>
                    <span className="font-mono text-white font-medium">
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
