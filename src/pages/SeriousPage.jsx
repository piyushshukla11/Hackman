import React, { useState, useEffect } from 'react';
import { fetchAlerts } from '../services/api';

export default function SeriousPage() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAlerts() {
      try {
        const data = await fetchAlerts();
        if (Array.isArray(data)) {
          setAlerts(data);
        } else if (data && Array.isArray(data.alerts)) {
          setAlerts(data.alerts);
        }
      } catch (err) {
        console.warn('Could not load alerts from backend:', err);
      } finally {
        setLoading(false);
      }
    }
    loadAlerts();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse" />
            <span className="text-xs font-bold text-rose-400 uppercase tracking-wider">
              Safety &amp; Critical Defect Triage
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white tracking-wide">
            Serious Complaints &amp; Spikes ({alerts.length})
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real backend incident queue populated directly from the PRISM database
          </p>
        </div>

        <div className="px-3.5 py-1.5 rounded-xl bg-rose-500/10 text-rose-300 border border-rose-500/25 text-xs font-semibold flex items-center gap-2">
          <svg className="w-3.5 h-3.5 text-rose-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          Live Alerts Active
        </div>
      </div>

      {loading ? (
        <div className="p-8 text-center text-xs text-slate-400">Loading alerts from backend...</div>
      ) : alerts.length === 0 ? (
        <div className="p-8 rounded-2xl bg-[#09090b] border border-white/10 text-center text-xs text-slate-400">
          No unresolved safety or severity alerts in the backend database.
        </div>
      ) : (
        /* Real Incident Queue Cards directly from SQLite */
        <div className="space-y-3">
          {alerts.map((item) => (
            <div key={item.id} className="p-5 rounded-2xl bg-[#09090b] border border-rose-500/20 space-y-3 relative overflow-hidden">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-2.5">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs font-bold text-rose-400 truncate max-w-[120px]">{item.id.slice(0, 8)}...</span>
                  <span className="text-sm font-bold text-white capitalize">{item.feature.replace('_', ' ')}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/10 text-rose-300 border border-rose-500/20 uppercase">
                    {item.severity}
                  </span>
                  <span className="text-xs font-mono text-slate-400 bg-white/5 px-2 py-0.5 rounded">
                    Target: {item.product_id}
                  </span>
                </div>
                <span className="text-xs font-mono text-slate-500">
                  {item.triggered_at ? new Date(item.triggered_at).toLocaleDateString() : 'Active'}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-black/40 border border-white/5 space-y-1">
                <div className="text-[10px] text-slate-500 uppercase font-semibold">Incident Telemetry:</div>
                <p className="text-xs text-slate-200">{item.message}</p>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 text-xs pt-1">
                <span className="text-slate-400 text-[11px]">Status: <strong className="text-amber-300">Under Investigation</strong></span>
                <div className="flex items-center gap-2">
                  <button className="px-3 py-1 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 font-medium transition-colors cursor-pointer">
                    Contact Customer
                  </button>
                  <button className="px-3 py-1 rounded-lg bg-teal-500/15 hover:bg-teal-500/25 border border-teal-500/25 text-teal-300 font-semibold transition-colors cursor-pointer">
                    Mark Resolved
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
