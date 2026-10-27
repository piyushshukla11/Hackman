import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { io } from 'socket.io-client';
import { runDemoPipeline, setGeminiKey, getGeminiKeyStatus } from '../../api';
import { PRODUCTS } from '../../constants/products';

/* ── Stage metadata ──────────────────────────────────────────────── */
const STAGE_META = {
  1: { icon: '🔤', color: '#38bdf8', loadText: 'Cleaning & translating review text…', name: 'Normalization' },
  2: { icon: '🛡️', color: '#a78bfa', loadText: 'Running spam & bot detection…', name: 'Trust Filter' },
  3: { icon: '🔍', color: '#34d399', loadText: 'Extracting product feature signals…', name: 'Feature Extraction' },
  4: { icon: '🕸️', color: '#f472b6', loadText: 'Building knowledge graph connections…', name: 'Graph Integration' },
  5: { icon: '📈', color: '#fb923c', loadText: 'Analyzing weekly sentiment trends…', name: 'Time-Series Analysis' },
  6: { icon: '🎯', color: '#facc15', loadText: 'Scoring insight confidence levels…', name: 'Confidence Scoring' },
  7: { icon: '✉️', color: '#22d3ee', loadText: 'Generating AI follow-up questions…', name: 'Adaptive Feedback' },
};

const SAMPLE_REVIEW = {
  product_id: 'prod_001', platform: 'amazon',
  review_text: 'Sound is great but battery dies in 3 hours ANC on. Box arrived crushed, very disappointed with packaging.',
  rating: 2, user_id: 'demo_user_1', email: 'judge@example.com', media_type: 'none',
  timestamp: new Date().toISOString(),
};

function nameForProduct(id) {
  return PRODUCTS.find(p => p.product_id === id)?.name || id;
}

/* ── Stage summary builders ──────────────────────────────────────── */
function stageSummary(n, st) {
  if (!st || st.status === 'running') return null;
  switch (n) {
    case 1: {
      const lang = st.result?.detected_language || st.detected_language || '?';
      return `Language: ${lang} → English`;
    }
    case 2: {
      const pass = st.result?.pass ?? st.pass;
      if (pass === false) return `⚠ Flagged: ${st.result?.reason || st.reason || 'trust layer'}`;
      return 'Trust: ✓ Passed';
    }
    case 3: {
      const feats = st.features || st.result?.features || {};
      const keys = Object.keys(feats);
      if (!keys.length) return 'No features detected';
      return keys.map(k => {
        const s = feats[k]?.sentiment;
        return `${k.replace(/_/g, ' ')} ${s === 'positive' ? '⊕' : '⊖'}`;
      }).join(' · ');
    }
    case 4: {
      const r = st.result || {};
      return `${r.edges_created ?? '—'} edges created`;
    }
    case 5: {
      const r = st.result || {};
      const spikes = r.spikes?.length ?? 0;
      return `${spikes} spike${spikes !== 1 ? 's' : ''} detected`;
    }
    case 6: {
      const r = st.result || {};
      return `Health: ${r.health_score ?? '—'} · ${r.insights_updated ?? '—'} insights`;
    }
    case 7: {
      return st.detail || 'Survey dispatched';
    }
    default: return JSON.stringify(st).slice(0, 120);
  }
}

/* ── Shimmer bar ─────────────────────────────────────────────────── */
function ShimmerBar({ color }) {
  return (
    <div className="mt-3 h-1.5 overflow-hidden rounded-full" style={{ background: `${color}22` }}>
      <motion.div className="h-full rounded-full" style={{ background: color }}
        initial={{ width: '0%', x: 0 }} animate={{ width: '60%', x: ['0%', '66%'] }}
        transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }} />
    </div>
  );
}

/* ── New Review Alert Toast ──────────────────────────────────────── */
function ReviewAlertToast({ alerts }) {
  return (
    <AnimatePresence>
      {alerts.map((a, i) => (
        <motion.div key={a.id || i}
          initial={{ opacity: 0, y: -30, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.95 }}
          transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          className="mb-2 flex items-center gap-3 rounded-xl border border-sky-500/30 bg-gradient-to-r from-sky-950/80 to-indigo-950/80 px-4 py-3 shadow-lg shadow-sky-900/20 backdrop-blur-sm"
        >
          <span className="text-lg">🔔</span>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold text-sky-200">New review from {a.platform}</p>
            <p className="truncate text-[11px] text-slate-400">
              {nameForProduct(a.product_id)} · {'★'.repeat(a.rating)}{'☆'.repeat(5 - a.rating)} · {(a.preview_text || '').slice(0, 80)}…
            </p>
          </div>
        </motion.div>
      ))}
    </AnimatePresence>
  );
}

