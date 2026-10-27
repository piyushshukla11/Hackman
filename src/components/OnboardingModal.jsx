import React, { useState } from 'react';

const ALL_MODULES = [
  { id: 'overview', label: 'Portfolio Overview', desc: 'Health index, top issues, and trust audit' },
  { id: 'issues', label: 'Issue Graph & Root Cause', desc: 'Connected clusters & confidence waterfall' },
  { id: 'xray', label: 'Review X-Ray', desc: 'Token breakdown, trust gates, and rating conflict' },
  { id: 'compare', label: 'Comparison Engine', desc: '5-lens statistical hypothesis testing' },
  { id: 'products', label: 'Products & Custom Features', desc: 'Hardware versions & F28 custom taxonomy' },
  { id: 'stream', label: 'Prism Stream', desc: 'Live ingest pipeline & Hinglish translation' },
  { id: 'serious', label: 'Serious Complaint Queue', desc: 'Safety and critical hazard alerts' },
  { id: 'timeline', label: 'Forensic Timeline', desc: 'Lead-time advantage (+15d) and batch capsules' },
  { id: 'investigations', label: 'Survey Threads', desc: 'Closed-loop customer verification' },
  { id: 'sources', label: 'Source Health', desc: 'Adapter latency, drift, and pipeline health' },
  { id: 'reports', label: 'Company Reports', desc: '1-click PDF executive report generation' },
  { id: 'settings', label: 'Settings', desc: 'API keys, widget snippet, and taxonomy config' },
  { id: 'judge', label: 'Judge Mode (90s)', desc: 'Guided walkthrough of core capabilities' },
];

const PRESETS = [
  {
    title: 'QA & Reliability Lead',
    roleId: 'qa',
    tabs: ['overview', 'issues', 'xray', 'timeline', 'compare', 'judge'],
  },
  {
    title: 'Customer Experience Lead',
    roleId: 'support',
    tabs: ['overview', 'stream', 'serious', 'investigations', 'xray'],
  },
  {
    title: 'Product Manager & Designer',
    roleId: 'designer',
    tabs: ['overview', 'issues', 'xray', 'compare', 'products'],
  },
  {
    title: 'Executive & Leadership',
    roleId: 'leadership',
    tabs: ['overview', 'timeline', 'reports', 'judge'],
  },
];

export default function OnboardingModal({ isOpen, onClose, currentUser, onSavePreferences }) {
  const [roleTitle, setRoleTitle] = useState(currentUser?.jobTitle || currentUser?.roleData?.title || 'Product Designer');
  const [selectedTabs, setSelectedTabs] = useState(
    currentUser?.roleData?.allowedTabs || ['overview', 'issues', 'xray', 'compare', 'products']
  );

  if (!isOpen) return null;

  function handleToggleTab(id) {
    if (selectedTabs.includes(id)) {
      if (selectedTabs.length === 1) return; // Keep at least one
      setSelectedTabs(selectedTabs.filter((t) => t !== id));
    } else {
      setSelectedTabs([...selectedTabs, id]);
    }
  }

  function handleApplyPreset(preset) {
    setRoleTitle(preset.title);
    setSelectedTabs(preset.tabs);
  }

  function handleSave(e) {
    e.preventDefault();
    onSavePreferences({
      roleTitle,
      allowedTabs: selectedTabs,
    });
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-fadeIn">
      <div className="w-full max-w-2xl bg-[#1c1d24] border border-zinc-700/60 rounded-2xl p-6 space-y-6 shadow-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-zinc-800 text-zinc-200 border border-zinc-700 font-mono">
                F27 Personalization
              </span>
              <span className="text-xs text-zinc-400">Zero Information Overload</span>
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Workspace &amp; Module Personalization
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              Select only the modules you need. PRISM hides everything else to keep your daily focus clutter-free.
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-white p-1 cursor-pointer transition-colors"
            aria-label="Close"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Quick Presets */}
        <div>
          <label className="block text-xs font-semibold text-zinc-300 uppercase tracking-wider mb-2">
            Quick Persona Presets
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {PRESETS.map((p) => (
              <button
                key={p.title}
                type="button"
                onClick={() => handleApplyPreset(p)}
                className="p-2.5 rounded-lg border border-zinc-800 hover:border-zinc-500 bg-white/5 hover:bg-zinc-800/60 text-left transition-colors cursor-pointer"
              >
                <div className="text-xs font-bold text-white truncate">{p.title}</div>
                <div className="text-[10px] font-mono text-zinc-300 mt-1">{p.tabs.length} Views</div>
              </button>
            ))}
          </div>
        </div>

        {/* Role Title Input */}
        <div>
          <label className="block text-xs font-semibold text-zinc-300 uppercase tracking-wider mb-1.5">
            Your Professional Role Title
          </label>
          <input
            type="text"
            value={roleTitle}
            onChange={(e) => setRoleTitle(e.target.value)}
            placeholder="e.g. Senior QA & Reliability Lead"
            className="w-full bg-[#121316] border border-zinc-700/70 rounded-lg px-3 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-zinc-400 font-medium"
          />
        </div>

        {/* Module Checkbox Grid */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
              Active Dashboard Modules ({selectedTabs.length} of {ALL_MODULES.length} enabled)
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setSelectedTabs(ALL_MODULES.map((m) => m.id))}
                className="text-[10px] text-zinc-300 hover:text-white hover:underline"
              >
                Select All
              </button>
              <span className="text-zinc-600 text-[10px]">·</span>
              <button
                type="button"
                onClick={() => setSelectedTabs(['overview', 'issues'])}
                className="text-[10px] text-zinc-400 hover:text-white hover:underline"
              >
                Minimal
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {ALL_MODULES.map((m) => {
              const isChecked = selectedTabs.includes(m.id);
              return (
                <div
                  key={m.id}
                  onClick={() => handleToggleTab(m.id)}
                  className={`p-3 rounded-lg border transition-all cursor-pointer flex items-start gap-3 ${
                    isChecked
                      ? 'bg-zinc-800/80 border-zinc-500 text-white'
                      : 'bg-[#121316] border-zinc-800 text-zinc-400 hover:border-zinc-700'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => {}}
                    className="mt-0.5 rounded bg-[#121316] border-zinc-600 text-white focus:ring-0 cursor-pointer pointer-events-none"
                  />
                  <div className="min-w-0">
                    <div className="text-xs font-bold text-white">{m.label}</div>
                    <div className="text-[10px] text-zinc-400 truncate mt-0.5">{m.desc}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-zinc-800">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-xs font-semibold text-zinc-300 transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="px-5 py-2 rounded-lg bg-white hover:bg-zinc-200 text-zinc-950 text-xs font-bold transition-colors cursor-pointer"
          >
            Save Workspace Preferences
          </button>
        </div>
      </div>
    </div>
  );
}
