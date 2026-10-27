import React, { useState, useEffect } from 'react';
import { socket } from '../services/socket';

export default function StreamPage() {
  const [filterReason, setFilterReason] = useState('all');
  const [isConnected, setIsConnected] = useState(socket.connected);
  const [lastLiveReview, setLastLiveReview] = useState(null);

  const STAGES = [
    { id: 'P0', name: 'Ingest Gateway', status: 'completed', duration: '12ms' },
    { id: 'P1', name: 'Normalise & Translate', status: 'completed', duration: '180ms' },
    { id: 'P2', name: 'Trust Cascade (G1-G6)', status: 'processing', duration: '45ms' },
    { id: 'P3', name: 'Understand (Features & Sarcasm)', status: 'pending', duration: '—' },
    { id: 'P4', name: 'Batch Inference (B0-B4)', status: 'pending', duration: '—' },
    { id: 'P5', name: 'Graph Integration', status: 'pending', duration: '—' },
  ];

  const INITIAL_EVENTS = [
    { id: 'EV-1092', stage: 'P2 Trust', status: 'WARN', reason: 'BURST_VELOCITY', detail: 'Author ID reviewed 4 products in 10 minutes', time: '18:24:12' },
    { id: 'EV-1091', stage: 'P1 Normalise', status: 'PASS', reason: 'TRANSLATED', detail: 'Hinglish input translated to English via Sarvam', time: '18:24:10' },
    { id: 'EV-1090', stage: 'P2 Trust', status: 'FAIL', reason: 'SHORT_TEXT', detail: 'Text < 2 words. Text discarded, 4.0 star rating COUNTED', time: '18:24:08' },
    { id: 'EV-1089', stage: 'P3 Understand', status: 'PASS', reason: 'AMBIGUITY_CHECK', detail: 'Sarcasm check cleared. Ambiguity Multiplier: 1.0', time: '18:24:05' },
    { id: 'EV-1088', stage: 'P4 Batch', status: 'PASS', reason: 'B2_REGISTRY', detail: 'Matched warehouse W2 ship window -> Batch B-0716', time: '18:24:01' },
    { id: 'EV-1087', stage: 'P2 Trust', status: 'FAIL', reason: 'EXACT_DUP', detail: 'Duplicate text hash rejected and quarantined', time: '18:23:54' },
  ];

  const [streamEvents, setStreamEvents] = useState(INITIAL_EVENTS);

  useEffect(() => {
    function onConnect() {
      setIsConnected(true);
    }
    function onDisconnect() {
      setIsConnected(false);
    }

    function handleNewReview(data) {
      const newEv = {
        id: `EV-${Date.now().toString().slice(-4)}`,
        stage: 'P0 Ingest',
        status: 'PASS',
        reason: 'NEW_SUBMISSION',
        detail: `[${data.platform || 'Storefront'}] ${data.preview_text || 'Submitted review'} (${data.rating}/5 rating)`,
        time: new Date().toLocaleTimeString(),
      };
      setStreamEvents((prev) => [newEv, ...prev.slice(0, 30)]);
      setLastLiveReview(data);
    }

    function handleProcessed(data) {
      const newEv = {
        id: `EV-${Date.now().toString().slice(-4)}`,
        stage: 'P5 Graph',
        status: 'PASS',
        reason: 'PROCESSED',
        detail: `Pipeline completed for review ${data.review_id || ''}`,
        time: new Date().toLocaleTimeString(),
      };
      setStreamEvents((prev) => [newEv, ...prev.slice(0, 30)]);
    }

    function handleAlert(data) {
      const newEv = {
        id: `AL-${Date.now().toString().slice(-4)}`,
        stage: 'P5 Alert',
        status: 'WARN',
        reason: 'SPIKE_TRIGGER',
        detail: `[Alert] ${data.message || 'Spike alert triggered'} (${data.severity || 'medium'} severity)`,
        time: new Date().toLocaleTimeString(),
      };
      setStreamEvents((prev) => [newEv, ...prev.slice(0, 30)]);
    }

    function handleSurvey(data) {
      const newEv = {
        id: `SV-${Date.now().toString().slice(-4)}`,
        stage: 'P7 Feedback',
        status: 'PASS',
        reason: 'SURVEY_RECEIVED',
        detail: `[Adaptive Survey] Feedback recorded from ${data.respondent_email || 'consumer'}`,
        time: new Date().toLocaleTimeString(),
      };
      setStreamEvents((prev) => [newEv, ...prev.slice(0, 30)]);
    }

    socket.on('connect', onConnect);
    socket.on('disconnect', onDisconnect);
    socket.on('review:new', handleNewReview);
    socket.on('review:processed', handleProcessed);
    socket.on('alert:new', handleAlert);
    socket.on('survey:summary', handleSurvey);

    return () => {
      socket.off('connect', onConnect);
      socket.off('disconnect', onDisconnect);
      socket.off('review:new', handleNewReview);
      socket.off('review:processed', handleProcessed);
      socket.off('alert:new', handleAlert);
      socket.off('survey:summary', handleSurvey);
    };
  }, []);

  const QUARANTINE_REASONS = [
    { code: 'all', label: 'All Quarantined', count: 138 },
    { code: 'SHORT_TEXT', label: 'Short Text (<2 Words)', count: 48 },
    { code: 'EXACT_DUP', label: 'Exact Duplicate', count: 32 },
    { code: 'NEAR_DUP', label: 'Near-Dup (Cosine > 0.95)', count: 21 },
    { code: 'PROMO_SPAM', label: 'Promo / Shill Pattern', count: 19 },
    { code: 'BURST_BOT', label: 'Coordinated Burst', count: 18 },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white tracking-wide">
            Prism Stream (Live Pipeline Canvas)
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time optical refraction: white review light split into feature beams via backend pipeline
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-teal-400 animate-ping' : 'bg-amber-400'}`} />
          <span className="text-xs font-mono text-teal-400 font-semibold">
            {isConnected ? 'BACKEND LINKED (LIVE)' : 'CONNECTING...'}
          </span>
        </div>
      </div>

      {/* Live Ingestion Alert Banner if storefront received a review */}
      {lastLiveReview && (
        <div className="p-3 rounded-xl bg-[#22242d] border border-zinc-700/60 flex items-center justify-between text-xs animate-fadeIn">
          <div className="flex items-center gap-2 min-w-0">
            <span className="font-bold text-zinc-200 font-mono">LIVE INGEST:</span>
            <span className="px-1.5 py-0.2 rounded bg-white/10 text-white font-mono text-[10px]">
              {lastLiveReview.platform}
            </span>
            <span className="text-zinc-200 truncate">"{lastLiveReview.preview_text}"</span>
          </div>
          <span className="text-amber-300 font-mono font-bold shrink-0">{lastLiveReview.rating}/5</span>
        </div>
      )}

      {/* Optical Canvas Stage Skeleton */}
      <div className="p-6 rounded-2xl bg-[#1c1d24] border border-zinc-700/60 relative overflow-hidden min-h-[320px] flex flex-col justify-between">
        {/* Optical Diagram Layout */}
        <div className="relative z-10 grid grid-cols-1 md:grid-cols-3 gap-6 items-center my-6">
          {/* Left: Inbound White Light */}
          <div className="p-4 rounded-xl bg-white/5 border border-zinc-700/60 text-center space-y-2">
            <div className="text-[10px] font-bold tracking-widest text-zinc-400 uppercase">Inbound Raw Feedback</div>
            <div className="text-lg font-bold text-white flex items-center justify-center gap-2">
              <span className="w-3 h-3 rounded-full bg-white shadow-lg shadow-white/80 animate-pulse" />
              White Light Stream
            </div>
            <p className="text-[11px] text-zinc-400">
              Unfiltered multi-channel reviews from 5 sources arriving with provenance envelopes
            </p>
          </div>

          {/* Center: The Computational Prism */}
          <div className="p-5 rounded-2xl bg-[#22242d] border border-zinc-600/70 text-center relative shadow-2xl">
            <div className="text-[10px] font-bold tracking-widest text-zinc-300 uppercase mb-2">Computational Prism</div>
            <div className="text-2xl font-black font-bold tracking-tight text-white tracking-wider mb-2">
              PRISM L2/L3
            </div>
            <div className="space-y-1.5 text-[11px] text-zinc-300">
              <div className="flex items-center justify-center gap-1.5">
                <svg className="w-3.5 h-3.5 text-zinc-300 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
                <span>Sarvam Translation (Hinglish → En)</span>
              </div>
              <div className="flex items-center justify-center gap-1.5">
                <svg className="w-3.5 h-3.5 text-zinc-300 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
                <span>6-Gate Trust Cascade Filter</span>
              </div>
              <div className="flex items-center justify-center gap-1.5">
                <svg className="w-3.5 h-3.5 text-zinc-300 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
                <span>Sentence Vector Embedding (384-d)</span>
              </div>
            </div>
            <div className="mt-3 pt-3 border-t border-zinc-700/60 text-[10px] text-amber-300 font-mono">
              Routing Filtered Anomalies to Quarantine
            </div>
          </div>

          {/* Right: Refracted Spectral Beams */}
          <div className="p-4 rounded-xl bg-white/5 border border-zinc-700/60 space-y-2">
            <div className="text-[10px] font-bold tracking-widest text-zinc-400 uppercase text-center">Refracted Feature Beams</div>
            <div className="space-y-1.5 text-xs font-mono">
              <div className="flex items-center justify-between p-1.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-200">
                <span>Silver: Battery & Power</span>
                <span className="text-[10px]">38 mentions</span>
              </div>
              <div className="flex items-center justify-between p-1.5 rounded bg-amber-950/50 border border-amber-500/30 text-amber-300">
                <span>Amber: Packaging & Box</span>
                <span className="text-[10px]">6 mentions (Spike)</span>
              </div>
              <div className="flex items-center justify-between p-1.5 rounded bg-blue-950/50 border border-blue-500/30 text-blue-300">
                <span>Blue: Build Quality</span>
                <span className="text-[10px]">14 mentions</span>
              </div>
              <div className="flex items-center justify-between p-1.5 rounded bg-purple-950/50 border border-purple-500/30 text-purple-300">
                <span>Purple: Audio & ANC</span>
                <span className="text-[10px]">52 mentions</span>
              </div>
            </div>
          </div>
        </div>

        {/* Stage Process Lane Bar */}
        <div className="border-t border-white/10 pt-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          {STAGES.map((s) => (
            <div key={s.id} className="p-2 rounded-lg bg-[#14151a] border border-zinc-700/50 text-[11px]">
              <div className="flex items-center justify-between text-zinc-400 text-[10px]">
                <span className="font-mono">{s.id}</span>
                <span className="font-mono text-zinc-300">{s.duration}</span>
              </div>
              <div className="font-medium text-white truncate mt-1">{s.name}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Lower Section: Quarantine Bin & Event Stream Table */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quarantine Chamber */}
        <div className="p-5 rounded-xl bg-[#1c1d24] border border-zinc-700/60 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <svg className="w-4 h-4 text-amber-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              Quarantine Chamber
            </h2>
            <span className="text-xs font-mono text-amber-400 font-bold">138 Excluded</span>
          </div>
          <p className="text-xs text-zinc-400">
            Reviews rejected or downweighted by Trust Cascade (G1-G6). Retained for auditability.
          </p>

          <div className="space-y-1.5">
            {QUARANTINE_REASONS.map((q) => (
              <button
                key={q.code}
                onClick={() => setFilterReason(q.code)}
                className={`w-full flex items-center justify-between p-2 rounded-lg text-xs transition-colors ${
                  filterReason === q.code
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                    : 'bg-white/5 hover:bg-zinc-800 text-zinc-300 border border-transparent'
                }`}
              >
                <span>{q.label}</span>
                <span className="font-mono font-semibold">{q.count}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Real-time Pipeline Events Log */}
        <div className="p-5 rounded-xl bg-[#1c1d24] border border-zinc-700/60 space-y-4 lg:col-span-2">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-white">Live Pipeline Events (SSE Log)</h2>
              <p className="text-xs text-zinc-400">Chronological telemetry stream directly from Render worker tasks</p>
            </div>
            <span className="text-[11px] font-mono text-zinc-400">EventBuffer: 100 max</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-400 text-[11px]">
                  <th className="pb-2 font-semibold">Event ID</th>
                  <th className="pb-2 font-semibold">Stage</th>
                  <th className="pb-2 font-semibold">Status</th>
                  <th className="pb-2 font-semibold">Reason Code</th>
                  <th className="pb-2 font-semibold">Telemetry Detail</th>
                  <th className="pb-2 font-semibold text-right">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/50 font-mono">
                {streamEvents.map((ev) => (
                  <tr key={ev.id} className="hover:bg-white/5 transition-colors">
                    <td className="py-2.5 text-zinc-500">{ev.id}</td>
                    <td className="py-2.5 text-zinc-300">{ev.stage}</td>
                    <td className="py-2.5">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          ev.status === 'PASS'
                            ? 'bg-teal-500/15 text-teal-300 border border-teal-500/25'
                            : ev.status === 'WARN'
                            ? 'bg-amber-500/15 text-amber-300 border border-amber-500/25'
                            : 'bg-rose-500/15 text-rose-300 border border-rose-500/25'
                        }`}
                      >
                        {ev.status}
                      </span>
                    </td>
                    <td className="py-2.5 text-zinc-200 text-[11px]">{ev.reason}</td>
                    <td className="py-2.5 text-zinc-300 text-[11px] font-sans truncate max-w-xs">{ev.detail}</td>
                    <td className="py-2.5 text-right text-zinc-500 text-[11px]">{ev.time}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
