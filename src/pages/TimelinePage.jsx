import React, { useState, useEffect } from 'react';
import { fetchDashboardData, fetchReviews } from '../services/api';

export default function TimelinePage({ selectedProduct = 'prod_001' }) {
  const [weeklyTrends, setWeeklyTrends] = useState([]);
  const [timeseriesVisual, setTimeseriesVisual] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [selectedWeekIdx, setSelectedWeekIdx] = useState(0);

  useEffect(() => {
    let isMounted = true;
    async function loadTimelineData() {
      try {
        const [dash, revRes] = await Promise.all([
          fetchDashboardData(selectedProduct),
          fetchReviews(selectedProduct, { limit: 30 }),
        ]);
        if (!isMounted) return;

        if (dash?.weekly_trends && Array.isArray(dash.weekly_trends)) {
          setWeeklyTrends(dash.weekly_trends);
          setSelectedWeekIdx(Math.max(0, dash.weekly_trends.length - 1));
        }
        if (dash?.timeseries_visual) {
          setTimeseriesVisual(dash.timeseries_visual);
        }
        if (revRes?.reviews && Array.isArray(revRes.reviews)) {
          setReviews(revRes.reviews);
        }
      } catch (err) {
        console.warn('Timeline data load error:', err);
      }
    }

    loadTimelineData();
    return () => {
      isMounted = false;
    };
  }, [selectedProduct]);

  const activeWeek = weeklyTrends[selectedWeekIdx] || weeklyTrends[0] || { week: 'Current' };
  const hints = timeseriesVisual?.hints || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-500/20 text-amber-300 border border-amber-500/30 font-mono">
              Lead-Time Telemetry
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Forensic Lead-Time Timeline
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Tracking weekly sentiment trajectory and batch defect spikes for <strong className="text-white font-mono">{selectedProduct}</strong>
          </p>
        </div>

        {/* Week Scrubber Controls */}
        {weeklyTrends.length > 0 && (
          <div className="flex items-center gap-3 p-2 rounded-xl bg-[#1c1d24] border border-zinc-700/60">
            <span className="text-xs text-zinc-400 font-mono">
              Week: <strong className="text-zinc-200">{activeWeek.week}</strong> ({selectedWeekIdx + 1} of {weeklyTrends.length})
            </span>
            <input
              type="range"
              min="0"
              max={Math.max(0, weeklyTrends.length - 1)}
              value={selectedWeekIdx}
              onChange={(e) => setSelectedWeekIdx(Number(e.target.value))}
              className="accent-zinc-300 cursor-pointer"
            />
          </div>
        )}
      </div>

      {/* Detected Spike Hints Banner (Real Backend timeseries_visual) */}
      {hints.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {hints.map((hint, i) => (
            <div key={i} className="p-4 rounded-xl bg-[#1c1d24] border border-amber-500/30 space-y-1 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-amber-400 uppercase tracking-wider">{hint.label}</span>
                <span className="font-mono text-[10px] text-zinc-400">{hint.week}</span>
              </div>
              <div className="font-semibold text-white capitalize">{hint.feature.replace(/_/g, ' ')}</div>
              <p className="text-zinc-300 text-[11px] leading-relaxed">{hint.detail}</p>
            </div>
          ))}
        </div>
      )}

      {/* Visual Canvas: Weekly Feature Sentiment Progression */}
      <div className="p-6 rounded-2xl bg-[#1c1d24] border border-zinc-700/60 space-y-5">
        <div className="flex items-center justify-between text-xs border-b border-zinc-800 pb-3">
          <span className="font-bold text-white uppercase tracking-wider">Weekly Feature Health Trajectory</span>
          <span className="font-mono text-zinc-400">Week: {activeWeek.week}</span>
        </div>

        {/* Feature Bars for selected week */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {['performance', 'battery_life', 'build_quality', 'packaging', 'customer_support', 'delivery_speed', 'value_for_money'].map((feat) => {
            const pos = activeWeek[feat];
            const neg = activeWeek[`${feat}_negative`];
            const hasData = pos != null;

            return (
              <div key={feat} className="p-3.5 rounded-xl bg-[#14151a] border border-zinc-700/50 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white capitalize">{feat.replace(/_/g, ' ')}</span>
                  <span className="font-mono text-[11px] text-zinc-400">
                    {hasData ? `${Math.round(pos * 100)}% Positive` : 'No mentions'}
                  </span>
                </div>
                {hasData && (
                  <div className="w-full h-2 rounded-full bg-zinc-800 flex overflow-hidden">
                    <div style={{ width: `${Math.round(pos * 100)}%` }} className="bg-teal-400" />
                    <div style={{ width: `${Math.round((neg || 0) * 100)}%` }} className="bg-rose-400" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Real Reviews Timeline Log (from SQLite) */}
      <div className="p-6 rounded-2xl bg-[#1c1d24] border border-zinc-700/60 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-white">Ingested Review Log from Database ({reviews.length})</h2>
          <span className="text-xs text-zinc-400 font-mono">Real-time SQLite Stream</span>
        </div>

        <div className="space-y-2 text-xs">
          {reviews.slice(0, 8).map((rev) => (
            <div key={rev.id} className="p-3 rounded-lg bg-[#14151a] border border-zinc-700/50 flex items-start justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-zinc-200 text-[11px] truncate max-w-[140px]">{rev.id}</span>
                  <span className="text-[10px] text-amber-300 font-semibold">{rev.rating}/5 rating</span>
                  <span className="text-[10px] text-zinc-400 capitalize">{rev.platform}</span>
                  <span className="text-[10px] text-zinc-500 font-mono">{rev.timestamp ? new Date(rev.timestamp).toLocaleDateString() : 'recent'}</span>
                </div>
                <p className="text-zinc-300 italic">"{rev.review_text}"</p>
              </div>
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold shrink-0 ${rev.status === 'processed' ? 'bg-teal-500/15 text-teal-300 border border-teal-500/25' : 'bg-amber-500/15 text-amber-300 border border-amber-500/25'}`}>
                {rev.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