/* ── Gemini Key Modal ────────────────────────────────────────────── */
function GeminiKeyModal({ onClose, onSaved }) {
  const [key, setKey] = useState('');
  const [show, setShow] = useState(false);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  async function save() {
    if (key.trim().length < 10) { setErr('Key too short'); return; }
    setSaving(true); setErr('');
    try {
      const r = await setGeminiKey(key.trim());
      if (!r.ok) throw new Error('Failed');
      onSaved(); onClose();
    } catch { setErr('Failed to save key'); }
    finally { setSaving(false); }
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <motion.div initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }}
        className="mx-4 w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"
        onClick={e => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-white">🔑 Gemini API Key</h3>
        <p className="mt-2 text-sm text-slate-400">Enter your Google Gemini API key to enable AI-powered context-aware survey generation.</p>
        <div className="mt-4 flex items-center gap-2 rounded-lg border border-slate-600 bg-slate-800 px-3 py-2">
          <input type={show ? 'text' : 'password'} value={key} onChange={e => setKey(e.target.value)}
            placeholder="AIzaSy..." className="flex-1 bg-transparent text-sm text-white outline-none placeholder:text-slate-500" />
          <button type="button" onClick={() => setShow(!show)} className="text-xs text-slate-400 hover:text-white">{show ? 'Hide' : 'Show'}</button>
        </div>
        {err && <p className="mt-2 text-xs text-red-400">{err}</p>}
        <div className="mt-4 flex gap-3">
          <button onClick={save} disabled={saving}
            className="rounded-lg bg-gradient-to-r from-sky-600 to-indigo-600 px-5 py-2 text-sm font-semibold text-white shadow-lg disabled:opacity-50">
            {saving ? 'Saving…' : 'Validate & Save'}
          </button>
          <button onClick={onClose} className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800">Cancel</button>
        </div>
      </motion.div>
    </motion.div>
  );
}

/* ── Stage Card ──────────────────────────────────────────────────── */
function StageCard({ n, st, surveySummary }) {
  const meta = STAGE_META[n];
  const active = !!st;
  const isRunning = st?.status === 'running';
  const isDone = st && st.status !== 'running';
  const summary = stageSummary(n, st);

  // Stage 7 special rendering
  if (n === 7 && isDone) {
    const sent = st?.status === 'sent' || isDone;
    const email = st?.respondent_email || '—';
    const features = st?.gemini_feature_focus || [];
    const showSummary = surveySummary && sent &&
      (!st?.respondent_email || surveySummary.respondent_email === st.respondent_email);

    return (
      <motion.div initial={false}
        animate={{ opacity: active ? 1 : 0.4, borderColor: active ? `${meta.color}66` : 'rgba(51,65,85,1)' }}
        transition={{ type: 'spring', stiffness: 260, damping: 22 }}
        className="relative overflow-hidden rounded-xl border bg-slate-900/50 p-4 backdrop-blur-sm">
        <div className="absolute inset-0 opacity-[0.03]" style={{ background: `radial-gradient(circle at top right, ${meta.color}, transparent 70%)` }} />
        <div className="relative">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg text-lg" style={{ background: `${meta.color}18` }}>{meta.icon}</span>
              <div>
                <span className="text-xs font-semibold text-slate-400">Stage {n}</span>
                <p className="text-sm font-medium text-white">{meta.name}</p>
              </div>
            </div>
            <span className="rounded-full border border-emerald-500/40 bg-emerald-950/50 px-2.5 py-0.5 text-[10px] font-medium text-emerald-300">✉ delivered</span>
          </div>
          <div className="mt-3 space-y-2 text-xs text-slate-300">
            <p><span className="text-slate-500">Sent to:</span> <span className="text-sky-200">{email}</span></p>
            {features.length > 0 && (
              <p><span className="text-slate-500">AI focus:</span> <span className="text-slate-200">{features.join(', ')}</span></p>
            )}
            <div className="my-2 border-t border-slate-700/60" />
            {!showSummary && (
              <div className="flex items-center gap-2">
                <motion.span className="inline-block h-2 w-2 rounded-full bg-sky-400"
                  animate={{ opacity: [0.35, 1, 0.35] }} transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }} />
                <span className="text-sky-300/90">Awaiting consumer response…</span>
              </div>
            )}
            {showSummary && (
              <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="space-y-1.5">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-emerald-400">Response received</p>
                <p className="text-sm leading-relaxed text-slate-200">{surveySummary.summary}</p>
              </motion.div>
            )}
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div initial={false}
      animate={{ opacity: active ? 1 : 0.4, borderColor: active ? `${meta.color}66` : 'rgba(51,65,85,1)' }}
      transition={{ type: 'spring', stiffness: 260, damping: 22 }}
      className="relative overflow-hidden rounded-xl border bg-slate-900/50 p-4 backdrop-blur-sm">
      <div className="absolute inset-0 opacity-[0.03]" style={{ background: `radial-gradient(circle at top right, ${meta.color}, transparent 70%)` }} />
      <div className="relative">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg text-lg" style={{ background: `${meta.color}18` }}>{meta.icon}</span>
            <div>
              <span className="text-xs font-semibold text-slate-400">Stage {n}</span>
              <p className="text-sm font-medium text-white">{meta.name}</p>
            </div>
          </div>
          {isDone && (
            <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: 'spring', stiffness: 400, damping: 15 }}
              className="flex h-6 w-6 items-center justify-center rounded-full text-xs" style={{ background: `${meta.color}22`, color: meta.color }}>✓</motion.span>
          )}
        </div>

        {isRunning && (
          <>
            <p className="mt-3 text-xs text-slate-400">{meta.loadText}</p>
            <ShimmerBar color={meta.color} />
          </>
        )}

        {isDone && summary && (
          <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="mt-3 rounded-lg px-3 py-2 text-xs leading-relaxed text-slate-300" style={{ background: `${meta.color}08`, border: `1px solid ${meta.color}15` }}>
            {summary}
          </motion.div>
        )}

        {!active && <p className="mt-3 text-xs text-slate-600">Waiting for pipeline run…</p>}
      </div>
    </motion.div>
  );
}

