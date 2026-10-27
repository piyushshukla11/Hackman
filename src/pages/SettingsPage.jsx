import React from 'react';

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-bold tracking-tight text-white tracking-wide">
            Platform Settings & Integrations
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Category feature taxonomies, batch registries, API secret keys, and embeddable widget snippets
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Embeddable Review Widget Snippet */}
        <div className="p-6 rounded-2xl bg-[#09090b] border border-white/10 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white font-bold tracking-tight">Embeddable Widget Snippet</h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-teal-500/15 text-teal-300 border border-teal-500/25">
              Vanilla TS (&lt;30KB)
            </span>
          </div>
          <p className="text-xs text-slate-400">
            For small companies without an API. Embed on any storefront to capture 0.5-star ratings, quick taxonomy tags, and batch codes via QR.
          </p>
          <div className="p-3.5 rounded-xl bg-black/60 border border-white/5 font-mono text-xs text-cyan-300 overflow-x-auto">
            {`<script src="https://api.prism.ai/widget.js" 
  data-key="pk_live_89f1a293" 
  data-product="HP-NORD3"></script>`}
          </div>
        </div>

        {/* API Credentials */}
        <div className="p-6 rounded-2xl bg-[#09090b] border border-white/10 space-y-4">
          <h2 className="text-sm font-bold text-white font-bold tracking-tight">API Gateway Keys</h2>
          <p className="text-xs text-slate-400">
            Use these keys to authenticate push webhooks from custom storefronts into <code>/v1/ingest/adapter/*</code>.
          </p>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between items-center p-3 rounded-xl bg-black/40 border border-white/5">
              <div>
                <div className="font-semibold text-white">Default Ingestion Secret Key</div>
                <div className="font-mono text-slate-500 text-[11px]">pr_sec_live_********************</div>
              </div>
              <button className="px-2.5 py-1 rounded bg-white/5 hover:bg-white/10 text-slate-300 font-medium">
                Copy
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
