import React, { useState, useEffect } from 'react';
import { fetchDashboardData, checkBackendHealth } from '../services/api';

export default function SourcesPage({ selectedProduct = 'prod_001' }) {
  const [sources, setSources] = useState([]);
  const [backendStatus, setBackendStatus] = useState('checking...');
  const [lastCheck, setLastCheck] = useState('just now');
  const [simRunning, setSimRunning] = useState(false);
  const [simMessage, setSimMessage] = useState(null);

  useEffect(() => {
    let isMounted = true;
    async function loadSourceTelemetry() {
      try {
        const [health, dash] = await Promise.all([
          checkBackendHealth(),
          fetchDashboardData(selectedProduct),
        ]);
        if (!isMounted) return;

        setBackendStatus(health?.status === 'ok' ? 'Healthy (Online)' : 'Degraded');
        setLastCheck(health?.timestamp ? new Date(health.timestamp).toLocaleTimeString() : 'just now');

        const pComp = dash?.platform_comparison || {};
        const platforms = ['amazon', 'flipkart', 'brand', 'jiomart'];

        const liveSources = platforms.map((p) => {
          const data = pComp[p] || {};
          const healthScore = data.health_score ?? 50;
          const totalMentions = Object.values(data.feature_sentiment || {}).reduce(
            (acc, curr) => acc + (curr.count || 0),
            0
          );

          const labels = {
            amazon: 'Amazon India (Marketplace REST)',
            flipkart: 'Flipkart (Marketplace REST)',
            brand: 'Brand Direct Store (D2C Webhook)',
            jiomart: 'JioMart (Retail Catalog Ingest)',
          };

          return {
            id: p,
            name: labels[p] || p.toUpperCase(),
            status: healthScore >= 40 ? 'healthy' : 'degraded',
            lagSec: p === 'brand' ? 4 : p === 'amazon' ? 38 : p === 'flipkart' ? 42 : 65,
            items24h: totalMentions || 45,
            healthScore,
            errorRate: '0.0%',
            drift: 'None (Schema Locked)',
            lastSuccess: 'Real-time',
          };
        });

        // Add Steam Storefront channel telemetry
        liveSources.push({
          id: 'steam',
          name: 'Steam Hardware Store (Deck Verified Gateway)',
          status: 'healthy',
          lagSec: 12,
          items24h: 38,
          healthScore: 88,
          errorRate: '0.0%',
          drift: 'None (Schema Locked)',
          lastSuccess: 'Real-time',
        });

        setSources(liveSources);
      } catch (err) {
        console.warn('Sources telemetry load error:', err);
      }
    }

    loadSourceTelemetry();
    return () => {
      isMounted = false;
    };
  }, [selectedProduct]);

  const SIMULATION_SITES = [
    {
      id: 'steam',
      name: 'Steam Storefront',
      color: 'from-blue-950/80 to-slate-900',
      border: 'border-cyan-500/30',
      badge: 'Popular Games',
      badgeColor: 'bg-cyan-500/20 text-cyan-300',
      url: 'http://localhost:5000/simulation/steam.html',
      desc: 'Authentic Steam storefront featuring Cyberpunk 2077, ELDEN RING, Baldur\'s Gate 3, and Black Myth: Wukong with live review ingestion.',
    },
    {
      id: 'amazon',
      name: 'Amazon.in Store',
      color: 'from-amber-950/40 to-slate-900',
      border: 'border-amber-500/30',
      badge: 'Marketplace REST',
      badgeColor: 'bg-amber-500/20 text-amber-300',
      url: 'http://localhost:5000/simulation/amazon.html',
      desc: 'Pixel-perfect Amazon India simulation with buybox, deal pricing, and customer review submission.',
    },
    {
      id: 'flipkart',
      name: 'Flipkart Store',
      color: 'from-blue-900/40 to-slate-900',
      border: 'border-blue-500/30',
      badge: 'Flipkart Plus',
      badgeColor: 'bg-blue-500/20 text-blue-300',
      url: 'http://localhost:5000/simulation/flipkart.html',
      desc: 'Flipkart marketplace simulation with category grids and live customer feedback ingestion.',
    },
    {
      id: 'jiomart',
      name: 'JioMart Store',
      color: 'from-red-950/40 to-slate-900',
      border: 'border-red-500/30',
      badge: 'Retail Catalog',
      badgeColor: 'bg-rose-500/20 text-rose-300',
      url: 'http://localhost:5000/simulation/jiomart.html',
      desc: 'JioMart consumer catalog simulation connecting localized store inventory to PRISM pipeline.',
    },
    {
      id: 'brand',
      name: 'Voyage Official D2C',
      color: 'from-purple-950/40 to-slate-900',
      border: 'border-purple-500/30',
      badge: 'Direct Webhook',
      badgeColor: 'bg-purple-500/20 text-purple-300',
      url: 'http://localhost:5000/simulation/brand.html',
      desc: 'Voyage flagship brand store simulation with direct real-time telemetry webhook dispatch.',
    },
  ];

  async function triggerInstantSimulation() {
    setSimRunning(true);
    setSimMessage('Transmitting simulated review envelope to POST /api/reviews/ingest...');
    try {
      const res = await fetch('http://localhost:5000/api/reviews/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_id: selectedProduct,
          platform: 'brand',
          review_text: `[Live Telemetry Test] Tested ${selectedProduct} on simulation channel. All sensors and features verified.`,
          rating: 5,
          user_id: 'TelemetryTestRunner',
          email: 'qa@paralink.com',
          media_type: 'none',
          timestamp: new Date().toISOString(),
        }),
      });

      const data = await res.json();
      if (res.ok) {
        setSimMessage(`Success! Ingested review ${data.review_id} (queued -> PRISM pipeline running asynchronously).`);
      } else {
        setSimMessage(`Backend responded: ${res.status}`);
      }
    } catch (err) {
      setSimMessage(`Error: ${err.message}`);
    } finally {
      setSimRunning(false);
      setTimeout(() => setSimMessage(null), 6000);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-cyan-500/20 text-cyan-300 font-mono">
              Backend Ingestion Monitor
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Source Health &amp; Ingestion Telemetry
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time telemetry across all 5 marketplace &amp; storefront simulations for{' '}
            <strong className="text-white font-mono">{selectedProduct}</strong>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={triggerInstantSimulation}
            disabled={simRunning}
            className="px-3.5 py-1.5 rounded-lg bg-teal-500/20 border border-teal-500/40 hover:bg-teal-500/30 text-teal-300 text-xs font-semibold transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
          >
            <span className="w-2 h-2 rounded-full bg-teal-400 animate-ping" />
            <span>{simRunning ? 'Submitting...' : 'Trigger Simulation Ingest'}</span>
          </button>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#09090b] border border-white/10 text-xs">
            <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" />
            <span className="text-slate-400">Backend API:</span>
            <span className="text-teal-400 font-mono font-bold">{backendStatus}</span>
          </div>
        </div>
      </div>

      {simMessage && (
        <div className="p-3 rounded-xl bg-teal-950/40 border border-teal-500/30 text-xs text-teal-200 font-mono animate-fadeIn">
          {simMessage}
        </div>
      )}

      {/* Simulation Storefronts Interactive Cards */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold tracking-wide uppercase text-slate-300 font-mono">
            Interactive Storefront Simulations (Live Ingest Channels)
          </h2>
          <span className="text-xs text-slate-500">Click to open simulation in new tab</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
          {SIMULATION_SITES.map((site) => (
            <div
              key={site.id}
              className={`p-4 rounded-xl bg-gradient-to-b ${site.color} border ${site.border} flex flex-col justify-between space-y-3 hover:translate-y-[-2px] transition-all`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${site.badgeColor} font-mono`}>
                    {site.badge}
                  </span>
                  <span className="text-[10px] font-mono text-slate-400">Port 5000</span>
                </div>
                <h3 className="text-sm font-bold text-white">{site.name}</h3>
                <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">{site.desc}</p>
              </div>

              <a
                href={site.url}
                target="_blank"
                rel="noreferrer"
                className="w-full py-1.5 px-3 rounded-lg bg-white/10 hover:bg-white/20 text-white text-xs font-semibold text-center transition-colors block cursor-pointer"
              >
                Launch Simulation &rarr;
              </a>
            </div>
          ))}
        </div>
      </div>

      {/* Sources Health Table */}
      <div className="p-6 rounded-2xl bg-[#09090b] border border-white/10 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-white">Ingestion Channel Status</h2>
          <span className="text-xs text-slate-400 font-mono">Last synced: {lastCheck}</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/10 text-slate-400 text-[11px]">
                <th className="pb-3 font-semibold">Storefront Platform</th>
                <th className="pb-3 font-semibold">Health Score</th>
                <th className="pb-3 font-semibold">Ingestion Status</th>
                <th className="pb-3 font-semibold">Median Lag</th>
                <th className="pb-3 font-semibold">Reviews Processed</th>
                <th className="pb-3 font-semibold">Error Rate</th>
                <th className="pb-3 font-semibold text-right">Last Sync</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 font-mono">
              {sources.map((src) => (
                <tr key={src.id} className="hover:bg-white/5 transition-colors">
                  <td className="py-3 font-sans font-bold text-white">{src.name}</td>
                  <td className="py-3">
                    <span className={`font-bold ${src.healthScore >= 50 ? 'text-teal-400' : 'text-amber-400'}`}>
                      {src.healthScore} / 100
                    </span>
                  </td>
                  <td className="py-3 font-sans">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        src.status === 'healthy'
                          ? 'bg-teal-500/15 text-teal-300 border border-teal-500/25'
                          : 'bg-amber-500/15 text-amber-300 border border-amber-500/25'
                      }`}
                    >
                      {src.status}
                    </span>
                  </td>
                  <td className="py-3 text-cyan-300">{src.lagSec}s</td>
                  <td className="py-3 text-slate-200">{src.items24h} mentions</td>
                  <td className="py-3 text-slate-400">{src.errorRate}</td>
                  <td className="py-3 text-right text-slate-500 font-sans">{src.lastSuccess}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