/* ── Main DemoCenter ─────────────────────────────────────────────── */
export default function DemoCenter({ onHealthDelta, leaderboard = [], productNames = {} }) {
  const [running, setRunning] = useState(false);
  const [stageState, setStageState] = useState({});
  const [doneInfo, setDoneInfo] = useState(null);
  const [error, setError] = useState(null);
  const [surveySummary, setSurveySummary] = useState(null);
  const [reviewAlerts, setReviewAlerts] = useState([]);
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [keyConfigured, setKeyConfigured] = useState(null);
  const alertTimeout = useRef(null);

  // Check Gemini key status on mount
  useEffect(() => {
    getGeminiKeyStatus().then(r => r.json()).then(d => setKeyConfigured(d.configured)).catch(() => {});
  }, []);

  // Socket.io for survey summaries + new review alerts
  useEffect(() => {
    const socket = io({ path: '/socket.io', withCredentials: true });
    socket.on('survey:summary', (data) => setSurveySummary(data));
    socket.on('review:new', (data) => {
      setReviewAlerts(prev => [{ ...data, id: Date.now() + Math.random() }, ...prev].slice(0, 3));
      // Auto-dismiss after 6s
      if (alertTimeout.current) clearTimeout(alertTimeout.current);
      alertTimeout.current = setTimeout(() => setReviewAlerts([]), 6000);
    });
    return () => socket.disconnect();
  }, []);

  async function run() {
    setRunning(true); setStageState({}); setDoneInfo(null); setError(null); setSurveySummary(null);

    try {
      const res = await runDemoPipeline(SAMPLE_REVIEW);
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.error || 'Demo request failed'); }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let boundary;
        while ((boundary = buffer.indexOf('\n\n')) !== -1) {
          const rawBlock = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          let eventName = 'message';
          const dataParts = [];
          for (const line of rawBlock.split('\n')) {
            if (line.startsWith('event:')) eventName = line.slice(6).trim();
            else if (line.startsWith('data:')) dataParts.push(line.slice(5).trim());
          }
          const dataStr = dataParts.join('');
          if (!dataStr) continue;
          let data;
          try { data = JSON.parse(dataStr); } catch { continue; }

          if (eventName === 'stage' && data?.stage) {
            setStageState(s => ({ ...s, [data.stage]: { ...data, at: Date.now() } }));
          }
          if (eventName === 'done') {
            setDoneInfo(data);
            if (data?.insight_delta?.health_score != null && onHealthDelta) onHealthDelta(data.insight_delta.health_score);
          }
          if (eventName === 'error') setError(data?.message || 'Pipeline error');
        }
      }
    } catch (e) { setError(e.message || 'Failed'); }
    finally { setRunning(false); }
  }

  const activeStageCount = Object.keys(stageState).length;
  const progress = running ? Math.round((activeStageCount / 7) * 100) : doneInfo ? 100 : 0;

  return (
    <section id="demo-center" className="mt-16 scroll-mt-8 border-t border-slate-800 pt-12">
      <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5 }}>

        {/* ── Review Alert Toasts ── */}
        <div className="mb-4">{reviewAlerts.length > 0 && <ReviewAlertToast alerts={reviewAlerts} />}</div>

        {/* ── Header ── */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-white">Demo Center</h2>
            <p className="mt-2 max-w-2xl text-sm text-slate-400">
              Stream a review through the seven-stage intelligence pipeline in real-time. Each stage lights up with live results — from text normalization to AI-generated diagnostic surveys.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {keyConfigured === true && (
              <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-[11px] font-medium text-emerald-300">🔑 Gemini active</span>
            )}
            {keyConfigured === false && (
              <button onClick={() => setShowKeyModal(true)}
                className="rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-[11px] font-medium text-amber-300 transition hover:bg-amber-500/20">
                🔑 Set Gemini key
              </button>
            )}
          </div>
        </div>

        {/* ── Controls ── */}
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button type="button" onClick={run} disabled={running}
            className="rounded-lg bg-gradient-to-r from-sky-600 to-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-sky-900/40 transition hover:shadow-sky-800/60 disabled:opacity-50">
            {running ? 'Running pipeline…' : '▶ Run live pipeline demo'}
          </button>
          <button type="button" onClick={() => setShowKeyModal(true)}
            className="rounded-lg border border-slate-600 bg-slate-900/60 px-4 py-2 text-xs font-medium text-slate-300 transition hover:border-slate-500 hover:bg-slate-800">
            🔑 API Key
          </button>
          {error && <span className="text-sm text-red-400">{error}</span>}
        </div>

        {/* ── Progress bar ── */}
        {(running || doneInfo) && (
          <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-slate-800">
            <motion.div className="h-full rounded-full bg-gradient-to-r from-sky-500 to-indigo-500"
              initial={{ width: '0%' }} animate={{ width: `${progress}%` }}
              transition={{ duration: 0.4, ease: 'easeOut' }} />
          </div>
        )}

        {/* ── Pipeline Stages ── */}
        <div className="mt-8 grid gap-4 md:grid-cols-2">
          {[1, 2, 3, 4, 5, 6, 7].map(n => (
            <StageCard key={n} n={n} st={stageState[n]} surveySummary={surveySummary} />
          ))}
        </div>

        {/* ── Done banner ── */}
        {doneInfo && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            className="mt-6 flex items-center gap-3 rounded-xl border border-emerald-500/30 bg-emerald-950/40 px-4 py-3">
            <span className="text-lg">✅</span>
            <p className="text-sm text-emerald-300">
              Pipeline complete
              {doneInfo.filtered ? ` — filtered: ${doneInfo.reason || 'trust layer'}` : ''}
              {doneInfo.insight_delta?.health_score != null ? ` · health score: ${doneInfo.insight_delta.health_score}` : ''}
            </p>
          </motion.div>
        )}

        {/* ── Mini leaderboard ── */}
        {leaderboard.length > 0 && (
          <div className="mt-10 rounded-xl border border-slate-700 bg-slate-900/30 p-4">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Mini leaderboard (live from /dashboard/all)</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {leaderboard.map((row, i) => (
                <motion.div key={row.product_id} initial={{ opacity: 0, y: 6 }} whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }} transition={{ delay: i * 0.06 }}
                  className="flex items-center justify-between rounded-lg border border-slate-700/80 bg-slate-950/50 px-3 py-2 text-xs">
                  <span className="truncate text-slate-200">{productNames[row.product_id] || row.name}</span>
                  <span className="tabular-nums font-semibold text-sky-300">{row.health_score}</span>
                </motion.div>
              ))}
            </div>
          </div>
        )}
      </motion.div>

      {/* ── Gemini Key Modal ── */}
      <AnimatePresence>
        {showKeyModal && (
          <GeminiKeyModal onClose={() => setShowKeyModal(false)}
            onSaved={() => setKeyConfigured(true)} />
        )}
      </AnimatePresence>
    </section>
  );
}
